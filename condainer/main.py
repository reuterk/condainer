"""Condainer
Argument handling and calling of the functions implemented in condainer.py
"""

import os
import sys
import argparse
from . import condainer

def get_args():
    """Handle command line arguments, return args.
    """
    parser = argparse.ArgumentParser(
        prog=sys.argv[0],
        description='Create and manage conda environments based on compressed squashfs images.',
        epilog='More information at https://gitlab.mpcdf.mpg.de/khr/condainer'
    )
    parser.add_argument('-q', '--quiet', action='store_true', help='be quiet, do not write to stdout unless an error occurs')
    parser.add_argument('-d', '--directory', help='condainer project directory, the default is the current working directory')

    subparsers   = parser.add_subparsers(dest='subcommand', required=True)

    subparsers.add_parser('init', help='initialize directory with config files')
    subparsers.add_parser('build', help='build containerized conda environment')

    parser_exec = subparsers.add_parser('exec', help='execute command within containerized conda environment')
    parser_exec.add_argument('command', type=str, nargs='+', help='command line of the containerized command')

    subparsers.add_parser('mount', help='mount containerized conda environment')
    subparsers.add_parser('umount', help='unmount ("eject") containerized conda environment')
    subparsers.add_parser('prereq', help='check if the necessary tools are installed')
    subparsers.add_parser('status', help='print status information about the condainer')
    # subparsers.add_parser('test', help=argparse.SUPPRESS)

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
