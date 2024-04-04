from Tracing.Tracer import Tracer
import inspect
class ConsoleTracer(Tracer):

    def info(self, message):
        print(f"{super()._get_function()} - {message}")

    def debug(self, message):
        print(f"{super()._get_function()} - {message}")

    def write(self, message):
        print(f"{super()._get_function()} - {message}")

    def error(self, message):
        print(f"Error:{super()._get_function()} - {message}:")

    def result(self, message):
        print(f"Result:{super()._get_function()} - {message}:")
