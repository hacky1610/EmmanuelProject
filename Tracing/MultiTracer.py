from typing import List

from Tracing.Tracer import Tracer

class MultiTracer(Tracer):

    def __init__(self, tracers:[Tracer]):
        self._tracers:List[Tracer] = tracers

    def write(self, message):
        for t in self._tracers:
            t.write(message)

    def info(self, message):
        for t in self._tracers:
            t.info(message)

    def debug(self, message):
        for t in self._tracers:
            t.debug(message)

    def error(self, message):
        for t in self._tracers:
            t.error(message)

    def warning(self, message):
        for t in self._tracers:
            t.warning(message)

    def result(self, message):
        for t in self._tracers:
            t.result(message)

    def set_prefix(self, prefix):
        self._prefix = prefix
