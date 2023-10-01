import copy
import unittest
from unittest.mock import MagicMock, call
from BL.trader import Trader, TradeConfig, TradeResult
from BL.analytics import Analytics
from Connectors.tiingo import TradeType
from Tracing.ConsoleTracer import ConsoleTracer
from pandas import DataFrame, Series
from BL.data_processor import DataProcessor


class TraderTest(unittest.TestCase):

    def setUp(self):
        self._tracer = ConsoleTracer()
        self._dataProcessor = DataProcessor()
        self.analytics = Analytics(ConsoleTracer())
        self._tiingo = MagicMock()
        self._mock_ig = MagicMock()
        self._mock_ig.buy = MagicMock(return_value=(True, {"date":"2016-3-4T00:00:00"}))
        self._mock_ig.sell = MagicMock(return_value=(True, {"date":"2016-3-4T00:00:00"}))
        self._trainer = MagicMock()
        self._predictor = MagicMock()
        self._predictor.stop = 2
        self._predictor.limit = 2
        self._predictor.best_result = 1.0
        self._predictor.trades = 100
        self._predictor_class_list = [MagicMock, MagicMock]

        self._stock_data = DataFrame()
        for i in range(20):
            self._stock_data = self._add_data(self._stock_data)

        self._tiingo.load_trade_data = MagicMock(return_value=self._stock_data)
        self._trader = Trader(ig=self._mock_ig,
                              tiingo=self._tiingo,
                              tracer=self._tracer,
                              dataprocessor=self._dataProcessor,
                              analytics=self.analytics,
                              predictor_class_list= self._predictor_class_list,
                              cache=MagicMock())
        self._trader._get_spread = MagicMock(return_value=1)
        self._trader._evalutaion_up_to_date = MagicMock(return_value=True)
        # Setzen der Test-Werte für _min_win_loss und _min_trades
        self._trader._min_win_loss = 0.7
        self._trader._min_trades = 5
        self._default_trade_config = TradeConfig(
            symbol="AAPL",
            epic="AAPL-12345",  # Annahme: Stellen Sie eine gültige Epic-Nummer ein.
            spread=0.5,
            scaling=10)

    @staticmethod
    def _add_data(df: DataFrame):
        return df.append(Series({
            "close": 23, "SMA7": 3, "EMA": 4, "BB_UPPER": 5, "BB_MIDDLE": 6, "BB_LOWER": 6, "ROC": 7, "%R": 8,
            "MACD": 4,
            "SIGNAL": 6}
        ), ignore_index=True)

    def test_trade_no_datafrom_tiingo(self):
        self._trader._is_good = MagicMock(return_value=True)
        self._tiingo.load_trade_data = MagicMock(return_value=DataFrame())
        self._predictor.predict = MagicMock(return_value=("none", 0, 0))
        res = self._trader.trade(predictor=self._predictor,
                                 config=self._default_trade_config)
        assert res == TradeResult.ERROR

    def test_trade_has_open_buy_positions(self):
        position = MagicMock()
        position.direction = "BUY"
        self._trader._is_good = MagicMock(return_value=True)
        self._mock_ig.get_opened_positions_by_epic = MagicMock(return_value=position)
        self._predictor.predict = MagicMock(return_value=("buy", 1, 1))
        res = self._trader.trade(predictor=self._predictor,
                                 config=self._default_trade_config)
        self._mock_ig.buy.assert_not_called()
        self._mock_ig.get_opened_positions_by_epic.assert_called()
        assert res == TradeResult.NOACTION

    def test_trade_has_open_sell_positions(self):
        position = MagicMock()
        position.direction = "SELL"
        self._trader._is_good = MagicMock(return_value=True)
        self._mock_ig.get_opened_positions_by_epic = MagicMock(return_value=position)
        self._predictor.predict = MagicMock(return_value=("sell", 1, 1))
        res = self._trader.trade(predictor=self._predictor,
                                 config=self._default_trade_config)
        self._mock_ig.sell.assert_not_called()
        self._mock_ig.get_opened_positions_by_epic.assert_called()
        assert res == TradeResult.NOACTION

    def test_trade_do_buy(self):
        self._trader._is_good = MagicMock(return_value=True)
        self._predictor.predict = MagicMock(return_value=("buy", 0, 0))
        self._trader._get_spread = MagicMock(return_value=1)
        res = self._trader.trade(predictor=self._predictor,
                                 config=self._default_trade_config)
        self._mock_ig.buy.asser_called()
        self._mock_ig.get_opened_positions_by_epic.assert_called()
        assert res == TradeResult.SUCCESS

    def test_trade_do_sell(self):
        self._trader._is_good = MagicMock(return_value=True)
        self._predictor.predict = MagicMock(return_value=("sell", 0, 0))
        res = self._trader.trade(predictor=self._predictor,
                                 config=self._default_trade_config)
        self._mock_ig.sell.asser_called()
        self._mock_ig.get_opened_positions_by_epic.assert_called()
        assert res == TradeResult.SUCCESS

    def test_trade_spread_to_big(self):
        self._trader._is_good = MagicMock(return_value=True)
        self._predictor.predict = MagicMock(return_value="buy")
        res = self._trader.trade(predictor=self._predictor,
                                 config=TradeConfig(
                                     symbol="AAPL",
                                     epic="AAPL-12345",  # Annahme: Stellen Sie eine gültige Epic-Nummer ein.
                                     spread=1.5,
                                     scaling=10)
                                 )
        self._mock_ig.buy.assert_not_called()
        self._mock_ig.sell.assert_not_called()
        assert res == TradeResult.ERROR

    def test_symbol_not_good(self):
        self._trader._is_good = MagicMock(return_value=False)
        res = self._trader.trade(predictor=self._predictor,
                                 config=self._default_trade_config
                                 )
        self._mock_ig.buy.assert_not_called()
        self._mock_ig.sell.assert_not_called()
        assert res == TradeResult.ERROR

    def test_trade_no_data(self):
        self._trader._is_good = MagicMock(return_value=True)
        self._tiingo.load_trade_data = MagicMock(return_value=DataFrame())
        res = self._trader.trade(predictor=self._predictor,
                                 config=self._default_trade_config
                                 )
        self._mock_ig.buy.assert_not_called()
        self._mock_ig.sell.assert_not_called()
        assert res == TradeResult.ERROR

    def test_trade_action_none(self):
        self._trader._is_good = MagicMock(return_value=True)
        self._predictor.predict = MagicMock(return_value=("none", 0, 0))
        self._trader._get_spread = MagicMock(return_value=1)
        res = self._trader.trade(predictor=self._predictor,
                                 config=self._default_trade_config
                                 )
        self._mock_ig.buy.assert_not_called()
        self._mock_ig.sell.assert_not_called()
        assert res == TradeResult.NOACTION

    def test_trade_markets(self):
        # Mock-Daten für currency_markets
        mock_currency_markets = [
            {"symbol": "AAPL", "epic": "AAPL-123", "spread": 0.05, "scaling": 100, "size": 1.0, "currency": "USD"},
            {"symbol": "GOOGL", "epic": "GOOGL-456", "spread": 0.03, "scaling": 200, "size": 2.0, "currency": "USD"}
        ]

        # Mock-Rückgabe für die IG get_markets-Methode
        self._mock_ig.get_markets.return_value = mock_currency_markets

        # Mock für die Trade-Funktion
        self._trader.trade = MagicMock()

        # Testaufruf der trade_markets-Funktion
        self._trader.trade_markets(trade_type=TradeType.FX, indicators=MagicMock())

        # Überprüfen, ob die trade-Funktion für jeden currency_market aufgerufen wurde
        self.assertEqual(self._trader.trade.call_count, len(mock_currency_markets) * len(self._predictor_class_list))

    def test_is_good_high_win_loss_and_trades(self):
        # Testen, ob das Ergebnis gut ist, wenn win_loss >= 0.75 und trades >= 3
        result = self._trader._is_good(win_loss=0.8, trades=8, symbol="AAPL")
        self.assertTrue(result)

    def test_is_good_good_win_loss_and_trades(self):
        # Testen, ob das Ergebnis gut ist, wenn win_loss >= _min_win_loss und trades >= _min_trades
        result = self._trader._is_good(win_loss=0.72, trades=6, symbol="AAPL")
        self.assertTrue(result)

    def test_is_good_low_win_loss_and_trades(self):
        # Testen, ob das Ergebnis nicht gut ist, wenn win_loss < _min_win_loss und trades < _min_trades
        result = self._trader._is_good(win_loss=0.68, trades=4, symbol="AAPL")
        self.assertFalse(result)

    def test_is_good_low_win_loss_high_trades(self):
        # Testen, ob das Ergebnis nicht gut ist, wenn win_loss < _min_win_loss und trades >= _min_trades
        result = self._trader._is_good(win_loss=0.65, trades=6, symbol="AAPL")
        self.assertFalse(result)

    def test_is_good_high_win_loss_low_trades(self):
        # Testen, ob das Ergebnis nicht gut ist, wenn win_loss >= _min_win_loss und trades < _min_trades
        result = self._trader._is_good(win_loss=0.72, trades=4, symbol="AAPL")
        self.assertFalse(result)

    def test_is_good_equal_win_loss_and_trades(self):
        # Testen, ob das Ergebnis gut ist, wenn win_loss = _min_win_loss und trades = _min_trades
        result = self._trader._is_good(win_loss=0.7, trades=5, symbol="AAPL")
        self.assertTrue(result)

    def test_save_result(self):


        # Testaufruf der trade_markets-Funktion
        predictor = MagicMock()
        deal_response = {"A":1, "date":"2020-3-3"}
        self._trader._save_result(predictor,deal_response,"foo")


    def trade_bad_result(self):
        self._predictor.best_result = 0.1
        self._predictor.trades = 100
        self._predictor.predict = MagicMock(return_value=("none", 0, 0))
        res = self._trader.trade(predictor=self._predictor,
                                 config=self._default_trade_config
                                 )
        self._mock_ig.buy.assert_not_called()
        self._tiingo.load_trade_data.assert_not_called()

        self._predictor.best_result = 1.0
        self._predictor.trades = 2
        self._predictor.predict = MagicMock(return_value=("none", 0, 0))
        res = self._trader.trade(predictor=self._predictor,
                                 epic="myepic",
                                 symbol="mysymbol",
                                 spread=1.0,
                                 scaling=10)
        self._mock_ig.buy.assert_not_called()
        self._tiingo.load_trade_data.assert_not_called()
        assert res == False
