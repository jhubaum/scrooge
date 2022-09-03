from .config import Config
from .database import create_session, MonthlyLog, Expense, SpendingCategory, Tag
from .analysis import Filter

from . import util
from . import analysis

from rich import print
from datetime import date

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
                         available=config.user.available,
                         allocated_for_savings=config.user.allocated_for_savings,
                         allocated_for_investments=config.user.allocated_for_investments)
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


def show_expenses(args):
    analysis.print_expenses_grouped_by_tags(Filter(session, *args.filters).apply(session))


def show_month(args):
    if args.month is None:
        year, month = date.today().year, date.today().month
    else:
        year, month = util.parse.parse_month(args.month)

    m = session.query(MonthlyLog).filter(MonthlyLog.month==month,
                                         MonthlyLog.year==year)
    if m.count() == 0:
        error_and_exit(f"No data found for {str(month).zfill(2)}/{year}")

    def important_tags(*tags):
        contexts = session.query(Tag).filter(Tag.name=='contexts')
        assert contexts.count() == 1
        for m in contexts.first().members:
            yield m

        for tag in tags:
            tag = session.query(Tag).filter(Tag.name==tag)
            if tag.count() == 0:
                print(f"Warning: Important tag '{tag}' does not exist")
            yield tag.first()

    analysis.analyse_monthly_log(m.first(),
                                 important_tags('food'))


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
        try: 
            is_negative, tag = util.parse.parse_modifier(session, modifier)
            if is_negative:
                to_remove.add(tag)
            else:
                to_add.add(tag)
        except util.parse.InvalidModifierString as e:
            error_and_exit(f"Invalid modifier `{modifier}`: {str(e)}")

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

