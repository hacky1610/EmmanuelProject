import itertools
import random

from BL.candle import Candle, Direction
from BL.high_low_scanner import PivotScanner
from BL.indicators import Indicators
from Connectors.dropbox_cache import BaseCache
from Predictors.base_predictor import BasePredictor
from pandas import Series, DataFrame
from Tracing.Tracer import Tracer
from Tracing.ConsoleTracer import ConsoleTracer
from UI.base_viewer import BaseViewer


class GenericPredictor(BasePredictor):
    # https://www.youtube.com/watch?v=6c5exPYoz3U

    # region Members
    _limit_factor: float = 2
    _indicator_names = [Indicators.RSI, Indicators.EMA]
    # endregion

    def __init__(self, indicators, config=None,
                 tracer: Tracer = ConsoleTracer(),
                 viewer: BaseViewer = BaseViewer(),
                 cache: BaseCache = BaseCache()):
        super().__init__(indicators, config, tracer=tracer, cache=cache)
        if config is None:
            config = {}
        self.setup(config)
        self._viewer = viewer

    def setup(self, config: dict):
        self._set_att(config, "_limit_factor")
        self._set_att(config, "_indicator_names")
        super().setup(config)

    def get_config(self) -> Series:
        parent_c = super().get_config()
        my_conf = Series([
            self._limit_factor,
            self._indicator_names

        ],
            index=[
                "_limit_factor",
                "_indicator_names",
            ])
        return parent_c.append(my_conf)

    def predict(self, df: DataFrame) -> (str, float, float):
        #action = self._indicators.predict_all(df, 1.0)
        action = self._indicators.predict_some(df, self._indicator_names)
        stop = limit = df.ATR.mean() * self._limit_factor
        return action, stop, limit



    @staticmethod
    def _indicator_names_sets(version: str):

        json_objs = []

        for i in range(5):
            names = Indicators.get_random_indicator_names(Indicators.ICHIMOKU)
            json_objs.append({
                "_indicator_names": names,
                "version": version
            })
        return json_objs



    @staticmethod
    def get_training_sets(version: str):
        return GenericPredictor._indicator_names_sets(version)

        # return ChartPatternPredictor._indicator_set(version)
