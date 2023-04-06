from pathlib import Path
import os
import json

def get_project_dir():
    return Path(__file__).parent.parent


def read_config():
    with open(os.path.join(get_project_dir(), "Config/config.json")) as f:
        return json.load(f)