from Tracing.Tracer import Tracer
from Tracing.Loggly.connection import LogglyConnection

class LogglyTracer(Tracer):

    _prefix: str = ""

    def __init__(self,token:str,type:str):
        self._log = LogglyConnection(token)
        self.type = type

    def write(self, message):
        self._log.create_input(f"[{self.type}] | INFO | {self._prefix} | {self._get_function()} | {message}")

    def debug(self, message):
        self._log.create_input(f"[{self.type}] | DEBUG | {self._prefix} | {self._get_function()} | {message}")

    def error(self, message):
        self._log.create_input(f"[{self.type}] | ERROR | {self._prefix} | {self._get_function()} | {message}")

    def warning(self, message):
        self._log.create_input(f"[{self.type}] | WARNING | {self._prefix} | {self._get_function()} | {message}")

    def result(self, message):
        print("Result: {}:".format(message))

    def set_prefix(self, prefix):
        self._prefix = prefix
