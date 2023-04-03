from Predictors.base_predictor import BasePredictor
from pandas import DataFrame

class PredictorCollection(BasePredictor):

    def __init__(self, predicors: list, config: dict):
        super().__init__(config)
        self._predictors = predicors

    def predict(self,df:DataFrame):
        a = self._predictors[0].predict(df)
        b = self._predictors[1].predict(df)

        if a == b:
            return a
        else:
            return BasePredictor.NONE



