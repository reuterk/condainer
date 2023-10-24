"""Condainer
This file implements the functions to be called from main.py.
"""

import os
import sys
import copy
import yaml
import uuid
import fcntl
import shutil
import socket
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


def get_example_environment_yml():
    raw = \
"""
name: basicnumpy
channels:
  - conda-forge
dependencies:
  - python=3.9
  - numpy
"""
    return yaml.safe_load(raw)


def write_example_environment_yml():
    """Write minimal usable environment.yml as an example.
    """
    with open('environment.yml', 'w') as fp:
        fp.write("# Conda environment definition file\n")
        fp.write("# This file is only provided as an example, replace it with your own file!\n")
        fp.write("# Hints on editing manually are available online:\n")
        fp.write("# https://conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html#creating-an-environment-file-manually\n")
        fp.write("#\n")
        environment_yml = get_example_environment_yml()
        fp.write(yaml.safe_dump(environment_yml, sort_keys=False))


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


def get_installer_path(cfg):
    if cfg['installer_url'].startswith('http'):
        return os.path.basename(cfg['installer_url'])
    else:
        return cfg['installer_url']


def is_mounted(cfg):
    """Return True if the container is mounted at its respective mountpoint, False otherwise.
    """
    env_directory = get_env_directory(cfg)
    q = False
    with open('/proc/mounts', 'r') as fp:
        for raw in fp:
            line = raw.split()
            if (line[1] == env_directory):
                q = True
                break
    return q


def get_image_filename(cfg):
    """Return image filename which is UUID.squashfs by convention.
    """
    return cfg['uuid']+".squashfs"


def get_activate_cmd(cfg):
    env_directory = get_env_directory(cfg)
    activate = os.path.join(os.path.join(env_directory, 'bin'), 'activate')
    return f"source {activate} condainer"


def write_activate_script(cfg):
    with open("activate", 'w') as fp:
        fp.write("# usage: source activate\n")
        fp.write("# (must be sourced from the condainer project directory)\n")
        fp.write("cnd --quiet mount\n")
        cmd = get_activate_cmd(cfg)
        fp.write(f"{cmd}\n")
    os.chmod("activate", 0o755)


def write_deactivate_script(cfg):
    with open("deactivate", 'w') as fp:
        fp.write("# usage: source deactivate\n")
        cmd = "conda deactivate"
        fp.write(f"{cmd}\n")
        fp.write("echo \"Hint: Run  cnd umount  now in case the environment is not activated in any other shell.\"\n")
    os.chmod("deactivate", 0o755)


def get_lockfilename(cfg):
    """Return lock file name unique to the present project and host name.
    """
    return get_env_directory(cfg)+"-"+socket.gethostname()+".mutex"


