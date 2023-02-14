import os

import Tracing.Tracer


class FileTracer(Tracing.Tracer.Tracer):
    _file = ""

    def __init__(self, file):
        self._file = file

    def write(self, text):
        with open(self._file, "a") as f:
            f.write("{}\n".format(text))

    def info(self, message):
        self.write(message)

    def error(self, message):
        self.write("Error: {}:".format(message))

    def result(self, message):
        self.write("Result: {}:".format(message))
