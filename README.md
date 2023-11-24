# Condainer - Conda environments for HPC systems

## TL;DR - Quick start guide

Condainer puts Conda environments into compressed squashfs images which makes
the use of such environments portable and more efficient, in particular on HPC systems.

### Build a compressed environment

Starting in an empty directory, use the following commands once to build a compressed image of your Conda environment, defined by 'environment.yml':

```bash
cnd init
# edit the provided example 'environment.yml' file, or copy your own file here, before running
cnd build
```

### Activate a compressed environment

After building successfully, you can activate the environment for your current shell session, just like with plain conda:

```bash
source activate
```

### Alternatively, run an executable from a compressed environment without activating it

In case you do not want to activate the environment, you can run individual executables from the environment transparently, e.g.

```bash
cnd exec -- python3
```

Please see below for more detailed explanations and more options.

## Background

### Problem: Conda environments on HPC systems

The Conda package manager and related workflows have become an
adopted standard when it comes to distributing scientific software
for easy installation by end users. It not only handles native
Python packages but also manages dependencies in the form of
binary blobs, such as third-party libraries that are provided as
shared objects. Using `conda`, complex software environments can
be defined by means of simple descriptive `environment.yml` files.

Large environments can easily amount to several 100k individual
(small) files. On a local desktop file system, this is typically not
an issue.  However, in particular on the large shared parallel file
systems of HPC systems, the vast amount of small files can cause
severe trouble as these filesystems are optimized for different IO
patterns. Inode exhaustion, and heavy load due to (millions of) file
opens, short reads, and closes during the startup phase of
(parallel) Python jobs from numerous different users on the HPC
cluster are only two examples.

### Solution: Put Conda environments into compressed image files

Condainer solves these issues by putting conda environments into
compressed squashfs images, reducing the number of files
stored directly on the host file system by orders of magnitude.
Condainer images are standalone and portable, i.e., they can be
copied between different systems, improving reproducibility
and reusability of proven working software environments.

Technically, Condainer uses the Python basis from `Miniforge`
(which is a free alternative similar to Miniconda) and installs the
software stack defined by the user via an `environment.yml` into a nested environment.
Package resolution and installation are extremely fast thanks to the
`mamba` package manager (an optimized replacement for `conda`).
As a second step, Condainer creates a compressed squashfs image file
from that installation, before it deletes the latter to save disk
space. The compressed image is then mounted at the very same
directory, providing the complete conda environment to
the user who can `activate` or `deactivate` it, just as usual. Moreover,
Condainer provides a wrapper to run executables from the
conda environment directly and transparently, without the need to
explicitly mount and unmount the image.

Please note that the squashfs images used by Condainer are not "containers"
in the strict terminology of Docker, Apptainer, etc. With Condainer,
there is no encapsulation, isolation, or similar, rather Condainer
is an easy-to-use wrapper around the building, compressing,
mounting, and unmounting of conda environments and their compressed
image files.

## Installation

Condainer can be installed using pip, e.g. using

`pip install --user .`

which would place the executable `cnd` into `~/.local/bin`.

## Usage

The Condainer executable is `cnd` and is controlled via subcommands and flags. See `cnd --help` for full details.
The following subcommands are available with Condainer:

### Initialize a project using `cnd init`

Create an empty directory, enter it, and run `cnd init` to
create a skeleton for a condainer project. You may edit
`condainer.yml`, and, importantly, add your `environment.yml` file
to the same directory.

### Build and compress an environment using `cnd build`

Build the conda environment specified in `environment.yml`.  In case
a file `requirements.txt` is present, its contents will be installed
in addition, using `pip`.  Finally, create a compressed
squashfs image, and delete the files from the staging environment.

### Execute a command using `cnd exec`

Using a command of the form `cnd exec -- python3 myscript.py`
it is possible to run executables from the contained conda
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
normal, however read-only.

### Explicitly mount the squashfs image using `cnd mount`

The command `cnd mount` mounts the squashfs image at the base
location specified in `condainer.yml`. Mount points have the form of
`cnd-UUID` where UUID is the type4 UUID generated and saved
during `cnd init`. Hints on activating and deactivating the
conda environment are printed.

### Explicitly un-mount the squashfs image using `cnd umount`

Unmount the image, if mounted. Make sure to run `conda deactivate`
in all relevant shell sessions prior to unmounting.

### Print information using `cnd status`

Show some information and the mount status of the image.

### Check if the necessary tools are available using `cnd prereq`

Check and show if the required software is locally available, also see
below.

## System requirements

Condainer should work on any recent Linux system and expects the following set
of tools available and enabled for non-privileged users:

* fuse
* squashfuse
* squashfs tools

On an Ubuntu (or similar) system, run (as root) the command

`apt install squashfs-tools squashfuse`

to install the necessary tools. In addition `curl` is required to download
the Miniforge installer, in case it is not available locally.

## Environment variables

The environment variable `CONDAINER_INSTALLER` allows to specify the full file
path to a Miniforge installer, e.g. to provide it centrally on a cluster.
No installer is downloaded in case that variable is defined.

## Contact

Copyright © 2023 Klaus Reuter <klaus.reuter@mpcdf.mpg.de>, Max Planck Computing and Data Facility
