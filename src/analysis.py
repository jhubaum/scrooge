from rich import print
from rich.console import Console
from rich.table import Table, Column

import re

from database import Bucket, MonthlyLog, Tag
from database import Expense
import util

import datetime
from collections import defaultdict

# how much of the available money should be spend per bucket?
# a tuple represents an interval, a single float a specific percentage
# TODO: This really should be defined in the same module where Bucket is defined (or even in the config?)
# I really need to think about how to organize this code...
CATEGORY_SPENDING_GUIDELINE = {
    Bucket.essential: (0.5, 0.6),
    Bucket.saving: (0.05, 0.1),
    Bucket.investing: 0.1,
    Bucket.fun: (0.2, 0.30),
    Bucket.giving_back: (0.05, 0.1),
}


def with_modifiers(str, *mod):
    if len(mod) == 0:
        return str
    return f"[{' '.join(mod)}]{str}[/{' '.join(mod)}]"


def fmt_amount(amount, *mod):
    return with_modifiers(f"{amount:0.2f}€", *mod)


def amount_row(table, title, amount, *mod):
    table.add_row(with_modifiers(title, *mod), fmt_amount(amount, *mod))


class DescriptionGroup:
    """Take a list of expenses, extract descriptions and print them in rows"""

    def __init__(self, title, expenses, *, misc=0.0, title_fmt_amount=fmt_amount):
        self.title = title
        self.total = 0.0
        self.misc = None
        self.descriptions = dict()
        self.title_fmt_amount = title_fmt_amount

        for expense in expenses:
            self.total += expense.amount
            if expense.description is not None:
                desc = expense.description
                tmp = self.descriptions.get(desc, (0, 0))
                self.descriptions[desc] = tmp[0] + 1, tmp[1] + expense.amount

        if len(self.descriptions) == 0:
            self.total += misc
        elif len(self.descriptions) > 0:
            misc += self.total - sum(map(lambda c: c[1], self.descriptions.values()))
            if misc > 0.001:
                self.misc = misc

    def insert_into_table(self, table):
        table.add_row(
            f"[bold]{self.title}[/bold]", self.title_fmt_amount(self.total, "bold")
        )

        for description, count in self.descriptions.items():
            cost = count[1]
            count = "" if count[0] == 1 else f" ({count[0]}x)"
            amount_row(table, f"{description}{count}", cost)
        if self.misc is not None:
            amount_row(table, "misc", self.misc, "italic")


class PartialDate:
    REGEX = re.compile(r"^(?P<year>\d{4})-?((?P<month>\d{2})-?(?P<day>\d{2})?)?$")

    def __init__(self, string):
        match = PartialDate.REGEX.match(string)

        if match is None:
            raise ValueError("Invalid format for partial date")

        if match["day"]:
            self.date = datetime.date(
                int(match["year"]), int(match["month"]), int(match["day"])
            )
        else:
            self.date = None
            self.year = int(match["year"])
            if match["month"]:
                self.month = int(match["month"])
                if self.month > 12:
                    raise ValueError("Month has to be <= 12")
            else:
                self.month = None

    def matches(self, date: datetime.date):
        if self.date is not None:
            return self.date == date
        if self.month is not None:
            return self.month == date.month and self.year == date.year
        return self.year == date.year

    def is_after(self, date):
        if self.date is not None:
            return self.date < date
        if self.month is not None and self.year == date.year:
            return self.month < date.month
        return self.year < date.year

    def is_before(self, date):
        if self.date is not None:
            return self.date > date
        if self.month is not None and self.year == date.year:
            return self.month > date.month
        return self.year > date.year


def full_tag_hierarchy(tags):
    visited = set()
    queue = list(tags)
    while len(queue) > 0:
        tag = queue.pop()
        if tag not in visited:
            visited.add(tag)
            queue.extend(tag.members)
    return visited


class Filter:
    def __init__(self, session, *elements):
        positive_tags = set()
        negative_tags = set()
        date_filter_functions = []

        for element in elements:
            if util.parse.may_be_modifier(element):
                is_negative, tag = util.parse.parse_modifier(session, element)
                if is_negative:
                    negative_tags.add(tag)
                else:
                    positive_tags.add(tag)
            elif element.startswith("on:"):
                date = PartialDate(element[3:])
                date_filter_functions.append(lambda d: date.matches(d))
            elif element.startswith("before:"):
                date = PartialDate(element[7:])
                date_filter_functions.append(lambda d: date.is_before(d))
            elif element.startswith("after:"):
                date = PartialDate(elements[6:])
                date_filter_functions.append(lambda d: date.is_after(d))
            else:
                raise ValueError(f"Unknown filter element: {element}")

        self.date_filter = lambda d: all(map(lambda f: f(d), date_filter_functions))
        self.positive_tags = full_tag_hierarchy(positive_tags)
        self.negative_tags = full_tag_hierarchy(negative_tags)

    def apply(self, session):
        # this filtering could be optimized by using SQLAlchemy methods.
        # especially moving the PartialDate to generate SQL queries should be
        # quite straight forward
        # TODO: Come back to this once it's actually a performance problem
        def include_based_on_tags(expense):
            if any(map(lambda t: t in self.negative_tags, expense.tags)):
                return False
            return len(self.positive_tags) == 0 or any(
                map(lambda t: t in self.positive_tags, expense.tags)
            )

        for expense in session.query(Expense).all():
            if self.date_filter(expense.date) and include_based_on_tags(expense):
                yield expense


