from datetime import datetime

from Tracing.Tracer import Tracer
import inspect
class ConsoleTracer(Tracer):
    def write(self, message):
        print(f"{self._get_time()} Info: {super()._get_function()} - {message}")

    def warning(self, message):
        print(f"{self._get_time()} Warning: {super()._get_function()} - {message}")

    def error(self, message):
        print(f"{self._get_time()} Error: {super()._get_function()} - {message}:")

    def result(self, message):
        print(f"{self._get_time()} Result: {super()._get_function()} - {message}:")

    def _get_time(self):
        return datetime.now().strftime("%H:%M:%S")