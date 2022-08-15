""" The module that contains everything to read the configuration
"""

import os
import yaml

from dataclasses import dataclass

@dataclass
class UserConfig:
    """ The configuration that is stored in the user's yaml file.
    """
    
    # the monthly money available (in Eur)
    available: float

    @staticmethod
    def load_from_yaml_file(filename):
        with open(filename, 'r') as f:
            data = {}
            for keys in yaml.safe_load(f):
                # TODO: Test here if a key is set twice and throw an error if so
                data = { **data, **keys }

            # TODO: Check for unknown keys here
            # TODO: Print better errors here as well
            return UserConfig(available=data['available'])


@dataclass
class Config:
    user: UserConfig
    database_path: str

    @staticmethod
    def load(path=None):
        if path is None:
            path = os.environ.get('SCROOGE_CONFIG_DIR', os.path.expanduser('~/.scrooge'))

        if not os.path.isdir(path):
            print("Config directory {path} doesn't exist. Exiting")
            exit(1)

        return Config(
            user=UserConfig.load_from_yaml_file(os.path.join(path, 'config.yml')),
            database_path=os.path.join(path, 'database.sqlite'))
