import datetime
from typing import List, Optional
from collections import Counter
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
            "_trading_hours": predictor._trading_hours,
            "_trade_mode": predictor._trade_mode
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

    def load_all_by_symbol_and_trade_mode(self, symbol, trade_mode):
        return self._collection.find({"_symbol": symbol, "_trade_mode": trade_mode})

    def load_all(self):
        return self._collection.find({})

    def count_of_all_by_symbol(self, symbol) -> int:
        return self._collection.count_documents({"_symbol": symbol})

    def count_of_all_by_symbol_and_trade_mode(self, symbol, trade_mode) -> int:
        return self._collection.count_documents({"_symbol": symbol, "_trade_mode":trade_mode})

    def get_most_used_features(self) -> List[str]:
        features_list = []
        for doc in self._collection.find({}, {"_features": 1}):
            if "_features" in doc and isinstance(doc["_features"], list):
                features_list.extend(doc["_features"])

        # Feature-Häufigkeit berechnen
        feature_counts = Counter(features_list)

        # Ergebnisse ausgeben
        print("Feature-Häufigkeiten:")
        for feature, count in feature_counts.most_common():
            print(f"{feature}: {count}")

        # Top 33 % Features bestimmen
        top_n = int(len(feature_counts) * 0.50)
        top_features = feature_counts.most_common(top_n)

        print("\nTop 33 % Features:")
        for feature, count in top_features:
            print(f"{feature}: {count}")

        top_features_list = [feature for feature, _ in feature_counts.most_common(top_n)]

        return top_features_list


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


