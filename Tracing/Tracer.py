import inspect
class Tracer:

    def write(self, text):
        pass
    def info(self, message):
        pass

    def debug(self, message):
        pass

    def error(self, message):
        pass

    def result(self, message):
        pass

    def _get_function(self):
        stack = inspect.stack()
        if len(stack) >= 3:
            return inspect.stack()[2].function
        return ""

