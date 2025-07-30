import hashlib
import math
from datetime import date, timedelta, datetime
from BL import DataProcessor, BaseReader
import requests
from pandas import DataFrame
import pandas as pd

from Predictors.utils import TimeUtils
from Tracing.Tracer import Tracer
from enum import Enum
from Connectors.dropbox_cache import DropBoxCache


# class syntax
class TradeType(Enum):
    FX = 1
    STOCK = 2
    CRYPTO = 3
    IEX = 4
    METAL = 5

class Tiingo:
    _BASEURL = "https://api.tiingo.com/tiingo/"

    def __init__(self, conf_reader: BaseReader, cache: DropBoxCache, tracer: Tracer = Tracer()):
        self._apykey = conf_reader.get("ti_api_key")
        self._tracer = tracer
        self._cache = cache

    def _send_request(self, suffix: str):
        try:
            headers = {
                'Content-Type': 'application/json'
            }
            request_response = requests.get(
                f"{self._BASEURL}{suffix}&token={self._apykey}&format=json",
                headers=headers)
            if request_response.status_code == 200:
                return request_response.json()
            else:
                self._tracer.error(f"Exception during _send_request {request_response.text}")
                return ""
        except Exception as e:
            self._tracer.error(f"Exception during _send_request {e}")
            return ""

    @staticmethod
    def get_uri_for_trade_type(trade_type: TradeType, symbol: str = str):
        if trade_type == TradeType.FX or trade_type == TradeType.METAL:
            return f"fx/{symbol}/prices?"
        elif trade_type == TradeType.CRYPTO:
            return f"crypto/prices?tickers={symbol}&"
        elif trade_type == TradeType.IEX:
            return f"iex/{symbol}/prices?"
        return ""

    def _send_history_request(self, ticker: str, start: str, end: str, resolution: str,
                              trade_type: TradeType = TradeType.FX) -> DataFrame:
        end_date_string = ""
        if end is not None:
            end_date_string = f"&endDate={end}"

        res = self._send_request(
            f"{self.get_uri_for_trade_type(trade_type, ticker)}resampleFreq={resolution}&startDate={start}{end_date_string}")
        if len(res) == 0:
            self._tracer.error("Could not load history")
            return DataFrame()
        if trade_type == TradeType.CRYPTO:
            df = DataFrame(DataFrame(res).priceData[0])
        else:
            df = DataFrame(res)
            df.drop(columns=["ticker"], inplace=True)
            df = df[:-1]

        return df

    def load_data_by_date(self, ticker: str, start: str, end: str, data_processor: DataProcessor,
                          resolution: str = "1hour", add_signals: bool = True, save_cache:bool = False,
                          clean_data: bool = True, trade_type: TradeType = TradeType.FX,
                          use_cache: bool = True, validate: bool = True, suffix:str="mega",
                          fix_close_price = False, remove_sundays = False) -> DataFrame:
        name = f"{ticker}_{resolution}{suffix}.csv"
        cached = self._cache.load_cache(name)

        if len(cached) > 0 and use_cache:
            lastchached = pd.to_datetime(cached[-1:].date.item())
            now = datetime.utcnow().replace(tzinfo=lastchached.tzinfo)
            toCompare = datetime(now.year, now.month, now.day, now.hour, tzinfo=lastchached.tzinfo) - timedelta(hours=1)
            if lastchached.to_pydatetime() == toCompare:
                res = cached
            elif end is None:
                res = self._send_history_request(ticker, TimeUtils.get_date_string(lastchached), end, resolution,
                                                 trade_type)
                # Sicherstellen, dass das Datum im letzten Eintrag von 'cached' als Wert extrahiert wird
                last_date = cached.iloc[-1].date  # Letztes Datum aus 'cached' extrahieren

                # Nur die Einträge in 'res' auswählen, die ein späteres Datum haben
                new_rows = res[res.date > last_date]
                res = pd.concat([cached, new_rows], ignore_index=True)
            else:
                start_str = TimeUtils.get_time_string(datetime.strptime(start, "%Y-%m-%d"))
                end_str = TimeUtils.get_time_string(datetime.strptime(end, "%Y-%m-%d"))
                res = cached[start_str < cached.date]
                res = res[res.date < end_str]
        else:
            res = self._send_history_request(ticker, start, end, resolution, trade_type)

        if len(res) == 0:
            return res

        if end is None:
            if save_cache:
                self._cache.save_cache(res, name)
        else:
            end_str = TimeUtils.get_time_string(datetime.strptime(end, "%Y-%m-%d"))
            res = res[res.date < end_str]

        start_str = TimeUtils.get_time_string(datetime.strptime(start, "%Y-%m-%d"))



        if remove_sundays:
            res['date_pd'] = pd.to_datetime(res['date'], utc=True)

            # Wochentag extrahieren
            res['weekday'] = res['date_pd'].dt.weekday  # 6 = Sonntag

            # Nur Montag bis Samstag (0–5)
            res = res[res['weekday'] != 6].copy()
            res = res.reset_index(drop=True)

        if fix_close_price:
            close = self.get_last_hour_of_yesterday(ticker, data_processor, TradeType.FX)
            old_close = res.loc[res.index[-1], "close"]
            self._tracer.debug(f"{ticker} replace {old_close} with {close}")
            res.loc[res.index[-1], "close"] = close

        if add_signals:
            data_processor.addSignals(res)
        if clean_data:
            data_processor.clean_data(res)
        if validate:
            self._validate(res)
        res = res[start_str < res.date]
        res = res.reset_index(drop=True)
        return res

    @staticmethod
    def _validate(res):
        last_date = res.date.iloc[-1]
        current_date = TimeUtils.get_time_string(datetime.utcnow() - timedelta(hours=1))
        if last_date != current_date:
            raise Exception(f"Invalid date. Last date {last_date} - Current {current_date} ")

    @staticmethod
    def _get_start_time(days: int):
        return TimeUtils.get_date_string(date.today() - timedelta(days=days))



    def load_trade_data(self, symbol: str, dp: DataProcessor, trade_type, days: int = 300):

        start_time = self._get_start_time(days=days)
        return self.load_data_by_date(ticker=symbol,
                                      start=start_time,
                                      end=None,
                                      validate=False,
                                      data_processor=dp,
                                      trade_type=trade_type,
                                      resolution="1day",
                                      use_cache=False,
                                      suffix="", fix_close_price=True, remove_sundays=True)

    def _load_long_period(self, symbol: str,
                          trade_type, days: int = 100,
                          resolution: str = "1hour",
                          window: int = 10,
                          use_cache: bool = True,
                          suffix: str = ""):
        name = f"{symbol}_{resolution}{suffix}.csv"

        cache = self._cache.load_cache(name)
        if len(cache) > 0:
            return

        data = DataFrame()

        end_time = datetime.now()
        start_time = end_time - timedelta(days=window)
        for i in range(0, days, window):
            df = self._send_history_request(ticker=symbol,
                                            start=TimeUtils.get_date_string(start_time),
                                            end=TimeUtils.get_date_string(end_time),
                                            trade_type=trade_type,
                                            resolution=resolution, )
            if len(data) == 0:
                data = df
            else:
                if "date" in df.columns:
                    df = df[df.date < data[0:1].date.item()]
                else:
                    break
                data = pd.concat([df, data], ignore_index=True)
            end_time = start_time + timedelta(days=1)
            start_time = end_time - timedelta(days=window)

        if len(data) == 0:
            return data

        self._cache.save_cache(data, name)
        print(f"Saved {name}")
        return data

    def init_data(self, symbol: str, trade_type, days: int = 100, suffix:str = ""):


        #self._load_long_period(symbol=symbol, trade_type=trade_type,
        #                       days=days, resolution="1day", use_cache=False, suffix=suffix, window=100)
        #self._load_long_period(symbol=symbol, trade_type=trade_type,
        #                       days=days, resolution="1hour", use_cache=False, suffix=suffix)
        self._load_long_period(symbol=symbol, trade_type=trade_type,
                               days=days, resolution="5min", use_cache=False, suffix=suffix)

    def load_train_data(self, symbol: str, dp: DataProcessor, trade_type, days_start: int = 365 * 1.5, days_end= None):

        start_time = self._get_start_time(days=days_start)
        end_time = self._get_start_time(days=days_end)
        df = self.load_data_by_date(ticker=symbol,
                                    start=start_time,
                                    end=end_time,
                                    data_processor=dp,
                                    trade_type=trade_type,
                                    resolution="1hour",
                                    validate=False)
        df_eval = self.load_data_by_date(ticker=symbol,
                                         start=start_time,
                                         end=end_time,
                                         data_processor=dp,
                                         trade_type=trade_type,
                                         resolution="5min",
                                         add_signals=False,
                                         validate=False)
        return df, df_eval

    def load_test_data(self, symbol: str, dp: DataProcessor, trade_type, days: int = 1200, use_cache=True, save_cache=True):

        start_time = self._get_start_time(days=days)
        df = self.load_data_by_date(ticker=symbol,
                                    start=start_time,
                                    end=None,
                                    data_processor=dp,
                                    use_cache=use_cache,
                                    trade_type=trade_type,
                                    resolution="1day",
                                    validate=False,
                                    save_cache=save_cache,
                                    suffix="mega", remove_sundays=True)
        df_eval = self.load_data_by_date(ticker=symbol,
                                         start=start_time,
                                         end=None,
                                         data_processor=dp,
                                         use_cache=use_cache,
                                         trade_type=trade_type,
                                         resolution="1hour",
                                         add_signals=False,
                                         save_cache=save_cache,
                                         validate=False,
                                         suffix="mega")
        return df, df_eval

    def load_test_data_hour(self, symbol: str, dp: DataProcessor, trade_type, days: int = 1200, use_cache=True,
                       save_cache=True):

        start_time = self._get_start_time(days=days)
        df = self.load_data_by_date(ticker=symbol,
                                    start=start_time,
                                    end=None,
                                    data_processor=dp,
                                    use_cache=use_cache,
                                    trade_type=trade_type,
                                    resolution="1hour",
                                    validate=False,
                                    save_cache=save_cache,
                                    suffix="mega", remove_sundays=True)
        df_eval = self.load_data_by_date(ticker=symbol,
                                         start=start_time,
                                         end=None,
                                         data_processor=dp,
                                         use_cache=use_cache,
                                         trade_type=trade_type,
                                         resolution="5min",
                                         add_signals=False,
                                         save_cache=save_cache,
                                         validate=False,
                                         suffix="mega")
        return df, df_eval

    def load_hour_data(self, symbol: str, dp: DataProcessor, trade_type, days: int = 1200, use_cache=True):

        start_time = self._get_start_time(days=days)
        df = self.load_data_by_date(ticker=symbol,
                                    start=start_time,
                                    end=None,
                                    data_processor=dp,
                                    use_cache=use_cache,
                                    trade_type=trade_type,
                                    resolution="1hour",
                                    validate=False,
                                    suffix="mega")

        return df

    def get_last_hour_of_yesterday(self, symbol: str, dp: DataProcessor, trade_type):
        from datetime import datetime, timedelta
        import pandas as pd

        # Hole die letzten 7–14 Tage Stunden-Daten
        df_hour = self.load_hour_data(symbol, dp, trade_type, days=14, use_cache=False)
        df_hour['date'] = pd.to_datetime(df_hour['date'], utc=True)

        # Extrahiere Datum und Uhrzeit
        df_hour['day'] = df_hour['date'].dt.date
        df_hour['hour'] = df_hour['date'].dt.hour

        # Filter auf Stunden == 23:00 UTC
        df_23 = df_hour[df_hour['hour'] == 23].copy()

        if df_23.empty:
            raise ValueError(f"Keine 23:00 UTC Daten vorhanden für {symbol}")

        # Sortiere nach Datum absteigend und nimm den letzten vollständigen Tag
        letzter_tag = df_23['day'].max()
        letzter_eintrag = df_23[df_23['day'] == letzter_tag].iloc[0]

        return letzter_eintrag['close']
