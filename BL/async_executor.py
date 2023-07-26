import os
from multiprocessing import Process


class AsyncExecutor:

    process_list = []


    def run(self, target,args):
        while self.is_full():
            pass
        p = Process(target=target, args=args)
        p.start()
        self.process_list.append(p)


    def is_full(self):
        if len(self.process_list) < os.cpu_count() - 1:
            return False
        else:
            for p in self.process_list:
                if not p.is_alive():
                    self.process_list.remove(p)
                    return False

        return True