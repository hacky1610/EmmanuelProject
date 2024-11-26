import random
from typing import List

import pandas
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
        self._buy_model = None
        self._buy_model_id = ""
        self._sell_model = None
        self._sell_model_id = ""
        self._buy_accuracy = 0.0
        self._sell_accuracy = 0.0
        self._buy_features:Series = Series()
        self._sell_features:Series = Series()
        self._buy_trading_hours = 4
        self._sell_trading_hours = 4
        self._buy_threshold = 0.5
        self._sell_threshold = 0.5
        self._indicators = indicators
        if config is None:
            config = {}

        super().__init__(symbol=symbol, config=config, tracer=tracer, indicators=indicators)
        self.setup(config)

    def setup(self, config: dict):
        self._set_att(config, "_buy_accuracy")
        self._set_att(config, "_sell_accuracy")
        self._set_att(config, "_buy_model_id")
        self._set_att(config, "_sell_model_id")

        self._set_att(config, "_buy_trading_hours")
        self._set_att(config, "_sell_trading_hours")
        self._set_att(config, "_buy_threshold")
        self._set_att(config, "_sell_threshold")

        self._buy_features = pandas.read_json(config.get("_buy_features","{}"),typ="series")
        self._sell_features = pandas.read_json(config.get("_sell_features", "{}"), typ="series")

        super().setup(config)

    def get_config(self) -> Series:
        parent_c = super().get_config()
        my_conf = Series([
            self._buy_accuracy,
            self._sell_accuracy,
            self._buy_model_id,
            self._sell_model_id,
            self._buy_features.to_json(),
            self._sell_features.to_json(),
            self._buy_trading_hours,
            self._sell_trading_hours,
            self._buy_threshold,
            self._sell_threshold

        ],
            index=[
                "_buy_accuracy",
                "_sell_accuracy",
                "_buy_model_id",
                "_sell_model_id",
                "_buy_features",
                "_sell_features",
                "_buy_trading_hours",
                "_sell_trading_hours",
                "_buy_threshold",
                "_sell_threshold",
            ])
        return pd.concat([parent_c, my_conf])

    def set_model_buy(self, model):
        self._buy_model = model
        self._buy_model_id =f"{uuid.uuid4()}"

    def set_buy_validation(self, accuracy:float, trading_hours:int, threshold:float, feature_factors):
        self._buy_accuracy = accuracy
        self._buy_trading_hours = trading_hours
        self._buy_threshold = threshold
        self._buy_features = feature_factors

    def get_buy_trading_hours(self):
        return self._buy_trading_hours

    def get_buy_threshold(self):
        return self._buy_threshold

    def get_sell_trading_hours(self):
        return self._sell_trading_hours

    def get_sell_threshold(self):
        return self._sell_threshold

    def set_model_sell(self, model):
        self._sell_model = model
        self._sell_model_id = f"{uuid.uuid4()}"

    def set_sell_validation(self, accuracy: float, trading_hours:int, threshold:float, feature_factors:Series):
        self._sell_accuracy = accuracy
        self._sell_trading_hours = trading_hours
        self._sell_threshold = threshold
        self._sell_features = feature_factors

    def is_good(self):
        return self.is_good_buy() or self.is_good_sell()

    def is_good_buy(self):
        return self._buy_accuracy >= 0.8

    def is_good_sell(self):
        return self._sell_accuracy >= 0.8

    def save(self):
        self._cache.save_model_cache(self._buy_model, self._buy_model_id)
        self._cache.save_model_cache(self._sell_model, self._sell_model_id)

    def predict(self, df: DataFrame):
        actions = {}


        if self._buy_model is not None:
            for indicator_name in self._buy_features.index:
                action = self._indicators.predict_single(df, indicator_name)
                actions[indicator_name] = action
            actions_df = DataFrame([actions])
            actions_buy_df = actions_df.replace({'none': 0.2, 'both': 1, 'buy': 1, 'sell': 0})
            actions_buy_df = actions_buy_df.multiply(self._buy_features, axis=1)
            probabilities = self._buy_model.predict_proba(actions_buy_df)
            # Nehme die Wahrscheinlichkeit für die positive Klasse (1)
            positive_prob = probabilities[-1][1]  # Wahrscheinlichkeit des letzten Eintrags für "BUY"

            # Vergleiche mit dem Threshold
            if positive_prob >= self._buy_threshold:  # self.threshold ist der gewünschte Schwellenwert (z.B. 0.6)
                return TradeAction.BUY


        if self._sell_model is not None:
            for indicator_name in self._sell_features.index:
                action = self._indicators.predict_single(df, indicator_name)
                actions[indicator_name] = action
            actions_df = DataFrame([actions])
            actions_sell_df = actions_df.replace({'none': 0.2, 'both': 1, 'buy': 0, 'sell': 1})
            actions_sell_df = actions_sell_df.multiply(self._sell_features, axis=1)
            probabilities = self._sell_model.predict_proba(actions_sell_df)
            # Nehme die Wahrscheinlichkeit für die positive Klasse (1)
            positive_prob = probabilities[-1][1]  # Wahrscheinlichkeit des letzten Eintrags für "BUY"

            # Vergleiche mit dem Threshold
            if positive_prob >= self._sell_threshold:  # self.threshold ist der gewünschte Schwellenwert (z.B. 0.6)
                return TradeAction.SELL

        return TradeAction.NONE

    def _clean_list(self, l):
        return list(set(l))

    def load_model(self):
        self._buy_model = self._cache.load_model_cache(self._buy_model_id)
        self._sell_model = self._cache.load_model_cache(self._sell_model_id)

    @staticmethod
    def _indicator_names_sets(best_indicators:List):

        json_objs = []
        to_skip = [Indicators.RSI30_70]

        json_objs.append({
            "_indicator_names": best_indicators
        })

        json_objs.append({
            "_indicator_names": random.choices(best_indicators,k=5)
        })

        for i in range(4):
            r = Indicators().get_random_indicator_names(min=1, max=1, skip=to_skip)
            json_objs.append({
                "_additional_indicators": r
            })

        for i in range(4):
            names = Indicators().get_random_indicator_names(skip=to_skip)
            json_objs.append({
                "_indicator_names": names
            })
        return json_objs

    @staticmethod
    def _indicator_names_sets_by_combos(best_indicator_combos: List[List[str]]):

        json_objs = []

        for combo in best_indicator_combos:
            json_objs.append({
                "_indicator_names": combo
            })


        return json_objs

    @staticmethod
    def get_training_sets(best_indicator_combs:List[List[str]]):
        return BasePredictor._stop_limit_trainer() + BasePredictor._isl_trainer()

