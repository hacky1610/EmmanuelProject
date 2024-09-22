from enum import Enum
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from pandas import DataFrame
from scipy.stats import linregress
from UI.base_viewer import BaseViewer
from Tracing.Tracer import Tracer
from BL.datatypes import TradeAction

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
    HeadShoulder = 5


class Item:

    def __init__(self, hl_type: HlType, value: float, date, candle_id: int):
        self.hl_type = hl_type
        self.value = value
        self.date = date
        self.candle_id = candle_id


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
            if df.low[line] > df.low[i]:
                pividlow = 0
            if df.high[line] < df.high[i]:
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
        if x['pivot_point'] == 1:
            return x['low'] - 1e-3
        elif x['pivot_point'] == 2:
            return x['high'] + 1e-3
        else:
            return np.nan

    def get_pivot_ids(self, df):
        return df[self._lookback * -1:].apply(lambda x: self.get_pivotid(df, x.name, self._be4after, self._be4after),
                                              axis=1)

    def scan(self, df):
        df['pivot_point'] = self.get_pivot_ids(df)
        #df['pointpos'] = df[self._lookback * -1:].apply(lambda row: self.pointpos(row), axis=1)

    def _is_ascending_triangle(self, slope_min_line, slope_max_line, max_pivot_points, atr):
        """
        :param slope_min_line: Steigung der unteren Linie
        :type slope_min_line: int
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

    @staticmethod
    def _is_triangle(slmin, slmax):
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

    def get_action(self, df: DataFrame, candle_id: int, type_filter) -> (ShapeType, str):

        maxim = np.array([])
        minim = np.array([])
        xxmin = np.array([])
        xxmax = np.array([])

        for i in range(candle_id - self._lookback, candle_id + 1):
            if df.iloc[i].pivot_point == 1:
                minim = np.append(minim, df.iloc[i].low)
                xxmin = np.append(xxmin, i)  # could be i instead df.iloc[i].name
            if df.iloc[i].pivot_point == 2:
                maxim = np.append(maxim, df.iloc[i].high)
                xxmax = np.append(xxmax, i)  # df.iloc[i].name

        if (xxmax.size < 3 and xxmin.size < 3) or xxmax.size <= 1 or xxmin.size <= 1:
            return ShapeType.NoShape, TradeAction.NONE

        slmin, intercmin, rmin, _, _ = linregress(xxmin, minim)
        slmax, intercmax, rmax, _, _ = linregress(xxmax, maxim)

        if abs(rmax) <= 0.7 or abs(rmin) <= 0.7:
            return ShapeType.NoShape, TradeAction.NONE

        current_close = df[-1:].close.item()
        current_atr = df[-1:].ATR.item()
        max_distance = current_atr * self._max_dist_factor

        if self._is_ascending_triangle(slmin, slmax, xxmax, current_atr) and ShapeType.AscendingTriangle in type_filter:
            self._tracer.write("Found Ascending Triangle")
            crossing_max = slmax * candle_id + intercmax
            self._viewer.custom_print(self._print, df, candle_id, xxmin, xxmax, slmin, slmax, intercmin, intercmax,
                                      f"Ascending triangle {candle_id}")
            if current_close > crossing_max and current_close - crossing_max < max_distance:
                return ShapeType.AscendingTriangle, TradeAction.BUY

            self._tracer.write(f"No action Close {current_close} Max Dist {max_distance} Max {crossing_max} ")

            return ShapeType.AscendingTriangle, TradeAction.NONE
        elif self._is_descending_triangle(slmin, slmax, xxmin, current_atr) and ShapeType.DescendingTriangle in type_filter:
            self._tracer.write("Found Descending Triangle")
            crossing_min = slmin * candle_id + intercmin

            self._viewer.custom_print(self._print, df, candle_id, xxmin, xxmax, slmin, slmax, intercmin, intercmax,
                                      f"Descending triangle {candle_id}")
            if current_close < crossing_min and crossing_min - current_close < max_distance:
                return ShapeType.DescendingTriangle, TradeAction.SELL
            self._tracer.write(f"No action Close {current_close} Max Dist {max_distance} min {crossing_min}")

            return ShapeType.DescendingTriangle, TradeAction.NONE

        elif self._is_triangle(slmin, slmax) and ShapeType.Triangle in type_filter:
            self._tracer.write("Found Triangle")
            crossing_max = slmax * candle_id + intercmax
            crossing_min = slmin * candle_id + intercmin

            self._viewer.custom_print(self._print, df, candle_id, xxmin, xxmax, slmin, slmax, intercmin, intercmax,
                                      "Symmetric triangle")
            if current_close > crossing_max and current_close - crossing_max < max_distance:
                return ShapeType.Triangle, TradeAction.BUY
            if current_close < crossing_min and crossing_min - current_close < max_distance:
                return ShapeType.Triangle, TradeAction.SELL
            self._tracer.write(
                f"No action Close {current_close} Max Dist {max_distance} Max {crossing_max} min {crossing_min}")

        elif self._is_rectangle(slmin, slmax) and ShapeType.Rectangle in type_filter:
            self._tracer.write("Found Rectangle")
            crossing_max = slmax * candle_id + intercmax
            crossing_min = slmin * candle_id + intercmin

            self._viewer.custom_print(self._print, df, candle_id, xxmin, xxmax, slmin, slmax, intercmin, intercmax,
                                      "Rectangle")
            if current_close > crossing_max and current_close - crossing_max < max_distance:
                return ShapeType.Rectangle, TradeAction.BUY
            if current_close < crossing_min and crossing_min - current_close < max_distance:
                return ShapeType.Rectangle, TradeAction.SELL

            self._tracer.write(
                f"No action Close {current_close} Max Dist {max_distance} Max {crossing_max} min {crossing_min}")
            return ShapeType.Rectangle, TradeAction.NONE

        # elif self._is_head_shoulder(xxmax, xxmin, df, current_atr) and ShapeType.HeadShoulder in type_filter:
        #     self._tracer.write("Found Head Shoulder")
        #
        #    # self._viewer.custom_print(self._print, df, candle_id, xxmin, xxmax, slmin, slmax, intercmin, intercmax,
        #     #                          "HeadShoulder")
        #     return ShapeType.HeadShoulder, TradeAction.NONE


        return ShapeType.NoShape, TradeAction.NONE


