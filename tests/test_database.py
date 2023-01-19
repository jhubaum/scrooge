import pytest

from database import create_session, Tag, MonthlyLog, Bucket, Expense
from config import UserConfig, RecurringExpense, Periodicity


@pytest.fixture
def session_with_simple_database(
    tags=["some_tag", ("some_other_tag", "with description")]
):
    # Create in-memory database
    session = create_session(path=None)

    for tag in tags:
        if type(tag) == str:
            session.add(Tag(name=tag))
        else:
            session.add(Tag(name=tag[0], description=tag[1]))

    session.add(MonthlyLog(month=11, year=2019, available=313.0))
    session.commit()

    return session


class TestMonthlyLogCreation:
    def test_fixture(self, session_with_simple_database):
        assert (
            MonthlyLog.get(session_with_simple_database, month=11, year=2019)
            is not None
        )
        assert Tag.get(session_with_simple_database, "some_tag") is not None
        t = Tag.get(session_with_simple_database, "some_other_tag")
        assert t is not None and t.description == "with description"

    def test_successful(self, session_with_simple_database):
        c = UserConfig(available=500, recurring_expenses=[])
        MonthlyLog.add_from_user_config(
            session_with_simple_database, month=11, year=2022, user_config=c
        )
        m = MonthlyLog.get(session_with_simple_database, month=11, year=2022)
        assert m is not None and m.available == 500.0

    def test_successful_with_recurring_expense(self, session_with_simple_database):
        c = UserConfig(
            available=500,
            recurring_expenses=[
                RecurringExpense(
                    amount=300,
                    bucket=Bucket.investing,
                    tags=["some_tag"],
                    name="I really hope this FTX thing works out",
                    periodicity=Periodicity.monthly,
                    due_month=None,
                )
            ],
        )
        MonthlyLog.add_from_user_config(
            session_with_simple_database, month=11, year=2022, user_config=c
        )
        expenses = session_with_simple_database.query(Expense).filter(
            Expense.tags.any(name="some_tag")
        )
        assert expenses.count() == 1
        expense = expenses.first()
        assert expense.description == "I really hope this FTX thing works out"
        assert expense.source == "recurring"
        assert expense.amount == 300.0

    def test_creation_with_yearly_periodicity(self, session_with_simple_database):
        c = UserConfig(
            available=500,
            recurring_expenses=[
                RecurringExpense(
                    amount=1200,
                    bucket=Bucket.investing,
                    tags=["some_tag"],
                    name="I really hope this FTX thing works out",
                    periodicity=Periodicity.yearly,
                    due_month=None,
                )
            ],
        )
        MonthlyLog.add_from_user_config(
            session_with_simple_database, month=11, year=2022, user_config=c
        )
        expenses = session_with_simple_database.query(Expense)
        assert expenses.count() == 1
        assert expenses.first().amount == 100.0  # only 1/12 due to yearly periodicity

    def test_error_with_unknown_tag(self, session_with_simple_database):
        c = UserConfig(
            available=500,
            recurring_expenses=[
                RecurringExpense(
                    amount=300,
                    bucket=Bucket.investing,
                    tags=["some_nonexisting_tag"],
                    name="I really hope this FTX thing works out",
                    periodicity=Periodicity.monthly,
                    due_month=None,
                )
            ],
        )
        with pytest.raises(ValueError) as exc_info:
            MonthlyLog.add_from_user_config(
                session_with_simple_database, month=11, year=2022, user_config=c
            )
        assert str(exc_info.value) == "Tag 'some_nonexisting_tag' does not exist"

    def test_error_if_exists(self, session_with_simple_database):
        c = UserConfig(available=500, recurring_expenses=[])
        with pytest.raises(ValueError) as exc_info:
            MonthlyLog.add_from_user_config(
                session_with_simple_database, month=11, year=2019, user_config=c
            )
        assert exc_info.value is not None
