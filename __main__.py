from . import commands

from argparse import ArgumentParser, Namespace, REMAINDER
from datetime import datetime

def str_to_date(string):
    return datetime.strptime(string, '%Y-%m-%d').date()

def create_argparser():
    parser = ArgumentParser(description="Scrooge – A command line based manager for personal finances")
    subparsers = parser.add_subparsers()
    
    track_parser = subparsers.add_parser("track", help="Track expenses")
    track_parser.set_defaults(func=commands.track_expense)

    #TODO: replace these argument by an import file instead
    track_parser.add_argument('amount', type=float, help='The amount spent')
    track_parser.add_argument('date', type=str_to_date, help='The day it was spent')
    track_parser.add_argument('category', choices=["fixed", 
                                                   "savings", 
                                                   "investments",
                                                   "free"])
    track_parser.add_argument('tags', nargs="*")
    track_parser.add_argument('--description', '-d', help='An optional description for the expense')

    summary_parser = subparsers.add_parser('show', help="Print the summary of expenses for a specific time frame")
    summary_parser.set_defaults(func=commands.show_expenses)
    summary_parser.add_argument('filters', nargs=REMAINDER)

    monthly_parser = subparsers.add_parser('month',
                                           help='Print info about the given month')
    monthly_parser.add_argument('month', nargs="?")
    monthly_parser.set_defaults(func=commands.show_month)

    tag_parser = subparsers.add_parser('tags', help='Manage tags')
    tag_parser = tag_parser.add_subparsers()

    # TODO: Add some functionality for adding tag relationships
    create_parser = tag_parser.add_parser('create', help='Create a new tag')
    create_parser.add_argument('name', help="The name of the tag")
    create_parser.add_argument('description', nargs="?", help="An optinal description")
    create_parser.set_defaults(func=commands.create_new_tag)

    member_parser = tag_parser.add_parser('members', help='Modify member categories')
    member_parser.add_argument('name', help="The name of the tag to modify")
    member_parser.add_argument('modifiers', nargs=REMAINDER, 
                               help="""A list of modifiers. A modifier matches the expression [+-]<tag>.
                               In case of +<tag>, <tag> will be added as a member. In case of -<tag>, it will be removed.""")
    member_parser.set_defaults(func=commands.modify_member_hierarchy)
    
    list_parser = tag_parser.add_parser('list', help="List all available tags")
    list_parser.set_defaults(func=commands.list_available_tags)

    backup_parser = subparsers.add_parser('backup', help='Backup the stored data')
    backup_parser.add_argument('action', nargs="?", choices=['create', 'restore'],
                               help="create is default")
    backup_parser.set_defaults(func=commands.backup_data)

    import_parser = subparsers.add_parser('import', 
                                          help='Import and verify multiple expenses from a .csv file')
    import_parser.add_argument('file', help='The file to import from. If the given file does not exist, this command may create a template file')
    import_parser.set_defaults(func=commands.import_from_csv_file)
    
    return parser

parser = create_argparser()
args = parser.parse_args()
if "func" in args:
    args.func(args)
else:
    parser.print_help()
    exit(1)
