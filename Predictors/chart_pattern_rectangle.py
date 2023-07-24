from BL.high_low_scanner import PivotScanner, ShapeType
from Connectors import BaseCache
from Predictors.base_predictor import BasePredictor
from pandas import DataFrame, Series
from Predictors.chart_pattern import ChartPatternPredictor
from Tracing.Tracer import Tracer
from Tracing.ConsoleTracer import ConsoleTracer
from UI.base_viewer import BaseViewer


class RectanglePredictor(ChartPatternPredictor):
    # https://www.youtube.com/watch?v=6c5exPYoz3U

    # region Members
    _rectangle_line_slope = 0.05
    # endregion

    def __init__(self, config=None,
                 tracer: Tracer = ConsoleTracer(),
                 viewer: BaseViewer = BaseViewer(),
                 cache: BaseCache = BaseCache()):
        super().__init__(config, tracer=tracer, cache=cache, viewer=viewer)
        self.model_version = "V2.0"

    def setup(self, config: dict):
        self._set_att(config, "_rectangle_line_slope")
        super().setup(config)

    def get_config(self) -> Series:
        parent_series = super().get_config()
        parent_series["_rectangle_line_slope"] = self._rectangle_line_slope
        return parent_series

    def predict(self, df: DataFrame):
        if len(df) <= self._look_back:
            return BasePredictor.NONE, 0, 0

        action = super()._get_action(df=df,
                                     filter=[ShapeType.Rectangle],
                                     local_lookback=1,
                                     _rectangle_line_slope=self._rectangle_line_slope)

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
    def _line_slope_diff(version: str):

        json_objs = []
        for diff in [0.01, 0.05, 0.007]:
            json_objs.append({
                "_rectangle_line_slope": diff,
                "version": version
            })
        return json_objs

    @staticmethod
    def get_training_sets(version: str):
        return ChartPatternPredictor.get_training_sets(version) + \
            RectanglePredictor._line_slope_diff(version)
