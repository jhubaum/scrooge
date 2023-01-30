""" The module that contains everything to read the configuration
"""

import os
import json
import yaml

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Set, Optional, List
from enum import Enum, auto

from rich import print

from database import Bucket, Expense, MonthlyLog, Tag


class Periodicity(Enum):
    yearly = auto()
    monthly = auto()


@dataclass
class RecurringExpense:
    """Spendings that occur every month (or year) that are configurable in the config"""

    amount: float
    bucket: Bucket
    tags: Set[str]
    name: Optional[str]
    periodicity: Periodicity
    # If the spending recurs every year, optionally include a month when it is due
    # This is used to print a warning when the monthly log is initialized
    due_month: Optional[str]

    @staticmethod
    def from_dict(data):
        try:
            periodicity = Periodicity[data.get("periodicity", "monthly")]
            if periodicity == Periodicity.monthly and "due" in data:
                raise ValueError("due date only allowed for yearly spendings")
            if "due" in data and "name" not in data:
                raise ValueError("recurring expenses with due date have to have a name")

            return RecurringExpense(
                amount=data["amount"],
                bucket=Bucket[data["bucket"]],
                tags=set(data.get("tags", [])),
                name=data.get("name"),
                periodicity=periodicity,
                due_month=data.get("due"),
            )
        except KeyError as e:
            raise ValueError from e

    def create_expense_for_month(self, session, log: MonthlyLog) -> Expense:
        return Expense(
            amount=self.amount
            if self.periodicity == Periodicity.monthly
            else self.amount / 12.0,
            date=datetime(day=1, month=log.month, year=log.year),
            bucket=self.bucket,
            description=self.name,
            source="recurring",
            log=log,
            tags=[Tag.get(session, t) for t in self.tags],
        )


@dataclass
class UserConfig:
    """The configuration that is stored in the user's yaml file."""

    # the monthly money available (in Eur)
    available: float
    recurring_expenses: List[RecurringExpense]

    @staticmethod
    def from_dict(data):
        def create_recurring(elem):
            i, data = elem
            try:
                return RecurringExpense.from_dict(data)
            except ValueError as e:
                name = f'\'{data["name"]}\'' if "name" in data else f"at index {i}"
                raise ValueError(
                    f"Error while reading recurring expense {name}: {str(e)}"
                )

        return UserConfig(
            available=data["available"],
            recurring_expenses=list(
                map(create_recurring, enumerate(data.get("recurring", [])))
            ),
        )

    @staticmethod
    def load_from_yaml_file(filename):
        with open(filename, "r") as f:
            data = yaml.safe_load(f)
        return UserConfig.from_dict(data)


@dataclass
class Config:
    user: UserConfig
    database_path: str
    backup_dir: Path
    num_backups_kept: int

    @staticmethod
    def load(path: Optional[Path] = None):
        if path is None:
            if os.environ.get("SCROOGE_TESTING", False):
                print("[Using test config]\n")
                path = Path(__file__).parents[0] / "test_config"
            else:
                path = Path(
                    os.environ.get("SCROOGE_CONFIG_DIR", "~/.scrooge")
                ).resolve()

        if not path.is_dir():
            print(f"Config directory {path} does not exist. Exiting")
            exit(1)

        return Config(
            user=UserConfig.load_from_yaml_file(path / "config.yml"),
            database_path=path / "database.sqlite",
            backup_dir=path / "backups",
            num_backups_kept=5,
        )

    def create_backup(self, data):
        new_file = self.backup_dir / datetime.now().strftime("%Y-%m-%d_%H%M%S.json")
        with open(new_file, "w") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"Created backup `{new_file}`")

        existing_backups = sorted(self.backup_dir.iterdir(), reverse=True)
        for to_delete in existing_backups[self.num_backups_kept :]:
            to_delete.unlink()
