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
    _use_macd: bool = False
    _use_candle: bool = False
    _use_cci: bool = False
    _use_psar: bool = False
    _use_bb: bool = False
    _use_all: bool = False
    _indicator_confirm_factor: float = 0.7

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
        self._set_att(config, "_use_macd")
        self._set_att(config, "_use_candle")
        self._set_att(config, "_use_cci")
        self._set_att(config, "_use_psar")
        self._set_att(config, "_use_bb")
        self._set_att(config, "_use_all")
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
            self._use_macd,
            self._use_candle,
            self._use_cci,
            self._use_psar,
            self._use_bb,
            self._use_all,
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
                "_use_macd",
                "_use_candle",
                "_use_cci",
                "_use_psar",
                "_use_bb",
                "_use_all",
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

    def _ema_confirmation(self, df):
        len_period = 4
        period = df[-1 * len_period:]

        if (len(period[period.EMA_30 < period.EMA_20]) == len_period and
                len(period[period.EMA_20 < period.EMA_10]) == len_period):
            return BasePredictor.BUY
        elif (len(period[period.EMA_30 > period.EMA_20]) == len_period and
              len(period[period.EMA_20 > period.EMA_10]) == len_period):
            return BasePredictor.SELL

        return BasePredictor.NONE

    def _rsi_smooth_slope(self, df):
        diff = df.RSI_SMOOTH.diff()[-1:].item()
        if diff < 0:
            return BasePredictor.SELL
        else:
            return BasePredictor.BUY


    def _rsi_confirmation(self, df):
        current_rsi = df[-1:].RSI.item()
        if current_rsi < 50 - self._rsi_add_value:
            return BasePredictor.SELL
        elif current_rsi > 50 + self._rsi_add_value:
            return BasePredictor.BUY

        return BasePredictor.NONE

    def _cci_confirmation(self, df):
        cci = df[-1:].CCI.item()

        if cci > 100:
            return BasePredictor.BUY
        elif cci < -100:
            return BasePredictor.SELL

        return BasePredictor.NONE

    def _psar_confirmation(self, df):
        psar = df[-1:].PSAR.item()
        ema_20 = df[-1:].EMA_20.item()
        close = df[-1:].close.item()

        if psar < ema_20 and close > ema_20 and psar < close:
            return BasePredictor.BUY
        elif psar > ema_20 and close < ema_20 and psar > close:
            return BasePredictor.SELL

        return BasePredictor.NONE

    def _candle_confirmation(self, df):
        c = Candle(df[-1:])

        if c.direction() == Direction.Bullish:
            return BasePredictor.BUY
        else:
            return BasePredictor.SELL

    def _adx_confirmation(self, df):
        adx = df.ADX[-1:].item()

        if adx > 25:
            return BasePredictor.BOTH

        return BasePredictor.NONE

    def _macd_confirmation(self, df):
        current_macd = df[-1:].MACD.item()
        current_signal = df[-1:].SIGNAL.item()
        if current_macd > current_signal:
            return BasePredictor.BUY
        else:
            return BasePredictor.SELL

    def _bb_confirmation(self, df):
        bb_middle = df[-1:].BB_MIDDLE.item()
        bb_upper = df[-1:].BB_UPPER.item()
        bb_lower = df[-1:].BB_LOWER.item()
        close = df[-1:].close.item()

        if bb_middle < close < bb_upper:
            return BasePredictor.BUY
        elif bb_middle > close > bb_lower:
            return BasePredictor.SELL

        return BasePredictor.NONE

    def _add_extra_confirmations(self, confirmation_func_list: list):
        confirmation_func_list.append(self._macd_confirmation)
        confirmation_func_list.append(self._candle_confirmation)
        confirmation_func_list.append(self._cci_confirmation)
        confirmation_func_list.append(self._psar_confirmation)
        confirmation_func_list.append(self._bb_confirmation)
        confirmation_func_list.append(self._rsi_smooth_slope)
        confirmation_func_list.append(self._adx_confirmation)
        return confirmation_func_list



    def _confirm(self, df) -> str:
        confirmation_func_list = [self._rsi_confirmation, self._ema_confirmation]
        confirmation_func_list = self._add_extra_confirmations(confirmation_func_list)

        confirmation_list = []
        for f in confirmation_func_list:
            confirmation_list.append(f(df))

        if (confirmation_list.count(BasePredictor.BUY) + confirmation_list.count(BasePredictor.BOTH)) > len(confirmation_list) * self._indicator_confirm_factor:
            return BasePredictor.BUY
        elif (confirmation_list.count(BasePredictor.SELL) + confirmation_list.count(BasePredictor.BOTH)) > len(confirmation_list) * self._indicator_confirm_factor:
            return BasePredictor.SELL


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
                self._tracer.write(f"{action} confirmed with indikators")
                return action, stop * self._stop_limit_ratio, limit
            else:
                self._tracer.write("No action because it was not confirmed")

        return BasePredictor.NONE, 0, 0

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
                "_use_all": True,
                "_use_bb": False,
                "_use_psar": False,
                "_use_cci": False,
                "_use_candle": False,
                "_use_macd": False,
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
