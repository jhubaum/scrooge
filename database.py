from enum import Enum, auto
from sqlalchemy import create_engine, Column, Date, Integer, String, Float, ForeignKey, Boolean, Enum, Text
from sqlalchemy.orm import declarative_base, relationship, Session
from datetime import datetime

Base = declarative_base()


class SpendingCategory(Enum):
    Fixed = auto() # for stuff like rent, food, ...
    Savings = auto()
    Investments = auto()
    Free = auto() # for everything to enjoy life


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
