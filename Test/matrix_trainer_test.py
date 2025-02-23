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








