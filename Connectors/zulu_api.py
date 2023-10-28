from typing import List

import requests

from BL.position import Position
from BL.trader_history import TraderHistory


class ZuluApi:

    _base_uri = "https://www.zulutrade.com/zulutrade-client/trading/api/providers"

    def get_history(self,id):

        resp = requests.get(f"{self._base_uri}/{id}/trades/history?timeframe=10000&page=0&size=100&sort=dateClosed,desc")
        if resp.status_code == 200:
            return TraderHistory(resp.json()["content"])
        else:
            return TraderHistory([])

    def get_opened_positions(self,id:str, name:str ) -> List[Position]:
        positions:List[Position] = []
        resp = requests.get(f"{self._base_uri}/{id}/trades/open/all?timeframe=10000&calculateProfit=true")
        if resp.status_code == 200:
            for p in resp.json():
                p["trader_id"] = id
                p["trader_name"] = name
                positions.append(Position(p))

        return positions

