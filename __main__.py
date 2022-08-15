from .commands import track_expense, print_summary

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

    summary_parser = subparsers.add_parser('show', help="Print the summary of expenses for a specific time frame")
    summary_parser.set_defaults(func=print_summary)

    summary_parser.add_argument('--month', '-m', type=int)
    summary_parser.add_argument('--year', '-y', type=int)

    return parser

args = create_argparser().parse_args()
if "func" in args:
    args.func(args)
else:
    print_summary(Namespace())
