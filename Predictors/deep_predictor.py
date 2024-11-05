import random
from typing import List

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

        super().setup(config)

    def get_config(self) -> Series:
        parent_c = super().get_config()
        my_conf = Series([
            self._buy_accuracy,
            self._sell_accuracy,
            self._buy_model_id,
            self._sell_model_id

        ],
            index=[
                "_buy_accuracy",
                "_sell_accuracy",
                "_buy_model_id",
                "_sell_model_id"
            ])
        return parent_c.append(my_conf)

    def set_model_buy(self, model):
        self._buy_model = model
        self._buy_model_id =f"{uuid.uuid4()}"

    def set_buy_validation(self, accuracy:float):
        self._buy_accuracy = accuracy

    def is_good(self):
        return self.is_good_buy() or self.is_good_sell()

    def is_good_buy(self):
        return self._buy_accuracy > 0.7

    def is_good_sell(self):
        return self._sell_accuracy > 0.7

    def save(self):
        self._cache.save_model_cache(self._buy_model, self._buy_model_id)
        self._cache.save_model_cache(self._sell_model, self._sell_model_id)

    def predict(self, df: DataFrame):
        actions = {}
        for indicator_name in  self._indicators.get_all_indicator_names():
            action = self._indicators.predict_single(df, indicator_name)
            actions[indicator_name] = action
        actions_df =  DataFrame([actions])
        actions_df = actions_df.replace({'none': -0.5, 'both': 1, 'buy': 1, 'sell': -1})

        if self._buy_model is not None:
            prediction = self._buy_model.predict(actions_df)
            if prediction[-1]  == 1:
                return TradeAction.BUY


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

