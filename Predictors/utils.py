from Predictors.base_predictor import BasePredictor
from pandas import DataFrame

def compare(a:BasePredictor,b:BasePredictor,df:DataFrame):
    similar = 0
    for i in range(len(df)):
        pred_a = a.predict(df[:i+1])
        pred_b = b.predict(df[:i + 1])
        if pred_a == pred_b:
            similar += 1

    print(similar/len(df))