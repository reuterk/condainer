# Condainer -- Conda environments in squashfs images

## Motivation and Solution

The `conda` package manager and related workflow has become a
de-facto standard when it comes to distributing scientific software
for easy installation by end users. It not only handles native
Python packages but also manages dependencies in the form of
binary blobs such as third-party libraries that are provided as
shared objects. Using `conda`, complex software environments can
be defined by means of simple `environment.yml` files.

Large environments can easily amount to several 100k individual
small files. On a local desktop file system, this is typically not
an issue.  However, in particular on the shared parallel file
systems of HPC systems this can cause severe trouble as these
filesystems are optimized for handling fewer and larger files. Inode
exhaustion, and heavy load due to (millions of) file opens, short
reads, and closes during the startup phase of (parallel) Python jobs
from numerous different users on the HPC cluster are examples.

Condainer solves these issues by putting conda environments into
compressed squashfs images, reducing the number of files involved on
the host file system by many orders of magnitude. Condainer images
are standalone and portable, i.e. they can be copied between
different systems, adding to reproducibility and reusability of
working software environments.

Technically, Condainer uses the Python basis from `Mambaforge`
(which is a free alternative to Miniconda) and installs arbitrary
software defined by the user via a `environment.yml` on top. Package
resolution and installation are extremely fast thanks to the `mamba`
package manager. Next, Condainer creates a compressed squashfs image
from that installation before it deletes the latter to save disk
space. The compressed image is then mounted at the very same
installation directory, providing the complete conda environment to
the user who can `activate` or `deactivate` it as usual. Moreover,
Condainer provides a wrapper to run binaries from the contained
conda environment directly and completely transparently.

## Installation

Condainer can be installed using pip, e.g. using

`pip install --user .`

which would place the executable `condainer` into `~/.local/bin`.

## Usage

The following subcommands are available to build and use
squashfs-based images of conda environments with Condainer.

### `condainer init`

Create an empty directory, enter it, and run `condainer init` to
create a skeleton for a condainer project. You may edit
`condainer.yml`, and, importantly, add your `environment.yml` file
to the same directory.

### `condainer build`

Build the conda environment specified in `environment.yml` and
create a compressed squashfs image.

### `condainer exec`

Using the command `condainer exec -- python3` it is possible to run
executables from the contained conda installation directly, in the
present example the Python interpreter `python3`. Mounting and
unmounting of the image are handled automatically and invisible to
the user.

### `condainer mount`

Mount the squashfs image at the location specified in
`condainer.yml`. Mount points have the form of `condainer-UUID`
where UUID is the type4 UUID generated and saved during `condainer
init`.

### `condainer umount`

Unmount the image, if mounted.

### `condainer status`

Show some information and the mount status of the image.

### `condainer prereq`

Check and show if the required software is locally available.

## System requirements

Condainer should work on any recent Linux system and expects the following set
of tools available and enabled for non-privileged users:

* squashfs tools
* fuse
* squashfuse
* curl

