from Tracing.Tracer import Tracer
class ConsoleTracer(Tracer):
    def write(self, message):
        print(message)

    def error(self, message):
        print("Error: {}:".format(message))

    def result(self, message):
        print("Result: {}:".format(message))