def acquire_lock(lock_file):
    """Try to acquire a file-based mutex and return its file handle, or None.
    """
    try:
        lock_fh = open(lock_file, 'w')
        fcntl.flock(lock_fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return lock_fh
    except BlockingIOError:
        return None


def release_lock(lock_fh):
    """Release mutex, unlink lock file.
    """
    if lock_fh:
        fcntl.flock(lock_fh, fcntl.LOCK_UN)
        os.unlink(lock_fh.name)
        lock_fh.close()


def create_base_environment(cfg):
    """Create base environment.
    """
    conda_installer = get_installer_path(cfg)
    env_directory = get_env_directory(cfg)
    cmd = f"bash {conda_installer} -b -f -p {env_directory}".split()
    env = copy.deepcopy(os.environ)
    if "PYTHONPATH" in env:
        del env["PYTHONPATH"]
    proc = subprocess.Popen(cmd, shell=False, env=env)
    proc.communicate()
    assert(proc.returncode == 0)


def create_condainer_environment(cfg):
    """Install user-defined software stack (environment.yml) into 'condainer' environment.
    """
    env_directory = get_env_directory(cfg)
    exe = os.path.join(os.path.join(env_directory, 'bin'), cfg['conda_exe'])
    environment_yml = cfg["environment_yml"]
    cmd = f"{exe} env create --file {environment_yml} --name condainer".split()
    proc = subprocess.Popen(cmd, shell=False)
    proc.communicate()
    assert(proc.returncode == 0)


def clean_environment(cfg):
    """Delete pkg files and other unnecessary files from base environment.
    """
    env_directory = get_env_directory(cfg)
    exe = os.path.join(os.path.join(env_directory, 'bin'), cfg['conda_exe'])
    cmd = f"{exe} clean --all --yes".split()
    proc = subprocess.Popen(cmd, shell=False)
    proc.communicate()
    assert(proc.returncode == 0)


def compress_environment(cfg):
    """Create squashfs image from base environment.
    """
    env_directory = get_env_directory(cfg)
    squashfs_image = get_image_filename(cfg)
    cmd = f"mksquashfs {env_directory}/ {squashfs_image} -noappend".split()
    proc = subprocess.Popen(cmd, shell=False)
    proc.communicate()
    assert(proc.returncode == 0)


def run_cmd(args, cwd):
    """Run command in a sub-process, where PATH is prepended with the 'bin' directory of the 'condainer' environment in the container.
    """
    cfg = get_cfg()
    env_directory = get_env_directory(cfg)
    bin_directory = os.path.join(env_directory, 'envs', 'condainer', 'bin')
    env = copy.deepcopy(os.environ)
    env['PATH'] = bin_directory + ':' + env['PATH']
    proc = subprocess.Popen(args.command, cwd=cwd, env=env, shell=False)
    proc.communicate()


# --- condainer entry point functions below ---


def init(args):
    """Initialize directory with a usable configuration skeleton.
    """
    # prioritize a locally provided installer, if available, expecting a full path
    www_installer_url = 'https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh'
    installer_url = os.environ.get('CONDAINER_INSTALLER')
    if not installer_url:
        installer_url = www_installer_url

    cfg = {}
    cfg['environment_yml'] = 'environment.yml'
    cfg['installer_url'] = installer_url
    cfg['conda_exe'] = 'mamba'
    cfg['mount_base_directory'] = '/tmp'
    cfg['uuid'] = str(uuid.uuid4())

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
                print(f"Found existing installer {conda_installer}, skipping download.")
    else:
        if not args.quiet:
            print(f"Using installer {cfg['installer_url']}")
        assert(os.path.isfile(cfg['installer_url']))

    write_example_environment_yml()


def build(args):
    """Create conda environment and create compressed squashfs image from it.
    """
    cfg = get_cfg()
    squashfs_image = get_image_filename(cfg)
    env_directory = get_env_directory(cfg)
    if os.path.isfile(squashfs_image):
        print(f"STOP. Found existing image file {squashfs_image}, please remove this first.")
        sys.exit(1)
    elif is_mounted(cfg):
        print(f"STOP. Mount point {env_directory} is in use, please unmount first.")
        sys.exit(1)
    else:
        try:
            os.makedirs(env_directory, exist_ok=True, mode=0o700)
            create_base_environment(cfg)
            create_condainer_environment(cfg)
            clean_environment(cfg)
            compress_environment(cfg)
            write_activate_script(cfg)
            write_deactivate_script(cfg)
        except:
            raise
        finally:
            shutil.rmtree(env_directory)


def mount(args):
    """Mount squashfs image, skip if already mounted.
    """
    cfg = get_cfg()
    if is_mounted(cfg):
        if not args.quiet:
            print("hint: condainer already mounted")
    else:
        env_directory = get_env_directory(cfg)
        os.makedirs(env_directory, exist_ok=True, mode=0o700)
        squashfs_image = get_image_filename(cfg)
        cmd = f"squashfuse {squashfs_image} {env_directory}".split()
        proc = subprocess.Popen(cmd, shell=False)
        proc.communicate()
        assert(proc.returncode == 0)
        if not args.quiet:
            activate = get_activate_cmd(cfg)
            print(termcol.BOLD+"Environment usage in the present shell"+termcol.ENDC)
            print( " - enable command  : "+termcol.BOLD+termcol.CYAN+f"{activate}"+termcol.ENDC)
            print( " - disable command : "+termcol.BOLD+termcol.RED+f"conda deactivate"+termcol.ENDC)
            # print(termcol.BOLD+"OK"+termcol.ENDC)


def umount(args):
    """Unmount squashfs image, skip if already unmounted.
    """
    cfg = get_cfg()
    if is_mounted(cfg):
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
            print("hint: condainer not mounted")


def exec(args, cwd):
    """Run command within container, set quiet mode for minimal inference with the command output.
    """
    cfg = get_cfg()
    lock=acquire_lock(get_lockfilename(cfg))
    if lock:
        try:
            args.quiet = True
            mount_required = not is_mounted(cfg)
            if mount_required:
                mount(args)
            run_cmd(args, cwd)
            if mount_required:
                umount(args)
        finally:
            release_lock(lock)
    else:
        print("Only one instance of `condainer exec` can be run at the same time. STOP.")
        sys.exit(1)


def prereq(args):
    """Check if the necessary tools are locally available.
    """
    print(termcol.BOLD+"Checking for local tool availability"+termcol.ENDC)
    for cmd in ["curl      ", "mksquashfs", "squashfuse", "fusermount"]:
        print(f" - {cmd} : {shutil.which(cmd.strip())}")


def status(args):
    """Print status of the present Condainer.
    """
    cfg = get_cfg()
    print(termcol.BOLD+"Condainer status"+termcol.ENDC)
    print(f" - project directory : {os.getcwd()}")
    print(f" - squashfs image    : {get_image_filename(cfg)}")
    print(f" - fuse mount point  : {get_env_directory(cfg)}")
    print(f" - image mounted     : {is_mounted(cfg)}")


def test(args):
    """Dummy function for quick testing
    """
    # cfg = get_cfg()
    # print(is_mounted(cfg))
    pass
