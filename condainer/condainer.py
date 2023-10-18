"""Condainer
This file implements the functions to be called from main.py.
"""

import os
import sys
import copy
import yaml
import uuid
import shutil
import subprocess


class termcol:
    """Some terminal color strings useful for highlighting terminal output
    """
    RED = '\033[31m'
    GREEN = '\033[32m'
    BLUE = '\033[34m'
    CYAN = '\033[36m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def write_cfg(cfg):
    """Write config dictionary to YAML.
    """
    with open('condainer.yml', 'w') as fp:
        fp.write("# Condainer project configuration file\n")
        fp.write("#\n")
        fp.write("# - initially created by `condainer init`\n")
        fp.write("# - can be edited by hand, if necessary\n")
        fp.write("# - more information at https://gitlab.mpcdf.mpg.de/khr/condainer\n")
        fp.write("#\n")
        fp.write(yaml.safe_dump(cfg, sort_keys=False))


def get_cfg():
    """Read config dictionary from YAML.
    """
    with open('condainer.yml', 'r') as fp:
        cfg = yaml.safe_load(fp)
    return cfg


def get_env_directory(cfg):
    return os.path.join(cfg['mount_base_directory'], "condainer-"+cfg['uuid'])


def is_mounted():
    """Return True if the container is mounted at its respective mountpoint, False otherwise.
    """
    cfg = get_cfg()
    env_directory = get_env_directory(cfg)
    q = False
    with open('/proc/mounts', 'r') as fp:
        for raw in fp:
            line = raw.split()
            if (line[1] == env_directory):
                q = True
                break
    return q


def create_environment():
    """Create base environment.
    """
    cfg = get_cfg()
    conda_installer = os.path.basename(cfg['installer_url'])

    env_directory = get_env_directory(cfg)
    os.makedirs(env_directory)

    cmd = f"bash {conda_installer} -b -f -p {env_directory}".split()
    proc = subprocess.Popen(cmd, shell=False)
    proc.communicate()
    assert(proc.returncode == 0)


def update_environment():
    """Install user-defined software stack (environment.yml) into base environment.
    """
    cfg = get_cfg()

    env_directory = get_env_directory(cfg)
    exe = os.path.join(os.path.join(env_directory, 'bin'), cfg['conda_exe'])
    environment_yml = cfg["environment_yml"]

    cmd = f"{exe} env update --name=base --file={environment_yml}".split()
    proc = subprocess.Popen(cmd, shell=False)
    proc.communicate()
    assert(proc.returncode == 0)


def clean_environment():
    """Delete pkg files and other unnecessary files from base environment.
    """
    cfg = get_cfg()

    env_directory = get_env_directory(cfg)
    exe = os.path.join(os.path.join(env_directory, 'bin'), cfg['conda_exe'])

    cmd = f"{exe} clean --all --yes".split()
    proc = subprocess.Popen(cmd, shell=False)
    proc.communicate()
    assert(proc.returncode == 0)


def compress_environment():
    """Create squashfs image from base environment, delete base environment directory afterwards.
    """
    cfg = get_cfg()
    env_directory = get_env_directory(cfg)
    squashfs_image = cfg['image']

    cmd = f"mksquashfs {env_directory}/ {squashfs_image} -noappend".split()
    proc = subprocess.Popen(cmd, shell=False)
    proc.communicate()
    assert(proc.returncode == 0)

    shutil.rmtree(env_directory)


def run_cmd(args):
    """Run command in a sub-process, where PATH is prepended with the 'bin' directory of the container.
    """
    cfg = get_cfg()
    env_directory = get_env_directory(cfg)
    bin_directory = os.path.join(env_directory, 'bin')
    env = copy.deepcopy(os.environ)
    env['PATH'] = bin_directory + ':' + env['PATH']
    proc = subprocess.Popen(args.command, env=env, shell=False)
    proc.communicate()


# --- condainer entry point functions below ---


