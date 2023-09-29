import itertools
import random
from typing import List

from BL.candle import Candle, Direction
from BL.datatypes import TradeAction
from BL.high_low_scanner import PivotScanner
from BL.indicators import Indicators
from Connectors.dropbox_cache import BaseCache
from Predictors.base_predictor import BasePredictor
from pandas import Series, DataFrame
from Tracing.Tracer import Tracer
from Tracing.ConsoleTracer import ConsoleTracer
from UI.base_viewer import BaseViewer


class JoyPredictor(BasePredictor):

    def __init__(self, indicators, config=None,
                 tracer: Tracer = ConsoleTracer(),
                 viewer: BaseViewer = BaseViewer(),
                 cache: BaseCache = BaseCache()):
        self._limit_factor: float = 2
        self._confirm_ratio = 0.7
        self._viewer = viewer
        if config is None:
            config = {}

        super().__init__(indicators, config, tracer=tracer, cache=cache)
        self.setup(config)

    def setup(self, config: dict):
        self._set_att(config, "_limit_factor")
        self._set_att(config, "_confirm_ratio")
        super().setup(config)

    def get_config(self) -> Series:
        parent_c = super().get_config()
        my_conf = Series([
            self._limit_factor,
            self._confirm_ratio

        ],
            index=[
                "_limit_factor",
                "_confirm_ratio",
            ])
        return parent_c.append(my_conf)

    def predict(self, df: DataFrame) -> (str, float, float):

        action = self._indicators.predict_all(df, self._confirm_ratio)

        if action != TradeAction.NONE:
            stop = limit = df.ATR.mean() * self._limit_factor
            return action, stop, limit

        return TradeAction.NONE, 0, 0


    @staticmethod
    def _confirm_ratio_sets(version: str):

        json_objs = []
        for ratio in [.5, .6,.7,.8,.9,.95]:

            json_objs.append({
                "_confirm_ratio": ratio,
                "version": version
            })


    @staticmethod
    def get_training_sets(version: str):
        return JoyPredictor._confirm_ratio_sets(version)

