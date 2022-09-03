from rich import print
from rich.console import Console
from rich.table import Table
from rich.align import Align

import re
from .database import Expense
from . import util

import datetime

class PartialDate:
    REGEX = re.compile(r'^(?P<year>\d{4})-?((?P<month>\d{2})-?(?P<day>\d{2})?)?$')

    def __init__(self, string):
        match = PartialDate.REGEX.match(string)

        if match is None:
            raise ValueError("Invalid format for partial date")
        
        if match['day']:
            self.date = datetime.date(int(match['year']),
                                      int(match['month']),
                                      int(match['day']))
        else:
            self.date = None
            self.year = int(match['year'])
            if match['month']:
                self.month = int(match['month'])
                if self.month > 12:
                    raise ValueError("Month has to be <= 12")
            else:
                self.month = None

    def matches(self, date : datetime.date):
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
            elif element.startswith('on:'):
                date = PartialDate(element[3:])
                date_filter_functions.append(lambda d: date.matches(d))
            elif element.startswith('before:'):
                date = PartialDate(element[7:])
                date_filter_functions.append(lambda d: date.is_before(d))
            elif element.startswith('after:'):
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
            return len(self.positive_tags) == 0 or \
                any(map(lambda t: t in self.positive_tags, expense.tags))

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


    table = Table(box=None, show_header=False)
    for tags, expenses in groups.items():
        total = 0
        description_counts = dict()
        for expense in expenses:
            total += expense.amount
            if expense.description is not None:
                desc = expense.description
                tmp = description_counts.get(desc, (0, 0))
                description_counts[desc] = tmp[0] + 1, tmp[1] + expense.amount

        table.add_row(f"[bold]{', '.join(tags)}[/bold]",
                      f"[bold]{total:.2f}€[/bold]")

        for description, count in description_counts.items():
            cost = count[1]
            count = "" if count[0] == 1 else f" ({count[0]}x)"
            table.add_row(f"{description}{count}", f"{cost:.2f}€")

        if len(description_counts) > 0:
            rem = total - sum(map(lambda c:c[1], description_counts.values()))
            if rem > 0.001:
                table.add_row("[italic]misc[/italic]",
                              f"[italic]{rem:.2f}[/italic]")
        table.add_row()
    table.add_row("[bold]Total[/bold]", 
                  f"{all_expenses:.2f}€")
    print(table)


