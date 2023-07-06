from enum import Enum
import plotly.graph_objects as go
from pandas import DataFrame
import pandas as pd
import numpy as np
from scipy.stats import linregress
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

class PivotScanner:
    #https://www.youtube.com/watch?v=WVNB_6JRbl0
    def pivotid(self,df1, l, n1, n2):  # n1 n2 before and after candle l
        if l - n1 < 0 or l + n2 >= len(df1):
            return 0

        pividlow = 1
        pividhigh = 1
        for i in range(l - n1, l + n2 + 1):
            if (df1.low[l] > df1.low[i]):
                pividlow = 0
            if (df1.high[l] < df1.high[i]):
                pividhigh = 0
        if pividlow and pividhigh:
            return 3
        elif pividlow:
            return 1
        elif pividhigh:
            return 2
        else:
            return 0

    def pointpos(self,x):
        if x['pivot'] == 1:
            return x['low'] - 1e-3
        elif x['pivot'] == 2:
            return x['high'] + 1e-3
        else:
            return np.nan

    def scan_points(self, df):

        fig = go.Figure(data=[go.Candlestick(x=df.index,
                                             open=df['open'],
                                             high=df['high'],
                                             low=df['low'],
                                             close=df['close'])])

        for i in range(50,len(df)-22,5):
            temp_df = df[0:i+1].copy()
            temp_df['pivot'] = temp_df.apply(lambda x: self.pivotid(temp_df, x.name, 3, 3), axis=1)
            temp_df['pointpos'] = temp_df.apply(lambda row: self.pointpos(row), axis=1)
            self.find_triangle(temp_df,fig,i)

        fig.show()



    def find_triangle(self,df,fig,candleid):


        backcandles = 20

        maxim = np.array([])
        minim = np.array([])
        xxmin = np.array([])
        xxmax = np.array([])

        for i in range(candleid - backcandles, candleid + 1):
            if df.iloc[i].pivot == 1:
                minim = np.append(minim, df.iloc[i].low)
                xxmin = np.append(xxmin, i)  # could be i instead df.iloc[i].name
            if df.iloc[i].pivot == 2:
                maxim = np.append(maxim, df.iloc[i].high)
                xxmax = np.append(xxmax, i)  # df.iloc[i].name

        # slmin, intercmin = np.polyfit(xxmin, minim,1) #numpy
        # slmax, intercmax = np.polyfit(xxmax, maxim,1)
        if (xxmax.size < 3 and xxmin.size < 3) or xxmax.size == 0 or xxmin.size == 0:
            return

        slmin, intercmin, rmin, pmin, semin = linregress(xxmin, minim)
        slmax, intercmax, rmax, pmax, semax = linregress(xxmax, maxim)

        if abs(rmax) <= 0.7 or abs(rmin) <= 0.7:
            return

        #sloap >= 0.0 -> steigend
        #sloap <= 0.0 -> fallend
        # slmin > 0.0 and slmax < 0.0 -> any dreieck

        #if slmin > 0.0 and slmax < 0.0 :

        dfpl = df[candleid - backcandles - 10:candleid + backcandles + 10]


        fig.add_scatter(x=dfpl.index, y=dfpl['pointpos'], mode="markers",
                        marker=dict(size=4, color="MediumPurple"),
                        name="pivot")

        # -------------------------------------------------------------------------
        # Fitting intercepts to meet highest or lowest candle point in time slice
        # adjintercmin = df.low.loc[candleid-backcandles:candleid].min() - slmin*df.low.iloc[candleid-backcandles:candleid].idxmin()
        # adjintercmax = df.high.loc[candleid-backcandles:candleid].max() - slmax*df.high.iloc[candleid-backcandles:candleid].idxmax()

        xxmin = np.append(xxmin, xxmin[-1] + 15)
        xxmax = np.append(xxmax, xxmax[-1] + 15)
        # fig.add_trace(go.Scatter(x=xxmin, y=slmin*xxmin + adjintercmin, mode='lines', name='min slope'))
        # fig.add_trace(go.Scatter(x=xxmax, y=slmax*xxmax + adjintercmax, mode='lines', name='max slope'))

        fig.add_trace(go.Scatter(x=xxmin, y=slmin * xxmin + intercmin, mode='lines', name=f"min slope {rmin} - {slmin}"))
        fig.add_trace(go.Scatter(x=xxmax, y=slmax * xxmax + intercmax, mode='lines', name=f'max slope {rmax} - {slmax}'))
        fig.add_scatter(x=[df[-1:].index.item()],
                             y=[df[-1:].close.item()],
                             marker=dict(
                                 color='Green',
                                 size=10
                             ),
                             )
        fig.update_layout(xaxis_rangeslider_visible=False)



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
