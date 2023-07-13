import itertools
from BL.high_low_scanner import PivotScanner
from Connectors import BaseCache
from Predictors.base_predictor import BasePredictor
from pandas import DataFrame, Series
from Tracing.Tracer import Tracer
from Tracing.ConsoleTracer import ConsoleTracer
from UI.base_viewer import BaseViewer


class ChartPatternPredictor(BasePredictor):
    # https://www.youtube.com/watch?v=6c5exPYoz3U
    _limit_factor: float = 2
    _look_back: int = 40
    _be4after: int = 3
    _max_dist_factor: float = 2.0
    _straight_factor: float = 0.4

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
        self._limit_factor = config.get("_limit_factor", self._limit_factor)
        self._look_back = config.get("_look_back", self._look_back)
        self._be4after = config.get("_be4after", self._be4after)
        self._max_dist_factor = config.get("_max_dist_factor", self._max_dist_factor)
        self._straight_factor = config.get("_straight_factor", self._straight_factor)

        super().setup(config)

    def get_config(self) -> Series:
        return Series(["SupResCandle",
                       self.stop,
                       self.limit,
                       self._limit_factor,
                       self._look_back,
                       self._be4after,
                       self._max_dist_factor,
                       self._straight_factor,
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
                             "_limit_factor",
                             "_look_back",
                             "_be4after",
                             "_max_dist_factor",
                             "_straight_factor",
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
        ps = PivotScanner(viewer=self._viewer,
                          lookback=self._look_back,
                          be4after=self._be4after,
                          max_dist_factor=self._max_dist_factor,
                          straight_factor=self._straight_factor)
        ps.scan(df)
        action = ps.get_action(df, df[-1:].index.item())

        current_ema_20 = df[-1:].EMA_20.item()
        current_ema_50 = df[-1:].EMA_50.item()

        if action != BasePredictor.NONE:
            if action == BasePredictor.BUY and current_ema_20 > current_ema_50:
                stop = limit = df.ATR.mean() * self._limit_factor
                return action, stop, limit
            if action == BasePredictor.SELL and current_ema_20 < current_ema_50:
                stop = limit = df.ATR.mean() * self._limit_factor
                return action, stop, limit

        return self.NONE, 0, 0

    @staticmethod
    def _scan_sets(version: str):

        json_objs = []
        for lookback, b4after in itertools.product(
                [17, 31],
                [3, 6, 9, 12],
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
        for factor in [1.7, 2.1, 2.7]:
            json_objs.append({
                "_limit_factor": factor,
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
    def _straight_factor_set(version: str):

        json_objs = []
        for fact in [0.1, 0.3, 0.4]:
            json_objs.append({
                "_straight_factor": fact,
                "version": version
            })
        return json_objs

    @staticmethod
    def get_training_sets(version: str):
        return ChartPatternPredictor._scan_sets(version) + \
            ChartPatternPredictor._stop_limit_sets(version) + \
            ChartPatternPredictor._straight_factor_set(version) + \
            ChartPatternPredictor._max_dist_set(version)
