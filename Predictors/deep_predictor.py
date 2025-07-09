import datetime
import pickle
from typing import List

import numpy as np
import pandas as pd
from BL import measure_time
from Predictors.base_predictor import BasePredictor
from pandas import Series, DataFrame
from Tracing.Tracer import Tracer
from Tracing.ConsoleTracer import ConsoleTracer
from UI.base_viewer import BaseViewer
from BL.datatypes import TradeAction
import uuid


class DeepPredictor(BasePredictor):
    # https://www.youtube.com/watch?v=6c5exPYoz3U

    def __init__(self, symbol:str,
                 cache,
                 indicators,
                 config=None,
                 tracer: Tracer = ConsoleTracer(),
                 viewer: BaseViewer = BaseViewer()
                 ):
        self._cache = cache
        self._viewer = viewer
        self._model = None
        self._model_id = ""
        self._model_data = None
        self._trade_mode = TradeAction.NONE

        self._features = []
        self._trading_hours = 4
        self._threshold = 0.5
        self._atr_factor = 0.0
        self._atr_factor_limit = 0.0
        self._atr_factor_stop = 0.0
        self._test_reward = None
        self._unique_indexes = None
        self._test_precision = None
        self._test_trade_count = None
        self._training_time = None
        self._indicators = indicators
        self._train_reward = None
        self._train_precision = None
        self._train_trade_count = None
        if config is None:
            config = {}

        super().__init__(symbol=symbol, config=config, tracer=tracer, indicators=indicators)
        self.setup(config)

    def setup(self, config: dict):
        self._set_att(config, "_model_id")
        self._set_att(config, "_features")
        self._set_att(config, "_trading_hours")
        self._set_att(config, "_threshold")
        self._set_att(config, "_trade_mode")
        self._set_att(config, "_atr_factor")
        self._set_att(config, "_training_time")
        self._set_att(config, "_model_data")
        self._set_att(config, "_test_reward")
        self._set_att(config, "_test_precision")
        self._set_att(config, "_test_trade_count")
        self._set_att(config, "_unique_indexes")

        self._set_att(config, "_train_reward")
        self._set_att(config, "_train_precision")
        self._set_att(config, "_train_trade_count")

        if "_atr_factor_limit" in config and "_atr_factor_stop" in config:
            self._set_att(config, "_atr_factor_limit")
            self._set_att(config, "_atr_factor_stop")
        elif "_atr_factor" in config:
            self._atr_factor_limit = config["_atr_factor"]
            self._atr_factor_stop = config["_atr_factor"]

        #fix features
        self._features = list(set(self._features))

        super().setup(config)

    def clean_for_mongo(self, obj):
        if isinstance(obj, dict):
            return {k: self.clean_for_mongo(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self.clean_for_mongo(v) for v in obj]
        elif isinstance(obj, np.ndarray):
            return [self.clean_for_mongo(v) for v in obj.tolist()]
        elif isinstance(obj, (np.integer,)):  # z. B. np.int64
            return int(obj)
        elif isinstance(obj, (np.floating,)):  # z. B. np.float64
            return float(obj)
        elif isinstance(obj, datetime.datetime):
            return obj  # oder .isoformat(), je nach Bedarf
        else:
            return obj

    def get_config(self) -> Series:
        parent_c = super().get_config()
        my_conf = Series([
            self._model_id,
            self.clean_for_mongo(self._features),
            self._trading_hours,
            self._threshold,
            self._trade_mode,
            self._atr_factor,
            self._atr_factor_limit,
            self._atr_factor_stop,
            self._training_time,
            self._model_data,
            self._test_reward,
            self._test_precision,
            self._test_trade_count,
            self.clean_for_mongo(self._unique_indexes),
            self._train_reward,
            self._train_precision,
            self._train_trade_count,

        ],
            index=[
                "_model_id",
                "_features",
                "_trading_hours",
                "_threshold",
                "_trade_mode",
                "_atr_factor",
                "_atr_factor_limit",
                "_atr_factor_stop",
                "_training_time",
                "_model_data",
                "_test_reward",
                "_test_precision",
                "_test_trade_count",
                "_unique_indexes",
                "_train_reward",
                "_train_precision",
                "_train_trade_count"
            ])
        return pd.concat([parent_c, my_conf])

    def set_model(self, model):
        self._model = model
        self._model_data = pickle.dumps(model)

    def convert(self):
        if self._model_data is None:
            self._model_data = pickle.dumps(self._model)

    def set_model_params(self,
                         trade_mode:str,
                         trading_hours:int,
                         features:List,
                         atr_factor_stop:float,
                         atr_factor_limit: float,
                         test_reward:int,
                         test_precision:float,
                         test_trade_count:int,
                         train_reward: int,
                         train_precision: float,
                         train_trade_count: int,
                         unique_indexes:int):
        self._trading_hours = trading_hours
        self._features = features
        self._trade_mode = trade_mode
        self._atr_factor = atr_factor_stop
        self._atr_factor_limit = atr_factor_limit
        self._atr_factor_stop = atr_factor_stop
        self._test_reward = test_reward
        self._training_time = datetime.datetime.now()
        self._unique_indexes = unique_indexes
        self._test_precision = test_precision
        self._test_trade_count = test_trade_count

        self._train_reward = train_reward
        self._train_precision = train_precision
        self._train_trade_count = train_trade_count

    def get_trading_hours(self) -> int:
        return self._trading_hours

    def get_atr_factor(self) -> float:
        return self._atr_factor

    def get_atr_factor_limit(self) -> float:
        return self._atr_factor_limit

    def get_atr_factor_stop(self) -> float:
        return self._atr_factor_stop

    def get_threshold(self) -> float:
        return self._threshold

    def save(self):
        self._cache.save_model_cache(self._model, self._model_id)

    def predict(self, buy_actions_df: DataFrame, sell_actions_df: DataFrame):

        if self._trade_mode == TradeAction.BUY:
            actions_df = buy_actions_df
        else:
            actions_df = sell_actions_df

            # Duplikate in Spalten prüfen
        duplicated_columns = actions_df.columns[actions_df.columns.duplicated()].tolist()
        if duplicated_columns:
            raise ValueError(f"Fehler: Doppelte Spalten im DataFrame gefunden: {duplicated_columns}")

        trades = actions_df[self._features].sum(axis=1) == len(self._features)
        if trades.iloc[0]:
            return self._trade_mode
        return TradeAction.NONE

    def _clean_list(self, l):
        return list(set(l))

    @measure_time
    def load_model(self):
        if self._model_data == None:
            self._model = self._cache.load_model_cache(self._model_id)
        else:
            self._model = pickle.loads(self._model_data)



