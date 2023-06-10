from datetime import date, timedelta, datetime
from BL import DataProcessor, BaseReader
import requests
from pandas import DataFrame
import pandas as pd
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
                          trim: bool = False) -> DataFrame:
        res = DataFrame()
        name = f"{ticker}_{resolution}.csv"
        cached = self._cache.load_cache(name)

        if len(cached) > 0:
            lastchached = pd.to_datetime(cached[-1:].date.item())
            now = datetime.utcnow().replace(tzinfo=lastchached.tzinfo)
            toCompare = datetime(now.year, now.month, now.day, now.hour, tzinfo=lastchached.tzinfo) - timedelta(hours=1)
            if lastchached.to_pydatetime() == toCompare:
                res = cached
            else:
                res = self._send_history_request(ticker, lastchached.strftime("%Y-%m-%d"), end, resolution, trade_type)
                res = cached.append(res[res.date > cached[-1:].date.item()])
        else:
            res = self._send_history_request(ticker, start, end, resolution, trade_type)

        if len(res) == 0:
            return res

        self._cache.save_cache(res, name)

        if add_signals:
            data_processor.addSignals(res)
        if clean_data:
            data_processor.clean_data(res)
        return res

    @staticmethod
    def _get_start_time(days: int):
        return (date.today() - timedelta(days=days)).strftime("%Y-%m-%d")

    def load_trade_data(self, symbol: str, dp: DataProcessor, trade_type, days: int = 30):

        start_time = self._get_start_time(days=days)
        return self.load_data_by_date(ticker=symbol,
                                      start=start_time,
                                      end=None,
                                      data_processor=dp,
                                      trade_type=trade_type,
                                      resolution="1hour",
                                      trim=True)

    def load_train_data(self, symbol: str, dp: DataProcessor, trade_type, days: int = 30):

        start_time = self._get_start_time(days=days)
        df = self.load_data_by_date(ticker=symbol,
                                    start=start_time,
                                    end=None,
                                    data_processor=dp,
                                    trade_type=trade_type,
                                    resolution="1hour",
                                    trim=True)
        df_eval = self.load_data_by_date(ticker=symbol,
                                         start=start_time,
                                         end=None,
                                         data_processor=dp,
                                         trade_type=trade_type,
                                         resolution="5min",
                                         add_signals=False)
        return df, df_eval