def print_expenses_grouped_by_tags(expenses):
    expenses = list(expenses)
    all_expenses = sum(map(lambda e: e.amount, expenses))
    groups = dict()
    for expense in expenses:
        key = tuple(sorted(map(lambda t: t.name, expense.tags)))
        groups.setdefault(key, [])
        groups[key].append(expense)

    table = Table(
        "descriptor",
        Column(header="Amount", justify="right"),
        box=None,
        show_header=False,
    )
    for tags, expenses in groups.items():
        group = DescriptionGroup(", ".join(tags), expenses)
        group.insert_into_table(table)
        table.add_row()
    table.add_row(with_modifiers("Total", "bold"), fmt_amount(all_expenses))
    print(table)


def group_expenses_by_bucket(expenses):
    group = defaultdict(list)
    for expense in expenses:
        group[expense.bucket].append(expense)
    return group


def fmt_with_percentage(amount, percentage, *mod):
    return with_modifiers(f"{fmt_amount(amount)} ({percentage*100:.2f}%)", *mod)


def fmt_amount_for_bucket(available, bucket, epsilon=0.001):
    def fmt(amount, *mod):
        percentage = amount / available
        target_value = None

        bucket_range = CATEGORY_SPENDING_GUIDELINE[bucket]
        if type(bucket_range) == tuple:
            lower_bound = bucket_range[0]
            upper_bound = bucket_range[1]
        else:
            lower_bound = bucket_range
            upper_bound = bucket_range

        if percentage - epsilon < lower_bound:
            color = "yellow"
            target_value = lower_bound
        elif percentage + epsilon > upper_bound:
            target_value = upper_bound
            color = "red"
        else:
            color = "green"

        if target_value is None:
            return fmt_with_percentage(amount, percentage, *mod, color)
        target_value = target_value * available
        return with_modifiers(
            f"{fmt_amount(amount)} ({percentage*100:.2f}%, target={target_value:.2f}€)",
            *mod,
            color,
        )

    return fmt


def analyse_monthly_log(log: MonthlyLog, important_tags):
    table = Table(
        "descriptor",
        Column(header="Amount", justify="right"),
        title=f"Data for {str(log.month).zfill(2)}/{log.year}",
        show_header=False,
        box=None,
    )

    grouped = group_expenses_by_bucket(log.expenses)

    def bucket_into_table(title, bucket, misc=0.0):
        title_fmt_amount = fmt_amount_for_bucket(log.available, bucket)
        group = DescriptionGroup(
            title,
            grouped.get(bucket, []),
            misc=misc,
            title_fmt_amount=title_fmt_amount,
        )
        group.insert_into_table(table)
        table.add_row()

    amount_row(table, "Available", log.available, "bold")
    sum_of_expenses = sum(map(lambda e: e.amount, log.expenses))
    unaccounted = log.available - sum_of_expenses
    if abs(unaccounted) < 0.001:
        pass
    elif unaccounted < 0.0:
        amount_row(table, "Amount spend", sum_of_expenses, "italic", "red")
        amount_row(table, "Excess spending", -unaccounted, "italic", "red")
    else:
        amount_row(table, "Amount spent", sum_of_expenses, "italic", "green")
        amount_row(table, "Unaccounted", unaccounted, "italic")
    for bucket, title in [
        (Bucket.investing, "Amount invested"),
        (Bucket.saving, "Amount saved"),
        (Bucket.essential, "Amount spent on fixed living expenses"),
        (Bucket.fun, "Amount spent to have fun"),
        (Bucket.giving_back, "Amount given back"),
    ]:
        amount = sum(map(lambda e: e.amount, grouped[bucket]))
        # Wow, I waas really rushed when I wrote this code...
        # If I ever have some time (or whoever is reading this), please refactor it all
        table.add_row(
            title, fmt_amount_for_bucket(log.available, bucket)(amount, "bold")
        )

    table.add_row()

    bucket_into_table("Fixed living expenses", Bucket.essential)
    bucket_into_table("Freely used money", Bucket.fun)

    table.add_row("Important tags", "(spendings may appear in multiple rows)")
    for tag in important_tags:
        matching_expenses = list(
            filter(lambda e: any(map(lambda t: t.matches(tag), e.tags)), log.expenses)
        )
        if len(matching_expenses) > 0:
            amount = sum(map(lambda e: e.amount, matching_expenses))
            table.add_row(tag.name, fmt_with_percentage(amount, amount / log.available))
    print(table)
