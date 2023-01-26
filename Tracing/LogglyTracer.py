from Tracing.Tracer import Tracer
from Tracing.Loggly.connection import LogglyConnection

class LogglyTracer(Tracer):

    def __init__(self,token):
        self._log = LogglyConnection(token)
    def write(self, message):
        self._log .create_input(message)

    def error(self, message):
        self._log.create_input(f"Error: {message}")

    def result(self, message):
        print("Result: {}:".format(message))
