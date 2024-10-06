from datetime import datetime, timedelta
from typing import List, Optional
import re
import time

from pandas import DataFrame
from Connectors.IG import IG, TradeResult
from Connectors.deal_store import Deal, DealStore
from Connectors.market_store import MarketStore
from Connectors.tiingo import TradeType
from Connectors.trader_store import TraderStore
from Connectors.zulu_api import ZuluApi
from Tracing.Tracer import Tracer
from UI.zulutrade import ZuluTradeUI


class ZuluTrader:

    def __init__(self, deal_storage: DealStore, market_storage: MarketStore, zulu_api: ZuluApi, zulu_ui: ZuluTradeUI,
                 ig: IG, trader_store: TraderStore, tracer: Tracer,
                 account_type: str, trading_size: float = 1.0, check_for_crash: bool = True,
                 check_trader_quality: bool = False, max_open_positions = 5):
        self._deal_storage = deal_storage
        self._zulu_api = zulu_api
        self._ig = ig
        self._max_minutes = 10
        self._trader_store = trader_store
        self._tracer = tracer
        self._max_open_positions = max_open_positions
        self._zulu_ui = zulu_ui
        self._min_wl_ration = 0.67
        self._trading_size = trading_size
        self._account_type = account_type
        self._check_for_crash = check_for_crash
        self._check_trader_quality = check_trader_quality
        self._market_store = market_storage

    def trade(self):
        self._tracer.debug(f"Check crash: {self._check_for_crash}")
        self._close_open_positions()
        #if not self._is_crash():
        #    self._open_new_positions()
        self._intelligent_update()
        self._update_deals()

    def _is_good_ig_trader(self, trader_id: str) -> bool:
        if not self._check_trader_quality:
            self._tracer.debug("Ignore Trader check")
            return True

        deals = self._deal_storage.get_deals_of_trader_as_df(trader_id, consider_account_type=False)

        if len(deals) < 12:
            self._tracer.warning(f"Trader {trader_id} had less than 12 trades")
            return False

        if deals.profit.sum() < 600:
            self._tracer.warning(f"Trader {trader_id} had bad profit {deals.profit.sum()} Euro less than 600")
            return False

        first_deal = deals[:1]
        diff = datetime.now() - first_deal.open_date_ig_datetime.item()
        if diff.days < 21:
            self._tracer.warning(f"Trader {trader_id} is known less than 21 days ago")
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
        open_deals_db = self._deal_storage.get_open_deals()
        self._tracer.debug(f"Open Deals from DB {open_deals_db} Needed time {time.time() - start}")

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
                deals_to_close.append(open_deal)
            else:
                self._tracer.debug(f"Position {open_deal} is still open")
        return deals_to_close

    def _close_open_positions(self):
        self._tracer.debug("Close positions")
        for open_deal in self._get_deals_to_close():
            if open_deal.intelligent_stop_used:
                self._tracer.debug(f"Position {open_deal} is closed by trader. BUT the Intelligent Stop Level is active")
                continue

            size = self._ig.get_size_of_deal(open_deal.dealId)
            result, _ = self._ig.close(direction=self._ig.get_inverse(open_deal.direction),
                                       deal_id=open_deal.dealId, size=size)
            if result:
                self._tracer.write(f"Position {open_deal} closed by app")
                open_deal.close("ByApp")
                self._deal_storage.save(open_deal)
            else:
                deals = self._ig.get_deals()
                if len(deals[deals.dealId == open_deal.dealId]) == 0:
                    self._tracer.info("Deal was already closed by IG")
                    open_deal.close("ByIG")
                    self._deal_storage.save(open_deal)
                else:
                    self._tracer.error(f"Position {open_deal} could not be closed")

    @staticmethod
    def _get_market_by_ticker_or_none(markets: List, ticker: str) -> Optional[dict]:
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
            self._tracer.debug(f"try to trade {position}")
            self._trade_position(markets=markets, position_id=position.position_id,
                                 trader_id=position.trader_id, direction=position.direction, ticker=position.ticker)

    def _intelligent_update(self):
        self._tracer.debug("Intelligent Update")
        for _, item in self._ig.get_opened_positions().iterrows():
            self._ig.intelligent_stop_level(item, self._market_store, self._deal_storage)

    def _trade_position(self, markets: List, position_id: str,
                        ticker: str, trader_id: str, direction: str):

        trader_db = self._trader_store.get_trader_by_id(trader_id)
        trade, message = trader_db.hist.trader_performance(ticker)
        if not trade:
            self._tracer.warning(f"Trader {trader_id} has bad performance with {ticker}. {message}")
            return

        if not self._is_good_ig_trader(trader_id):
            self._tracer.warning(f"Trader {trader_id} is a bad trader based of Results of last IG trades")
            return

        if self._deal_storage.has_id(position_id):
            self._tracer.warning(f"Position {position_id} - {ticker} by {trader_id} is already open")
            return

        if self._deal_storage.get_opened_positions(ticker) >= self._max_open_positions:
            self._tracer.warning(f"More than {self._max_open_positions:} of {ticker} opened")
            return

        open_positions_of_trader = self._deal_storage.positions_of_same_trader(ticker=ticker, trader_id=trader_id)
        if open_positions_of_trader >= 2:
            self._tracer.warning(f"This trader {trader_id} has already open positions of {ticker} ")
            return

        m = self._get_market_by_ticker_or_none(markets, ticker)
        if m is None:
            self._tracer.warning(f"Could not find market for {ticker}")
            return

        self._tracer.write(f"Try to open position {position_id} - {ticker} by {trader_id}")
        market = self._market_store.get_market(ticker)
        stop_pips = int(market.get_pip_value(trader_db.stop))
        limit_pips = int(market.get_pip_value(trader_db.limit))

        self._tracer.debug(
            f"StopLoss {stop_pips} pips {trader_db.stop} Euro - Limit {limit_pips}  pips {trader_db.limit}€")

        result, deal_response = self._ig.open(epic=m["epic"], direction=direction,
                                              currency=m["currency"], limit=limit_pips,
                                              stop=stop_pips, size=self._trading_size)

        if (result == TradeResult.NOT_SUCCESSFUL and
                deal_response['reason'] == "INSUFFICIENT_FUNDS" and
                self._trading_size > 1):
            self._tracer.debug("INSUFFICIENT_FUNDS -> try to trade a smaller size ")
            result, deal_response = self._ig.open(epic=m["epic"], direction=direction,
                                                  currency=m["currency"], limit=limit_pips,
                                                  stop=stop_pips, size=self._trading_size * 0.5)

        if result == TradeResult.SUCCESSFUL:
            self._tracer.debug("Save Deal in db")
            date_string = self._create_date_string(deal_response['date'])

            self._deal_storage.save(Deal(zulu_id=position_id, ticker=ticker,
                                         dealReference=deal_response["dealReference"],
                                         dealId=deal_response["dealId"], trader_id=trader_id,
                                         epic=m["epic"], direction=direction, account_type=self._account_type,
                                         open_date_ig_str=date_string,
                                         open_date_ig_datetime=datetime.strptime(date_string, '%Y-%m-%dT%H:%M:%S'),
                                         stop_factor=trader_db.stop, limit_factor=trader_db.limit))
            self._tracer.debug("Deal was saved")
        elif result == TradeResult.NOT_SUCCESSFUL:
            self._tracer.warning(f"Could not open position {position_id} - {ticker} by {trader_id}")
        else:
            self._tracer.error(f"Error while open position {position_id} - {ticker} by {trader_id}")

    @staticmethod
    def _create_date_string(date_string_long: str):
        date_string = re.match(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', date_string_long)
        date_string = date_string.group().replace(" ", "T")
        return date_string

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

    @staticmethod
    def _get_newest_positions(positions: DataFrame) -> DataFrame:
        return positions[positions.time >= datetime.now() - timedelta(minutes=20)]

    def _get_positions(self) -> DataFrame:
        positions = self._zulu_ui.get_my_open_positions()
        if len(positions) == 0:
            self._tracer.write("No open positions")
            return positions

        # Filter for time
        positions = self._get_newest_positions(positions)
        if len(positions) == 0:
            self._tracer.debug("All positions are to old")
            return positions

        positions["wl_ratio"] = positions.apply(self._calc_hist, axis=1)
        positions["trader_id"] = positions.apply(self._get_trader_id, axis=1)

        # Filter for quality
        good_positions = positions[positions.wl_ratio > self._min_wl_ration]
        if len(good_positions) == 0:
            self._tracer.debug(
                f"All positions are from bad traders. "
                f"This positions are bad: \n {positions[positions.wl_ratio <= self._min_wl_ration]}")
            return good_positions

        good_positions = good_positions.sort_values(by=["wl_ratio"], ascending=False)

        self._tracer.debug(
            f"new positions: "
            f"{good_positions.filter(['time', 'ticker', 'wl_ratio', 'trader_id', 'trader_name', 'direction'])}")
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
            ticker = self._get_ticker_name(ig_deal.instrumentName)
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

    @staticmethod
    def _get_ticker_name(instrument_name: str):
        return re.match(r"\w{3}/\w{3}", instrument_name).group().replace("/", "")