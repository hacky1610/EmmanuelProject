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

    def clear_df(self):
        df_new = DataFrame()
        df_new = df_new.append(self._hist_df[0:1])

        for i in range(1, len(self._hist_df)):
            if self._hist_df[i:i + 1]["dateOpen_datetime_utc"].item() > df_new[-1:][
                "dateClosed_datetime_utc"].item():
                df_new = df_new.append(self._hist_df[i:i + 1])

        return df_new

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

    def get_median_invested_amount(self):
        return self._hist_df.investedAmount.median()

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

    def trader_performance(self, ticker: str) -> (bool, str):
        if not self.has_history():
            return False, "no history"

        if self.get_wl_ratio() < 0.7:
            return False, f"Bad Wl Ratio. Ratio is less than 0.7"

        currency_df = self._hist_df[self._hist_df.currency_clean == ticker]
        if currency_df.ig_custom.sum() <= 0:
            return False, "Currency profit is less than null"

        if len(currency_df) < 5:
            return False, f"Less than 5 trades with {ticker}"

        median_open_hours = ((currency_df.dateClosed - currency_df.dateOpen) / 1000 / 60 / 60).median()
        if median_open_hours > 48:
            return False, "Open hours is greater than 48 hours"

        if self._hist_df["ig_custom"].sum() < 400:
            return False, f"IG Profit is bad {self._hist_df.ig_custom.sum()}"

        return True, "OK"

    def __str__(self):
        return f"{self.get_wl_ratio()} - {self.get_ig_profit()}"

    def calc_ig_profit(self, market_store: MarketStore) -> (int, int):

        if len(self._hist_df) == 0:
            return 0, 0

        def stop_and_limit(data, stop_val, limit_val):
            m = market_store.get_market(data.currency_clean)
            if m is None:
                return 0
            pip_wl = abs(data.priceClosed - data.priceOpen) * data.pipMultiplier
            eur_wl = m.get_euro_value(pips=pip_wl)

            if m.get_euro_value(data.worstDrawdown) < stop_val * -1:
                return stop_val * -1
            if m.get_euro_value(data.maxProfit) > limit_val:
                return limit_val

            if data.netPnl > 0:
                return eur_wl
            else:
                return eur_wl * -1

        def get_drawdown(data):
            m = market_store.get_market(data.currency_clean)
            if m is None:
                return 0
            return m.get_euro_value(data.worstDrawdown)

        self._hist_df["drawdown"] = self._hist_df.apply(get_drawdown, axis=1)

        best_col = None
        best_stop = 0
        best_limit = 0
        for stop in [70]:
            for limit in [50]:
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

    def get_diff_to_today(self) -> int:
        if len(self._hist_df) == 0:
            return 1000 #TODO
        last_d = self._unix_timestamp_to_datetime(self._hist_df[-1:].dateClosed.item())
        diff = datetime.now() - last_d
        return diff.days

    def get_series(self):
        rating, text = self._rate_trader()
        return Series(data=[self.get_wl_ratio(),
                            self.get_avg_wl(),
                            self.get_result(),
                            self.get_avg_trades_per_week(),
                            self.amount_of_peaks(),
                            self.get_max_win(),
                            self.get_max_loses(),
                            self.profit_loss_ratio(),
                            self.median_open_hours(),
                            self.open_hours_ratio(),
                            self.get_median_invested_amount(),
                            self._hist_df["drawdown"].min(),
                            self._hist_df["drawdown"].median(),
                            self._hist_df["ig_custom"].sum(),
                            self._hist_df["ig_custom_name"].iloc[0],
                            rating,
                            text],
                      index=["wl_ratio",
                             "avg_wl",
                             "result",
                             "trades_per_week",
                             "amount_of_peaks",
                             "max_win",
                             "max_looses",
                             "profit_loss_ratio",
                             "open_hours",
                             "open_hours_ratio",
                             "invested_amount",
                             "drawdown_min",
                             "drawdown_median",
                             "ig_custom",
                             "ig_custom_name",
                             "rating",
                             "comment"])
