import asyncio
import concurrent.futures
import os
import traceback
from enum import Enum
from typing import List, NamedTuple, Any
import re
from datetime import datetime
import pandas as pd
from BL import DataProcessor, measure_time
from BL.analytics import Analytics
from BL.datatypes import TradeAction
from BL.indicators import Indicators
from Connectors import IG
from Connectors.deal_store import Deal, DealStore
from Connectors.dropbox_cache import DropBoxCache
from Connectors.market_store import MarketStore
from Connectors.predictore_store import PredictorStore
from Connectors.tiingo import TradeType
from Tracing import Tracer
from pandas import DataFrame
from Predictors.base_predictor import BasePredictor
from Predictors.deep_predictor import DeepPredictor

pd.set_option('future.no_silent_downcasting', True)

class TradeConfig(NamedTuple):
    """Konfigurationsdaten für den Handel.

    Attributes:
        symbol (str): Das Handelssymbol.
        epic (str): Die Epic-Nummer für das Handelsinstrument.
        spread (float): Der Spread des Instruments.
        scaling (int): Der Skalierungsfaktor für den Spread.
        trade_type (TradeType, optional): Der Handelstyp (Standardwert: TradeType.FX).
        size (float, optional): Die Größe des Trades (Standardwert: 1.0).
        currency (str, optional): Die Währung des Trades (Standardwert: "USD").
    """
    symbol: str
    epic: str
    spread: float
    scaling: int
    trade_type: TradeType = TradeType.FX
    size: float = 1.0
    currency: str = "USD"


class TradeResult(Enum):
    """Ergebnis des Handels."""
    SUCCESS = 1
    NOACTION = 2
    ERROR = 3


