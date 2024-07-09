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
                          resolution: str = "1hour", add_signals: bool = True,
                          clean_data: bool = True, trade_type: TradeType = TradeType.FX,
                          use_cache: bool = True, validate: bool = True, suffix:str="mega") -> DataFrame:
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
                res = cached.append(res[res.date > cached[-1:].date.item()])
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
            self._cache.save_cache(res, name)
        else:
            end_str = TimeUtils.get_time_string(datetime.strptime(end, "%Y-%m-%d"))
            res = res[res.date < end_str]

        start_str = TimeUtils.get_time_string(datetime.strptime(start, "%Y-%m-%d"))
        res = res[start_str < res.date]
        res = res.reset_index()

        if add_signals:
            data_processor.addSignals(res)
        if clean_data:
            data_processor.clean_data(res)
        if validate:
            self._validate(res)
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



    def load_trade_data(self, symbol: str, dp: DataProcessor, trade_type, days: int = 30):

        start_time = self._get_start_time(days=days)
        return self.load_data_by_date(ticker=symbol,
                                      start=start_time,
                                      end=None,
                                      data_processor=dp,
                                      trade_type=trade_type,
                                      resolution="1hour",
                                      suffix="")

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
                data = df.append(data)
            end_time = start_time + timedelta(days=1)
            start_time = end_time - timedelta(days=window)

        if len(data) == 0:
            return data

        self._cache.save_cache(data, name)
        print(f"Saved {name}")
        return data

    def init_data(self, symbol: str, trade_type, days: int = 100, suffix:str = ""):

        self._load_long_period(symbol=symbol, trade_type=trade_type,
                               days=days, resolution="1hour", use_cache=False, suffix=suffix)
        self._load_long_period(symbol=symbol, trade_type=trade_type,
                               days=days, resolution="5min", use_cache=False, suffix=suffix)

    def load_train_data(self, symbol: str, dp: DataProcessor, trade_type, days_start: int = 4 * 365, days_end:int = 300):

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

    def load_test_data(self, symbol: str, dp: DataProcessor, trade_type, days: int = 300, use_cache=True):

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
        df_eval = self.load_data_by_date(ticker=symbol,
                                         start=start_time,
                                         end=None,
                                         data_processor=dp,
                                         use_cache=use_cache,
                                         trade_type=trade_type,
                                         resolution="5min",
                                         add_signals=False,
                                         validate=False,
                                         suffix="mega")
        return df, df_eval