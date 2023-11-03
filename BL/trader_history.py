from datetime import datetime

import numpy
from pandas import DataFrame, Series


class TraderHistory:

    def __init__(self,hist):
        self._hist_df = self._create_df(hist)
        self._hist = hist
        if len(hist) > 0:
            self._hist_df = self._hist_df.sort_values(by=["dateClosed"])
            self._hist_df = self._hist_df.reset_index()

    def _create_df(self, hist):
        df = DataFrame()

        for t in hist:
            df = df.append(Series(t), ignore_index=True)

        return df

    def get_result(self):
        if len(self._hist_df) == 0:
            return 0

        return self._hist_df.netPnl.sum()

    def get_avg_wl(self):
        if len(self._hist_df) == 0:
            return 0

        return self._hist_df.netPnl.median()


    def amount_of_peaks(self):
        if len(self._hist_df) == 0:
            return 0

        return self._hist_df.netPnl.cumsum()[::5].diff().std()

    def get_avg_wl_10(self):
        if len(self._hist_df) == 0:
            return 0

        return self._hist_df.netPnl[-10:].median()

    def get_wl_ratio(self):
        return (self.get_wl_ratio_100() + self.get_wl_ratio_20()) / 2

    def get_avg_trades_per_week(self):
        if len(self._hist_df) == 0 or len(self._hist_df) < 100:
            return 0


        s = datetime.utcfromtimestamp(self._hist_df.iloc[-99].dateOpen / 1000)
        e = datetime.utcfromtimestamp(self._hist_df.iloc[-1].dateOpen / 1000)
        delta = e - s
        days = delta.total_seconds() / 60 / 60 / 24
        res = len(self._hist_df) * 7 / days
        return res

    def get_wl_ratio_100(self):
        return self._get_wl_ration_custom(100)

    def get_wl_ratio_20(self):
        return self._get_wl_ration_custom(20)

    def get_max_win(self):
        return self._hist_df.netPnl.max()

    def get_max_loses(self):
        return self._hist_df.netPnl.min()

    def _get_wl_ration_custom(self, past):
        if len(self._hist_df) == 0 and len(self._hist_df) < past:
            return 0

        period = self._hist_df[past * - 1:]
        wins = len(period[period.netPnl > 0])

        return wins / len(period)

    def get_avg_seconds(self):
        if len(self._hist) == 0:
            return 0

        open_times = []

        for t in self._hist:
            delta = datetime.utcfromtimestamp(t["dateClosed"] / 1000) - datetime.utcfromtimestamp(t["dateOpen"] / 1000)
            open_times.append(delta.seconds)

        return numpy.median(open_times)

    def show(self, name):
        if len(self._hist_df) == 0:
            return

        import matplotlib.pyplot as plt
        # Erstelle eine Figur mit zwei Subplots (eine Zeile, zwei Spalten)
        plt.figure(figsize=(12, 6))

        # Linie für den Umsatz (blau)
        plt.plot(self._hist_df.index, self._hist_df.netPnl.cumsum(), label=f'Umsatz {name}', color='blue')

        # Linie für die Umsatzänderung (rot, gestrichelt)
        plt.plot(self._hist_df.index, self._hist_df.netPnl.cumsum().diff(), label=f'Umsatzänderung {name}', color='red',
                 linestyle='--')

        plt.title('Umsatz und Umsatzänderung')
        plt.xlabel('Zeit')
        plt.ylabel('Werte')
        plt.legend()  # Fügt eine Legende hinzu, um die beiden Linien zu kennzeichnen
        plt.grid(True)
        plt.show()


    def __str__(self):
        return f"{self.get_wl_ratio()} - {self.get_result()}"

    def get_series(self):
        return Series(data=[self.get_wl_ratio(),
                            self.get_wl_ratio_20(),
                            self.get_wl_ratio_100(),
                            self.get_avg_wl(),
                            self.get_avg_wl_10(),
                            self.get_result(),
                            self.get_avg_trades_per_week(),
                            self.amount_of_peaks(),
                            self.get_max_win(),
                            self.get_max_loses()],
                      index=["wl_ratio",
                             "wl_ratio_20",
                             "wl_ratio_100",
                             "avg_wl",
                             "avg_wl_10",
                             "result",
                             "trades_per_week",
                             "amount_of_peaks",
                             "max_win",
                             "max_looses"])



