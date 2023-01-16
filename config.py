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

from database import Bucket

class Periodicity(Enum):
    Yearly = auto()
    Monthly = auto()

@dataclass
class RecurringSpending:
    """ Spendings that occur every month (or year) that are configurable in the config
    """
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
            periodicity = Periodicity[data['periodicity']]
            if periodicity == Periodicity.Monthly and 'due' in data:
                raise ValueError("due value only allowed for yearly recurring spendings")
            return RecurringSpending(amount=data['amount'],
                                     bucket=Bucket[data['bucket']],
                                     tags=set(data.get('tags', [])),
                                     name=data.get('name'),
                                     periodicity=periodicity,
                                     due_month=data.get('due'))
        except KeyError as e:
            raise ValueError from e


@dataclass
class UserConfig:
    """ The configuration that is stored in the user's yaml file.
    """
    
    # the monthly money available (in Eur)
    available: float
    recurring_spendings: List[RecurringSpending]

    @staticmethod
    def load_from_yaml_file(filename):
        with open(filename, 'r') as f:
            data = yaml.safe_load(f)
        return UserConfig(available=data['available'],
                          recurring_spendings=list(map(RecurringSpending.from_dict, data.get('recurring', []))))
            for keys in yaml.safe_load(f):
                # TODO: Test here if a key is set twice and throw an error if so
                data = { **data, **keys }

            # TODO: Print better errors for missing or wrong keys
            return UserConfig(**data)


@dataclass
class Config:
    user: UserConfig
    database_path: str
    backup_dir: Path
    num_backups_kept: int

    @staticmethod
    def load():
        if os.environ.get('SCROOGE_TESTING', False):
            print('[Using test config]\n')
            path = Path(__file__).parents[0] / 'test_config'
        else:
            path = Path(os.environ.get('SCROOGE_CONFIG_DIR', '~/.scrooge')).resolve()

        if not path.is_dir():
            print(f"Config directory {path} does not exist. Exiting")
            exit(1)

        return Config(
            user=UserConfig.load_from_yaml_file(path / 'config.yml'),
            database_path=path / 'database.sqlite',
            backup_dir=path / 'backups',
            num_backups_kept=5
        )


    def create_backup(self, data):
        new_file = self.backup_dir / datetime.now().strftime('%Y-%m-%d_%H%M%S.json')
        with open(new_file, 'w') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"Created backup `{new_file}`")

        existing_backups = sorted(self.backup_dir.iterdir(), reverse=True)
        for to_delete in existing_backups[self.num_backups_kept:]:
            to_delete.unlink()

