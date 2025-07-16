# BL/trade_types.py
from enum import Enum

class TradeResult(Enum):
    SUCCESS = 1
    NOACTION = 2
    ERROR = 3