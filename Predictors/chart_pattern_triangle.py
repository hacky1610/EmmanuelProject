from BL.datatypes import TradeAction
from BL.high_low_scanner import ShapeType
from Connectors.dropbox_cache import BaseCache
from Predictors.base_predictor import BasePredictor
from pandas import DataFrame, Series
from Predictors.chart_pattern import ChartPatternPredictor
from Tracing.Tracer import Tracer
from Tracing.ConsoleTracer import ConsoleTracer
from UI.base_viewer import BaseViewer


class TrianglePredictor(ChartPatternPredictor):
    # https://www.youtube.com/watch?v=6c5exPYoz3U


    def __init__(self,indicators, config=None,
                 tracer: Tracer = ConsoleTracer(),
                 viewer: BaseViewer = BaseViewer(),
                 cache: BaseCache = BaseCache()):
        super().__init__(indicators, config, tracer=tracer, cache=cache, viewer=viewer)
        self._straight_factor: float = 0.4
        self.fallback_model_version = "V2.0"
        self.model_version = "V3.0"

    def setup(self, config: dict):
        self._set_att(config, "_straight_factor")
        super().setup(config)

    def get_config(self) -> Series:
        parent_series = super().get_config()
        parent_series["_straight_factor"] = self._straight_factor
        return parent_series

    def predict(self, df: DataFrame) -> (str, float, float):
        if len(df) <= self._look_back:
            return TradeAction.NONE, 0, 0

        action = super()._get_action(df=df,
                                     filter=[ShapeType.Triangle,
                                             ShapeType.DescendingTriangle,
                                             ShapeType.AscendingTriangle],
                                     local_lookback=self._local_look_back,
                                     straight_factor=self._straight_factor)

        return self.validate(action, df)

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
        return ChartPatternPredictor.get_training_sets(version) + \
            TrianglePredictor._straight_factor_set(version)
