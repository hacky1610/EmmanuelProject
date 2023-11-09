from Tracing.Tracer import Tracer
from Tracing.ConsoleTracer import ConsoleTracer



class Analytics:

    def __init__(self, tracer: Tracer = ConsoleTracer()):
        self._tracer = tracer

    @staticmethod
    def _create_additional_info(row, *args):
        text = ""
        for i in args:
            text += f"{i}:" + "{0:0.5}".format(row[i]) + "\r\n"

        return text



