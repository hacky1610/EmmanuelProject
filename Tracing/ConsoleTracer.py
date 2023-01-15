from Tracer import Tracer
class ConsoleTracer(Tracer):
    def Info(self, message):
        print(message)

    def Error(self, message):
        print("Error: {}:".format(message))

    def Result(self, message):
        print("Result: {}:".format(message))
