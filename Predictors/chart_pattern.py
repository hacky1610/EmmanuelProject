import itertools
import random
from BL.high_low_scanner import PivotScanner
from Connectors.dropbox_cache import BaseCache
from Predictors.base_predictor import BasePredictor
from pandas import Series, DataFrame
from Tracing.Tracer import Tracer
from Tracing.ConsoleTracer import ConsoleTracer
from UI.base_viewer import BaseViewer


class ChartPatternPredictor(BasePredictor):
    # https://www.youtube.com/watch?v=6c5exPYoz3U

    # region Members
    _limit_factor: float = 2
    _look_back: int = 40
    _local_look_back: int = 1
    _be4after: int = 3
    _max_dist_factor: float = 2.0
    _straight_factor: float = 0.4
    _stop_limit_ratio: float = 1.0
    _rsi_add_value: int = 0
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
        self._set_att(config, "_local_look_back")
        self._set_att(config, "_stop_limit_ratio")
        self._set_att(config, "_rsi_add_value")


        self._look_back = int(self._look_back)
        self._be4after = int(self._be4after)
        self._local_look_back = int(self._local_look_back)
        super().setup(config)

    def get_config(self) -> Series:
        parent_c = super().get_config()
        my_conf =  Series([
                       self._limit_factor,
                       self._look_back,
                       self._be4after,
                       self._max_dist_factor,
                       self._local_look_back,
                       self._stop_limit_ratio,
                       self._rsi_add_value
                       ],
                      index=[
                             "_limit_factor",
                             "_look_back",
                             "_be4after",
                             "_max_dist_factor",
                             "_local_look_back",
                             "_stop_limit_ratio",
                             "_rsi_add_value"
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

    def _ema_confirmation(self, df):
        current_ema_10 = df[-1:].EMA_10.item()
        current_ema_20 = df[-1:].EMA_20.item()
        current_ema_30 = df[-1:].EMA_30.item()

        if current_ema_10 > current_ema_20 > current_ema_30:
            return BasePredictor.BUY
        elif current_ema_30 > current_ema_20 > current_ema_10:
            return BasePredictor.SELL

        return BasePredictor.NONE

    def _rsi_confirmation(self,df):
        current_rsi = df[-1:].RSI.item()
        if current_rsi < 50 - self._rsi_add_value:
            return BasePredictor.SELL
        elif current_rsi > 50 + self._rsi_add_value:
            return BasePredictor.BUY

        return BasePredictor.NONE

    def _confirm(self, df) -> str:
        confirmation_func_list = [self._rsi_confirmation, self._ema_confirmation]
        confirmation_list = []
        for f in confirmation_func_list:
            confirmation_list.append(f(df))

        s = set(confirmation_list)
        if len(s) == 1:
            return confirmation_list[0]
        else:
            return BasePredictor.NONE

    def _get_action(self, df, filter, local_lookback=1, **kwargs):
        action = BasePredictor.NONE
        for i in range(local_lookback):
            if i == 0:
                temp_df = df
            else:
                temp_df = df[:-1 * i]
            ps = self._scan(temp_df, **kwargs)
            _, action = ps.get_action(temp_df, temp_df[-1:].index.item(), filter)
            if action != BasePredictor.NONE:
                return action
        return action

    def validate(self, action: str, df: DataFrame) -> (str, float, float):


        if action != BasePredictor.NONE:
            self._tracer.write(f"Got {action} from PivotScanner")
            validation_result = self._confirm(df)
            if action == validation_result:
                stop = limit = df.ATR.mean() * self._limit_factor
                self._tracer.write(f"{action} confirmed with Uptrend")
                return action, stop * self._stop_limit_ratio, limit
            elif action == validation_result:
                stop = limit = df.ATR.mean() * self._limit_factor
                self._tracer.write(f"{action} confirmed with Downtrend")
                return action, stop  * self._stop_limit_ratio, limit
            else:
                self._tracer.write("No action because it was not confirmed")

        return BasePredictor.NONE, 0, 0

    @staticmethod
    def _scan_sets(version: str):

        json_objs = []
        for lookback, b4after in itertools.product(
                random.choices(range(14, 36), k=2),
                random.choices(range(3, 12), k=2)
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
                random.choices([1.7,2.1,2.7,2.5], k=2),
                random.choices([0.7,1.0,1.3,1.5,1.8], k=2)
        ):
            json_objs.append({
                "_limit_factor": factor,
                "_stop_limit_ratio":ratio,
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
        for rsi_add_val in random.choices(range(0, 10, 3), k=1):
            json_objs.append({
                "_rsi_add_value": rsi_add_val,
                "version": version
            })
        return json_objs

    @staticmethod
    def get_training_sets(version: str):
        return ChartPatternPredictor._scan_sets(version) + \
            ChartPatternPredictor._stop_limit_sets(version) + \
            ChartPatternPredictor._indicator_set(version) + \
            ChartPatternPredictor._max_dist_set(version)
