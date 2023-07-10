import itertools

from BL.candle import Candle, Direction
from BL.chart_pattern import ChartPattern, PatternType
from BL.high_low_scanner import HighLowScanner, PivotScanner
from Connectors import BaseCache
from Predictors.base_predictor import BasePredictor
from pandas import DataFrame, Series
from Tracing.Tracer import Tracer
from Tracing.ConsoleTracer import ConsoleTracer
from UI.base_viewer import BaseViewer


class ChartPatternPredictor(BasePredictor):
    # https://www.youtube.com/watch?v=6c5exPYoz3U
    _min_diff_factor = 1.5
    _limit_factor = 2
    _look_back = 20

    def __init__(self, config=None,
                 tracer: Tracer = ConsoleTracer(),
                 viewer: BaseViewer = BaseViewer(),
                 cache: BaseCache = BaseCache()):
        super().__init__(config, tracer=tracer, cache=cache)
        if config is None:
            config = {}
        self.setup(config)
        self._viewer = viewer

    def setup(self, config: dict):
        self._min_diff_factor = config.get("_min_diff_factor", self._min_diff_factor)
        self._limit_factor = config.get("_limit_factor", self._limit_factor)
        self._look_back = config.get("_look_back", self._look_back)


        super().setup(config)

    def get_config(self) -> Series:
        return Series(["SupResCandle",
                       self.stop,
                       self.limit,
                       self._min_diff_factor,
                       self._limit_factor,
                       self._look_back,
                       self.version,
                       self.best_result,
                       self.best_reward,
                       self.trades,
                       self.frequence,
                       self.last_scan,
                       ],
                      index=["Type",
                             "stop",
                             "limit",
                             "_min_diff_factor",
                             "_limit_factor",
                             "_look_back",
                             "version",
                             "best_result",
                             "best_reward",
                             "trades",
                             "frequence",
                             "last_scan",
                             ])

    def predict(self, df: DataFrame):

        if len(df) <= self._look_back:
            return BasePredictor.NONE, 0, 0
        ps = PivotScanner(viewer=self._viewer)
        ps.scan(df)
        action = ps.get_action(df, df[-1:].index.item())


        if action != BasePredictor.NONE:
            stop = limit = df.ATR.mean() * self._limit_factor
            return action,  stop, limit

        return self.NONE, 0, 0

    @staticmethod
    def _limit_diff(version: str):

        json_objs = []
        for diff, limit in itertools.product(
                [.3,.7,1.,1.5,2.7],
                [.3,.7,1.,1.5,2.7],
        ):
            json_objs.append({
                "_min_diff_factor": diff,
                "_limit_factor": limit,
                "version": version
            })
        return json_objs



    @staticmethod
    def get_training_sets(version: str):
        return ChartPatternPredictor._limit_diff(version)

