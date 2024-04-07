from Tracing.Tracer import Tracer
from Tracing.Loggly.connection import LogglyConnection


class LogglyTracer(Tracer):

    def __init__(self, token: str, type: str, mode: str = ""):
        self._log = LogglyConnection(token)
        self.type = type
        self._prefix: str = ""
        self._mode: str = mode

    def write(self, message):
        self._log.create_input(
            f"[TI {self.type}] | {self._mode} | INFO | {self._prefix} | {self._get_function()} | {message}")

    def info(self, message):
        self._log.create_input(
            f"[TI {self.type}] | {self._mode} | INFO | {self._prefix} | {self._get_function()} | {message}")

    def debug(self, message):
        self._log.create_input(
            f"[TI {self.type}] | {self._mode} | DEBUG | {self._prefix} | {self._get_function()} | {message}")

    def error(self, message):
        self._log.create_input(
            f"[TI {self.type}] | {self._mode} | ERROR | {self._prefix} | {self._get_function()} | {message}")

    def warning(self, message):
        self._log.create_input(
            f"[TI {self.type}] | {self._mode} | WARNING | {self._prefix} | {self._get_function()} | {message}")

    def result(self, message):
        print("Result: {}:".format(message))

    def set_prefix(self, prefix):
        self._prefix = prefix
