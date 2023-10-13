from . import condainer

def cli():
    """Entry point function when calling `condainer` from the command line.
    """
    args = condainer.args()
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
