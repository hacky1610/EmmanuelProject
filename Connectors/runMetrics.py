import os
import json


class FileHandler():
    _best_runs_file = "best_runs.json"
    _runs = {}

    def __init__(self, run_folder: str = "../runs"):
        self._best_runs_file = os.path.join(run_folder, "best_runs.json")
        self._load()

    def save(self):
        with open(self._best_runs_file, mode="w") as writer:
            writer.write(json.dumps(self._runs))

    def _load(self):
        if self._does_file_exist():
            with open(self._best_runs_file, mode="r") as reader:
                content = reader.read()
            self._runs = json.loads(content)

    def _does_file_exist(self):
        return os.path.exists(self._best_runs_file)

    def get_last_run(self, id: str):
        if id in self._runs:
            return self._runs[id]
        else:
            return None

    def set_last_run(self, id: str, content: dict):
        self._runs[id] = content


class RunMetric():

    def __init__(self, file_handler: FileHandler):
        self._fileHandler = file_handler

    def is_better_than_last(self, id: str, content: dict):
        last = self._fileHandler.get_last_run(id)
        if last == None:
            return True
        else:
            return content["total_profit"] > last["total_profit"]

    def save(self, id: str, content: dict):
        self._fileHandler.set_last_run(id, content)
        self._fileHandler.save()
