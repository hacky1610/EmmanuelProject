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
                 cache: DropBoxCache,
                 deal_storage:DealStore,
                 market_storage:MarketStore):
        self._ig = ig
        self._dataprocessor = dataprocessor
        self._tiingo = tiingo
        self._tracer: Tracer = tracer
        self._predictor_class_list = predictor_class_list
        self._analytics = analytics
        self._min_win_loss = 0.75
        self._min_trades = 16
        self._cache = cache
        self._deal_storage = deal_storage
        self._market_store = market_storage

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

    def update_deals(self):
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
                deal.close()
                self._deal_storage.save(deal)
            else:
                self._tracer.debug(f"No deal for {ig_deal.openDateUtc} and {ticker}")

    def trade_markets(self, trade_type: TradeType, indicators):
        """Führt den Handel für alle Märkte eines bestimmten Typs durch.

               Args:
                   trade_type (TradeType): Der Handelstyp.
               """
        self._tracer.debug("Start")
        currency_markets = self._ig.get_markets(trade_type)
        for market in currency_markets:
            try:
                self.trade_market(indicators, market)
            except Exception as EX:
                self._tracer.error(f"Error while trading {market['symbol']} {EX}")
                traceback_str = traceback.format_exc()  # Das gibt die Traceback-Information als String zurück
                self._tracer.error(f"Error: {EX} File:{traceback_str}")

        self.update_deals()
        self._tracer.debug("End")

    def trade_market(self, indicators, market):
        symbol_ = market["symbol"]
        self._tracer.set_prefix(symbol_)
        for predictor_class in self._predictor_class_list:
            self._tracer.debug(f"Try to trade {symbol_} with {predictor_class.__name__}")
            predictor = predictor_class(tracer=self._tracer, cache=self._cache, indicators=indicators)
            predictor.load(symbol_)
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

    def _is_good(self, win_loss: float, trades: float, symbol: str):
        """Überprüft, ob das Handelsergebnis gut genug für den Handel ist.

                Args:
                    win_loss (float): Das Verhältnis von Gewinnen zu Verlusten.
                    trades (float): Die Anzahl der Trades.
                    symbol (str): Das Handelssymbol.

                Returns:
                    bool: True, wenn das Ergebnis gut ist, sonst False.
                """
        if win_loss >= self._min_win_loss and trades >= self._min_trades:
            return True

        self._tracer.warning(
            f"{symbol} Best result not good {win_loss} or  trades {trades} less than  {self._min_trades}")
        return False

    @staticmethod
    def _evalutaion_up_to_date(last_scan_time):
        """Überprüft, ob die Bewertung aktuell ist.

              Args:
                  last_scan_time (datetime): Das Datum der letzten Bewertung.

              Returns:
                  bool: True, wenn die Bewertung aktuell ist, sonst False.
              """
        return (datetime.utcnow() - last_scan_time).days < 10

    def _execute_trade(self,
                       symbol,
                       epic,
                       stop,
                       limit,
                       size,
                       currency,
                       config,
                       last_eval_result,
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
            self._tracer.write(f"Trade {symbol} with settings {config} and evaluation result {last_eval_result}.")
            return TradeResult.SUCCESS, deal_response
        else:
            self._tracer.error(f"Error while trading {symbol}")
            return TradeResult.ERROR, deal_response

    def _save_result(self, predictor: BasePredictor, deal_response: dict, symbol: str):
        predictor_data = predictor.get_config().append(predictor.get_last_result().get_data())
        deal_data = Series(deal_response)
        all_data = predictor_data.append(deal_data)
        name = f"{deal_response['date'][:-4]}_{symbol}"
        self._cache.save_deal_info(all_data.to_json(), name)

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

        if not self._evalutaion_up_to_date(predictor.get_last_scan_time()):
            self._tracer.warning(f"{config.symbol} Last evaluation too old")
            return TradeResult.ERROR

        if not predictor.get_last_result().is_good():
            self._tracer.warning(f"{config.symbol} has bad result {predictor.get_last_result()}")
            return TradeResult.ERROR

        open_deals = self._deal_storage.get_open_deals_by_ticker(config.symbol)
        if len(open_deals) > 0:
            self._tracer.warning(f"there is already an open position of {config.symbol}")
            return TradeResult.ERROR


        trade_df = self._tiingo.load_trade_data(config.symbol, self._dataprocessor, config.trade_type)

        if len(trade_df) == 0:
            self._tracer.error(f"Could not load train data for {config.symbol}")
            return TradeResult.ERROR

        spread_limit = self._get_spread(trade_df, config.scaling)
        if config.spread > spread_limit:
            self._tracer.debug(f"Spread {config.spread} is greater than {spread_limit} for {config.symbol}")
            return TradeResult.ERROR

        self._tracer.debug(f"{config.symbol} valid to predict")
        signal = predictor.predict(trade_df)
        market = self._market_store.get_market(config.symbol)
        stop = int(market.pip_euro * predictor.stop)
        limit = int(market.pip_euro * predictor.limit)

        if signal == TradeAction.NONE:
            return TradeResult.NOACTION

        self._tracer.info(f"Trade {signal} ")

        if signal == TradeAction.BUY:
            res, deal_response = self._execute_trade(config.symbol, config.epic, stop, limit,config.size,
                                                     config.currency, predictor.get_config(),
                                                     predictor.get_last_result().get_data(),
                                                     self._ig.buy)
        else:
            res, deal_response = self._execute_trade(config.symbol, config.epic, stop, limit, config.size,
                                                     config.currency, predictor.get_config(),
                                                     predictor.get_last_result().get_data(),
                                                     self._ig.sell)
        if res == TradeResult.SUCCESS:
            self._save_result(predictor, deal_response, config.symbol)
            self._tracer.debug("Save Deal in db")
            date_string = re.match("\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", deal_response['date'])
            date_string = date_string.group().replace(" ", "T")

            self._deal_storage.save(Deal(ticker=config.symbol,
                                         dealReference=deal_response["dealReference"],
                                         dealId=deal_response["dealId"],
                                         epic=config.epic, direction=signal, account_type="DEMO",
                                         open_date_ig_str=date_string,
                                         open_date_ig_datetime=datetime.strptime(date_string, '%Y-%m-%dT%H:%M:%S'),
                                         stop_factor=stop, limit_factor=limit))
        return res
