import re
from datetime import date

from ..database import Tag


class InvalidModifierString(Exception):
    pass


def may_be_modifier(string):
    return not len(string) == 0 and string[0] == "+" or string[0] == "-"


def parse_modifier(session, string):
    if not may_be_modifier(string):
        raise InvalidModifierString("Modifiers have to start with either '+' or '-'")

    tag = session.query(Tag).filter(Tag.name == string[1:])
    if tag.count() == 0:
        raise InvalidModifierString(f"`{string[1:]}` is not a known tag name")

    return string[0] == "-", tag.first()


def parse_month(string):
    """

    Return (year, month)
    """
    month_as_name = dict(
        jan=1,
        january=1,
        feb=2,
        february=2,
        mar=3,
        march=3,
        apr=4,
        april=4,
        may=5,
        jun=6,
        june=6,
        jul=7,
        july=7,
        aug=8,
        august=8,
        sep=9,
        september=9,
        oct=10,
        october=10,
        nov=11,
        november=11,
        dec=12,
        december=12,
    )
    if string in month_as_name:
        return date.today().year, month_as_name[string]

    m = re.match(r"^(?P<year>\d{4})-(?P<month>\d{2})", string)
    if m is not None:
        return int(m["year"]), int(m["month"])

    raise ValueError(f"`{string}` doesn't describe a month")
