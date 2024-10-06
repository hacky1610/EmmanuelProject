import time
import random
from typing import List

import requests

from BL.position import Position
from BL.trader_history import TraderHistory
from Tracing.Tracer import Tracer


class ZuluApi:
    _base_uri = "https://www.zulutrade.com/zulutrade-client/trading/api/providers"

    def __init__(self, tracer: Tracer):
        self._tracer = tracer

    def get_history(self, trader_id: str, pages: int = 1, size=100):

        result = []
        for i in range(0, pages):
            resp = requests.get(
                f"{self._base_uri}/{trader_id}/trades/history?timeframe=10000&page={i}&size={size}&sort=dateClosed,desc")
            if resp.status_code == 200:
                result = result + resp.json()["content"]
            if pages > 1:
                time.sleep(random.randint(120, 200))
        return TraderHistory(result)

    def get_opened_positions(self, trader_id: str, name: str) -> List[Position]:
        positions: List[Position] = []
        resp = requests.get(f"{self._base_uri}/{trader_id}/trades/open/all?timeframe=10000&calculateProfit=true")
        if resp.status_code == 200:
            if len(resp.json()) == 0:
                self._tracer.write(f"No open positions from trader {trader_id}")
                return positions
            for p in resp.json():
                p["trader_id"] = trader_id
                p["trader_name"] = name
                positions.append(Position(p))
        else:
            self._tracer.error(f"Could not read open positions {resp.text}")
            raise Exception("Could not read open positions")

        return positions