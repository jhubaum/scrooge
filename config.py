""" The module that contains everything to read the configuration
"""

import os
import json
import yaml

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

@dataclass
class UserConfig:
    """ The configuration that is stored in the user's yaml file.
    """
    
    # the monthly money available (in Eur)
    available: float
    allocated_for_savings: float
    allocated_for_investments: float

    @staticmethod
    def load_from_yaml_file(filename):
        with open(filename, 'r') as f:
            data = {}
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
    def load(path=None):
        if path is None:
            path = Path(os.environ.get('SCROOGE_CONFIG_DIR', '~/.scrooge')).resolve()
        else:
            path = Path(path)

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

