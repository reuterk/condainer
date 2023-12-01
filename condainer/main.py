"""Condainer - main.py

Argument handling and calling of the entry points implemented in condainer.py
"""

import os
import sys
import argparse
from . import version
from . import condainer

def get_args():
    """Handle command line arguments, return args.
    """
    parser = argparse.ArgumentParser(
        prog=sys.argv[0],
        description='Create and manage conda environments based on compressed squashfs images.',
        epilog='More information at https://gitlab.mpcdf.mpg.de/mpcdf/condainer'
    )
    parser.add_argument('-q', '--quiet', action='store_true', help='be quiet, do not write to stdout unless an error occurs')
    parser.add_argument('-d', '--directory', help='condainer project directory, the default is the current working directory')
    parser.add_argument('-y', '--dryrun', action='store_true', help='dry run, do not actually do any operations, instead print information on what would be done')

    subparsers   = parser.add_subparsers(dest='subcommand', required=True)

    parser_init = subparsers.add_parser('init', help='initialize directory with config files')
    parser_init.add_argument('-n', '--non-conda-application', action='store_true', help='use condainer to store a non-conda application (advanced use case)')

    parser_build = subparsers.add_parser('build', help='build containerized conda environment')
    parser_build.add_argument('-s', '--steps', type=str, default="1,2,3,4,5,6,7", help='debug option to select individual build steps, default is all steps: 1,2,3,4,5,6,7')

    parser_exec = subparsers.add_parser('exec', help='execute command within containerized conda environment')
    parser_exec.add_argument('command', type=str, nargs='+', help='command line of the containerized command')

    parser_mount = subparsers.add_parser('mount', help='mount containerized conda environment')
    parser_mount.add_argument('-p', '--print', action='store_true', help='print the mount directory to stdout')

    subparsers.add_parser('umount', help='unmount ("eject") containerized conda environment')
    subparsers.add_parser('prereq', help='check if the necessary tools are installed')
    subparsers.add_parser('status', help='print status information about the condainer')
    # subparsers.add_parser('test', help=argparse.SUPPRESS)

    subparsers.add_parser('version', help='print version information and exit')

    args = parser.parse_args()
    return args


def cli():
    """Entry point function to call `condainer` from the command line.
    """
    args = get_args()
    cwd = os.getcwd()
    if args.directory:
        os.chdir(args.directory)
    if   args.subcommand == 'init':
        condainer.init(args)
    elif args.subcommand == 'build':
        condainer.build(args)
    elif args.subcommand == 'mount':
        condainer.mount(args)
    elif args.subcommand == 'umount':
        condainer.umount(args)
    elif args.subcommand == 'prereq':
        condainer.prereq(args)
    elif args.subcommand == 'exec':
        condainer.exec(args, cwd)
    elif args.subcommand == 'test':
        condainer.test(args)
    elif args.subcommand == 'status':
        condainer.status(args)
    elif args.subcommand == 'version':
        print(version.get_descriptive_version_string())
