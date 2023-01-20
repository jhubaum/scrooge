from config import Config
from database import create_session, MonthlyLog, Expense, Bucket, Tag
from analysis import Filter

import util
import analysis

from rich import print
from rich.prompt import Confirm
from datetime import date
from pathlib import Path

config = Config.load()
session = create_session(config.database_path)


def error_and_exit(message, error_code=1):
    print(f"Error: {message}")
    exit(error_code)


def track_expense(args):
    log = MonthlyLog.get_or_create(
        session, args.date.month, args.date.year, config.user
    )
    tags = []
    for tag in args.tags:
        q = session.query(Tag).filter(Tag.name == tag)
        if q.count() == 0:
            error_and_exit(f"Tag `{tag}` doesn't exist")
        tags.append(q.first())

    expense = Expense(
        amount=args.amount,
        date=args.date,
        log=log,
        category=Bucket[args.category],
        tags=tags,
        description=args.description,
    )
    session.add(expense)
    session.commit()


def show_expenses(args):
    analysis.print_expenses_grouped_by_tags(
        Filter(session, *args.filters).apply(session)
    )


def show_month(args):
    if args.month is None:
        year, month = date.today().year, date.today().month
    else:
        year, month = util.parse.parse_month(args.month)

    m = MonthlyLog.get(session, month=month, year=year)
    if m is None:
        if Confirm.ask(f"No data exists for {month}/{year}. Do you want to create a log based on the config values?"):
            MonthlyLog.add_from_user_config(session, month, year, config.user)
            print(f"Created monthly log for {month}/{year}")
        return
        

    def important_tags(*tags):
        contexts = session.query(Tag).filter(Tag.name == "contexts")
        assert contexts.count() == 1
        for m in contexts.first().members:
            yield m

        for tag in tags:
            tag = session.query(Tag).filter(Tag.name == tag)
            if tag.count() == 0:
                print(f"Warning: Important tag '{tag}' does not exist")
            yield tag.first()

    analysis.analyse_monthly_log(m, important_tags("food"))


def create_new_tag(args):
    if session.query(Tag).filter(Tag.name == args.name).count() > 0:
        print(f"Tag with name {args.name} already exists!")
        exit(1)

    session.add(Tag(name=args.name, description=args.description))
    session.commit()


def list_available_tags(args):
    for tag in session.query(Tag):
        if tag.description is not None:
            print(f"{tag.name}: {tag.description}")
        else:
            print(tag.name)

        for member in tag.members:
            print(f"- {member.name}")


def modify_member_hierarchy(args):
    parent = session.query(Tag).filter(Tag.name == args.name)
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
            print(
                f"Skipping `{tag.name}`. Adding it as member of `{parent.name}` would create a cycle."
            )
        else:
            print(f"Added `{tag.name}` as member of `{parent.name}`")
            parent.members.append(tag)
            session.commit()


def import_from_csv_file(args):
    importer = util.files.CSVExpenseImporter(args.file)
    if not importer.file_exists() and Confirm.ask(
        "Import file does not exist. Do you want to create it?"
    ):
        importer.write_sample_file()
    else:
        importer.import_to(session, config.user)


def backup_data(args):
    if args.action is None or args.action == "create":
        data = dict(
            tags={t.id: t.to_json() for t in session.query(Tag)},
            months=[m.to_json() for m in session.query(MonthlyLog)],
        )
        config.create_backup(data)
    else:
        raise NotImplementedError
