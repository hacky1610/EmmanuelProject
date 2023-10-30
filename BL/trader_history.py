from datetime import datetime

import numpy


class TraderHistory:

    def __init__(self,hist):
        self._hist = hist

    def get_result(self):
        result = 0

        if len(self._hist) == 0:
            return result

        for t in self._hist:
            result += t["netPnl"]
        return result

    def get_wl_ratio(self):
        return (self.get_wl_ratio_100() + self.get_wl_ratio_20()) / 2

    def get_wl_ratio_100(self):
        return self._get_wl_ration_custom(100)

    def get_wl_ratio_20(self):
        return self._get_wl_ration_custom(20)

    def _get_wl_ration_custom(self, past):
        if len(self._hist) == 0 and len(self._hist) < past:
            return 0

        wins = 0
        lost = 0

        for t in self._hist[:past]:
            if t["netPnl"] > 0:
                wins += 1
            else:
                lost += 1

        return wins / (wins + lost)

    def get_avg_seconds(self):
        if len(self._hist) == 0:
            return 0

        open_times = []

        for t in self._hist:
            delta = datetime.utcfromtimestamp(t["dateClosed"] / 1000) - datetime.utcfromtimestamp(t["dateOpen"] / 1000)
            open_times.append(delta.seconds)

        return numpy.median(open_times)

    def __str__(self):
        return f"{self.get_wl_ratio()} - {self.get_result()}"


