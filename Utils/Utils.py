import os
from pathlib import Path
import json
import numpy as np
import math

def get_project_dir():
    return Path(__file__).parent.parent

def get_runs_dir():
    return os.path.join(get_project_dir(), "runs")

def get_models_dir():
    return os.path.join(get_project_dir(), "Models")

def get_log_dir():
    return os.path.join(get_project_dir(), "logs")

def read_config():
    with open(os.path.join(get_project_dir(), "Config/config.json")) as f:
        return json.load(f)

def formatPrice(n):
    return ("-$" if n < 0 else "$") + "{0:.2f}".format(abs(n))

# returns the vector containing stock data from a fixed file
def getStockDataVec(key):
    vec = []
    file = f"{key}.csv"
    path = os.path.join(get_project_dir(),"Data",file)
    lines = open(path, "r").read().splitlines()

    for line in lines[1:]:
        vec.append(float(line.split(",")[4]))

    return vec

# returns the sigmoid
def sigmoid(x):
    return 1 / (1 + math.exp(-x))

# returns an an n-day state representation ending at time t
def getState(data, t, n):
    d = t - n + 1
    block = data[d:t + 1] if d >= 0 else -d * [data[0]] + data[0:t + 1]  # pad with t0
    res = []
    for i in range(n - 1):
        res.append(sigmoid(block[i + 1] - block[i]))

    return np.array([res])
