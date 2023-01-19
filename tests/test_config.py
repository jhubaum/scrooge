import pytest

from config import UserConfig, RecurringExpense, Periodicity
from database import Bucket


def test_recurring_expense_working_values():
    spending = RecurringExpense.from_dict(
        dict(
            bucket="investing",
            amount=1000,
            name="MSCI World ETF",
            tags=["some_tag"],
            periodicity="monthly",
        )
    )
    assert spending.amount == 1000.0
    assert spending.bucket == Bucket.investing
    assert type(spending.tags) == set
    assert len(spending.tags) == 1
    assert "some_tag" in spending.tags
    assert spending.name == "MSCI World ETF"
    assert spending.periodicity == Periodicity.monthly
    assert spending.due_month is None


def test_recurring_expense_default_values():
    spending = RecurringExpense.from_dict(
        dict(
            bucket="investing",
            amount=1000,
        )
    )
    assert len(spending.tags) == 0
    assert spending.name is None
    assert spending.periodicity == Periodicity.monthly
    assert spending.due_month is None


def test_recurring_expense_missing_values():
    with pytest.raises(ValueError) as exc_info:
        RecurringExpense.from_dict(dict(amount=1000))

    assert exc_info.value


def test_read_config_from_file(tmp_path):
    file = tmp_path / "config.yml"
    file.write_text(
        """
available: 300
recurring:
  - bucket: investing
    amount: 240
  - bucket: saving
    amount: 15.37
"""
    )

    user_config = UserConfig.load_from_yaml_file(file)
    assert user_config.available == 300.0
    assert len(user_config.recurring_expenses) == 2
    for i, (bucket, amount) in enumerate([("investing", 240.0), ("saving", 15.37)]):
        assert user_config.recurring_expenses[i].amount == amount
        assert user_config.recurring_expenses[i].bucket == Bucket[bucket]


def test_recurring_expense_missing_value_error_messages():
    with pytest.raises(ValueError) as exc_info:
        UserConfig.from_dict(
            dict(
                available=300.0,
                recurring=[
                    dict(name="Named Expense", bucket="fun", amount=17, due="june")
                ],
            )
        )
    assert (
        str(exc_info.value)
        == "Error while reading recurring expense 'Named Expense': due date only allowed for yearly spendings"
    )

    with pytest.raises(ValueError) as exc_info:
        UserConfig.from_dict(
            dict(available=300.0, recurring=[dict(bucket="fun", amount=17, due="june")])
        )
    assert (
        str(exc_info.value)
        == "Error while reading recurring expense at index 0: due date only allowed for yearly spendings"
    )
