import os

import Tracing.Tracer


class FileTracer(Tracing.Tracer.Tracer):
    _file = ""

    def __init__(self, file):
        self._file = file

    def write(self, text):
        with open(self._file, "a") as f:
            f.write("{}\n".format(text))

    def Info(self, message):
        self.write(message)

    def Error(self, message):
        self.write("Error: {}:".format(message))

    def Result(self, message):
        self.write("Result: {}:".format(message))
