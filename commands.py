from .config import Config
from .database import create_session, MonthlyLog, Expense, SpendingCategory, Tag

from rich import print

config = Config.load('scrooge/test_config')
session = create_session(config.database_path)

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
            print(f"Tag `{tag}` doesn't exist")
            exit(1)
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


def manage_tags(args):
    if args.action == 'add':
        if session.query(Tag).filter(Tag.name == args.name).count() > 0:
            print(f'Tag with name {args.name} already exists!')
            exit(1)

        session.add(Tag(name=args.name, description=args.description))
        session.commit()
    elif args.action == 'list':
        for tag in session.query(Tag):
            if tag.description is not None:
                print(f'{tag.name}: {tag.description}')
            else:
                print(tag.name)
    else:
        raise NotImplementedError('This actio nis not supported for now')
