

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
        if len(self._hist) == 0:
            return 0

        wins = 0
        lost = 0

        for t in self._hist:
            if t["netPnl"] > 0:
                wins += 1
            else:
                lost += 1

        return wins / (wins + lost)

    def __str__(self):
        return f"{self.get_wl_ratio()} - {self.get_result()}"


