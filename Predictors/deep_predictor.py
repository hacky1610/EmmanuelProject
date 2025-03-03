import datetime
import pickle
from typing import List
import pandas as pd
from BL import measure_time
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
        self._model_data = None
        self._trade_mode = TradeAction.NONE

        self._features = []
        self._trading_hours = 4
        self._threshold = 0.5
        self._atr_factor = 0.0
        self._train_reward = None
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
        self._set_att(config, "_model_data")
        self._set_att(config, "_train_reward")



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
            self._training_time,
            self._model_data,
            self._train_reward

        ],
            index=[
                "_model_id",
                "_features",
                "_trading_hours",
                "_threshold",
                "_trade_mode",
                "_atr_factor",
                "_training_time",
                "_model_data",
                "_train_reward"
            ])
        return pd.concat([parent_c, my_conf])

    def set_model(self, model):
        self._model = model
        self._model_data = pickle.dumps(model)

    def convert(self):
        if self._model_data is None:
            self._model_data = pickle.dumps(self._model)

    def set_model_params(self, trade_mode:str,  trading_hours:int,
                         threshold:float, features:List,
                         atr_factor:float, train_reward:int):
        self._trading_hours = trading_hours
        self._threshold = threshold
        self._features = features
        self._trade_mode = trade_mode
        self._atr_factor = atr_factor
        self._train_reward = train_reward
        self._training_time = datetime.datetime.now()

    def get_trading_hours(self) -> int:
        return self._trading_hours

    def get_atr_factor(self) -> float:
        return self._atr_factor

    def get_threshold(self) -> float:
        return self._threshold

    def save(self):
        self._cache.save_model_cache(self._model, self._model_id)

    def predict(self, buy_actions_df: DataFrame, sell_actions_df: DataFrame):

        if self._trade_mode == TradeAction.BUY:
            actions_df = buy_actions_df
        else:
            actions_df = sell_actions_df

        if self._model is not None:
            probabilities = self._model.predict_proba(actions_df[self._features])
            positive_prob = probabilities[-1][1]  # Wahrscheinlichkeit des letzten Eintrags für "BUY"

            # Vergleiche mit dem Threshold
            if positive_prob >= self._threshold:  # self.threshold ist der gewünschte Schwellenwert (z.B. 0.6)
                self._tracer.debug(actions_df[self._features])
                return  self._trade_mode

        return TradeAction.NONE

    def _clean_list(self, l):
        return list(set(l))

    @measure_time
    def load_model(self):
        if self._model_data == None:
            self._model = self._cache.load_model_cache(self._model_id)
        else:
            self._model = pickle.loads(self._model_data)



