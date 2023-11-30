from datetime import datetime, timedelta
from typing import List, Optional
import re
import time

from pandas import DataFrame

from BL import DataProcessor
from Connectors.IG import IG
from Connectors.deal_store import Deal, DealStore
from Connectors.market_store import MarketStore
from Connectors.tiingo import TradeType, Tiingo
from Connectors.trader_store import TraderStore
from Connectors.zulu_api import ZuluApi
from Tracing.Tracer import Tracer
from UI.zulutrade import ZuluTradeUI


class ZuluTrader:

    def __init__(self, deal_storage: DealStore, market_storage:MarketStore, zulu_api: ZuluApi, zulu_ui: ZuluTradeUI,
                 ig: IG, trader_store: TraderStore, tracer: Tracer, tiingo: Tiingo,
                 account_type: str, check_for_crash: bool = True, stop_ratio: float = 8.0,
                 limit_ratio:float = 4.0, check_trader_quality:bool = False):
        self._deal_storage = deal_storage
        self._zulu_api = zulu_api
        self._ig = ig
        self._max_minutes = 10
        self._trader_store = trader_store
        self._tracer = tracer
        self._zulu_ui = zulu_ui
        self._min_wl_ration = 0.67
        self._tiingo = tiingo
        self._account_type = account_type
        self._check_for_crash = check_for_crash
        self._limit_ratio = limit_ratio
        self._stop_ratio = stop_ratio
        self._check_trader_quality = check_trader_quality
        self._market_store = market_storage

    def trade(self):
        self._tracer.debug(f"Check crash: {self._check_for_crash }")
        self._close_open_positions()
        if not self._is_crash():
            self._open_new_positions()
        self._update_deals()

    def _is_good_trader(self, trader_id: str):
        if not self._check_trader_quality:
            self._tracer.debug("Ignore Trader check")
            return True

        deals = self._deal_storage.get_deals_of_trader_as_df(trader_id, consider_account_type=False)

        if len(deals) < 3:
            self._tracer.debug(f"Trader {trader_id} had less than 3 trades")
            return False

        if deals.profit.sum() < 0:
            self._tracer.debug(f"Trader {trader_id} had bad profit {deals.profit.sum()}€")
            return False

        if deals.profit.min() < -50:
            self._tracer.debug(f"Trader {trader_id} had really bad lose of  {deals.profit.min()}€")
            return False

        self._tracer.debug(f"Trader {trader_id} is a good trader")

        return True


    def _get_deals_to_close(self):
        deals_to_close = []
        start = time.time()
        open_positions_zulu = self._zulu_ui.get_my_open_positions()
        self._tracer.debug(f"Open Zulu Positions {open_positions_zulu}. Needed time {time.time() - start}")
        start = time.time()
        open_ig_deals = self._ig.get_opened_positions()
        self._tracer.debug(f"Open Ig Positions {open_ig_deals} Needed time {time.time() - start}")
        start = time.time()
        closed_positions_zulu = self._zulu_ui.get_my_closed_positions()
        self._tracer.debug(f"Closed Zulu Positions {closed_positions_zulu} Needed time {time.time() - start}")
        start = time.time()
        open_deals_db = self._deal_storage.get_open_deals()
        self._tracer.debug(f"Open Deals drom DB {open_deals_db} Needed time {time.time() - start}")

        if len(open_deals_db) == 0 and len(open_ig_deals) > 0:
            self._tracer.error("Something is wrong")

        for open_deal in open_deals_db:
            if len(open_ig_deals[open_ig_deals.dealId == open_deal.dealId]) == 0:
                self._tracer.warning(f"StopLoss: The deal {open_deal} seems to be already closed in IG")
                open_deal.close("ByIG")
                self._deal_storage.save(open_deal)
                continue

            if (len(open_positions_zulu) == 0 or
                    len(open_positions_zulu[open_positions_zulu.position_id == open_deal.id]) == 0):
                self._tracer.write(f"Position {open_deal} is not listed as open")
                if len(closed_positions_zulu[closed_positions_zulu.position_id == open_deal.id]) == 0:
                    self._tracer.error(f"Cant find position {open_deal} in open nor in closed positions")
                deals_to_close.append(open_deal)
            else:
                self._tracer.debug(f"Position {open_deal} is still open")
        return deals_to_close

    def _close_open_positions(self):
        self._tracer.debug("Close positions")
        for open_deal in self._get_deals_to_close():
            result, _ = self._ig.close(direction=self._ig.get_inverse(open_deal.direction),
                                       deal_id=open_deal.dealId)
            if result:
                self._tracer.write(f"Position {open_deal} closed")
                open_deal.close("ByApp")
                self._deal_storage.save(open_deal)
            else:
                deals = self._ig.get_deals()
                if len(deals[deals.dealId == open_deal.dealId]) == 0:
                    self._tracer.warning("There was en error during close. But the deal is not open anymore")
                    open_deal.close("ByIG")
                    self._deal_storage.save(open_deal)
                else:
                    self._tracer.error(f"Position {open_deal} could not be closed")

    def _get_market_by_ticker_or_none(self, markets: List, ticker: str) -> Optional[dict]:
        for m in markets:
            if m["symbol"] == ticker:
                return m
        return None

    def _open_new_positions(self):
        self._tracer.debug("Open positions")

        markets = self._ig.get_markets(trade_type=TradeType.FX, tradeable=True)
        if len(markets) == 0:
            self._tracer.warning("market closed")
            return

        for _, position in self._get_positions().iterrows():
            self._tracer.write(f"try to trade {position}")
            self._trade_position(markets=markets, position_id=position.position_id,
                                 trader_id=position.trader_id, direction=position.direction, ticker=position.ticker)

    def _calc_limit_stop(self, symbol, scaling:float) -> (float, float):
        data = self._tiingo.load_trade_data(symbol, DataProcessor(), trade_type=TradeType.FX, days=10)
        atr = data.iloc[-1].ATR
        return atr * self._limit_ratio * scaling, atr * self._stop_ratio * scaling

    def _trade_position(self, markets: List, position_id: str,
                        ticker: str, trader_id: str, direction: str):

        trader_db = self._trader_store.get_trader_by_id(trader_id)
        trade, message = trader_db.hist.currency_performance(ticker)
        if not trade:
            self._tracer.warning(f"Trader {trader_id} has bad performance with {ticker}. {message}")
            return

        if not self._is_good_trader(trader_id):
            self._tracer.debug(f"Trader {trader_id} is a bad trader")
            return

        if self._deal_storage.has_id(position_id):
            self._tracer.debug(f"Position {position_id} - {ticker} by {trader_id} is already open")
            return

        if self._deal_storage.position_is_open(ticker):
            self._tracer.write(
                f"There is already an open position of {ticker}")
            return

        m = self._get_market_by_ticker_or_none(markets, ticker)
        if m is None:
            self._tracer.warning(f"Could not find market for {ticker}")
            return

        self._tracer.write(f"Try to open position {position_id} - {ticker} by {trader_id}")
        _, atr_stop = self._calc_limit_stop(ticker, m["scaling"])
        market = self._market_store.get_market(ticker)
        ig_stop = market.pip_euro * 20

        self._tracer.debug(f"IG {ig_stop} - Atr Stop {atr_stop}")

        if ig_stop < atr_stop:
            stop = ig_stop
            limit = ig_stop
        else:
            stop = atr_stop
            limit = atr_stop

        result, deal_response = self._ig.open(epic=m["epic"], direction=direction,
                                              currency=m["currency"], limit=limit,
                                              stop=stop)
        if result:
            self._tracer.debug("Save Deal in db")
            date_string = re.match("\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", deal_response['date'])
            date_string = date_string.group().replace(" ", "T")

            self._deal_storage.save(Deal(zulu_id=position_id, ticker=ticker,
                                         dealReference=deal_response["dealReference"],
                                         dealId=deal_response["dealId"], trader_id=trader_id,
                                         epic=m["epic"], direction=direction, account_type=self._account_type,
                                         open_date_ig_str=date_string,
                                         open_date_ig_datetime=datetime.strptime(date_string, '%Y-%m-%dT%H:%M:%S'),
                                         stop_ratio=self._stop_ratio,limit_ratio=self._limit_ratio))
            self._tracer.debug("Deal was saved")
        else:
            self._tracer.error(f"Error while open position {position_id} - {ticker} by {trader_id}")

    def _calc_hist(self, row):
        try:
            trader = self._trader_store.get_trader_by_name(row.trader_name)
            return trader.hist.get_wl_ratio()
        except Exception as e:
            self._tracer.error(f"Trader {row.trader_name} could not be found {e}")
            return 0.0

    def _get_trader_id(self, row):
        try:
            trader = self._trader_store.get_trader_by_name(row.trader_name)
            return trader.id
        except Exception as e:
            self._tracer.error(f"Trader {row.trader_name} could not be found {e}")
            return "unknown"

    def _get_newest_positions(self, positions: DataFrame) -> DataFrame:
        return positions[positions.time >= datetime.now() - timedelta(minutes=20)]

    def _get_positions(self) -> DataFrame:
        positions = self._zulu_ui.get_my_open_positions()
        if len(positions) == 0:
            self._tracer.write("No open positions")
            return positions

        # Filter for time
        positions = self._get_newest_positions(positions)
        if len(positions) == 0:
            self._tracer.debug("All postions are to old")
            return positions

        positions["wl_ratio"] = positions.apply(self._calc_hist, axis=1)
        positions["trader_id"] = positions.apply(self._get_trader_id, axis=1)

        # Filter for quality
        good_positions = positions[positions.wl_ratio > self._min_wl_ration]
        if len(good_positions) == 0:
            self._tracer.debug(
                f"All postions are from bad traders. This postions are bad: \n {positions[positions.wl_ratio <= self._min_wl_ration]}")
            return good_positions

        good_positions = good_positions.sort_values(by=["wl_ratio"], ascending=False)

        self._tracer.write(
            f"new positions: {good_positions.filter(['time', 'ticker', 'wl_ratio', 'trader_id', 'trader_name', 'direction'])}")
        return good_positions

    def _get_ig_hist(self):
        hist = self._ig.get_transaction_history(5)
        hist['profit_float'] = hist['profitAndLoss'].str.replace('E', '').astype(float)
        return hist

    def _is_crash(self):
        if self._check_for_crash:
            hist = self._get_ig_hist()
            if hist[:3].profit_float.sum() < -50:
                self._tracer.error(f"CRASH CRASH CRASH {hist[:3]}")
                return True
        return False

    def _update_deals(self):
        hist = self._ig.get_transaction_history(3)

        for _, ig_deal in hist.iterrows():
            ticker = re.match("\w{3}\/\w{3}", ig_deal.instrumentName).group().replace("/", "")
            deal = self._deal_storage.get_deal_by_ig_id(ig_deal.openDateUtc, ticker)
            if deal is not None:
                deal.profit = float(ig_deal.profitAndLoss[1:])
                deal.close_date_ig_datetime = datetime.strptime(ig_deal.dateUtc, '%Y-%m-%dT%H:%M:%S')
                if deal.profit > 0:
                    deal.result = 1
                else:
                    deal.result = -1
                self._deal_storage.save(deal)
            else:
                self._tracer.debug(f"No deal for {ig_deal.openDateUtc} and {ticker}")