class Trader:
    """Klasse, die den Handel mit verschiedenen Predictors durchführt.

      Attributes:
          ig (IG): Die Instanz des IG Connectors.
          tiingo (Any): Der Tiingo Connector.
          tracer (Tracer): Der Tracer für die Protokollierung.
          predictor_class_list (List[type]): Eine Liste der Predictor-Klassen, die verwendet werden sollen.
          dataprocessor (DataProcessor): Der DataProcessor für die Datenverarbeitung.
          analytics (Analytics): Die Analytics-Klasse für die Ergebnisanalyse.
          cache (DropBoxCache): Der Cache zum Speichern der Handelsberichte.
      """

    def __init__(self,
                 ig: IG,
                 tiingo,
                 tracer: Tracer,
                 predictor_class_list: List[type],
                 dataprocessor: DataProcessor,
                 analytics: Analytics,
                 cache: DropBoxCache,
                 predictor_store: PredictorStore,
                 deal_storage: DealStore,
                 market_storage: MarketStore,
                 check_ig_performance: bool = False):
        self._ig: IG = ig
        self._dataprocessor = dataprocessor
        self._tiingo = tiingo
        self._tracer: Tracer = tracer
        self._predictor_class_list = predictor_class_list
        self._analytics = analytics
        self._min_win_loss = 0.75
        self._min_trades = 16
        self._predictor_store = predictor_store
        self._deal_storage = deal_storage
        self._market_store = market_storage
        self._cache = cache
        self._check_ig_performance = check_ig_performance

    def _is_good_ticker(self, ticker: str, min_avg_profit: float, min_deal_count: int, days: int = 1) -> bool:
        deals = self._deal_storage.get_closed_deals_by_ticker_not_older_than_df(ticker, days)
        if len(deals) >= min_deal_count:
            min_profit = min_avg_profit * len(deals)
            if deals.profit.sum() > min_profit:
                self._tracer.debug(f"Profit {deals.profit.sum()} is greater than {min_profit}")
                return True
            else:
                self._tracer.debug(f"Profit {deals.profit.sum()} is less than {min_profit}")
                return False
        else:
            self._tracer.debug("To less deals")

        return True

    def update_deals(self):
        hist = self._ig.get_transaction_history(3)

        for _, ig_deal in hist.iterrows():
            ticker = re.match("\w{3}\/\w{3}", ig_deal.instrumentName).group().replace("/", "")
            deal:Deal = self._deal_storage.get_deal_by_ig_id(ig_deal.openDateUtc, ticker)
            if deal is not None:
                deal.profit = float(ig_deal.profitAndLoss[1:])
                deal.open_level = float(ig_deal["openLevel"])
                deal.close_level = float(ig_deal["closeLevel"])
                deal.close_date_ig_datetime = datetime.strptime(ig_deal.dateUtc, '%Y-%m-%dT%H:%M:%S')

                if deal.profit == 0:
                    ig_m = self._ig.get_market_details(deal.epic)
                    scaling = int(ig_m["instrument"]["contractSize"])
                    m = self._market_store.get_market(deal.ticker)

                    deal.profit = self._calc_profit(ig_deal, m, scaling)

                    self._tracer.warning(
                        f"Problem with IG Calcululation. Profit is 0 Euro. Real profit is {deal.profit} . "
                        f"Deal {deal.dealId}")

                if deal.profit > 0:
                    deal.result = 1
                else:
                    deal.result = -1

                deal.close()
                self._tracer.debug(f"Update deal for {deal.dealId} and {ticker}")
                self._deal_storage.save(deal)
            else:
                self._tracer.debug(f"No deal for {ig_deal.openDateUtc} and {ticker}")

    def _fix_deals(self):
        opened = self._ig.get_opened_positions()
        deals = self._deal_storage.get_open_deals()
        for deal in deals:
            if deal.dealId not in opened.dealId.values:
                if not deal.is_closed():
                    self._tracer.error(f"Unable to find open {deal.ticker} {deal.open_date_ig_str}")
                    deal.close_by_error()
                    self._deal_storage.save(deal)

    @staticmethod
    def _calc_profit(ig_deal, m, scaling) -> float:
        if int(ig_deal["size"]) > 0:
            profit = float(ig_deal["closeLevel"]) - float(ig_deal["openLevel"])
            return m.get_euro_value(profit, scaling)
        else:
            profit = float(ig_deal["openLevel"]) - float(ig_deal["closeLevel"])
            return m.get_euro_value(profit, scaling)

    @measure_time
    async def trade_markets(self, indicators):
        """Führt den Handel für alle Märkte eines bestimmten Typs asynchron durch,
           aber begrenzt die Anzahl der gleichzeitig laufenden Threads auf die Anzahl der CPU-Kerne.
        """

        self._tracer.debug("Start")
        currency_markets = IG.IG.get_markets_offline()
        low_spread_pairs = [
            "EURUSD", "USDJPY", "GBPUSD", "AUDUSD", "USDCHF", "NZDUSD",
            "EURJPY", "EURGBP", "USDCAD", "GBPJPY", "AUDJPY", "EURCHF",
            "EURAUD", "GBPCHF", "EURCAD", "GBPAUD", "CHFJPY", "CADJPY",
            "NZDJPY", "GBPNZD",
            "USDHKD", "USDSGD", "EURSGD", "AUDNZD", "CADCHF", "NZDCAD",
            "EURNZD", "AUDCAD", "NOKSEK", "USDNOK"
        ]

        max_workers = os.cpu_count() or 4  # Falls os.cpu_count() None zurückgibt, setze Standardwert 4
        self._tracer.debug(f"Using max {max_workers} concurrent threads")

        async def trade_single_market(market):
            try:
                if self.market_tradable(market["symbol"]) and market["symbol"] in low_spread_pairs:
                    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                        loop = asyncio.get_running_loop()
                        await loop.run_in_executor(executor, self.trade_market, Indicators(), market)
            except Exception as EX:
                self._tracer.error(f"Error while trading {market['symbol']} {EX}")
                traceback_str = traceback.format_exc()
                self._tracer.error(f"Error: {EX} File:{traceback_str}")

        await asyncio.gather(*(trade_single_market(market) for market in currency_markets))

        self._tracer.debug("End")

    def update_markets(self):
        self._intelligent_update()
        self.update_deals()
        self._fix_deals()

    def _close_after_time(self):
        self._tracer.debug("Close after time")
        for _, item in self._ig.get_opened_positions().iterrows():
            deal = self._deal_storage.get_deal_by_deal_id(item.dealId)
            if deal is not None:
                self._ig.manual_close_after_time(item, self._deal_storage, self._predictor_store)
            else:
                self._tracer.error(f"Unable to find deal for {item.dealId}")

    def _get_predictors(self, symbol: str, indicators) -> List[DeepPredictor]:
        predictors = []

        for predictor_data in self._predictor_store.load_all_by_symbol(symbol):
            predictor = DeepPredictor(symbol=symbol, tracer=self._tracer, indicators=indicators, cache=self._cache)
            predictor.setup(predictor_data)
            predictors.append(predictor)
        return predictors

    def _get_predictors_by_id(self, symbol: str, indicators, id) -> List[DeepPredictor]:
        predictors = []

        for predictor_data in [self._predictor_store.load_by_id(id)]:
            predictor = DeepPredictor(symbol=symbol, tracer=self._tracer, indicators=indicators, cache=self._cache)
            predictor.setup(predictor_data)
            predictors.append(predictor)
        return predictors

    def market_tradable(self, market: str) -> bool:
        return self._predictor_store.count_of_all_by_symbol(market) > 0

    def trade_market(self, indicators: Any, market: dict) -> TradeResult:
        """
        Executes trading for a single market.

        Args:
            indicators (Any): The indicators used for trading.
            market (dict): The market data.

        Returns:
            TradeResult: The result of the trade (SUCCESS, NOACTION, or ERROR).
        """
        symbol = market["symbol"]
        indicators.reset_caches()

        self._tracer.debug(f"Attempting to trade {symbol}")

        trade_df = self._tiingo.load_trade_data(symbol=symbol, dp=self._dataprocessor, trade_type=TradeType.FX)
        if trade_df.empty:
            self._tracer.error(f"Could not load trade data for {symbol}")
            return TradeResult.ERROR

        if self._has_open_positions(symbol):
            self._tracer.debug(f"Already 1 open positions for {symbol}")
            return TradeResult.ERROR

        if not self._is_good_ticker(symbol, 0.5, 4):
            self._tracer.debug(f"BAD ticker {symbol}")
            return TradeResult.ERROR


        indicators.init_caches(trade_df)
        predictors = self._get_predictors(symbol, indicators)
        #predictors = self._get_predictors_by_id(symbol, indicators,ObjectId('67cab6aca5f967606f612fbe'))
        actions_df = self._get_actions_df(predictors, trade_df, indicators)

        buy_actions_df = actions_df.replace({'none': 0, 'both': 1, 'buy': 1, 'sell': 0}).astype(int)
        sell_actions_df = actions_df.replace({'none': 0, 'both': 1, 'buy': 0, 'sell': 1}).astype(int)

        pd.set_option('display.max_columns', None)
        self._tracer.debug(f"{symbol} DF Cache {indicators._df_cache._4h_cache}")

        return self._execute_trades(predictors, trade_df, buy_actions_df, sell_actions_df, market)

    def _has_open_positions(self, symbol: str) -> bool:
        open_deals = self._deal_storage.get_open_deals_by_ticker(symbol)
        return len(open_deals) >= 1

    @staticmethod
    def _get_actions_df(predictors: List[DeepPredictor], trade_df: DataFrame, indicators: Any) -> DataFrame:
        all_features = set(feature for predictor in predictors for feature in predictor._features)
        actions = {indicator_name: indicators.predict_single(trade_df, indicator_name) for indicator_name in
                   all_features}
        return DataFrame([actions])

    def _execute_trades(self, predictors: List[DeepPredictor], trade_df: DataFrame, buy_actions_df: DataFrame,
                        sell_actions_df: DataFrame, market: dict) -> TradeResult:
        opened = 0
        self._tracer.debug(f"{market['symbol']} valid to predict")
        for predictor in predictors:
            predictor.set_tracer(self._tracer)
            result = self.trade(
                predictor=predictor,
                trade_df=trade_df,
                buy_actions_df=buy_actions_df,
                sell_actions_df=sell_actions_df,
                config=TradeConfig(
                    symbol=market["symbol"],
                    epic=market["epic"],
                    spread=market["spread"],
                    scaling=market["scaling"],
                    trade_type=TradeType.FX,
                    size=market["size"],
                    currency=market["currency"]
                )
            )
            if result == TradeResult.SUCCESS:
                self._tracer.info("One position opened")
                opened += 1
                if opened == 1:
                    self._tracer.info("Break because 1 positions opened")
                    break
        return TradeResult.SUCCESS if opened > 0 else TradeResult.NOACTION

    @staticmethod
    def _evalutaion_up_to_date(last_scan_time):
        """Überprüft, ob die Bewertung aktuell ist.

              Args:
                  last_scan_time (datetime): Das Datum der letzten Bewertung.

              Returns:
                  bool: True, wenn die Bewertung aktuell ist, sonst False.
              """
        return (datetime.utcnow() - last_scan_time).days < 30

    def _execute_trade(self,
                       symbol,
                       epic,
                       stop,
                       limit,
                       size,
                       currency,
                       trade_function) -> (TradeResult, dict):
        """Führt den Handel für ein bestimmtes Symbol durch.

                Args:
                    symbol (str): Das Handelssymbol.
                    epic (str): Die Epic-Nummer für das Handelsinstrument.
                    stop (float): Der Stop-Level für den Trade.
                    limit (float): Der Limit-Level für den Trade.
                    size (float): Die Größe des Trades.
                    currency (str): Die Währung des Trades.
                    trade_function: Die Handelsfunktion (z.B. self._ig.buy oder self._ig.sell).

                Returns:
                    TradeResult: Das Ergebnis des Handels (SUCCESS, NOACTION oder ERROR).
                """
        result, deal_response = trade_function(epic, stop, limit, size, currency)
        if result:
            self._tracer.write(f"Trade {symbol} and evaluation result.")
            return TradeResult.SUCCESS, deal_response
        else:
            self._tracer.error(f"Error while trading {symbol}")
            return TradeResult.ERROR, deal_response

    def _save_result(self, predictor: BasePredictor, deal_response: dict, symbol: str):
        pass

    def trade(self,
              predictor: DeepPredictor,
              config: TradeConfig,
              trade_df: DataFrame,
              buy_actions_df: DataFrame,
              sell_actions_df: DataFrame) -> TradeResult:
        """Führt den Handel für ein bestimmtes Symbol und einen Predictor durch.

                Args:
                    predictor (BasePredictor): Der Predictor, der den Handel durchführt.
                    config (TradeConfig): Die Konfiguration für den Handel.

                Returns:
                    TradeResult: Das Ergebnis des Handels (SUCCESS, NOACTION oder ERROR).
                """
        if len(trade_df) == 0:
            return TradeResult.ERROR

        signal = predictor.predict(buy_actions_df, sell_actions_df)
        market = self._market_store.get_market(config.symbol)
        stop = trade_df.ATR.iloc[-1] * 0.8 * config.scaling
        limit = trade_df.ATR.iloc[-1] * 1.2 * config.scaling

        if signal == TradeAction.NONE or signal == TradeAction.BOTH:
                return TradeResult.NOACTION

        is_manual_stop = False
        minimal_stop = self._ig.get_min_stop_distance(config.epic)
        if stop < minimal_stop:
            self._tracer.debug(f"Current stop {stop} is lower than min stop distance {minimal_stop}")
            self._tracer.debug("Use manual stop")
            is_manual_stop = True
            new_stop = minimal_stop * 1.01
            self._tracer.debug(f"Set stop to {new_stop}")
            stop = new_stop

        self._tracer.info(f"Trade {signal} ")

        if signal == TradeAction.BUY:
            res, deal_response = self._execute_trade(config.symbol, config.epic, stop, limit, config.size,
                                                     config.currency,
                                                     self._ig.buy)

        else:
            res, deal_response = self._execute_trade(config.symbol, config.epic, stop, limit, config.size,
                                                     config.currency,
                                                     self._ig.sell)

        if res == TradeResult.SUCCESS:
            self._save_result(predictor, deal_response, config.symbol)
            self._tracer.debug("Save Deal in db")
            self._tracer.debug(f"Buy actions {buy_actions_df}")
            self._tracer.debug(f"Sell actions {sell_actions_df}")
            self._tracer.debug(f"Features {predictor._features}")
            pd.set_option('display.max_columns', None)
            self._tracer.debug(trade_df)
            date_string = re.match("\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", deal_response['date'])
            date_string = date_string.group().replace(" ", "T")
            manual_stop_level = None

            if is_manual_stop:
                pip_diff = market.get_pip_value(stop, config.scaling)
                if signal == TradeAction.BUY:
                    manual_stop_level = deal_response["level"] - pip_diff
                elif signal == TradeAction.SELL:
                    manual_stop_level = deal_response["level"] + pip_diff
                self._tracer.debug(f"set manual stop to {manual_stop_level} - level {deal_response['level']}")

            self._deal_storage.save(Deal(ticker=config.symbol,
                                         is_manual_stop=is_manual_stop,
                                         dealReference=deal_response["dealReference"],
                                         dealId=deal_response["dealId"],
                                         epic=config.epic, direction=signal, account_type="DEMO",
                                         open_date_ig_str=date_string,
                                         manual_stop_level=manual_stop_level,
                                         open_date_ig_datetime=datetime.strptime(date_string, '%Y-%m-%dT%H:%M:%S'),
                                         stop_factor=stop, limit_factor=limit, predictor_scan_id=predictor.get_id(),
                                         size=config.size))
        return res




    def _intelligent_update(self):
        self._tracer.debug("Intelligent Update")
        data = self._ig.get_markets_offline()
        for _, item in self._ig.get_opened_positions().iterrows():
            deal = self._deal_storage.get_deal_by_deal_id(item.dealId)
            if deal is not None:

                market = [item for item in data if item['epic'] == deal.epic]

                self._ig.set_intelligent_stop_level(item, deal,
                                                    self._deal_storage, market[0]["scaling"],  self._tiingo)
            else:
                self._tracer.error(f"Unable to find deal for {item.dealId}")

    def is_ready_to_set_intelligent_stop(self, diff, limit: float):

        ready = diff > limit
        if ready:
            self._tracer.debug(f"Current profit {diff} is greate than limit {limit * 0.7}")
        return ready









