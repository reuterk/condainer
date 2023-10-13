import os
import sys
import argparse
import yaml
import uuid
import shutil
import subprocess


# --- condainer building blocks below ---

def cfg_write(cfg):
    with open('condainer.yml', 'w') as fp:
        fp.write("# Condainer configuration file,\n")
        fp.write("# edit manually, if necessary!\n")
        fp.write("# (initially created by `condainer init`)\n")
        fp.write("#\n")
        fp.write(yaml.safe_dump(cfg))


def cfg_read():
    with open('condainer.yml', 'r') as fp:
        cfg = yaml.safe_load(fp)
    return cfg


def create_base_installation():
    cfg = cfg_read()
    conda_installer = os.path.basename(cfg['conda_installer_url'])

    env_directory = os.path.join(cfg['mount_base_directory'], "condainer-"+cfg['uuid'])
    os.makedirs(env_directory)

    cmd = f"bash {conda_installer} -b -f -p {env_directory}".split()
    proc = subprocess.Popen(cmd, shell=False)
    proc.communicate()
    assert(proc.returncode == 0)


def update_base_installation():
    cfg = cfg_read()

    env_directory = os.path.join(cfg['mount_base_directory'], "condainer-"+cfg['uuid'])
    mamba_exe = os.path.join(os.path.join(env_directory, 'bin'), 'mamba')
    environment_yml = cfg["environment_yml"]

    cmd = f"{mamba_exe} env update --name=base --file={environment_yml}".split()
    proc = subprocess.Popen(cmd, shell=False)
    proc.communicate()
    assert(proc.returncode == 0)


def clean_base_installation():
    cfg = cfg_read()

    env_directory = os.path.join(cfg['mount_base_directory'], "condainer-"+cfg['uuid'])
    mamba_exe = os.path.join(os.path.join(env_directory, 'bin'), 'mamba')

    cmd = f"{mamba_exe} clean --all --yes".split()
    proc = subprocess.Popen(cmd, shell=False)
    proc.communicate()
    assert(proc.returncode == 0)


def compress_installation():
    cfg = cfg_read()
    env_directory = os.path.join(cfg['mount_base_directory'], "condainer-"+cfg['uuid'])
    squashfs_image = cfg['uuid']+".squashfs"

    cmd = f"mksquashfs {env_directory}/ {squashfs_image} -noappend".split()
    proc = subprocess.Popen(cmd, shell=False)
    proc.communicate()
    assert(proc.returncode == 0)

    shutil.rmtree(env_directory)


# --- entry point functions below ---


def condainer_init(args):
    """Initialize directory with a configuration skeleton.
    """
    cfg = {}
    cfg['label'] = 'my compressed environment'
    cfg['environment_yml'] = 'environment.yml'
    cfg['uuid'] = str(uuid.uuid4())
    cfg['mount_base_directory'] = '/tmp'
    cfg['conda_installer_url'] = 'https://github.com/conda-forge/miniforge/releases/latest/download/Mambaforge-Linux-x86_64.sh'

    conda_installer = os.path.basename(cfg['conda_installer_url'])
    if not os.path.isfile(conda_installer):
        if not args.quiet:
            print("Downloading conda installer ...")
        cmd = f"curl -JLO {cfg['conda_installer_url']}".split()
        proc = subprocess.Popen(cmd, shell=False)
        proc.communicate()
        assert(proc.returncode == 0)
    else:
        if not args.quiet:
            print(f"Found existing {conda_installer}, skipping download.")

    cfg_write(cfg)


def condainer_build(args):
    """Create conda environment, create compressed squashfs image from it.
    """
    create_base_installation()
    update_base_installation()
    clean_base_installation()
    compress_installation()


def condainer_mount(args):
    """Mount squashfs image.
    """
    cfg = cfg_read()
    env_directory = os.path.join(cfg['mount_base_directory'], "condainer-"+cfg['uuid'])
    os.makedirs(env_directory, exist_ok=True)

    squashfs_image = cfg['uuid']+".squashfs"

    cmd = f"squashfuse {squashfs_image} {env_directory}".split()
    proc = subprocess.Popen(cmd, shell=False)
    proc.communicate()
    assert(proc.returncode == 0)

    env_label = cfg['label']

    activate = os.path.join(os.path.join(env_directory, 'bin'), 'activate')
    if not args.quiet:
        print(f"Condainer mounted successfully:")
        print()
        print(f"   * squashfs:    {squashfs_image}")
        print(f"   * mount point: {env_directory}")
        print(f"   * label:       {env_label}")
        print(f"   * run `source {activate}` to enable the environment in your shell")
        print(f"   * run `conda deactivate` in your shell prior to unmounting")
        print()


def condainer_umount(args):
    """Unmount squashfs image.
    """
    cfg = cfg_read()
    env_directory = os.path.join(cfg['mount_base_directory'], "condainer-"+cfg['uuid'])
    cmd = f"fusermount -u {env_directory}".split()
    proc = subprocess.Popen(cmd, shell=False)
    proc.communicate()
    assert(proc.returncode == 0)
    if not args.quiet:
        print("OK")


def condainer_prereq(args):
    """Check for the necessary tools.
    """
    for cmd in ["mksquashfs", "squashfuse", "fusermount"]:
        print(cmd, ":", shutil.which(cmd))


def condainer_args():
    """Handle command line arguments.
    """
    parser = argparse.ArgumentParser(
        prog=sys.argv[0],
        description='Create and manage conda environments based on compressed squashfs images.',
        epilog='"Do not set Anacondas free, put them into a container!" -- Old Bavarian wisdom.'
    )
    parser.add_argument('-q', '--quiet', action='store_true', help='do not write to stdout')
    subparsers = parser.add_subparsers(dest='subcommand', required=True)
    parser_init = subparsers.add_parser('init', help='initialize directory with config files')
    parser_build = subparsers.add_parser('build', help='build containerized conda environment')
    parser_mount = subparsers.add_parser('mount', help='mount containerized conda environment')
    parser_eject = subparsers.add_parser('umount', help='eject/unmount containerized conda environment')
    parser_mount = subparsers.add_parser('prereq', help='check if the necessary tools are installed')
    args = parser.parse_args()
    return args