def init(args):
    """Initialize directory with a usable configuration skeleton.
    """
    # prioritize a locally provided installer, if available, expecting a full path
    www_installer_url = 'https://github.com/conda-forge/miniforge/releases/latest/download/Mambaforge-Linux-x86_64.sh'
    installer_url = os.environ.get('CONDAINER_INSTALLER')
    if not installer_url:
        installer_url = www_installer_url

    cfg = {}
    cfg['environment_yml'] = 'environment.yml'
    cfg['installer_url'] = installer_url
    cfg['conda_exe'] = 'mamba'
    cfg['mount_base_directory'] = '/tmp'
    cfg['uuid'] = str(uuid.uuid4())
    cfg['image'] = cfg['uuid']+".squashfs"

    condainer_yml = "condainer.yml"
    if not os.path.isfile(condainer_yml):
        write_cfg(cfg)
    else:
        print(f"STOP. Found existing file {condainer_yml}, please run `init` from an empty directory.")
        sys.exit(1)

    if cfg['installer_url'].startswith('http'):
        conda_installer = os.path.basename(cfg['installer_url'])
        if not os.path.isfile(conda_installer):
            if not args.quiet:
                print("Downloading conda installer ...")
            cmd = f"curl -JLO {cfg['installer_url']}".split()
            proc = subprocess.Popen(cmd, shell=False)
            proc.communicate()
            assert(proc.returncode == 0)
        else:
            if not args.quiet:
                print(f"Found existing {conda_installer}, skipping download.")
    else:
        if not args.quiet:
            print(f"Using {cfg['installer_url']}")
        assert(os.path.isfile(cfg['installer_url']))


def build(args):
    """Create conda environment and create compressed squashfs image from it.
    """
    cfg = get_cfg()
    squashfs_image = cfg['image']
    if os.path.isfile(squashfs_image):
        print(f"STOP. Found existing image file {squashfs_image}, please remove this first.")
        sys.exit(1)
    else:
        create_environment()
        update_environment()
        clean_environment()
        compress_environment()


def mount(args):
    """Mount squashfs image, skip if already mounted.
    """
    if is_mounted():
        if not args.quiet:
            print("condainer already mounted, skipping")
    else:
        cfg = get_cfg()
        env_directory = get_env_directory(cfg)
        os.makedirs(env_directory, exist_ok=True)
        squashfs_image = cfg['image']
        cmd = f"squashfuse {squashfs_image} {env_directory}".split()
        proc = subprocess.Popen(cmd, shell=False)
        proc.communicate()
        assert(proc.returncode == 0)
        if not args.quiet:
            activate = os.path.join(os.path.join(env_directory, 'bin'), 'activate')
            print(termcol.BOLD+"Environment usage in the present shell"+termcol.ENDC)
            print( " - enable command  : "+termcol.CYAN+f"source {activate}"+termcol.ENDC)
            print( " - disable command : "+termcol.RED+f"conda deactivate"+termcol.ENDC)
            # print(termcol.BOLD+"OK"+termcol.ENDC)


def umount(args):
    """Unmount squashfs image, skip if already unmounted.
    """
    if is_mounted():
        cfg = get_cfg()
        env_directory = get_env_directory(cfg)
        cmd = f"fusermount -u {env_directory}".split()
        proc = subprocess.Popen(cmd, shell=False)
        proc.communicate()
        assert(proc.returncode == 0)
        shutil.rmtree(env_directory)
        if not args.quiet:
            # print(termcol.BOLD+"OK"+termcol.ENDC)
            pass
    else:
        if not args.quiet:
            print("condainer already unmounted, skipping")


def exec(args):
    """Run command within container, set quiet mode for minimal inference with the command output.
    """
    args.quiet = True
    mount(args)
    run_cmd(args)
    umount(args)


def prereq(args):
    """Check if the necessary tools are locally available.
    """
    for cmd in ["curl", "mksquashfs", "squashfuse", "fusermount"]:
        print(cmd, ":", shutil.which(cmd))


def status(args):
    """Print status of the present Condainer.
    """
    cfg = get_cfg()
    env_directory = get_env_directory(cfg)
    squashfs_image = cfg['image']
    if not args.quiet:
        print(termcol.BOLD+"Condainer status"+termcol.ENDC)
        print(f" - project directory  : {os.getcwd()}")
        print(f" - squashfs image     : {squashfs_image}")
        print(f" - fuse mount point   : {env_directory}")
        print(f" - squashfuse mounted : {is_mounted()}")


def test(args):
    """Dummy function for quick testing
    """
    cfg = get_cfg()
    # print(is_mounted())
    pass
