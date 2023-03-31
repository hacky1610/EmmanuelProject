from Data.data_processor import DataProcessor
import requests
from pandas import DataFrame
from Tracing.Tracer import Tracer
from LSTM_Logic import Utils


class Tiingo:
    _BASEURL = "https://api.tiingo.com/tiingo/fx/"

    def __init__(self, tracer: Tracer = Tracer()):
        c = Utils.read_config()
        self._apykey = c["ti_api_key"]
        self._tracer = tracer

    def _send_request(self, suffix: str):
        try:
            headers = {
                'Content-Type': 'application/json'
            }
            request_response = requests.get(
                f"{self._BASEURL}{suffix}&token={self._apykey}&format=json",
                headers=headers)
            return request_response.json()
        except Exception as e:
            self._tracer.error(f"Exception during _send_request {e}")
            return ""

    def _send_history_request(self, ticker: str, start: str, end: str, resolution: str) -> DataFrame:
        end_date_string = ""
        if end != None:
            end_date_string = f"&endDate={end}"

        res = self._send_request(f"{ticker}/prices?resampleFreq={resolution}&startDate={start}{end_date_string}")
        if len(res) == 0:
            self._tracer.error("Could not load history")
            return DataFrame()
        df = DataFrame(res)
        df.drop(columns=["ticker"], inplace=True)
        return df

    def load_data_by_date(self, ticker: str, start: str, end: str, data_processor: DataProcessor,
                          resolution: str = "1hour", add_signals:bool=True, clean_data:bool = True) -> DataFrame:
        res = self._send_history_request(ticker, start, end, resolution)
        if len(res) == 0:
            return res
        if add_signals:
            data_processor.addSignals(res)
        if clean_data:
            data_processor.clean_data(res)
        return res
