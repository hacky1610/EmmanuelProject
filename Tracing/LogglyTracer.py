from Tracing.Tracer import Tracer
from Tracing.Loggly.connection import LogglyConnection

class LogglyTracer(Tracer):

    def __init__(self,token:str,type:str):
        self._log = LogglyConnection(token)
        self.type = type
    def write(self, message):
        self._log.create_input(f"[{self.type}] | INFO | {self._get_function()} | {message}")

    def debug(self, message):
        self._log.create_input(f"[{self.type}] | DEBUG | {self._get_function()} | {message}")

    def error(self, message):
        self._log.create_input(f"[{self.type}] | ERROR | {self._get_function()} | {message}")

    def result(self, message):
        print("Result: {}:".format(message))
