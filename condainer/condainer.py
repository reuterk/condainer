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


def cfg_write(cfg):
    """Write config dictionary to YAML.
    """
    with open('condainer.yml', 'w') as fp:
        fp.write("# Condainer project configuration file,\n")
        fp.write("# initially created by `condainer init`,\n")
        fp.write("# can be edited if necessary.\n")
        fp.write("#\n")
        fp.write(yaml.safe_dump(cfg))


def cfg_read():
    """Read config dictionary from YAML.
    """
    with open('condainer.yml', 'r') as fp:
        cfg = yaml.safe_load(fp)
    return cfg


def is_mounted():
    """Return True if the container is mounted at its respective mountpoint, False otherwise.
    """
    cfg = cfg_read()
    env_directory = os.path.join(cfg['mount_base_directory'], "condainer-"+cfg['uuid'])
    q = False
    with open('/proc/mounts', 'r') as fp:
        for raw in fp:
            line = raw.split()
            if (line[1] == env_directory):
                q = True
                break
    return q


def create_environment():
    """Create base Miniforge/Mambaforge environment.
    """
    cfg = cfg_read()
    conda_installer = os.path.basename(cfg['mamba_installer_url'])

    env_directory = os.path.join(cfg['mount_base_directory'], "condainer-"+cfg['uuid'])
    os.makedirs(env_directory)

    cmd = f"bash {conda_installer} -b -f -p {env_directory}".split()
    proc = subprocess.Popen(cmd, shell=False)
    proc.communicate()
    assert(proc.returncode == 0)


def update_environment():
    """Install user-defined software stack (environment.yml) into base environment.
    """
    cfg = cfg_read()

    env_directory = os.path.join(cfg['mount_base_directory'], "condainer-"+cfg['uuid'])
    mamba_exe = os.path.join(os.path.join(env_directory, 'bin'), 'mamba')
    environment_yml = cfg["environment_yml"]

    cmd = f"{mamba_exe} env update --name=base --file={environment_yml}".split()
    proc = subprocess.Popen(cmd, shell=False)
    proc.communicate()
    assert(proc.returncode == 0)


def clean_environment():
    """Delete pkg files and other unnecessary files from base environment.
    """
    cfg = cfg_read()

    env_directory = os.path.join(cfg['mount_base_directory'], "condainer-"+cfg['uuid'])
    mamba_exe = os.path.join(os.path.join(env_directory, 'bin'), 'mamba')

    cmd = f"{mamba_exe} clean --all --yes".split()
    proc = subprocess.Popen(cmd, shell=False)
    proc.communicate()
    assert(proc.returncode == 0)


def compress_environment():
    """Create squashfs image from base environment, delete base environment directory afterwards.
    """
    cfg = cfg_read()
    env_directory = os.path.join(cfg['mount_base_directory'], "condainer-"+cfg['uuid'])
    squashfs_image = cfg['uuid']+".squashfs"

    cmd = f"mksquashfs {env_directory}/ {squashfs_image} -noappend".split()
    proc = subprocess.Popen(cmd, shell=False)
    proc.communicate()
    assert(proc.returncode == 0)

    shutil.rmtree(env_directory)


def run_cmd(args):
    """Run command in a sub-process, where PATH is prepended with the 'bin' directory of the container.
    """
    cfg = cfg_read()
    env_directory = os.path.join(cfg['mount_base_directory'], "condainer-"+cfg['uuid'])
    bin_directory = os.path.join(env_directory, 'bin')
    env = copy.deepcopy(os.environ)
    env['PATH'] = bin_directory + ':' + env['PATH']
    proc = subprocess.Popen(args.command, env=env, shell=False)
    proc.communicate()


# --- condainer entry point functions ---


def init(args):
    """Initialize directory with a usable configuration skeleton.
    """
    cfg = {}
    cfg['environment_yml'] = 'environment.yml'
    cfg['uuid'] = str(uuid.uuid4())
    cfg['mount_base_directory'] = '/tmp'
    cfg['mamba_installer_url'] = 'https://github.com/conda-forge/miniforge/releases/latest/download/Mambaforge-Linux-x86_64.sh'

    condainer_yml = "condainer.yml"
    if not os.path.isfile(condainer_yml):
        cfg_write(cfg)
    else:
        print(f"STOP. Found existing file {condainer_yml}, please run `init` from an empty directory.")
        sys.exit(1)

    conda_installer = os.path.basename(cfg['mamba_installer_url'])
    if not os.path.isfile(conda_installer):
        if not args.quiet:
            print("Downloading Mamba installer ...")
        cmd = f"curl -JLO {cfg['mamba_installer_url']}".split()
        proc = subprocess.Popen(cmd, shell=False)
        proc.communicate()
        assert(proc.returncode == 0)
    else:
        if not args.quiet:
            print(f"Found existing {conda_installer}, skipping download.")


def build(args):
    """Create conda environment and create compressed squashfs image from it.
    """
    cfg = cfg_read()
    squashfs_image = cfg['uuid']+".squashfs"
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
        cfg = cfg_read()
        env_directory = os.path.join(cfg['mount_base_directory'], "condainer-"+cfg['uuid'])
        os.makedirs(env_directory, exist_ok=True)
        squashfs_image = cfg['uuid']+".squashfs"
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
        cfg = cfg_read()
        env_directory = os.path.join(cfg['mount_base_directory'], "condainer-"+cfg['uuid'])
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
    cfg = cfg_read()
    env_directory = os.path.join(cfg['mount_base_directory'], "condainer-"+cfg['uuid'])
    squashfs_image = cfg['uuid']+".squashfs"
    if not args.quiet:
        print(termcol.BOLD+"Condainer status"+termcol.ENDC)
        print(f" - project directory  : {os.getcwd()}")
        print(f" - squashfs image     : {squashfs_image}")
        print(f" - fuse mount point   : {env_directory}")
        print(f" - squashfuse mounted : {is_mounted()}")


def test(args):
    """Hidden dummy function for quick testing
    """
    # print(is_mounted())
    pass
