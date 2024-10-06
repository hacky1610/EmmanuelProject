from datetime import datetime


class Position:

    def __init__(self, data):
        self._data = data

    def get_open_time(self):
        return datetime.utcfromtimestamp(int(self._data["dateTime"] / 1000))

    def get_ticker(self):
        return self._data["currencyName"].replace("/", "")

    def get_direction(self):
        return self._data["tradeType"]

    def get_trader_id(self):
        return self._data["trader_id"]

    def get_id(self):
        return f"{self._data['trader_id']}_{self._data['dateTime']}"

    def __str__(self):
        return f"{self.get_ticker()} by {self._data['trader_name']} opened {self.get_open_time()}"