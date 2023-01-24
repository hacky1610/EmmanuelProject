import os
from pathlib import Path
import json

def get_project_dir():
    return Path(__file__).parent.parent

def get_runs_dir():
    return os.path.join(get_project_dir(),"runs")

def get_log_dir():
    return os.path.join(get_project_dir(),"logs")

def read_config():

    with open(os.path.join(get_project_dir(),"Config/credentials.json")) as f:
        return json.load(f)


