from .commands import track_expense, print_summary, manage_tags

from argparse import ArgumentParser, Namespace
from datetime import datetime

def str_to_date(string):
    return datetime.strptime(string, '%Y-%m-%d').date()

def create_argparser():
    parser = ArgumentParser(description="Scrooge – A command line based manager for personal finances")
    subparsers = parser.add_subparsers()
    
    track_parser = subparsers.add_parser("track", help="Track expenses")
    track_parser.set_defaults(func=track_expense)

    #TODO: replace these argument by an import file instead
    track_parser.add_argument('amount', type=int, help='The amount spent')
    track_parser.add_argument('date', type=str_to_date, help='The day it was spent')
    track_parser.add_argument('category', choices=["fixed", 
                                                   "savings", 
                                                   "investments",
                                                   "free"])
    track_parser.add_argument('tags', nargs="*")
    track_parser.add_argument('--description', '-d', help='An optional description for the expense')

    summary_parser = subparsers.add_parser('show', help="Print the summary of expenses for a specific time frame")
    summary_parser.set_defaults(func=print_summary)

    summary_parser.add_argument('--month', '-m', type=int)
    summary_parser.add_argument('--year', '-y', type=int)

    # TODO: add more fine-grained control for categories
    tag_parser = subparsers.add_parser('tag', help='Manage tags')
    tag_parser.set_defaults(func=manage_tags)

    # TODO: remove the name and description argument for list, since they are not needed
    tag_parser.add_argument('action', choices=['add', 'list'])
    tag_parser.add_argument('name', help="The name of the tag")
    tag_parser.add_argument('description', nargs="?", help="An optional description")

    return parser

args = create_argparser().parse_args()
if "func" in args:
    args.func(args)
else:
    print_summary(Namespace())
