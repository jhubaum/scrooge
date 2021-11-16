import os
import sys

def path():
    return os.getenv("SCROOGE_CONFIG_PATH") or "~/.scrooge"

def initialize():
    raise NotImplementedError("Sorry, you have to initialize the project manually for now. For more information, see the readme")

def load():
    if not os.path.isdir(path()):
        raise RuntimeError("Unable to load config – project probably wasn't initialized correctly")
    sys.path.append(path())
    os.environ["SCROOGE_PATH"] = os.path.abspath(os.path.dirname(__file__))
