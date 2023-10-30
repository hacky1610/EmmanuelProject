import inspect
class Tracer:

    depth = 2

    def write(self, text):
        pass
    def info(self, message):
        pass

    def debug(self, message):
        pass

    def error(self, message):
        pass

    def warning(self, message):
        pass

    def result(self, message):
        pass

    def set_prefix(self, prefix):
        pass

    @staticmethod
    def _get_function():
        stack = inspect.stack()
        if len(stack) >= Tracer.depth +1 :
            return inspect.stack()[ Tracer.depth].function
        return ""

