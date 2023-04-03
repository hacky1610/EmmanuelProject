from Predictors.base_predictor import BasePredictor
from pandas import DataFrame


class PredictorCollection(BasePredictor):

    def __init__(self, predicors: list, config=None):
        super().__init__(config)
        if config is None:
            config = {}
        self._predictors = predicors

    def predict(self, df: DataFrame):
        predictions = []
        for predictor in self._predictors:
            predictions.append(predictor.predict(df))

        if predictions.count(self.BUY) > len(predictions) * 0.6:
            return self.BUY
        if predictions.count(self.SELL) > len(predictions) * 0.6:
            return self.SELL

        return self.NONE
