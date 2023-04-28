from datetime import date, timedelta

from BL.data_processor import DataProcessor
import requests
from pandas import DataFrame
import pandas as pd
from Tracing.Tracer import Tracer
from BL.utils import BaseReader
from enum import Enum

# class syntax
class TradeType(Enum):
    FX = 1
    STOCK = 2
    CRYPTO = 3
    IEX = 4
    METAL = 5

class Tiingo:
    _BASEURL = "https://api.tiingo.com/tiingo/"

    def __init__(self, conf_reader: BaseReader, tracer: Tracer = Tracer()):
        self._apykey = conf_reader.get("ti_api_key")
        self._tracer = tracer

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

    def get_uri_for_trade_type(self, trade_type:TradeType,symbol:str=str):
        if trade_type == TradeType.FX or trade_type == TradeType.METAL:
            return f"fx/{symbol}/prices?"
        elif trade_type == TradeType.CRYPTO:
            return f"crypto/prices?tickers={symbol}&"
        elif trade_type == TradeType.IEX:
            return f"iex/{symbol}/prices?"
        return ""

    def _send_history_request(self, ticker: str, start: str, end: str, resolution: str, trade_type:TradeType=TradeType.FX) -> DataFrame:
        end_date_string = ""
        if end != None:
            end_date_string = f"&endDate={end}"

        res = self._send_request(f"{self.get_uri_for_trade_type(trade_type,ticker)}resampleFreq={resolution}&startDate={start}{end_date_string}")
        if len(res) == 0:
            self._tracer.error("Could not load history")
            return DataFrame()
        if trade_type == TradeType.CRYPTO:
            df = DataFrame(DataFrame(res).priceData[0])
        else:
            df = DataFrame(res)
            df.drop(columns=["ticker"], inplace=True)
        return df

    def load_data_by_date(self, ticker: str, start: str, end: str, data_processor: DataProcessor,
                          resolution: str = "1hour", add_signals: bool = True,
                          clean_data: bool = True, trade_type:TradeType=TradeType.FX,
                          trim:bool=False) -> DataFrame:
        res = self._send_history_request(ticker, start, end, resolution,trade_type)
        if len(res) == 0:
            return res
        if trim:
            res = res[:-1]
        if add_signals:
            data_processor.addSignals(res)
        if clean_data:
            data_processor.clean_data(res)
        return res

    def load_live_data_last_days(self, symbol: str, dp: DataProcessor, trade_type):

        start_time = (date.today() - timedelta(days=6)).strftime("%Y-%m-%d")
        return self.load_data_by_date(ticker=symbol,
                                    start=start_time,
                                    end=None,
                                    data_processor=dp,
                                    trade_type=trade_type,
                                    resolution="1hour",
                                    trim=True)


    def load_live_data(self, symbol: str, dp:DataProcessor, trade_type):

        start_time = (date.today() - timedelta(days=30)).strftime("%Y-%m-%d")
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
                                       resolution="5min")

        return df, df_eval
