import inspect
from wonderwords import RandomWord

class Tracer:

    depth = 2

    def __init__(self):
        self.name = ""

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
        func_name = ""
        if len(stack) >= Tracer.depth +1 :
            func_name =  inspect.stack()[ Tracer.depth].function
        return Tracer._set_string_len(func_name)

    def _get_random_name(self):
        if self.name == "":
            r = RandomWord()
            self.name = f"{r.word(include_categories=['adjective'])}_{r.word(include_categories=['noun'])}"
        return Tracer._set_string_len(self.name)

    @staticmethod
    def _set_string_len(text, min_len = 20):
        if len(text) >= min_len:
            return text
        else:
            return text + " " * ((min_len - len(text)) + 1)



