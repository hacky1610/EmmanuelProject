import traceback
from enum import Enum
from typing import List, NamedTuple
import re
from datetime import datetime
from BL import  DataProcessor
from BL.analytics import Analytics
from BL.datatypes import TradeAction
from Connectors import IG
from Connectors.deal_store import Deal, DealStore
from Connectors.dropbox_cache import DropBoxCache
from Connectors.market_store import MarketStore
from Connectors.predictore_store import PredictorStore
from Connectors.tiingo import TradeType
from Tracing import Tracer
from pandas import DataFrame, Series
from Predictors.base_predictor import BasePredictor


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
                 predictor_store: PredictorStore,
                 deal_storage:DealStore,
                 market_storage:MarketStore,
                 check_ig_performance: bool = False):
        self._ig = ig
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
        self._check_ig_performance = check_ig_performance

    @staticmethod
    def _get_spread(df: DataFrame, scaling: float) -> float:
        """Berechnet den Spread basierend auf den Daten eines DataFrame.

          Args:
              df (DataFrame): Der DataFrame mit den Handelsdaten.
              scaling (float): Der Skalierungsfaktor.

          Returns:
              float: Der berechnete Spread.
          """
        return (abs((df.close - df.close.shift(1))).median() * scaling) * 1.5

    def _is_good_ticker(self, ticker: str, min_avg_profit:float, min_deal_count:int, days:int = 30) -> bool:
        if not self._check_ig_performance:
            return True
        deals = self._deal_storage.get_closed_deals_by_ticker_not_older_than_df(ticker,days)
        if len(deals) > min_deal_count:
            min_profit = min_avg_profit * len(deals)
            if deals.profit.sum() > min_profit:
                self._tracer.debug(f"Profit {deals.profit.sum()} is greater than {min_profit}")
                return True
            else:
                self._tracer.debug(f"Profit {deals.profit.sum()} is less than {min_profit}")
                return False
        else:
            self._tracer.debug("To less deals")

        return False

    def update_deals(self):
        hist = self._ig.get_transaction_history(3)

        for _, ig_deal in hist.iterrows():
            ticker = re.match("\w{3}\/\w{3}", ig_deal.instrumentName).group().replace("/", "")
            deal = self._deal_storage.get_deal_by_ig_id(ig_deal.openDateUtc, ticker)
            if deal is not None:
                deal.profit = float(ig_deal.profitAndLoss[1:])
                deal.open_level = float(ig_deal["openLevel"])
                deal.close_level = float(ig_deal["closeLevel"])
                deal.close_date_ig_datetime = datetime.strptime(ig_deal.dateUtc, '%Y-%m-%dT%H:%M:%S')

                if deal.profit == 0:
                    ig_m = self._ig.get_market_details(deal.epic)
                    scaling = int(ig_m["instrument"]["contractSize"])
                    m = self._market_store.get_market(deal.ticker)

                    deal.profit = self._calc_profit( ig_deal, m, scaling)

                    self._tracer.warning(f"Problem with IG Calcululation. Profit is 0 Euro. Real profit is {deal.profit} . Deal {deal.dealId}")

                if deal.profit > 0:
                    deal.result = 1
                else:
                    deal.result = -1

                deal.close()
                self._deal_storage.save(deal)
            else:
                self._tracer.debug(f"No deal for {ig_deal.openDateUtc} and {ticker}")


    def _fix_deals(self):
        opened = self._ig.get_opened_positions()
        deals = self._deal_storage.get_open_deals()
        for deal in deals:
            if deal.dealId not in opened.dealId.values:
                self._tracer.error(f"Unable to find open {deal.ticker} {deal.open_date_ig_str}")
                deal.close()
                self._deal_storage.save(deal)

    def _calc_profit(self,  ig_deal, m, scaling) -> float:
        if int(ig_deal["size"]) > 0:
            profit = float(ig_deal["closeLevel"]) - float(ig_deal["openLevel"])
            return m.get_euro_value(profit, scaling)
        else:
            profit = float(ig_deal["openLevel"]) - float(ig_deal["closeLevel"])
            return m.get_euro_value(profit, scaling)

    def trade_markets(self, trade_type: TradeType, indicators):
        """Führt den Handel für alle Märkte eines bestimmten Typs durch.

               Args:
                   trade_type (TradeType): Der Handelstyp.
               """
        self._tracer.debug("Start")
        currency_markets = IG.IG.get_markets_offline()
        for market in currency_markets:
            try:
                self.trade_market(indicators, market)
            except Exception as EX:
                self._tracer.error(f"Error while trading {market['symbol']} {EX}")
                traceback_str = traceback.format_exc()  # Das gibt die Traceback-Information als String zurück
                self._tracer.error(f"Error: {EX} File:{traceback_str}")

        self._tracer.debug("End")

    def update_markets(self):
        self._intelligent_update_and_close()
        self.update_deals()
        self._fix_deals()


    def _intelligent_update_and_close(self):
        self._tracer.debug("Intelligent Update")
        for _, item in self._ig.get_opened_positions().iterrows():
            deal = self._deal_storage.get_deal_by_deal_id(item.dealId)
            if deal is not None:
                self._ig.set_intelligent_stop_level(item, self._market_store, self._deal_storage, self._predictor_store)
                self._ig.manual_close(item, self._deal_storage)

    def trade_market(self, indicators, market):
        symbol_ = market["symbol"]
        self._tracer.set_prefix(symbol_)
        for predictor_class in self._predictor_class_list:
            self._tracer.debug(f"Try to trade {symbol_} with {predictor_class.__name__}")
            predictor = predictor_class(symbol=symbol_, tracer=self._tracer, indicators=indicators)
            predictor.setup(self._predictor_store.load_active_by_symbol(symbol_))
            self.trade(
                predictor=predictor,
                config=TradeConfig(
                    symbol=symbol_,
                    epic=market["epic"],
                    spread=market["spread"],
                    scaling=market["scaling"],
                    trade_type=TradeType.FX,
                    size=market["size"],
                    currency=market["currency"])
            )

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
                    config: Die Handelskonfiguration.
                    last_eval_result: Das letzte Ergebnis der Evaluation.
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
              predictor: BasePredictor,
              config: TradeConfig) -> TradeResult:
        """Führt den Handel für ein bestimmtes Symbol und einen Predictor durch.

                Args:
                    predictor (BasePredictor): Der Predictor, der den Handel durchführt.
                    config (TradeConfig): Die Konfiguration für den Handel.

                Returns:
                    TradeResult: Das Ergebnis des Handels (SUCCESS, NOACTION oder ERROR).
                """

        if not self._is_good_ticker(config.symbol, min_avg_profit=3, min_deal_count=5, days=7):
            self._tracer.debug(f"{config.symbol} has a bad IG Performance in the last 2 weeks")
            return TradeResult.NOACTION

        if not self._evalutaion_up_to_date(predictor.get_last_scan_time()):
            self._tracer.debug(f"{config.symbol} Last evaluation too old")
            return TradeResult.ERROR

        if not predictor.get_result().is_good():
            self._tracer.debug(f"{config.symbol} has bad result {predictor.get_result()}")
            return TradeResult.ERROR

        open_deals = self._deal_storage.get_open_deals_by_ticker(config.symbol)
        if len(open_deals) >= 2:
            self._tracer.debug(f"there are already 2 open position of {config.symbol}")
            return TradeResult.ERROR


        trade_df = self._tiingo.load_trade_data(symbol=config.symbol, dp=self._dataprocessor,
                                                trade_type=config.trade_type)

        if len(trade_df) == 0:
            self._tracer.error(f"Could not load train data for {config.symbol}")
            return TradeResult.ERROR

        self._tracer.debug(f"{config.symbol} valid to predict")
        signal = predictor.predict(trade_df)
        market = self._market_store.get_market(config.symbol)
        stop = market.get_pip_value(predictor._stop)
        limit = market.get_pip_value(predictor._limit)

        if signal == TradeAction.NONE or signal == TradeAction.BOTH:
            return TradeResult.NOACTION

        if predictor.get_open_limit_isl():
            self._tracer.debug("ISL is used")
            limit = None

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
            date_string = re.match("\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", deal_response['date'])
            date_string = date_string.group().replace(" ", "T")
            manual_stop_level = None

            if is_manual_stop:
                pip_diff = market.get_pip_value(stop,config.scaling)
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
                                         stop_factor=stop, limit_factor=limit,predictor_scan_id=predictor.get_id(), size=config.size))
        return res
