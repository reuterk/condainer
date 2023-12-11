# Condainer - Compressed Conda environments for HPC systems

## TL;DR - Quick start guide

Condainer puts Conda environments into compressed (squashfs) images which makes
the use of such environments portable and more efficient, in particular on HPC
systems. These Condainer environments are standalone, and sidestep the typical
integration of a specific `conda` executable into the user's `.bashrc` file
completely, which often causes issues, for example with the software environment
on HPC systems.

### Build a compressed environment

Starting in an empty directory, use the following commands once to build a
compressed image of your Conda environment that is defined in 'environment.yml':

```bash
cnd init
ls
# edit the example 'environment.yml' file, or copy your own file here, before running
cnd build
ls
```

### Activate a compressed environment

After building successfully you can activate the environment for your current
shell session, sililar to plain Conda or to a Python virtual environment:

```bash
source activate
```

Please note that `source activate` will only work with bourne shells (e.g.
`bash` or `zsh`), not with the older C shells and korn shells.

### Alternatively, run an executable from a compressed environment directly

In case you do not want to activate the environment, you can run individual executables from the environment transparently, e.g.

```bash
cnd exec -- python3
```

See the sections below for more detailed explanations and more options.

## Background

### Often a Problem: Conda environments on HPC file systems

The Conda package manager and the related workflows have become an adopted
standard when it comes to distributing scientific software for easy installation
by end users. Using `conda`, complex software environments can be defined by
means of simple descriptive `environment.yml` files. On MPCDF systems, users
may use Conda environments, but without support from MPCDF for the software therein.

Once installed, large Conda environments can easily amount to several 100k
individual (small) files. On a local file system of a laptop or PC this is
typically not an issue.  However, in particular on the large shared parallel
file systems of HPC systems the vast amount of small files can cause issues as
these filesystems are optimized for different scenarios. Inode exhaustion and
heavy load due to (millions of) file opens, short reads, and closes happening
during the startup phase of Python jobs from the different users on the system
are only two examples.

### Solution: Move Conda environments into compressed image files

Condainer adresses these issues by moving Conda
environments into compressed squashfs images, reducing the number of files
stored directly on the host file system by orders of magnitude.  Condainer
images are standalone and portable: They can be copied between different
systems, improving reproducibility and reusability of proven-to-work software
environments.  In particular, they sidestep the integration of a specific
`conda` executable into the user's `.bashrc` file, which often causes issues and
is orthogonal to the module-based software environments provided on HPC systems.

Technically, Condainer uses a Python basis from Miniforge (which is a free
alternative similar to Miniconda) and then installs the user-defined software
stack from the usual `environment.yml` file.  Package resolution and
installation are extremely fast thanks to the `mamba` package manager (an
optimized replacement for `conda`).  As a second step, Condainer creates a
compressed squashfs image file from the staging installation, before it deletes
the latter to save disk space. Subsequently, the compressed image is mounted (using
`squashfuse`) at the very same directory, providing the full Conda environment
to the user who can `activate` or `deactivate` it, just as usual. Moreover,
Condainer provides functionality to run executables from the Conda environment
directly and transparently, without the need to explicitly mount and unmount the
image.

Please note that the squashfs images used by Condainer are not "containers" in
the strict terminology of Docker, Apptainer, or alike. With Condainer, there is no
process isolation or similar, rather Condainer is an easy-to-use and highly
efficient wrapper around the building, compressing, mounting, and unmounting of
Conda environments on top of compressed image files.
In the following, the basic usage is outlined.

## Installation

After cloning the repository, Condainer can be installed via `pip``, e.g. using the command

`pip install --user .`

which would place the executable `cnd` into `~/.local/bin` in the user's homedirectory.

## Usage

The Condainer executable is `cnd` and is controlled via subcommands and flags.
See `cnd --help` for full details. The following subcommands are available for `cnd`
and are described briefly below.

### Initialize a project using `cnd init`

Create an empty directory, enter it, and run `cnd init` to create a skeleton for
a Condainer project. Optionally, you may inspect and edit the config file
`condainer.yml`. Importantly, add your `environment.yml` file to the same
directory.

### Build and compress an environment using `cnd build`

Build the Conda environment specified in `environment.yml`.  In case a file
`requirements.txt` is present, its contents will be installed in addition using
`pip`.  Finally, create a compressed squashfs image, and delete the files from
the staging process.

To stage the files for the Conda environment, a uniquely named directory below
the base directory (as specified in `condainer.yml`) is used.  By default, the base
directory is `/tmp`.  The unique subdirectory name is of the form `condainer-UUID`
where UUID is a type4 UUID generated and saved during `cnd init`.

### Execute a command using `cnd exec`

Using a command of the form `cnd exec -- python3 myscript.py`
it is possible to run executables from the compressed Conda
environment directly, in the present example the Python interpreter
`python3`.  Mounting and unmounting of the squashfs image are
handled automatically and invisibly to the user.  Note that the '--'
is a necessary separator to be able to pass arguments and flags to
the executable.  It can be omitted in case there are no arguments or
flags.

### Activate the environment

In the project directory, run `source activate` to activate the
compressed environment for your current shell session.  Similarly,
run `source deactivate` to deactivate it.
Once activated, the compressed environment is available just like
normal, however, in read-only mode.

### Explicitly mount the squashfs image using `cnd mount`

The command `cnd mount` mounts the squashfs image below the base directory that
is specified in `condainer.yml`.  Hints on activating and deactivating the Conda
environment are printed.

Consistent with the `cnd build` step, the mount point is identical to the
directory used during staging and building, such that the absolute paths to the
files are unchanged between build and mount.

### Explicitly unmount the squashfs image using `cnd umount`

Unmount the image, if mounted.

Make sure to run `conda deactivate`
in all relevant shell sessions prior to unmounting.

### Print information using `cnd status`

Show some information and the mount status of the image.

### Check if the necessary tools are available using `cnd prereq`

Check and show if the required software is locally available (see below).

## System requirements

Condainer works on any recent Linux system and expects the following set
of tools available and enabled for non-privileged users:

* fuse
* squashfuse
* squashfs tools

On an Ubuntu (or similar) system, run the command

`sudo apt install squashfs-tools squashfuse`

to install the necessary tools. In addition `curl` is required to download
the Miniforge installer, in case it is not available locally.

## Environment variables

The environment variable `CONDAINER_INSTALLER` allows to specify the full file
path to a Miniforge installer, e.g. to provide it centrally on a cluster.
No installer is downloaded in case that variable is defined.

## Features and Limitations

* Any valid `environment.yml` will work with Condainer, there is no lock-in when using Condainer, as you can use the same `environment.yml` with plain Conda elsewhere.
* Condainer environments are read-only and immutable. In case you need to add packages, rebuild the image.
* Within the same project, when experimenting, you can toggle between multiple existing squashfs images by editing the UUID string in `condainer.yml`.

## Source Code and Contact

Condainer is available under the MIT license at <https://gitlab.mpcdf.mpg.de/mpcdf/condainer> or <https://github.com/reuterk/condainer>.

Copyright © 2023- Klaus Reuter <klaus.reuter@mpcdf.mpg.de>, Max Planck Computing and Data Facility
