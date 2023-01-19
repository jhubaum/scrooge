from sqlalchemy import (
    create_engine,
    Column,
    Date,
    Integer,
    String,
    Float,
    ForeignKey,
    Boolean,
    Enum,
    Text,
    Table,
)
from sqlalchemy.orm import declarative_base, relationship, Session
from datetime import datetime

import enum

from rich.prompt import Confirm

Base = declarative_base()


class Bucket(enum.Enum):
    essential = enum.auto()  # for stuff like rent, food, ...
    saving = enum.auto()
    investing = enum.auto()
    fun = enum.auto()  # for everything to enjoy life
    giving_back = enum.auto()


tag_expense_association_table = Table(
    "tag_expense_associations",
    Base.metadata,
    Column("tag_id", ForeignKey("tags.id"), primary_key=True),
    Column("expense_id", ForeignKey("expenses.id"), primary_key=True),
)

tag_hierarchy_association_table = Table(
    "tag_hierarchies",
    Base.metadata,
    Column("parent_id", ForeignKey("tags.id"), primary_key=True),
    Column("member_id", ForeignKey("tags.id"), primary_key=True),
)


class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    expenses = relationship(
        "Expense", secondary=tag_expense_association_table, back_populates="tags"
    )

    members = relationship(
        "Tag",
        secondary=tag_hierarchy_association_table,
        primaryjoin="Tag.id==tag_hierarchies.c.parent_id",
        secondaryjoin="Tag.id==tag_hierarchies.c.member_id",
        back_populates="parents",
    )

    parents = relationship(
        "Tag",
        secondary=tag_hierarchy_association_table,
        primaryjoin="Tag.id==tag_hierarchies.c.member_id",
        secondaryjoin="Tag.id==tag_hierarchies.c.parent_id",
        back_populates="members",
    )

    def matches(self, tag):
        return tag.id == self.id or any(map(lambda p: p.matches(tag), self.parents))

    def to_json(self):
        return dict(
            id=self.id,
            name=self.name,
            description=self.description,
            members=list(map(lambda t: t.id, self.members)),
        )

    @staticmethod
    def get(session, string):
        q = session.query(Tag).filter(Tag.name == string)
        if q.count() == 0:
            raise ValueError(f"Tag '{string}' does not exist")
        return q.first()


class MonthlyLog(Base):
    __tablename__ = "monthly_logs"

    # todo: budget is uniquely identified by month and year. Do I need the id?
    id = Column(Integer, primary_key=True)
    month = Column(Integer, nullable=False)
    year = Column(Integer, nullable=False)

    available = Column(Float, nullable=False)

    expenses = relationship("Expense", back_populates="log", cascade="all, delete")

    def to_json(self):
        return dict(
            id=self.id,
            month=self.month,
            year=self.year,
            available=self.available,
            expenses=list(map(lambda e: e.to_json(), self.expenses)),
        )

    @staticmethod
    def get(session, month, year):
        log = session.query(MonthlyLog).filter(
            MonthlyLog.month == month, MonthlyLog.year == year
        )
        if log.count() > 0:
            return log.first()

        return None

    @staticmethod
    def add_from_user_config(session, month, year, user_config):
        if MonthlyLog.get(session, month, year) is not None:
            raise ValueError(
                f"Tried to create already existing monthly log for {month}/{year}"
            )

        log = MonthlyLog(month=month, year=year, available=user_config.available)
        session.add(log)
        for expense in user_config.recurring_expenses:
            session.add(expense.create_expense_for_month(session, log))

        session.commit()
        return log

    @staticmethod
    def get_or_create(session, month, year, user_config):
        # TODO: It feels like this method belongs somewhere else.
        # Maybe in util or commands.py?
        log = MonthlyLog.get(session, month, year)
        if log is not None:
            return log

        if not Confirm.ask(
            f"Log for {str(month).zfill(2)}/{year} does not exist. Do you want to create it?"
        ):
            raise ValueError("Could not create monthly log")

        return MonthlyLog.create_from_user_config(session, month, year, user_config)


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True)
    amount = Column(Float, nullable=False)
    date = Column(Date, nullable=False)
    bucket = Column(Enum(Bucket), nullable=False)
    description = Column(Text, nullable=True)
    # Where does this expense come from. Right now only used to mark recurring expenses
    source = Column(String(20), nullable=True)

    tags = relationship(
        "Tag", secondary=tag_expense_association_table, back_populates="expenses"
    )

    log_id = Column(
        Integer, ForeignKey(MonthlyLog.id, ondelete="cascade"), nullable=False
    )
    log = relationship("MonthlyLog", back_populates="expenses")

    def to_json(self):
        return dict(
            id=self.id,
            amount=self.amount,
            date=dict(day=self.date.day, month=self.date.month, year=self.date.year),
            category=str(self.category),
            description=self.description,
            source=self.source,
            tags=list(map(lambda t: t.id, self.tags)),
        )


def create_session(path):
    if path is None:
        path = ":memory:"
    path = f"sqlite+pysqlite:///{path}"
    engine = create_engine(path, future=True)
    Base.metadata.create_all(engine)
    return Session(engine)
