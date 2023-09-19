import itertools
import random

from BL.candle import Candle, Direction
from BL.datatypes import TradeAction
from BL.high_low_scanner import PivotScanner
from Connectors.dropbox_cache import BaseCache
from Predictors.base_predictor import BasePredictor
from pandas import Series, DataFrame
from Tracing.Tracer import Tracer
from Tracing.ConsoleTracer import ConsoleTracer
from UI.base_viewer import BaseViewer


class ChartPatternPredictor(BasePredictor):
    # https://www.youtube.com/watch?v=6c5exPYoz3U

    def __init__(self, indicators, config=None,
                 tracer: Tracer = ConsoleTracer(),
                 viewer: BaseViewer = BaseViewer(),
                 cache: BaseCache = BaseCache()):
        super().__init__(indicators, config, tracer=tracer, cache=cache)
        # region Members
        self._limit_factor: float = 2
        self._look_back: int = 40
        self._local_look_back: int = 1
        self._be4after: int = 3
        self._max_dist_factor: float = 2.0
        self._straight_factor: float = 0.4
        self._stop_limit_ratio: float = 1.0
        self._rsi_add_value: int = 0
        self._use_macd: bool = False
        self._use_candle: bool = False
        self. _use_cci: bool = False
        self._use_psar: bool = False
        self._use_bb: bool = False
        self._use_all: bool = False
        self._indicator_confirm_factor: float = 0.7
        # endregion

        if config is None:
            config = {}
        self.setup(config)
        self._viewer = viewer

    def setup(self, config: dict):
        self._set_att(config, "_limit_factor")
        self._set_att(config, "_look_back")
        self._set_att(config, "_be4after")
        self._set_att(config, "_max_dist_factor")
        self._set_att(config, "_local_look_back")
        self._set_att(config, "_stop_limit_ratio")
        self._set_att(config, "_rsi_add_value")
        self._set_att(config, "_indicator_confirm_factor")

        self._look_back = int(self._look_back)
        self._be4after = int(self._be4after)
        self._local_look_back = int(self._local_look_back)
        self._use_all = True
        super().setup(config)

    def get_config(self) -> Series:
        parent_c = super().get_config()
        my_conf = Series([
            self._limit_factor,
            self._look_back,
            self._be4after,
            self._max_dist_factor,
            self._local_look_back,
            self._stop_limit_ratio,
            self._rsi_add_value,
            self._indicator_confirm_factor
        ],
            index=[
                "_limit_factor",
                "_look_back",
                "_be4after",
                "_max_dist_factor",
                "_local_look_back",
                "_stop_limit_ratio",
                "_rsi_add_value",
                "_indicator_confirm_factor"
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

    def _confirm(self, df) -> str:

        return self._indicators.predict_all(df, self._indicator_confirm_factor)

    def _get_action(self, df, filter, local_lookback=1, **kwargs):
        action = TradeAction.NONE
        for i in range(local_lookback):
            if i == 0:
                temp_df = df
            else:
                temp_df = df[:-1 * i]
            ps = self._scan(temp_df, **kwargs)
            _, action = ps.get_action(temp_df, temp_df[-1:].index.item(), filter)
            if action != TradeAction.NONE:
                return action
        return action

    def validate(self, action: str, df: DataFrame) -> (str, float, float):
        if action != TradeAction.NONE:
            self._tracer.write(f"Got {action} from PivotScanner")
            validation_result = self._confirm(df)
            if action == validation_result:
                stop = limit = df.ATR.mean() * self._limit_factor
                self._tracer.write(f"{action} confirmed with indikators")
                return action, stop * self._stop_limit_ratio, limit
            else:
                self._tracer.write("No action because it was not confirmed")

        return TradeAction.NONE, 0, 0

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
