from .config import Config
from .database import create_session, MonthlyLog, Expense, SpendingCategory, Tag
from .analysis import analyse_monthly_log

from . import util

from rich import print

config = Config.load('scrooge/test_config')
session = create_session(config.database_path)

def error_and_exit(message, error_code=1):
    print(f"Error: {message}")
    exit(error_code)

def track_expense(args):
    log = session.query(MonthlyLog).filter(MonthlyLog.month==args.date.month,
                                           MonthlyLog.year==args.date.year)
    if log.count() == 0:
        print(f"Create log for {args.date.month}/{args.date.year} based on information from the config")
        log = MonthlyLog(month=args.date.month, 
                         year=args.date.year,
                         available=config.user.available)
        session.add(log)
        session.commit()
    else:
        log = log.first()

    tags = []
    for tag in args.tags:
        q = session.query(Tag).filter(Tag.name==tag)
        if q.count() == 0:
            error_and_exit(f"Tag `{tag}` doesn't exist")
        tags.append(q.first())

    expense = Expense(amount=args.amount, date=args.date, log=log,
                      category=SpendingCategory[args.category], tags=tags,
                      description=args.description)
    session.add(expense)
    session.commit()


def print_summary(args):
    if args.month is None or args.year is None:
        print('Showing complete or yearly history not yet supported. Please specify month and year')
        exit(1)

    log = session.query(MonthlyLog).filter(MonthlyLog.month==args.month,
                                           MonthlyLog.year==args.year)
    if log.count() == 0:
        print(f'No data available for {args.month}/{args.year}')
    else:
        log = log.first()
        print(f"Available: {log.available}")
        print("Expenses:")
        for expense in log.expenses:
            print(expense.amount, expense.date, expense.category, 
                  expense.description,
                  ', '.join(map(lambda t: t.name, expense.tags)))

def create_new_tag(args):
    if session.query(Tag).filter(Tag.name == args.name).count() > 0:
        print(f'Tag with name {args.name} already exists!')
        exit(1)

    session.add(Tag(name=args.name, description=args.description))
    session.commit()

def list_available_tags(args):
    for tag in session.query(Tag):
        if tag.description is not None:
            print(f'{tag.name}: {tag.description}')
        else:
            print(tag.name)

        for member in tag.members:
            print(f'- {member.name}')

def modify_member_hierarchy(args):
    parent = session.query(Tag).filter(Tag.name==args.name)
    if parent.count() == 0:
        error_and_exit(f"Tag `{args.name}` doesn't exist")
    parent = parent.first()

    to_add = set()
    to_remove = set()

    for modifier in args.modifiers:
        if modifier[0] != '-' and modifier[0] != '+':
            error_and_exit(f"Invalid modifier `{modifier}`: First character has to be either '+' or '-'")

        tag = session.query(Tag).filter(Tag.name==modifier[1:])
        if tag.count() == 0:
            error_and_exit(f"Invalid modifier `{modifier}`: `{modifier[1:]}` is not a known category name")

        if modifier[0] == '-':
            to_remove.add(tag.first())
        else:
            to_add.add(tag.first())

    for tag in to_remove:
        if tag not in parent.members:
            print(f"`{tag.name}` is not a direct member of `{parent.name}`")
        else:
            print(f"Removed `{tag.name}` from `{parent.name}`")
            parent.members.remove(tag)
            session.commit()

    for tag in to_add:
        if tag == parent:
            print("Can't add tags as members of themselves")
        elif tag in parent.members:
            print(f"`{tag.name}` already is a member of `{parent.name}`")
        elif util.tags.path_between_tags_exists(tag, parent):
            print(f"Skipping `{tag.name}`. Adding it as member of `{parent.name}` would create a cycle.")
        else:
            print(f"Added `{tag.name}` as member of `{parent.name}`")
            parent.members.append(tag)
            session.commit()

