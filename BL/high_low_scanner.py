from enum import Enum

from pandas import DataFrame
import pandas as pd

pd.options.mode.chained_assignment = None


class HlType(Enum):
    HIGH = 1
    LOW = 2


class Item:

    def __init__(self, type: HlType, value: float, date,id):
        self.type = type
        self.value = value
        self.date = date
        self.id = id


class HighLowScanner:
    MAX = "max"
    MIN = "min"
    NONE = "none"
    COLUMN_NAME = "HLTYPE"
    _min_diff_factor = 3
    _df = DataFrame()

    def __init__(self, min_diff_factor):
        self._min_diff_factor = min_diff_factor

    def get_high_low(self):
        return self._df[self._df[self.COLUMN_NAME] != self.NONE]

    def get_high_low_items(self):
        hl_list = []
        l = self.get_high_low()
        for i in l.iterrows():
            item = i[1]
            if item[self.COLUMN_NAME] == self.MAX:
                hl_list.append(Item(HlType.HIGH, item.high, item.date,item["index"]))
            else:
                hl_list.append(Item(HlType.LOW, item.low, item.date,item["index"]))

        return hl_list

    def get_high(self):

        return self._df[self._df[self.COLUMN_NAME] == self.MAX]

    def get_low(self):

        return self._df[self._df[self.COLUMN_NAME] == self.MIN]

    def scan(self, df, max_count: int = -1):
        self._df = df

        df.loc[:, self.COLUMN_NAME] = self.NONE

        last_high_index = -1
        last_low_index = -1
        last_type = self.NONE
        min_diff = df[-1:].ATR.item() * self._min_diff_factor

        for i in range(len(df) - 2, 0, -1):

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

                if max_count > -1:
                    if len(self.get_high_low()) >= max_count:
                        return df

        return df
