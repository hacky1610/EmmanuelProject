import itertools
import random

from BL.candle import Candle, Direction
from BL.high_low_scanner import PivotScanner
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

        super().setup(config)

    def get_config(self) -> Series:
        parent_c = super().get_config()
        my_conf = Series([
            self._limit_factor,

        ],
            index=[
                "_limit_factor"
            ])
        return parent_c.append(my_conf)

    def predict(self, df: DataFrame) -> (str, float, float):

        action = self._indicators.predict_all(df, 0.9)
        stop = limit = df.ATR.mean() * self._limit_factor
        return action, stop, limit



    @staticmethod
    def _scan_sets(version: str):

        json_objs = []
        for lookback, b4after in itertools.product(
                random.choices(range(14, 36), k=1),
                random.choices(range(3, 12), k=1)
        ):
            json_objs.append({
                "_look_back": lookback,
                "_be4after": b4after,
                "version": version
            })
        return json_objs

    @staticmethod
    def _stop_limit_sets(version: str):

        json_objs = []
        for factor, ratio in itertools.product(
                random.choices([1.7, 2.1, 2.7, 2.5], k=1),
                random.choices([0.7, 1.0, 1.3, 1.5, 1.8], k=1)
        ):
            json_objs.append({
                "_limit_factor": factor,
                "_stop_limit_ratio": ratio,
                "version": version
            })
        return json_objs

    @staticmethod
    def _max_dist_set(version: str):

        json_objs = []
        for max_dist in [0.7, 1.5, 2.0]:
            json_objs.append({
                "_max_dist_factor": max_dist,
                "version": version
            })
        return json_objs

    @staticmethod
    def _indicator_set(version: str):

        json_objs = []

        for fact in [0.6, 0.7, 0.8, 0.9]:
            json_objs.append({
                "_indicator_confirm_factor": fact,
                "version": version
            })

        random.shuffle(json_objs)
        return json_objs

    @staticmethod
    def get_training_sets(version: str):
        return ChartPatternPredictor._scan_sets(version) + \
            ChartPatternPredictor._indicator_set(version) + \
            ChartPatternPredictor._max_dist_set(version)

        # return ChartPatternPredictor._indicator_set(version)
