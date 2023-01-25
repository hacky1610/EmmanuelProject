from Data.data_processor import DataProcessor
import requests
import Utils.Utils
import pandas as pd
from pandas import DataFrame


class Tiingo():

    _BASEURL = "https://api.tiingo.com/tiingo/fx/"

    def __init__(self):
        c = Utils.Utils.read_config()
        self._apykey = c["ti_api_key"]
    def _send_request(self,suffix:str):
        headers = {
            'Content-Type': 'application/json'
        }
        requestResponse = requests.get(
            f"{self._BASEURL}{suffix}&token={self._apykey}&format=json",
            headers=headers)
        return requestResponse.json()

    def _send_history_request(self,ticker,start,end,resolution):
        res = self._send_request(f"{ticker}/prices?resampleFreq={resolution}&startDate={start}&endDate={end}")
        if len(res) == 0:
            return None
        df = DataFrame(res)
        df.drop(columns=["ticker"],inplace=True)
        return df
    def load_data_by_date(self, ticker:str, start:str, end:str, data_processor:DataProcessor, resolution:str= "1hour"):
        res = self._send_history_request(ticker,start,end,resolution)
        data_processor.addSignals(res)
        data_processor.clean_data(res)
        return res

