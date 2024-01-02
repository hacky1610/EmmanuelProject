import itertools
import random
from typing import List

from BL.candle import Candle, Direction
from BL.high_low_scanner import PivotScanner
from BL.indicators import Indicators
from Connectors.dropbox_cache import BaseCache
from Connectors.market_store import MarketStore
from Predictors.base_predictor import BasePredictor
from pandas import Series, DataFrame
from Tracing.Tracer import Tracer
from Tracing.ConsoleTracer import ConsoleTracer
from UI.base_viewer import BaseViewer


class GenericPredictor(BasePredictor):
    # https://www.youtube.com/watch?v=6c5exPYoz3U

    def __init__(self, indicators,
                 config=None,
                 tracer: Tracer = ConsoleTracer(),
                 viewer: BaseViewer = BaseViewer(),
                 cache: BaseCache = BaseCache(),
                 ):
        self._limit_factor: float = 2
        self._indicator_names = [Indicators.RSI, Indicators.EMA]
        self._additional_indicators:List = []
        self._max_nones: int = 0
        self._viewer = viewer
        if config is None:
            config = {}

        super().__init__(indicators, config, tracer=tracer, cache=cache)
        self.setup(config)

    def setup(self, config: dict):
        self._set_att(config, "_limit_factor")
        self._set_att(config, "_indicator_names")
        self._set_att(config, "_additional_indicators")
        self._set_att(config, "_max_nones")

        if len(self._additional_indicators) > 0:
            self._indicator_names = self._indicator_names + self._additional_indicators
            self._additional_indicators = []

        self._indicator_names = self._clean_list(self._indicator_names)
        super().setup(config)

    def get_config(self) -> Series:
        parent_c = super().get_config()
        my_conf = Series([
            self._limit_factor,
            self._indicator_names,
            self._max_nones,

        ],
            index=[
                "_limit_factor",
                "_indicator_names",
                "_max_nones"
            ])
        return parent_c.append(my_conf)

    def predict(self, df: DataFrame) -> str:
        all = self._indicator_names + []
        action = self._indicators.predict_some(df, all, self._max_nones)
        return action

    def _clean_list(self, l):
        return list(set(l))

    @staticmethod
    def _indicator_names_sets(version: str, best_indicators:List):

        json_objs = []
        to_skip = [Indicators.RSI30_70]

        for max_nones in [0, 1]:
            json_objs.append({
                "_indicator_names": best_indicators,
                "version": version,
                "_max_nones": max_nones
            })

        json_objs.append({
            "_indicator_names": random.choices(best_indicators,k=5),
            "version": version
        })

        for i in range(4):
            r = Indicators().get_random_indicator_names(min=1, max=1, skip=to_skip)
            json_objs.append({
                "_additional_indicators": r,
                "version": version
            })

        for max_nones in [0,1,2]:
            for i in range(4):
                names = Indicators().get_random_indicator_names(skip=to_skip)
                json_objs.append({
                    "_indicator_names": names,
                    "_max_nones": max_nones,
                    "version": version
                })
        return json_objs

    @staticmethod
    def get_training_sets(version: str, best_indicators:List):
        return GenericPredictor._indicator_names_sets(version,best_indicators) + BasePredictor._stop_limit_trainer(version)

