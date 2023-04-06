from pathlib import Path
import os
import json

def get_project_dir():
    return Path(__file__).parent.parent

class ConfigReader():

    def read_config(self):
        with open(os.path.join(get_project_dir(), "Config/config.json")) as f:
            return json.load(f)