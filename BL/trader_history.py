from datetime import datetime

import numpy
from pandas import DataFrame, Series

from Connectors.market_store import MarketStore


class TraderHistory:

    def __init__(self, hist):
        self._hist_df = self._create_df(hist)
        self._hist = hist
        if len(hist) > 0:
            self._hist_df = self._hist_df.sort_values(by=["dateClosed"])
            self._hist_df = self._hist_df.reset_index(drop=True)
            self._hist_df["dateOpen_datetime_utc"] = self._hist_df.dateOpen.apply(self._unix_timestamp_to_datetime)
            self._hist_df["dateClosed_datetime_utc"] = self._hist_df.dateClosed.apply(self._unix_timestamp_to_datetime)
            self._hist_df["currency_clean"] = self._hist_df.currency.str.replace("/", "")

    def has_history(self):
        return len(self._hist_df) > 0

    @staticmethod
    def _create_df(hist):
        df = DataFrame()

        for t in hist:
            df = df.append(Series(t), ignore_index=True)

        return df

    @staticmethod
    def _unix_timestamp_to_datetime(timestamp):
        return datetime.utcfromtimestamp(timestamp / 1000)

    def get_ig_profit(self) -> float:
        return self._hist_df["ig_custom"].sum()

    def get_result(self) -> float:
        if len(self._hist_df) == 0:
            return 0

        return self._hist_df.netPnl.sum()

    def get_avg_wl(self):
        if len(self._hist_df) == 0:
            return 0

        return self._hist_df.netPnl.median()

    def profit_loss_ratio(self):
        wins = self._hist_df[self._hist_df.netPnl > 0]
        loss = self._hist_df[self._hist_df.netPnl < 0]
        return abs(loss.netPnl.median() / abs(wins.netPnl.median()))

    def amount_of_peaks(self):
        if len(self._hist_df) == 0:
            return 0

        return self._hist_df.netPnl.cumsum()[::5].diff().std()

    def get_avg_wl_10(self):
        if len(self._hist_df) == 0:
            return 0

        return self._hist_df.netPnl[-10:].median()

    def get_wl_ratio(self) -> float:
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

    def _rate_trader(self) -> (str, str):
        trade = "TRADE"
        skip = "SKIP"

        if self.get_wl_ratio() < 0.7:
            return skip, "Bad WL Ratio"

        if self.get_avg_trades_per_week() > 50:
            return skip, "To much trades"

        if self.get_max_loses() < -100:
            return skip, "To big looses"

        d = (datetime.now() - self._hist_df.iloc[-1].dateOpen_datetime_utc)
        days = d.total_seconds() / 60 / 60 / 24

        if days > 7:
            return skip, "Last Trade older than 7 days"

        return trade, ""

    def get_stop_distance(self, ticker:str) -> float:

        for _,i in self._hist_df.iterrows():
            print(i["currency_clean"])
            pips = self._calc_pip_euro(i)
            print(pips)
        return

    def _calc_pip_euro(self, data):
        netPnl = abs(data["grossPnl"])
        pips = abs(data.priceOpen - data.priceClosed)
        pipMultiplier = data["pipMultiplier"]

        # Berechnungen
        PnL_per_pip = netPnl / pips
        PnL_per_euro = PnL_per_pip * pipMultiplier

        desired_loss_euro = 20.0
        stop_loss_euro = desired_loss_euro
        return stop_loss_euro / PnL_per_euro * data["amount"]


    def median_open_hours(self) -> float:
        return ((self._hist_df.dateClosed - self._hist_df.dateOpen) / 1000 / 60 / 60).median()

    def median_open_hours_wins(self) -> float:
        wins = self._hist_df[self._hist_df.netPnl > 0]
        return ((wins.dateClosed - wins.dateOpen) / 1000 / 60 / 60).median()

    def median_open_hours_loss(self) -> float:
        loss = self._hist_df[self._hist_df.netPnl < 0]
        return ((loss.dateClosed - loss.dateOpen) / 1000 / 60 / 60).median()

    def open_hours_ratio(self) -> float:
        return self.median_open_hours_loss() / self.median_open_hours_wins()

    def trader_performance(self, ticker:str) -> (bool, str):
        currency_df = self._hist_df[self._hist_df.currency_clean == ticker]
        if currency_df.netPnl.sum() <= 0:
            return False, "Currency profit is less than null"

        if len(currency_df) < 5:
            return False, f"Less than 5 trades with {ticker}"

        median_open_hours = ((currency_df.dateClosed - currency_df.dateOpen) / 1000 /60 / 60 ).median()
        if median_open_hours > 48:
            return False, "Open hours is creater than 24 hours"

        if self._hist_df["ig_custom"].sum() < 400:
            return False, f"IG Profit is bad {self._hist_df.ig_custom.sum()}"

        if self.get_avg_trades_per_week() > 50:
            return False, f"To much trades {self.get_avg_trades_per_week()} per week"

        return True, "OK"

    def __str__(self):
        return f"{self.get_wl_ratio()} - {self.get_ig_profit()}"

    def calc_ig_profit(self, market_store:MarketStore) -> (int, int):

        if len(self._hist_df) == 0:
            return 0,0
        def no_stop_no_limit(data):
            m  = market_store.get_market(data.currency_clean)
            pip_wl = abs(data.priceClosed - data.priceOpen) * data.pipMultiplier
            eur_wl = pip_wl / m.pip_euro

            if data.netPnl > 0:
                return eur_wl
            else:
                return eur_wl * -1

        def stop_and_limit(data, stop, limit):
            m = market_store.get_market(data.currency_clean)
            pip_wl = abs(data.priceClosed - data.priceOpen) * data.pipMultiplier
            eur_wl = pip_wl / m.pip_euro

            if data.worstDrawdown / m.pip_euro < stop * -1:
                return stop * -1
            if data.maxProfit / m.pip_euro > limit:
                return limit

            if data.netPnl > 0:
                return eur_wl
            else:
                return eur_wl * -1

        def only_stop(data, stop):
            m = market_store.get_market(data.currency_clean)
            pip_wl = abs(data.priceClosed - data.priceOpen) * data.pipMultiplier
            eur_wl = pip_wl / m.pip_euro

            if data.worstDrawdown / m.pip_euro < stop * -1:
                return stop * -1

            if data.netPnl > 0:
                return eur_wl
            else:
                return eur_wl * -1

        self._hist_df["ig_profit_no_stop_no_limit"] = self._hist_df.apply(no_stop_no_limit, axis=1)
        self._hist_df["ig_profit_stop_limit_equal_10"] = self._hist_df.apply(stop_and_limit, axis=1, args=(10,10))
        self._hist_df["ig_profit_stop_limit_equal_20"] = self._hist_df.apply(stop_and_limit, axis=1, args=(20,20))
        self._hist_df["ig_profit_stop_limit_equal_30"] = self._hist_df.apply(stop_and_limit, axis=1, args=(30,30))
        self._hist_df["ig_profit_stop_limit_equal_50"] = self._hist_df.apply(stop_and_limit, axis=1, args=(50, 50))
        self._hist_df["ig_profit_stop_20"] = self._hist_df.apply(only_stop, axis=1, args=(20,))
        self._hist_df["ig_profit_stop_50"] = self._hist_df.apply(only_stop, axis=1, args=(50,))
        self._hist_df["ig_profit_stop_20_limit_10"] = self._hist_df.apply(stop_and_limit, axis=1, args=(20, 10))
        self._hist_df["ig_profit_stop_50_limit_20"] = self._hist_df.apply(stop_and_limit, axis=1, args=(50, 25))

        best_col = None
        best_stop = 0
        best_limit = 0
        for stop in range(20,71,10):
            for limit in range(20, 71, 10):
                col = self._hist_df.apply(stop_and_limit, axis=1, args=(stop, limit))
                if best_col is None:
                    best_col = col
                    best_stop = stop
                    best_limit = limit
                if col.sum() > best_col.sum():
                    best_col = col
                    best_stop = stop
                    best_limit = limit

        self._hist_df["ig_custom"] = best_col
        self._hist_df["ig_custom_name"] = f"Stop {best_stop} Limit {best_limit}"
        self._hist = self._hist_df.to_dict("records")
        return best_stop, best_limit


    def get_ig_profit_no_stop_no_limit(self):
        return self._hist_df["ig_profit_no_stop_no_limit"].sum()

    def get_series(self):
        rating, text = self._rate_trader()
        return Series(data=[self.get_wl_ratio(),
                            self.get_wl_ratio_20(),
                            self.get_wl_ratio_100(),
                            self.get_avg_wl(),
                            self.get_avg_wl_10(),
                            self.get_result(),
                            self.get_avg_trades_per_week(),
                            self.amount_of_peaks(),
                            self.get_max_win(),
                            self.get_max_loses(),
                            self.profit_loss_ratio(),
                            self.median_open_hours(),
                            self.median_open_hours_wins(),
                            self.median_open_hours_loss(),
                            self.open_hours_ratio(),
                            self._hist_df["ig_profit_no_stop_no_limit"].sum(),
                            self._hist_df["ig_profit_stop_limit_equal_10"].sum(),
                            self._hist_df["ig_profit_stop_limit_equal_20"].sum(),
                            self._hist_df["ig_profit_stop_limit_equal_30"].sum(),
                            self._hist_df["ig_profit_stop_limit_equal_50"].sum(),
                            self._hist_df["ig_profit_stop_20"].sum(),
                            self._hist_df["ig_profit_stop_50"].sum(),
                            self._hist_df["ig_profit_stop_20_limit_10"].sum(),
                            self._hist_df["ig_profit_stop_50_limit_20"].sum(),
                            self._hist_df["ig_custom"].sum(),
                            self._hist_df["ig_custom_name"].iloc[0],
                            rating,
                            text],
                      index=["wl_ratio",
                             "wl_ratio_20",
                             "wl_ratio_100",
                             "avg_wl",
                             "avg_wl_10",
                             "result",
                             "trades_per_week",
                             "amount_of_peaks",
                             "max_win",
                             "max_looses",
                             "profit_loss_ratio",
                             "open_hours",
                             "open_hours_wins",
                             "open_hours_loss",
                             "open_hours_ratio",
                             "ig_profit_no_stop_no_limit",
                             "ig_profit_stop_limit_equal_10",
                             "ig_profit_stop_limit_equal_20",
                             "ig_profit_stop_limit_equal_30",
                             "ig_profit_stop_limit_equal_50",
                             "ig_profit_stop_20",
                             "ig_profit_stop_50",
                             "ig_profit_stop_20_limit_10",
                             "ig_profit_stop_50_limit_20",
                             "ig_custom",
                             "ig_custom_name",
                             "rating",
                             "comment"])
