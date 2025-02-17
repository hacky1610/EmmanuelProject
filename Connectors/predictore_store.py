import datetime
from typing import List, Optional

from bson import ObjectId
from pandas import DataFrame
from pymongo.database import Database
from pymongo.results import UpdateResult

from Predictors.base_predictor import BasePredictor


class PredictorStore:

    def __init__(self, db: Database):

        self._collection = db["Predictors_Combo"]

    def save(self, predictor: BasePredictor, overwrite: bool = True):
        query = {"_id": predictor.get_id()}

        # Zusätzliche Bedingung für _symbol und _features
        alternative_query = {
            "_symbol": predictor.get_symbol(),
            "_features": {"$size": len(predictor._features), "$all": predictor._features},
            "_trading_hours": predictor._trading_hours
        }

        existing_record = self._collection.find_one(query)
        alternative_record = self._collection.find_one(alternative_query)

        if existing_record and overwrite:
            self._collection.update_one(query, {"$set": predictor.get_save_data()})
        elif alternative_record and overwrite:
            self._collection.update_one(alternative_query, {"$set": predictor.get_save_data()})
        else:
            self._collection.insert_one(predictor.get_save_data())

    def load_by_id(self, predictor_id: str):
        return self._collection.find_one({"_id": predictor_id})

    def load_all_by_symbol(self, symbol):
        return self._collection.find({"_symbol": symbol})

    def load_best_by_symbol(self, symbol):
        return self._collection.find({"_symbol": symbol}, sort=[('_reward', -1)])[0]

    def load_active_by_symbol(self, symbol):
        d =  self._collection.find_one({"_symbol": symbol, "_active": True})
        if d == None:
            return {}
        return d


    def load_active_by_id(self, predictor_id:str):
        d = self._collection.find_one({"_id": ObjectId(predictor_id)})
        if d == None:
            return {}
        return d


