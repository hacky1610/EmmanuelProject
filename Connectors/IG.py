import time
from typing import List, Optional

import pandas
from trading_ig import IGService
from trading_ig.rest import IGException
from BL import BaseReader
from Connectors.market_store import MarketStore
from Tracing.ConsoleTracer import ConsoleTracer
from Tracing.Tracer import Tracer
from pandas import DataFrame, Series
import re
from Connectors.tiingo import TradeType


class IG:

    def __init__(self, conf_reader: BaseReader, tracer: Tracer = ConsoleTracer(), acount_type: str = "DEMO"):
        self.ig_service: IGService = None
        self.user = conf_reader.get("ig_demo_user")
        self.password = conf_reader.get("ig_demo_pass")
        self.key = conf_reader.get("ig_demo_key")
        self.accNr = conf_reader.get("ig_demo_acc_nr")
        self.type = acount_type
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

    def adapt_stop_level(self, dealId:str, limitLevel:float, stopLevel:float):

        return self.ig_service.update_open_position(deal_id=dealId, limit_level=limitLevel,
                                           stop_level=stopLevel)

    def intelligent_stop_level(self, pos:Series, ms:MarketStore ):

        #wenn Buy -> bid
        #wenn Sell -> offer
        openPrice = pos.level
        bidPrice = pos.bid
        offerPrice = pos.offer
        stopLevel = pos.stopLevel
        limitLevel = pos.limitLevel
        direction = pos.direction
        dealId = pos.dealId
        scalingFactor = pos.scalingFactor
        ticker = pos.instrumentName.replace("/","")
        ticker = ticker.replace(" Mini", "")

        self._tracer.debug(f"{ticker} {direction} {dealId} {openPrice} {bidPrice} {offerPrice} {stopLevel} {limitLevel}")

        market = ms.get_market(ticker)
        if direction == "BUY":
            self._tracer.debug("Buy")
            if bidPrice > openPrice:
                self._tracer.debug("bid greater than open")
                diff = (bidPrice - openPrice) * scalingFactor / market.pip_euro
                if diff > 10:
                    self._tracer.debug(f"Diff {diff}")
                    new_stopLevel = bidPrice - (market.pip_euro * 5 / scalingFactor)
                    if new_stopLevel > stopLevel:
                        self._tracer.debug(f"Change Stop level")
                        res = self.adapt_stop_level(dealId=dealId, limitLevel=limitLevel, stopLevel=new_stopLevel)
                        self._tracer.debug(res)
                        if res["dealStatus"] != "ACCEPTED":
                            self._tracer.error("Stop level cant be adapted")

        else:
            self._tracer.debug("Sell")
            if offerPrice < openPrice:
                self._tracer.debug("offer smaller than open")
                diff = (openPrice - offerPrice) * scalingFactor / market.pip_euro
                if diff > 10:
                    self._tracer.debug(f"Diff {diff}")
                    new_stopLevel = offerPrice + (market.pip_euro * 5 / scalingFactor)
                    if new_stopLevel < stopLevel:
                        self._tracer.debug(f"Change Stop level")
                        res = self.adapt_stop_level(dealId=dealId, limitLevel=limitLevel, stopLevel=new_stopLevel)
                        self._tracer.debug(res)
                        if res["dealStatus"] != "ACCEPTED":
                            self._tracer.error("Stop level cant be adapted")



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

    def _get_markets(self, id: int, tradebale: bool = True) -> List:
        market_df = self._get_markets_by_id(id)
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
             currency: str = "USD") -> (bool, dict):

        deal_response: dict = {}
        result = False
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
                else:
                    self._tracer.error(f"could not open trade (Unknown Reason): {response['reason']} for {epic}")
            else:
                self._tracer.write(f"Opened successfull {epic}. Deal details {response}")
                result = True
            deal_response = response
        except IGException as ex:
            self._tracer.error(f"Error during open a position. {ex} for {epic}")

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
            response = self.ig_service.fetch_open_positions(
            )
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
        for i in range(1,days):
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

    def _calc_report(self, hist:DataFrame):
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
