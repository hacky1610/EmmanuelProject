from datetime import datetime

from Tracing.Tracer import Tracer
import inspect
class ConsoleTracer(Tracer):

    def __init__(self, show_debug:bool = False):
        self._show_debug = show_debug

    def write(self, message):
        print(f"{self._get_time()} Info: {super()._get_function()} - {message}")

    def warning(self, message):
        print(f"{self._get_time()} Warning: {super()._get_function()} - {message}")

    def debug(self, message):
        if self._show_debug:
            print(f"{self._get_time()} Debug: {super()._get_function()} - {message}")

    def error(self, message):
        print(f"{self._get_time()} Error: {super()._get_function()} - {message}:")

    def result(self, message):
        print(f"{self._get_time()} Result: {super()._get_function()} - {message}:")

    def _get_time(self):
        return datetime.now().strftime("%H:%M:%S")