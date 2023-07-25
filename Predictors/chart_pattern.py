import itertools
import random
from BL.high_low_scanner import PivotScanner, ShapeType
from Connectors import BaseCache
from Predictors.base_predictor import BasePredictor
from pandas import DataFrame, Series
from Tracing.Tracer import Tracer
from Tracing.ConsoleTracer import ConsoleTracer
from UI.base_viewer import BaseViewer


class ChartPatternPredictor(BasePredictor):
    # https://www.youtube.com/watch?v=6c5exPYoz3U

    # region Members
    _limit_factor: float = 2
    _look_back: int = 40
    _be4after: int = 3
    _max_dist_factor: float = 2.0
    _straight_factor: float = 0.4
    # endregion

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
        self._set_att(config, "_limit_factor")
        self._set_att(config, "_look_back")
        self._set_att(config, "_be4after")
        self._set_att(config, "_max_dist_factor")

        self._look_back = int(self._look_back)
        self._be4after = int(self._be4after)
        super().setup(config)

    def get_config(self) -> Series:
        parent_c = super().get_config()
        my_conf =  Series([
                       self._limit_factor,
                       self._look_back,
                       self._be4after,
                       self._max_dist_factor
                       ],
                      index=[
                             "_limit_factor",
                             "_look_back",
                             "_be4after",
                             "_max_dist_factor",
                             ])
        return parent_c.append(my_conf)

    def _scan(self, df, **kwargs):
        ps = PivotScanner(viewer=self._viewer,
                          lookback=self._look_back,
                          be4after=self._be4after,
                          max_dist_factor=self._max_dist_factor,
                          tracer=self._tracer,
                          **kwargs)
        ps.scan(df)
        return ps

    def _get_action(self, df, filter, local_lookback=1, **kwargs):
        action = BasePredictor.NONE
        for i in range(local_lookback):
            if i == 0:
                temp_df = df
            else:
                temp_df = df[:-1 * i]
            ps = self._scan(temp_df, **kwargs)
            t, action = ps.get_action(temp_df, temp_df[-1:].index.item(), filter)
            if action != BasePredictor.NONE:
                return action
        return action

    def is_with_trend(self, action,df):
        current_ema_20 = df[-1:].EMA_20.item()
        current_ema_50 = df[-1:].EMA_50.item()

        if action != BasePredictor.NONE:
            self._tracer.debug(f"Got {action} from PivotScanner")
            if action == BasePredictor.BUY and current_ema_20 > current_ema_50:
                stop = limit = df.ATR.mean() * self._limit_factor
                return action, stop, limit
            if action == BasePredictor.SELL and current_ema_20 < current_ema_50:
                stop = limit = df.ATR.mean() * self._limit_factor
                return action, stop, limit
            self._tracer.debug(f"No action because it is against trend")

        return BasePredictor.NONE, 0, 0

    @staticmethod
    def _scan_sets(version: str):

        json_objs = []
        for lookback, b4after in itertools.product(
                random.choices(range(14, 36), k=2),
                random.choices(range(3, 12), k=2),
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
    def get_training_sets(version: str):
        return ChartPatternPredictor._scan_sets(version) + \
            ChartPatternPredictor._stop_limit_sets(version) + \
            ChartPatternPredictor._max_dist_set(version)
