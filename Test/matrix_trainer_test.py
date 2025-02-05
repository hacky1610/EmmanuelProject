import unittest
from unittest.mock import MagicMock

import pandas as pd

from BL.analytics import Analytics
from BL.datatypes import TradeAction
from BL.eval_result import EvalResultCollection, TradeResult, EvalResult
from BL.indicators import Indicators
from Connectors.market_store import Market
from Predictors.base_predictor import BasePredictor
from pandas import DataFrame, Series

from Predictors.matrix_trainer import MatrixTrainer


class TestMatrixTrainer(unittest.TestCase):

    def setUp(self):
        # Beispiel-Instanz der Klasse erstellen
        self.test_instance = MatrixTrainer(MagicMock(), MagicMock(),MagicMock())  # Ersetze 'YourClass' durch den Namen der Klasse, die die Methode enthält.

        # Beispiel-Daten für den Mock
        self.mock_data_1 = pd.DataFrame({
            "Unnamed: 0": [0, 1, 2],
            "action": ["buy", "sell", "buy"],
            "chart_index": [12, 13, 14]
        })

        self.mock_data_2 = pd.DataFrame({
            "Unnamed: 0": [0, 1, 2],
            "action": ["both", "sell", "buy"],
            "chart_index": [12, 13, 14]
        })

        self.expected_result = pd.DataFrame({
            "buy_indicator": ["buy", "sell", "buy", "none"],
            "sell_indicator": ["none", "sell", "buy", "none"]
        }, index=[12, 13, 14, 15])

    def test_create_combined_indicator_data(self):
        # Mock für `load_signal` konfigurieren
        self.test_instance._cache.load_signal.side_effect = [
            self.mock_data_1.rename(columns={"action": "buy_indicator"}),  # Mock für ersten Indikator
            self.mock_data_2.rename(columns={"action": "sell_indicator"})  # Mock für zweiten Indikator
        ]

        # Indikatorliste simulieren
        mock_indicators = MagicMock()
        mock_indicators.get_all_indicator_names.return_value = ["buy_indicator", "sell_indicator"]

        # Funktion aufrufen
        result = self.test_instance.create_combined_indicator_data(mock_indicators, "mock_symbol")

        # Assert-Erwartungen
        pd.testing.assert_frame_equal(result, self.expected_result)

        # Sicherstellen, dass `load_signal` mit den richtigen Argumenten aufgerufen wurde
        self.test_instance._cache.load_signal.assert_any_call("signal_mock_symbol_buy_indicator.csv")
        self.test_instance._cache.load_signal.assert_any_call("signal_mock_symbol_sell_indicator.csv")






