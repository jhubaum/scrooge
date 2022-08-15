from sqlalchemy import create_engine, Column, Date, Integer, String, Float, ForeignKey, Boolean, Enum, Text, Table
from sqlalchemy.orm import declarative_base, relationship, Session
from datetime import datetime

import enum

Base = declarative_base()


class SpendingCategory(enum.Enum):
    fixed = enum.auto() # for stuff like rent, food, ...
    savings = enum.auto()
    investments = enum.auto()
    free = enum.auto() # for everything to enjoy life


tag_expense_association_table = Table(
    "tag_expense_associations",
    Base.metadata,
    Column('tag_id', ForeignKey('tags.id'), primary_key=True),
    Column('expense_id', ForeignKey('expenses.id'), primary_key=True)
)

class Tag(Base):
    __tablename__ = 'tags'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    expenses = relationship('Expense', 
                            secondary=tag_expense_association_table, 
                            back_populates='tags')


class MonthlyLog(Base):
    __tablename__ = 'monthly_logs'

    # todo: budget is uniquely identified by month and year. Do I need the id?
    id = Column(Integer, primary_key=True)
    month = Column(Integer, nullable=False)
    year = Column(Integer, nullable=False)

    available = Column(Float, nullable=False)

    expenses = relationship('Expense', back_populates='log', cascade='all, delete')


class Expense(Base):
    __tablename__ = 'expenses'

    id = Column(Integer, primary_key=True)
    amount = Column(Float, nullable=False)
    date = Column(Date, nullable=False)
    category = Column(Enum(SpendingCategory), nullable=False)
    description = Column(Text, nullable=True)

    tags = relationship('Tag', 
                        secondary=tag_expense_association_table, 
                        back_populates='expenses')
    

    log_id = Column(Integer, ForeignKey(MonthlyLog.id, ondelete='cascade'), nullable=False)
    log = relationship('MonthlyLog', back_populates='expenses')


def create_session(path):
    if path is None:
        path = ':memory:'
    else:
        path = f'sqlite+pysqlite:///{path}'
    engine = create_engine(path, future=True)
    Base.metadata.create_all(engine)
    return Session(engine)
