from enum import Enum
import plotly.graph_objects as go
from pandas import DataFrame
import pandas as pd
import numpy as np
from scipy.stats import linregress
from Predictors.base_predictor import BasePredictor
from UI.base_viewer import BaseViewer
from Tracing.Tracer import Tracer

pd.options.mode.chained_assignment = None


class HlType(Enum):
    HIGH = 1
    LOW = 2


class ShapeType(Enum):
    NoShape = 0
    Triangle = 1
    AscendingTriangle = 2
    DescendingTriangle = 3
    Rectangle = 4


class Item:

    def __init__(self, type: HlType, value: float, date, id):
        self.type = type
        self.value = value
        self.date = date
        self.id = id


class PivotScanner:
    # https://www.youtube.com/watch?v=WVNB_6JRbl0

    def __init__(self,
                 lookback: int = 20,
                 be4after: int = 3,
                 max_dist_factor: float = 2.0,
                 straight_factor: float = 0.4,
                 _rectangle_line_slope: float = 0.05,
                 viewer: BaseViewer = BaseViewer(),
                 tracer: Tracer = Tracer()):
        self._lookback = lookback
        self._viewer = viewer
        self._be4after = be4after
        self._max_dist_factor = max_dist_factor
        self._straight_factor = straight_factor
        self._rectangle_line_slope = _rectangle_line_slope
        self._tracer = tracer

    @staticmethod
    def get_pivotid(df, line, before, after):  # n1 n2 before and after candle l
        if line - before < 0:
            return 0

        pividlow = 1
        pividhigh = 1

        start = line - before
        end = line + after + 1

        if line + after >= len(df):
            end = len(df)

        for i in range(start, end):
            if (df.low[line] > df.low[i]):
                pividlow = 0
            if (df.high[line] < df.high[i]):
                pividhigh = 0
        if pividlow and pividhigh:
            return 3
        elif pividlow:
            return 1
        elif pividhigh:
            return 2
        else:
            return 0

    @staticmethod
    def pointpos(x):
        if x['pivot'] == 1:
            return x['low'] - 1e-3
        elif x['pivot'] == 2:
            return x['high'] + 1e-3
        else:
            return np.nan

    def get_pivot_ids(self, df):
        return df[self._lookback * -1:].apply(lambda x: self.get_pivotid(df, x.name, self._be4after, self._be4after),
                                              axis=1)

    def scan_points(self, df):

        fig = go.Figure(data=[go.Candlestick(x=df.index,
                                             open=df['open'],
                                             high=df['high'],
                                             low=df['low'],
                                             close=df['close'])])

        for i in range(self._lookback, len(df)):
            temp_df = df[0:i + 1].copy()
            self.scan(df)
            self.get_action(temp_df, i)

        fig.show()

    def scan(self, df):
        df['pivot'] = self.get_pivot_ids(df[:-2])
        df['pointpos'] = df.apply(lambda row: self.pointpos(row), axis=1)

    def _is_ascending_triangle(self, slope_min_line: float, slope_max_line: float, max_pivot_points: float, atr: float):
        """
        :param slope_min_line: Steigung der unteren Linie
        :type slope_min_line: float
        :param slope_max_line: Steigung der oberen Linie
        :type slope_max_line: float
        :param max_pivot_points: Steigung der oberen Linie
        :type max_pivot_points: float

        """
        diff = abs(slope_max_line * max_pivot_points[0] - slope_max_line * max_pivot_points[-1])
        if diff < atr * self._straight_factor:
            return slope_min_line > 0.0

    def _is_descending_triangle(self, slmin, slmax, xxmin, atr):
        diff = abs(slmin * xxmin[0] - slmin * xxmin[-1])
        if diff < atr * self._straight_factor:
            return slmax < 0.0

    def _is_triangle(self, slmin, slmax):
        return slmin > 0.0 > slmax

    def _is_rectangle(self, slmin, slmax):
        if slmin < 0 and slmax < 0 or slmin > 0 and slmax > 0:
            diff = PivotScanner.get_percentage_diff(slmin, slmax)
            return diff < self._rectangle_line_slope

    @staticmethod
    def get_percentage_diff(previous, current):
        try:
            percentage = abs(previous - current) / max(previous, current) * 100
        except ZeroDivisionError:
            percentage = float('inf')
        return percentage

    def _print(self, fig, df, candleid, xxmin, xxmax, slmin, slmax, intercmin, intercmax, name):

        dfpl = df[candleid - self._lookback - 10:candleid + self._lookback + 10]

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

        fig.add_trace(
            go.Scatter(x=xxmin, y=slmin * xxmin + intercmin, mode='lines', name=f"Lower of {name}", hovertemplate=
            f'<b>{name}</b>' +
            '<i>Price</i>: $%{y:.4f}' +
            '<br><b>X</b>: %{x}<br>' +
            '<b>%{text}</b>',
                       text=dfpl.date))
        fig.add_trace(
            go.Scatter(x=xxmax, y=slmax * xxmax + intercmax, mode='lines', name=f"Upper of {name}", hovertemplate=
            f'<b>{name}</b>' +
            '<i>Price</i>: $%{y:.4f}' +
            '<br><b>X</b>: %{x}<br>' +
            '<b>%{text}</b>',
                       text=dfpl.date))

        fig.add_scatter(x=[candleid],
                        y=[df.close[candleid]],
                        name=name,
                        marker=dict(
                            color='Blue',
                            size=10,
                            symbol="square",
                        )
                        )

        fig.update_layout(xaxis_rangeslider_visible=False)

    def get_action(self, df, candleid, filter) -> (ShapeType, str):

        maxim = np.array([])
        minim = np.array([])
        xxmin = np.array([])
        xxmax = np.array([])

        for i in range(candleid - self._lookback, candleid + 1):
            if df.iloc[i].pivot == 1:
                minim = np.append(minim, df.iloc[i].low)
                xxmin = np.append(xxmin, i)  # could be i instead df.iloc[i].name
            if df.iloc[i].pivot == 2:
                maxim = np.append(maxim, df.iloc[i].high)
                xxmax = np.append(xxmax, i)  # df.iloc[i].name

        if (xxmax.size < 3 and xxmin.size < 3) or xxmax.size <= 1 or xxmin.size <= 1:
            return ShapeType.NoShape, BasePredictor.NONE

        slmin, intercmin, rmin, pmin, semin = linregress(xxmin, minim)
        slmax, intercmax, rmax, pmax, semax = linregress(xxmax, maxim)

        if abs(rmax) <= 0.7 or abs(rmin) <= 0.7:
            return ShapeType.NoShape, BasePredictor.NONE

        current_close = df[-1:].close.item()
        current_atr = df[-1:].ATR.item()
        max_distance = current_atr * self._max_dist_factor

        if self._is_ascending_triangle(slmin, slmax, xxmax, current_atr) and ShapeType.AscendingTriangle in filter:
            self._tracer.debug("Found Ascending Triangle")
            crossing_max = slmax * candleid + intercmax
            self._viewer.custom_print(self._print, df, candleid, xxmin, xxmax, slmin, slmax, intercmin, intercmax,
                                      f"Ascending triangle {candleid}")
            if current_close > crossing_max and current_close - crossing_max < max_distance:
                return ShapeType.AscendingTriangle, BasePredictor.BUY

            self._tracer.debug(f"No action Close {current_close} Max Dist {max_distance} Max {crossing_max} ")

            return ShapeType.AscendingTriangle, BasePredictor.NONE
        elif self._is_descending_triangle(slmin, slmax, xxmin, current_atr) and ShapeType.DescendingTriangle in filter:
            self._tracer.debug("Found Descending Triangle")
            crossing_min = slmin * candleid + intercmin

            self._viewer.custom_print(self._print, df, candleid, xxmin, xxmax, slmin, slmax, intercmin, intercmax,
                                      f"Descending triangle {candleid}")
            if current_close < crossing_min and crossing_min - current_close < max_distance:
                return ShapeType.DescendingTriangle, BasePredictor.SELL
            self._tracer.debug(f"No action Close {current_close} Max Dist {max_distance} min {crossing_min}")

            return ShapeType.DescendingTriangle, BasePredictor.NONE

        elif self._is_triangle(slmin, slmax) and ShapeType.Triangle in filter:
            self._tracer.debug("Found Triangle")
            crossing_max = slmax * candleid + intercmax
            crossing_min = slmin * candleid + intercmin

            self._viewer.custom_print(self._print, df, candleid, xxmin, xxmax, slmin, slmax, intercmin, intercmax,
                                      "Symmetric triangle")
            if current_close > crossing_max and current_close - crossing_max < max_distance:
                return ShapeType.Triangle, BasePredictor.BUY
            if current_close < crossing_min and crossing_min - current_close < max_distance:
                return ShapeType.Triangle, BasePredictor.SELL
            self._tracer.debug(
                f"No action Close {current_close} Max Dist {max_distance} Max {crossing_max} min {crossing_min}")

        elif self._is_rectangle(slmin, slmax) and ShapeType.Rectangle in filter:
            self._tracer.debug("Found Rectangle")
            crossing_max = slmax * candleid + intercmax
            crossing_min = slmin * candleid + intercmin

            self._viewer.custom_print(self._print, df, candleid, xxmin, xxmax, slmin, slmax, intercmin, intercmax,
                                      "Rectangle")
            if current_close > crossing_max and current_close - crossing_max < max_distance:
                return ShapeType.Rectangle, BasePredictor.BUY
            if current_close < crossing_min and crossing_min - current_close < max_distance:
                return ShapeType.Rectangle, BasePredictor.SELL

            self._tracer.debug(
                f"No action Close {current_close} Max Dist {max_distance} Max {crossing_max} min {crossing_min}")
            return ShapeType.Rectangle, BasePredictor.NONE

        return ShapeType.NoShape, BasePredictor.NONE


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
                hl_list.append(Item(HlType.HIGH, item.high, item.date, item["index"]))
            else:
                hl_list.append(Item(HlType.LOW, item.low, item.date, item["index"]))

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
