import datetime
import random
from typing import List

import pandas as pd

from BL.indicators import Indicators
from Predictors.base_predictor import BasePredictor
from pandas import Series, DataFrame
from Tracing.Tracer import Tracer
from Tracing.ConsoleTracer import ConsoleTracer
from UI.base_viewer import BaseViewer
from BL.datatypes import TradeAction
import uuid


class DeepPredictor(BasePredictor):
    # https://www.youtube.com/watch?v=6c5exPYoz3U

    def __init__(self, symbol:str,
                 cache,
                 indicators,
                 config=None,
                 tracer: Tracer = ConsoleTracer(),
                 viewer: BaseViewer = BaseViewer()
                 ):
        self._cache = cache
        self._viewer = viewer
        self._model = None
        self._model_id = ""
        self._trade_mode = TradeAction.NONE

        self._features = []
        self._trading_hours = 4
        self._threshold = 0.5
        self._atr_factor = 0.0
        self._training_time = None
        self._indicators = indicators
        if config is None:
            config = {}

        super().__init__(symbol=symbol, config=config, tracer=tracer, indicators=indicators)
        self.setup(config)

    def setup(self, config: dict):
        self._set_att(config, "_model_id")
        self._set_att(config, "_features")
        self._set_att(config, "_trading_hours")
        self._set_att(config, "_threshold")
        self._set_att(config, "_trade_mode")
        self._set_att(config, "_atr_factor")
        self._set_att(config, "_training_time")




        super().setup(config)

    def get_config(self) -> Series:
        parent_c = super().get_config()
        my_conf = Series([
            self._model_id,
            self._features,
            self._trading_hours,
            self._threshold,
            self._trade_mode,
            self._atr_factor,
            self._training_time

        ],
            index=[
                "_model_id",
                "_features",
                "_trading_hours",
                "_threshold",
                "_trade_mode",
                "_atr_factor",
                "_training_time"
            ])
        return pd.concat([parent_c, my_conf])

    def set_model(self, model):
        self._model = model
        self._model_id = f"{uuid.uuid4()}"

    def set_model_params(self, trade_mode:str,  trading_hours:int, threshold:float, features:List, atr_factor:float):
        self._trading_hours = trading_hours
        self._threshold = threshold
        self._features = features
        self._trade_mode = trade_mode
        self._atr_factor = atr_factor
        self._training_time = datetime.datetime.now()

    def get_trading_hours(self) -> int:
        return self._trading_hours

    def get_atr_factor(self) -> float:
        return self._atr_factor

    def get_threshold(self) -> float:
        return self._threshold

    def save(self):
        self._cache.save_model_cache(self._model, self._model_id)

    def predict(self, df: DataFrame):
        actions = {}


        if self._model is not None:
            for indicator_name in self._features:
                action = self._indicators.predict_single(df, indicator_name)
                actions[indicator_name] = action
            actions_df = DataFrame([actions])

            if self._trade_mode == TradeAction.BUY:
                actions_df = actions_df.replace({'none': 0, 'both': 1, 'buy': 1, 'sell': 0})
            elif self._trade_mode == TradeAction.SELL:
                actions_df = actions_df.replace({'none': 0, 'both': 1, 'buy': 0, 'sell': 1})

            probabilities = self._model.predict_proba(actions_df)
            positive_prob = probabilities[-1][1]  # Wahrscheinlichkeit des letzten Eintrags für "BUY"

            # Vergleiche mit dem Threshold
            if positive_prob >= self._threshold:  # self.threshold ist der gewünschte Schwellenwert (z.B. 0.6)
                return  self._trade_mode

        return TradeAction.NONE

    def _clean_list(self, l):
        return list(set(l))

    def load_model(self):
        self._model = self._cache.load_model_cache(self._model_id)



