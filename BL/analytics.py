from BL.eval_result import EvalResult, TradeResult
from Tracing.Tracer import Tracer
from Tracing.ConsoleTracer import ConsoleTracer
from pandas import DataFrame
from BL.datatypes import TradeAction
import pandas as pd
from datetime import timedelta
from UI.base_viewer import BaseViewer


class Analytics:

    def __init__(self, tracer: Tracer = ConsoleTracer()):
        self._tracer = tracer

    @staticmethod
    def _create_additional_info(row, *args):
        text = ""
        for i in args:
            text += f"{i}:" + "{0:0.5}".format(row[i]) + "\r\n"

        return text



    @staticmethod
    def _calc_spread(df_train):
        return (abs((df_train.close - df_train.close.shift(1))).median()) * 0.8
