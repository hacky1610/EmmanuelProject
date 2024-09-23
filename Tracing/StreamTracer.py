import logging

from Tracing.Tracer import Tracer
import inspect
class StreamTracer(Tracer):

    def __init__(self, verbose = False):
        logging.basicConfig(level=logging.INFO)
        self._logger = logging.getLogger(__name__)
        self._verbose = verbose

    def info(self, message):
        if self._verbose:
            self._logger.info(f"{super()._get_function()} - {message}")

    def debug(self, message):
        if self._verbose:
            self._logger.info(f"{super()._get_function()} - {message}")

    def write(self, message):
        if self._verbose:
            self._logger.info(f"{super()._get_function()} - {message}")

    def error(self, message):
        self._logger.error(f"EmmanuelError:{super()._get_function()} - {message}:")

    def result(self, message):
        self._logger.info(f"Result:{super()._get_function()} - {message}:")
