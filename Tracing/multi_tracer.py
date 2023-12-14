from typing import List

from Tracing.Tracer import Tracer
import inspect
class MultiTracer(Tracer):

    def __init__(self, tracers: List[Tracer]):
        super().__init__()
        self._tracers = tracers
        Tracer.depth = 3


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
