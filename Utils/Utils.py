import os
from pathlib import Path
def get_project_dir():
    return Path(__file__).parent.parent

def get_runs_dir():
    return os.path.join(get_project_dir(),"runs")

def get_log_dir():
    return os.path.join(get_project_dir(),"logs")

