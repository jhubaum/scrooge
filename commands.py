from .config import Config
from .database import create_session, MonthlyLog, Expense

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

    expense = Expense(amount=args.amount, date=args.date, log=log)
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
            print(expense.amount, expense.date)


