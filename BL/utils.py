from pathlib import Path
import os
import json

def get_project_dir():
    return Path(__file__).parent.parent

class BaseReader:

    def get(self, key: str):
        raise NotImplementedError

class ConfigReader(BaseReader):
    _config = {}

    def __init__(self):
        with open(os.path.join(get_project_dir(), "Config/config.json")) as f:
            self._config =  json.load(f)

    def get(self,key:str):
        return self._config[key]

class EnvReader(BaseReader):

    def get(self,key:str):
        return os.getenv(key)
