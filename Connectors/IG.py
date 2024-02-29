import time
from enum import Enum
from typing import List, Optional

import pandas
from trading_ig import IGService
from trading_ig.rest import IGException
from BL import BaseReader
from Connectors.deal_store import DealStore
from Connectors.market_store import MarketStore
from Tracing.ConsoleTracer import ConsoleTracer
from Tracing.Tracer import Tracer
from pandas import DataFrame, Series
import re
from Connectors.tiingo import TradeType


# Define an enumeration class
class TradeResult(Enum):
    SUCCESSFUL = 1
    NOT_SUCCESSFUL = 2
    EXCEPTION = 3


class IG:

    def __init__(self, conf_reader: BaseReader, tracer: Tracer = ConsoleTracer(), acount_type: str = "DEMO"):
        self.ig_service: IGService = None
        self.user = conf_reader.get("ig_demo_user")
        self.password = conf_reader.get("ig_demo_pass")
        self.key = conf_reader.get("ig_demo_key")
        self.accNr = conf_reader.get("ig_demo_acc_nr")
        self.type = acount_type
        self.intelligent_stop_border = conf_reader.get_float("is_border", 13)
        self.intelligent_stop_distance = conf_reader.get_float("is_distance", 6)
        if self.type == "DEMO":
            self._fx_id = 264139
            self._crypto_id = 1002200
            self._gold_id = 104139
            self._silver_id = 264211
        else:
            self._fx_id = 342535
            self._crypto_id = None
            self._gold_id = None
            self._silver_id = None
        self._tracer: Tracer = tracer
        self.connect()
        self._excluded_markets = ["CHFHUF", "EMFX USDTWD ($1 Contract)", "EMFX USDPHP ($1 Contract)",
                                  "EMFX USDKRW ($1 Contract)",
                                  "EMFX USDINR ($1 Contract)", "EMFX USDIDR ($1 Contract)", "EMFX INRJPY",
                                  "EMFX GBPINR (1 Contract)", "NZDGBP",
                                  "NZDEUR", "NZDAUD", "AUDGBP", "AUDEUR", "GBPEUR"]

        self._symbol_reference = {
            "CS.D.BCHUSD.CFD.IP":
                {
                    "symbol": "BCHUSD",
                    "size": 1,
                    "currency": "USD"
                },
            "CS.D.BCHUSD.CFE.IP":
                {
                    "symbol": "BCHEUR",
                    "size": 1,
                    "currency": "EUR"
                },
            # Gold
            "CS.D.CFDGOLD.CFDGC.IP":
                {
                    "symbol": "XAUUSD",
                    "size": 1,
                    "currency": "USD"
                },
            # Silber
            "CS.D.CFDSILVER.CFM.IP":
                {
                    "symbol": "XAGUSD",
                    "size": 0.5,
                    "currency": "USD"
                }
        }
        self._tracer.debug(f"IG Config: Stop Border {self.intelligent_stop_border} Distance {self.intelligent_stop_distance}")

    def _get_markets_by_id(self, market_id):
        try:
            res = self.ig_service.fetch_sub_nodes_by_node(market_id)
        except Exception as ex:
            self._tracer.error(f"Error while fetching nodes: {ex}")
            time.sleep(10)
            return DataFrame()

        if len(res["nodes"]) > 0:
            markets = DataFrame()
            for i in res["nodes"].id:
                markets = markets.append(self._get_markets_by_id(i))
            return markets
        else:
            return res["markets"]

    def _set_symbol(self, markets):
        for m in markets:
            epic = m["epic"]
            if epic in self._symbol_reference:
                m["symbol"] = self._symbol_reference[epic]["symbol"]
                m["size"] = self._symbol_reference[epic]["size"]
                m["currency"] = self._symbol_reference[epic]["currency"]

        return markets

    def adapt_stop_level(self, deal_id: str, limit_level: float, stop_level: float):

        return self.ig_service.update_open_position(deal_id=deal_id, limit_level=limit_level,
                                                    stop_level=stop_level)

    def intelligent_stop_level(self, position: Series, market_store: MarketStore, deal_store:DealStore):
        open_price = position.level
        bid_price = position.bid
        offer_price = position.offer
        stop_level = position.stopLevel
        limit_level = position.limitLevel
        direction = position.direction
        deal_id = position.dealId
        scaling_factor = position.scalingFactor
        ticker = position.instrumentName.replace("/", "").replace(" Mini", "")

        self._tracer.debug(
            f"{ticker} {direction} {deal_id} {open_price} {bid_price} {offer_price} {stop_level} {limit_level}")



        market = market_store.get_market(ticker)
        if direction == "BUY":
            if bid_price > open_price:
                diff = market.get_euro_value(pips=bid_price - open_price, scaling_factor=scaling_factor)
                if diff > self.intelligent_stop_border:
                    new_stop_level = bid_price - market.get_pip_value(euro=self.intelligent_stop_distance,
                                                                      scaling_factor=scaling_factor)
                    if new_stop_level > stop_level:
                        self._adjust_stop_level(deal_id, limit_level, new_stop_level, deal_store)
        else:
            if offer_price < open_price:
                diff = market.get_euro_value(pips=open_price - offer_price, scaling_factor=scaling_factor)
                if diff > self.intelligent_stop_border:
                    new_stop_level = offer_price + market.get_pip_value(euro=self.intelligent_stop_distance,
                                                                        scaling_factor=scaling_factor)
                    if new_stop_level < stop_level:
                        self._adjust_stop_level(deal_id, limit_level, new_stop_level, deal_store)

    def _adjust_stop_level(self, deal_id: str, limit_level: float, new_stop_level: float, deal_store):
        self._tracer.debug(f"Change Stop level to {new_stop_level}")
        res = self.adapt_stop_level(deal_id=deal_id, limit_level=limit_level, stop_level=new_stop_level)
        self._tracer.debug(res)
        if res["dealStatus"] != "ACCEPTED":
            self._tracer.error("Stop level cant be adapted")
        else:
            deal = deal_store.get_deal_by_deal_id(deal_id)
            deal.set_intelligent_stop_level(new_stop_level)
            deal_store.save(deal)

    def get_markets(self, trade_type: TradeType, tradeable: bool = True) -> List:
        if trade_type == TradeType.FX:
            return self._get_markets(self._fx_id, tradeable)
        elif trade_type == TradeType.CRYPTO:
            markets = self._get_markets(self._crypto_id, tradeable)  # 668997 is only Bitcoin Cash
            return self._set_symbol(markets)
        elif trade_type == TradeType.METAL:
            gold = self._get_markets(self._gold_id, tradeable)  # Gold
            silver = self._get_markets(self._silver_id, tradeable)
            return self._set_symbol(gold + silver)

        return []

    @staticmethod
    def _get_spread(market_object):
        offer = market_object.offer
        bid = market_object.bid
        scaling = market_object.scalingFactor

        if offer is not None and bid is not None:
            return (offer - bid) * scaling

        return 0

    def _get_markets(self, market_id: int, tradebale: bool = True) -> List:
        market_df = self._get_markets_by_id(market_id)
        markets = []

        if len(market_df) == 0:
            return markets

        if tradebale:
            market_df = market_df[market_df.marketStatus == "TRADEABLE"]
        for _, market in market_df.iterrows():
            symbol = (market.instrumentName.replace("/", "").replace(" Mini", "")).strip()
            if symbol not in self._excluded_markets:
                markets.append({
                    "symbol": symbol,
                    "epic": market.epic,
                    "spread": self._get_spread(market),
                    "scaling": market.scalingFactor,
                    "size": 1.0,
                    "currency": self._get_currency(market.epic)
                })

        return markets

    def connect(self):
        # no cache
        self.ig_service = IGService(
            self.user, self.password, self.key, self.type, acc_number=self.accNr
        )
        try:
            self.ig_service.create_session()
        except Exception as ex:
            self._tracer.error(f"Error during open a IG Connection {ex}")

    @staticmethod
    def _get_currency(epic: str):
        m = re.match("[\w]+\.[\w]+\.[\w]{3}([\w]{3})\.", epic)
        if m != None and len(m.groups()) == 1:
            return m.groups()[0]
        return "USD"

    def open(self,
             epic: str,
             direction: str,
             stop: Optional[int] = 25,
             limit: Optional[int] = 25,
             size: float = 1.0,
             currency: str = "USD") -> (TradeResult, dict):

        deal_response: dict = {}
        try:
            response = self.ig_service.create_open_position(
                currency_code=currency,
                direction=direction,
                epic=epic,
                expiry="-",
                force_open=True,
                guaranteed_stop=False,
                order_type="MARKET",
                size=size,
                level=None,
                limit_distance=limit,
                limit_level=None,
                quote_id=None,
                stop_distance=stop,
                stop_level=None,
                trailing_stop=False,
                trailing_stop_increment=None
            )
            if response["dealStatus"] != "ACCEPTED":
                reason = response['reason']
                if reason == "INSUFFICIENT_FUNDS":
                    self._tracer.warning(f"could not open trade: {response['reason']} for {epic}")
                    result = TradeResult.NOT_SUCCESSFUL
                else:
                    result = TradeResult.EXCEPTION
                    self._tracer.error(f"could not open trade (Unknown Reason): {response['reason']} for {epic}")
            else:
                self._tracer.write(f"Opened successfull {epic}. Deal details {response}")
                result = TradeResult.SUCCESSFUL
            deal_response = response
        except IGException as ex:
            self._tracer.error(f"Error during open a position. {ex} for {epic}")
            result = TradeResult.EXCEPTION

        return result, deal_response

    def close(self,
              direction: str,
              deal_id: str,
              size: float = 1.0, ) -> (bool, dict):

        deal_response: dict = {}
        result = False
        try:
            response = self.ig_service.close_open_position(
                direction=direction,
                epic=None,
                expiry="-",
                order_type="MARKET",
                size=size,
                level=None,
                quote_id=None,
                deal_id=deal_id
            )
            if response["dealStatus"] != "ACCEPTED":
                self._tracer.error(f"could not close trade: {response['reason']}")
            else:
                self._tracer.write(f"Close successfull {deal_id}. Deal details {response}")
                result = True
            deal_response = response
        except IGException as ex:
            self._tracer.error(f"Error during close a position. {ex} for {deal_id}")

        return result, deal_response

    def get_deals(self) -> DataFrame:

        try:
            response = self.ig_service.fetch_open_positions()
            return response
        except IGException as ex:
            self._tracer.error(f"Error during getting Deal Ids {ex}")
        return DataFrame()

    def get_size_of_deal(self, deal_id: str):
        positions = self.ig_service.fetch_open_positions()
        pos = positions[positions.dealId == deal_id]
        return pos["size"].item()

    @staticmethod
    def get_inverse(direction: str) -> str:
        if direction == "SELL":
            return "BUY"
        else:
            return "SELL"

    def get_opened_positions(self) -> DataFrame:
        return self.ig_service.fetch_open_positions()

    def get_transaction_history(self, days: int, trans_type="ALL_DEAL") -> DataFrame:
        df = DataFrame()
        for i in range(1, days):
            if i % 5 == 0:
                time.sleep(42)
            df = df.append(self.ig_service.fetch_transaction_history(trans_type=trans_type, page_size=50,
                                                                     max_span_seconds=60 * 60 * 24 * days,
                                                                     page_number=i))
        return df.reset_index()

    def get_current_balance(self):
        balance = self.ig_service.fetch_accounts().loc[0].balance
        if balance == None:
            return 0
        return balance

    def _calc_report(self, hist: DataFrame):
        trades = hist[hist.transactionType == "TRADE"]

        payed_kapital_fees_list = hist[hist.instrumentName == "Kapitalertragssteuer"]
        return_kapital_ertrag_list = hist[hist.instrumentName == "Verrechnung Kapitalertragsteuer"]

        payed_kapital_fees = payed_kapital_fees_list.profit_float.sum()
        return_kapital_fees = return_kapital_ertrag_list.profit_float.sum()
        payed_kapital_fees_netto = int(payed_kapital_fees * -1 - return_kapital_fees)

        result = trades.profit_float.sum()
        wins = trades[trades.profit_float > 0].profit_float.sum()
        losses = trades[trades.profit_float < 0].profit_float.sum()

        print(f"Result {result}€")
        print(f"Wins {wins}€")
        print(f"Looses {losses}€")
        print(f"Payed kapital fees {payed_kapital_fees_netto}€")

    def create_report(self, load_live=False):

        if load_live:
            hist = self.get_transaction_history(100, "ALL")
            temp = hist['profitAndLoss'].str.replace('E', '')
            hist['profit_float'] = temp.str.replace(',', '').astype(float)
        else:
            hist = pandas.read_csv("./trades.csv")

        y23 = hist[hist.date <= "2023-12-31"]
        y24 = hist[hist.date > "2023-12-31"]

        print("2023")
        self._calc_report(y23)

        print("2024")
        self._calc_report(y24)
