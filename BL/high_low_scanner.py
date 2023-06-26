from enum import Enum

import numpy as np
import pandas as pd
from scipy.signal import argrelextrema, find_peaks





class HighLowScanner:
    MAX = "max"
    MIN = "min"
    NONE = "none"
    COLUMN_NAME = "HLTYPE"
    window = 5

    def is_done(self,df):
        if self.COLUMN_NAME not in df.columns:
            return False

        highs_lows =  df[df[self.COLUMN_NAME] != self.NONE]
        if len(highs_lows) == 0:
            return False

        pairs = highs_lows[highs_lows[self.COLUMN_NAME] == highs_lows[self.COLUMN_NAME].shift(-1)]

        if len(pairs) > 0:
            return False

        return True




    def scan2(self, df):
        df[self.COLUMN_NAME]  = self.NONE

        for i in range(self.window, len(df),self.window):
            if i == self.window:
                period = df[i * -1:]
            else:
                period = df[i * -1:(i - self.window) * -1]

            max = period.high.idxmax()
            min = period.low.idxmin()

            if min != max:
                df.loc[max,self.COLUMN_NAME] = self.MAX
                df.loc[min, self.COLUMN_NAME] = self.MIN


        #while not self.is_done(df):
        #    highs_lows = df[df[self.COLUMN_NAME] != self.NONE]
        #    pairs = highs_lows[highs_lows[self.COLUMN_NAME] == highs_lows[self.COLUMN_NAME].shift(-1)]

        return df

    def scan(self,df):

        df[self.COLUMN_NAME] = self.NONE

        last_high_index = -1
        last_low_index = -1
        last_type = self.NONE
        min_diff = df[-1:].ATR.item() * 3

        for i in range(len(df) - 2,0,-1):

            current_low_val = df.loc[i, "low"]
            current_high_val = df.loc[i, "high"]

            if i == len(df) - 2:
                first_low_val = df.loc[i + 1, "low"]
                first_high_val = df.loc[i + 1, "high"]

                if current_high_val < first_high_val:
                    df.loc[0, self.COLUMN_NAME] = self.MAX
                    df.loc[1, self.COLUMN_NAME] = self.MIN
                    last_high_index = i + 1
                    last_low_index = i
                    last_type = self.MIN
                else:
                    df.loc[0, self.COLUMN_NAME] = self.MIN
                    df.loc[1, self.COLUMN_NAME] = self.MAX
                    last_high_index = i
                    last_low_index = i + 1
                    last_type = self.MAX
            else:
                last_low_val = df.loc[last_low_index, "low"]
                last_high_val = df.loc[last_high_index, "high"]

                if last_type == self.MAX:
                    if current_high_val > last_high_val:
                        df.loc[last_high_index, self.COLUMN_NAME] = self.NONE
                        df.loc[i, self.COLUMN_NAME] = self.MAX
                        last_high_index = i
                    elif current_low_val < last_high_val and abs(current_low_val - last_high_val) > min_diff:
                            df.loc[i, self.COLUMN_NAME] = self.MIN
                            last_low_index = i
                            last_type = self.MIN
                elif last_type == self.MIN:
                    if current_low_val < last_low_val:
                        df.loc[last_low_index, self.COLUMN_NAME] = self.NONE
                        df.loc[i, self.COLUMN_NAME] = self.MIN
                        last_low_index = i
                    elif current_high_val > last_low_val:
                        if abs(current_high_val - last_low_val) > min_diff:
                            df.loc[i, self.COLUMN_NAME] = self.MAX
                            last_high_index = i
                            last_type = self.MAX




        return df







