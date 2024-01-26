"""Condainer - condainer.py

Entry point functions, and factorized building blocks implementing all functionality.
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
    """Return an example environment.yml file
    """
    raw = \
"""#
name: basic
channels:
  - conda-forge
dependencies:
  - python=3.9
  - pip
  #- numpy
"""
    return raw


def write_example_environment_yml():
    """Write minimal usable environment.yml as an example.
    """
    with open('environment.yml', 'w') as fp:
        fp.write("# Conda environment definition file\n")
        fp.write("# This file is only provided as an example, replace it with your own file!\n")
        fp.write("# Hints on editing manually are available online:\n")
        fp.write("# https://conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html#creating-an-environment-file-manually\n")
        environment_yml = get_example_environment_yml()
        fp.write(environment_yml)


def write_cfg(cfg, cfg_yml='condainer.yml'):
    """Write config dictionary to YAML.
    """
    with open(cfg_yml, 'w') as fp:
        fp.write("# Condainer project configuration file\n")
        fp.write("#\n")
        fp.write("# - initially created by `condainer init`\n")
        fp.write("# - can be edited by hand, if necessary\n")
        fp.write("# - more information at https://gitlab.mpcdf.mpg.de/mpcdf/condainer\n")
        fp.write("#\n")
        fp.write(yaml.safe_dump(cfg, sort_keys=False))


def get_cfg(cfg_yml='condainer.yml'):
    """Read a config dictionary from YAML, and return.
    """
    with open(cfg_yml, 'r') as fp:
        cfg = yaml.safe_load(fp)
    return cfg


def get_base_env_directory(cfg):
    """Determine and return the base directory of the environment (which is identical to the squashfuse mount point).
    """
    if cfg.get('multiuser_mountpoint'):
        suffix = '-' + str(os.getuid())
        # we cannot add the slurm job id because this would break compiled extensions linking back to libraries provided by condainer
        # if os.environ.get('SLURM_JOB_ID'):
        #     suffix = suffix + '-' + os.environ.get('SLURM_JOB_ID')
    else:
        suffix = ''
    return os.path.join(cfg['mount_base_directory'], "condainer-"+cfg['uuid']+suffix)


def get_user_env_directory(cfg):
    """Determine and return the directory of the nested conda environment.
    """
    return os.path.join(get_base_env_directory(cfg), "envs", cfg["user_env_name"])


def get_installer_path(cfg):
    """Return the path to the Miniforge installer, either the full path including the filename,
    or the filename alone, assuming that it has been downloaded to the Condainer project directory already.
    """
    if cfg['installer_url'].startswith('http'):
        return os.path.basename(cfg['installer_url'])
    else:
        return cfg['installer_url']


def is_mounted(cfg):
    """Return True if the container is mounted at its respective mountpoint, False otherwise.
    """
    env_directory = get_base_env_directory(cfg)
    q = False
    with open('/proc/mounts', 'r') as fp:
        for raw in fp:
            line = raw.split()
            if (line[1] == env_directory):
                q = True
                break
    return q


def get_image_filename(cfg):
    """Return image filename which is 'UUID.squashfs' by convention.
    """
    return cfg['uuid']+".squashfs"


def get_activate_cmd(cfg):
    """Return the shell command necessary to `activate` the condainer environment.
    """
    env_directory = get_base_env_directory(cfg)
    activate = os.path.join(os.path.join(env_directory, 'bin'), 'activate')
    user_env_name = cfg["user_env_name"]
    return f"source {activate} {user_env_name}"


def write_activate_script(cfg):
    """Create the `activate` script (mounting the condainer and activating the condainer env).
    """
    with open("activate", 'w') as fp:
        fp.write("# usage: source activate\n")
        fp.write("# - must be sourced from the condainer project directory\n")
        fp.write("# - only bourne shells are supported, such as bash or zsh\n")
        fp.write("cnd --quiet mount\n")
        cmd = get_activate_cmd(cfg)
        fp.write(f"{cmd}\n")
    os.chmod("activate", 0o755)


def write_deactivate_script(cfg):
    """Create the `deactivate` script (deactivating the condainer env and hinting at unmounting the condainer).
    """
    with open("deactivate", 'w') as fp:
        fp.write("# usage: source deactivate\n")
        fp.write("# - only bourne shells are supported, such as bash or zsh\n")
        cmd = "conda deactivate"
        fp.write(f"{cmd}\n")
        fp.write("[[ $- == *i* ]] && echo \"Hint: In case the environment is not activated in any other shell, please run now: cnd umount\"\n")
    os.chmod("deactivate", 0o755)


def get_lockfilename(cfg):
    """Return lock file name unique to the present project and host name.
    """
    return get_base_env_directory(cfg)+"-"+socket.gethostname()+".mutex"


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


def create_base_environment(cfg, args):
    """Create base environment.
    """
    conda_installer = get_installer_path(cfg)
    env_directory = get_base_env_directory(cfg)
    cmd = f"/bin/bash {conda_installer} -b -f -p {env_directory}".split()
    env = copy.deepcopy(os.environ)
    if "PYTHONPATH" in env:
        del env["PYTHONPATH"]
    if args.dryrun:
        print(f"dryrun: {' '.join(cmd)}")
    else:
        proc = subprocess.Popen(cmd, shell=False, env=env)
        proc.communicate()
        assert(proc.returncode == 0)
        condarc = {}
        condarc["envs_dirs"] = [os.path.join(env_directory, 'envs'),]
        condarc_yml = os.path.join(env_directory, '.condarc')
        with open(condarc_yml, 'w') as fp:
            fp.write(yaml.safe_dump(condarc))


def create_condainer_environment(cfg, args):
    """Install user-defined software stack (environment.yml) into 'condainer' environment.
    """
    env_directory = get_base_env_directory(cfg)
    exe = os.path.join(os.path.join(env_directory, 'bin'), cfg['conda_exe'])
    environment_yml = cfg["environment_yml"]
    environment_cfg = get_cfg(environment_yml)
    user_env_name = environment_cfg.get("name", "env") + "@condainer"
    cmd = f"{exe} env create --file {environment_yml} --name {user_env_name}".split()
    cfg["user_env_name"] = user_env_name
    env = copy.deepcopy(os.environ)
    if "PYTHONPATH" in env:
        del env["PYTHONPATH"]
    if args.dryrun:
        print(f"dryrun: {' '.join(cmd)}")
        write_cfg(cfg)
    else:
        proc = subprocess.Popen(cmd, shell=False, env=env)
        proc.communicate()
        assert(proc.returncode == 0)
        cfg["user_env_name"] = user_env_name
        write_cfg(cfg)


def pip_condainer_environment(cfg, args):
    """Install user-defined software stack (requirements.txt) into 'condainer' environment.
    """
    exe = os.path.join(get_user_env_directory(cfg), 'bin', 'pip3')
    requirements_txt = cfg["requirements_txt"]
    if os.path.isfile(requirements_txt):
        cmd = f"{exe} install --requirement {requirements_txt} --no-cache-dir".split()
        env = copy.deepcopy(os.environ)
        if "PYTHONPATH" in env:
            del env["PYTHONPATH"]
        if args.dryrun:
            print(f"dryrun: {' '.join(cmd)}")
        else:
            proc = subprocess.Popen(cmd, shell=False, env=env)
            proc.communicate()
            assert(proc.returncode == 0)
    else:
        if not args.quiet:
            print(f"{requirements_txt} not found, skipping pip")


def clean_environment(cfg, args):
    """Delete pkg files and other unnecessary files from base environment.
    """
    env_directory = get_base_env_directory(cfg)
    exe = os.path.join(os.path.join(env_directory, 'bin'), cfg['conda_exe'])
    cmd = f"{exe} clean --all --yes".split()
    env = copy.deepcopy(os.environ)
    if "PYTHONPATH" in env:
        del env["PYTHONPATH"]
    if args.dryrun:
        print(f"dryrun: {' '.join(cmd)}")
    else:
        proc = subprocess.Popen(cmd, shell=False, env=env)
        proc.communicate()
        assert(proc.returncode == 0)


def get_squashfs_num_threads():
    """Determine and return the number of threads to be used for `mksquashfs`
    """
    # on large shared login nodes, we need to limit the number of threads, 16 seems reasonable as of now
    n_threads_limit = 16
    # get the number of vcores that is actually available to the process
    n_cores = len(os.sched_getaffinity(0))
    if n_cores > n_threads_limit:
        n_cores = n_threads_limit
    return n_cores


def compress_environment(cfg, args, read_only_flags=True):
    """Create squashfs image from base environment.
    """
    env_directory = get_base_env_directory(cfg)
    # explicitly set read-only flags before compressing
    if read_only_flags:
        cmd = f"chmod -R a-w {env_directory}".split()
        if args.dryrun:
            print(f"dryrun: {' '.join(cmd)}")
        else:
            proc = subprocess.Popen(cmd, shell=False)
            proc.communicate()
            # assert(proc.returncode == 0)
    # compress files into image
    squashfs_image = get_image_filename(cfg)
    num_threads = get_squashfs_num_threads()
    cmd = f"mksquashfs {env_directory}/ {squashfs_image} -noappend -processors {num_threads}".split()
    if args.dryrun:
        print(f"dryrun: {' '.join(cmd)}")
    else:
        proc = subprocess.Popen(cmd, shell=False)
        proc.communicate()
        assert(proc.returncode == 0)
    # restore permissions, allowing to delete the staging directory later
    if read_only_flags:
        cmd = f"chmod -R u+w {env_directory}".split()
        if args.dryrun:
            print(f"dryrun: {' '.join(cmd)}")
        else:
            proc = subprocess.Popen(cmd, shell=False)
            proc.communicate()
            # assert(proc.returncode == 0)


def run_cmd(args, cwd):
    """Run command in a sub-process, where PATH is prepended with the 'bin' directory of the 'condainer' environment in the container.
    """
    cfg = get_cfg()
    if cfg.get('non_conda_application'):
        bin_directory = os.path.join(get_base_env_directory(cfg), 'bin')
    else:
        bin_directory = os.path.join(get_user_env_directory(cfg), 'bin')
    env = copy.deepcopy(os.environ)
    env['PATH'] = bin_directory + ':' + env['PATH']
    if args.dryrun:
        print(f"dryrun: {bin_directory}:{args.command}")
    else:
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
    # --- base settings ---
    cfg['mount_base_directory'] = '/tmp'
    cfg['uuid'] = str(uuid.uuid4())
    # --- conda-related settings ---
    cfg['environment_yml'] = 'environment.yml'
    cfg["requirements_txt"] = 'requirements.txt'
    cfg['installer_url'] = installer_url
    cfg['conda_exe'] = 'mamba'
    # Advanced: non-conda application, e.g. Matlab, default False ---
    # cfg['non_conda_application'] = args.non_conda_application
    # The following flag can be added later to the config file, e.g. when building and compressing via the OBS
    # For some applications, this would work (Matlab), for others not (Conda):
    #cfg['multiuser_mountpoint'] = False

    condainer_yml = "condainer.yml"
    if not os.path.isfile(condainer_yml):
        if not args.dryrun:
            write_cfg(cfg)
    else:
        print(f"STOP. Found existing file {condainer_yml}, please run `init` from an empty directory.")
        sys.exit(1)

    if not cfg.get('non_conda_application'):
        if cfg['installer_url'].startswith('http'):
            conda_installer = os.path.basename(cfg['installer_url'])
            if not os.path.isfile(conda_installer):
                if not args.quiet:
                    print("Downloading conda installer ...")
                cmd = f"curl -JLO {cfg['installer_url']}".split()
                if args.dryrun:
                    print(f"dryrun: {' '.join(cmd)}")
                else:
                    proc = subprocess.Popen(cmd, shell=False)
                    proc.communicate()
                    assert(proc.returncode == 0)
            else:
                if not args.quiet:
                    print(f"found existing installer {conda_installer}, skipping download")
        else:
            if not args.quiet:
                print(f"using installer {cfg['installer_url']}")
            assert(os.path.isfile(cfg['installer_url']))

        if not args.dryrun:
            write_example_environment_yml()
    else:
        env_directory = get_base_env_directory(cfg)
        os.makedirs(env_directory, exist_ok=True, mode=0o700)
        print(env_directory)


def build(args):
    """Create conda environment and create compressed squashfs image from it.
    """
    cfg = get_cfg()
    squashfs_image = get_image_filename(cfg)
    env_directory = get_base_env_directory(cfg)
    if os.path.isfile(squashfs_image):
        print(f"STOP. Found existing image file {squashfs_image}, please remove this first.")
        sys.exit(1)
    elif is_mounted(cfg):
        print(f"STOP. Mount point {env_directory} is in use, please unmount first.")
        sys.exit(1)
    else:
        steps = {int(i) for i in args.steps.split(',')}
        try:
            if not args.quiet:
                print(termcol.BOLD+"Starting Condainer build process ..."+termcol.ENDC)
                print("By continuing you accept the BSD-3-Clause license of the Miniforge installer,")
                print("see https://github.com/conda-forge/miniforge for details.")
            if not args.dryrun:
                os.makedirs(env_directory, exist_ok=True, mode=0o700)
            if (1 in steps) and (not cfg.get('non_conda_application')):
                if not args.quiet:
                    print(termcol.BOLD+termcol.CYAN+"1) Creating \"base\" environment ..."+termcol.ENDC)
                create_base_environment(cfg, args)
            if (2 in steps) and (not cfg.get('non_conda_application')):
                if not args.quiet:
                    print(termcol.BOLD+termcol.CYAN+f"2) Creating \"condainer\" environment from {cfg['environment_yml']} ..."+termcol.ENDC)
                create_condainer_environment(cfg, args)
            if (3 in steps) and (not cfg.get('non_conda_application')):
                if not args.quiet:
                    print(termcol.BOLD+termcol.CYAN+f"3) Adding packages from {cfg['requirements_txt']} via pip ..."+termcol.ENDC)
                pip_condainer_environment(cfg, args)
            if (4 in steps) and (not cfg.get('non_conda_application')):
                if not args.quiet:
                    print(termcol.BOLD+termcol.CYAN+"4) Cleaning environments from unnecessary files ..."+termcol.ENDC)
                clean_environment(cfg, args)
            if 5 in steps:
                if not args.quiet:
                    print(termcol.BOLD+termcol.CYAN+"5) Compressing installation directory into SquashFS image ..."+termcol.ENDC)
                compress_environment(cfg, args)
            if (6 in steps) and (not cfg.get('non_conda_application')):
                if not args.quiet:
                    print(termcol.BOLD+termcol.CYAN+"6) Creating activate and deactivate scripts ..."+termcol.ENDC)
                if args.dryrun:
                    print("dryrun: skipping")
                else:
                    write_activate_script(cfg)
                    write_deactivate_script(cfg)
        except:
            raise
        finally:
            if 7 in steps:
                if not args.quiet:
                    print(termcol.BOLD+termcol.CYAN+"7) Cleaning up ..."+termcol.ENDC)
                if args.dryrun:
                    print("dryrun: skipping")
                else:
                    shutil.rmtree(env_directory)
            if not args.quiet:
                print(termcol.BOLD+"Done!"+termcol.ENDC)


def mount(args):
    """Mount squashfs image, skip if already mounted.
    """
    cfg = get_cfg()
    if cfg.get('multiuser_mountpoint'):
        assert(cfg.get('non_conda_application') == True)
    if is_mounted(cfg):
        if not args.quiet:
            print("hint: condainer already mounted")
    else:
        env_directory = get_base_env_directory(cfg)
        os.makedirs(env_directory, exist_ok=True, mode=0o700)
        squashfs_image = get_image_filename(cfg)
        cmd = f"squashfuse {squashfs_image} {env_directory}".split()
        if args.dryrun:
            print(f"dryrun: {' '.join(cmd)}")
        else:
            proc = subprocess.Popen(cmd, shell=False)
            proc.communicate()
            assert(proc.returncode == 0)
        if (not args.quiet) and (not cfg.get('non_conda_application')):
            activate = get_activate_cmd(cfg)
            print(termcol.BOLD+"Environment usage in the present shell"+termcol.ENDC)
            print( " - enable command  : "+termcol.BOLD+termcol.CYAN+f"{activate}"+termcol.ENDC)
            print( " - disable command : "+termcol.BOLD+termcol.RED+f"conda deactivate"+termcol.ENDC)
            # print(termcol.BOLD+"OK"+termcol.ENDC)
    # print feature necessary for the dynamic mount directory feature within the activate script
    if args.print:
        print(get_base_env_directory(cfg))


def umount(args):
    """Unmount squashfs image, skip if already unmounted.
    """
    cfg = get_cfg()
    if is_mounted(cfg):
        env_directory = get_base_env_directory(cfg)
        cmd = f"fusermount -u {env_directory}".split()
        if args.dryrun:
            print(f"dryrun: {' '.join(cmd)}")
        else:
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
    """Run command within container, set quiet mode for minimal interference with the command output.
    """
    cfg = get_cfg()
    lock = acquire_lock(get_lockfilename(cfg))
    if lock:
        try:
            args.quiet = True
            args.print = False
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
    """Print status of the present Condainer project directory.
    """
    cfg = get_cfg()
    print(termcol.BOLD+"Condainer status"+termcol.ENDC)
    print(f" - project directory : {os.getcwd()}")
    print(f" - squashfs image    : {get_image_filename(cfg)}")
    print(f" - fuse mount point  : {get_base_env_directory(cfg)}")
    print(f" - image mounted     : {is_mounted(cfg)}")


def cache(args):
    """Read squashfs image file once to motivate the OS to cache it.
    """
    cfg = get_cfg()
    squashfs_image = get_image_filename(cfg)
    cmd = f"dd if={squashfs_image} of=/dev/null bs=1M".split()
    if args.dryrun:
        print(f"dryrun: {' '.join(cmd)}")
    else:
        proc = subprocess.Popen(cmd, shell=False)
        proc.communicate()
        assert(proc.returncode == 0)


def test(args):
    """Dummy function for quick testing
    """
    # cfg = get_cfg()
    # print(is_mounted(cfg))
    print(args)
    pass
