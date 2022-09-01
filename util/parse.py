from ..database import Tag

class InvalidModifierString(Exception):
    pass

def may_be_modifier(string):
    return not len(string) == 0 and string[0] == '+' or string[0] == '-'

def parse_modifier(session, string):
    if not may_be_modifier(string):
        raise InvalidModifierString("Modifiers have to start with either '+' or '-'")

    tag = session.query(Tag).filter(Tag.name==string[1:])
    if tag.count() == 0:
        raise InvalidModifierString(f"`{string[1:]}` is not a known tag name")

    return string[0] == '-', tag.first()
