from Tracing.Tracer import Tracer
from Tracing.Loggly.connection import LogglyConnection

class LogglyTracer(Tracer):

    def __init__(self,token:str,type:str):
        self._log = LogglyConnection(token)
        self.type = type
    def write(self, message):
        self._log.create_input(f"[{self.type}] - INFO: : {message}")

    def debug(self, message):
        self._log.create_input(f"[{self.type}] - DEBUG: : {message}")

    def error(self, message):
        self._log.create_input(f"[{self.type}] - ERROR: {message}")

    def result(self, message):
        print("Result: {}:".format(message))
