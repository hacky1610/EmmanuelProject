import logging

from Tracing.Tracer import Tracer
import inspect
class StreamTracer(Tracer):

    def __init__(self):
        logging.basicConfig(level=logging.INFO)
        self._logger = logging.getLogger(__name__)

    def info(self, message):
        self._logger.info(f"{super()._get_function()} - {message}")

    def debug(self, message):
        self._logger.debug(f"{super()._get_function()} - {message}")

    def write(self, message):
        self._logger.info(f"{super()._get_function()} - {message}")

    def error(self, message):
        self._logger.error(f"Error:{super()._get_function()} - {message}:")

    def result(self, message):
        self._logger.info(f"Result:{super()._get_function()} - {message}:")
