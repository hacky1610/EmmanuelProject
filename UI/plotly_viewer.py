from UI.base_viewer import BaseViewer
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from zigzag import peak_valley_pivots


class PlotlyViewer(BaseViewer):



    def __init__(self):
        super().__init__()
        self.fig = None
        self.df = None
        self.df_eval = None
        self.title = ""
        self._level_list = []

    def init(self, title, df, df_eval):
        self.df = df
        self.df_eval = df_eval
        self.title = title


    def print_graph(self):
        self.fig = go.Figure(data=[
            #go.Line(x=self.df['date'], y=self.df["EMA_14"],
            #        line=dict(shape='linear', color='Red')),

            go.Candlestick(x=self.df['date'],
                           open=self.df['open'],
                           high=self.df['high'],
                           low=self.df['low'],
                           close=self.df['close']),
        ])
        self.fig.update_layout(
            title=self.title,
            legend_title="Legend Title",
        )

    def print_buy(self, x, y):
        self.fig.add_scatter(x=[pd.to_datetime(x)],
                             y=[y],
                             marker=dict(
                                 color='Blue',
                                 size=10,
                                 line=dict(
                                     color='Black',
                                     width=2
                                 ),
                                 symbol="triangle-up"
                             ),
                             )

    def print_sell(self, x, y):
        self.fig.add_scatter(x=[pd.to_datetime(x)],
                             y=[y],
                             marker=dict(
                                 color='Blue',
                                 size=10,
                                 line=dict(
                                     color='Black',
                                     width=2
                                 ),
                                 symbol="triangle-down"
                             ),
                             )

    def print_won(self, x, y):
        self.fig.add_scatter(x=[pd.to_datetime(x)],
                        y=[y],
                        marker=dict(
                            color='Green',
                            size=10
                        ),
                        )

    def print_lost(self, x, y):
        self.fig.add_scatter(x=[pd.to_datetime(x)],
                             y=[y],
                             marker=dict(
                                 color='Red',
                                 size=10
                             ),
                             )

    def print_text(self, x, y,text):
        self.fig.add_trace(go.Scatter(
            x=[pd.to_datetime(x)],
            y=[y],
            mode="lines+markers+text",
            name="Lines, Markers and Text",
            text=[text],
            textposition="top center"
        ))

    def print_level(self,start,end,y,color="Black"):

        self.fig.add_shape(type='line',
                      x0=start,
                      y0=y,
                      x1=end,
                      y1=y,
                      line=dict(color=color, ),
                      xref='x',
                      yref='y')

    def _plot_levels(self,where, levels, only_good=False):
        for l in levels:

            if isinstance(l, float):
                where.axhline(y=l, color='black', linestyle='-')
            elif isinstance(l, dict):
                if 'score' in l.keys():
                    if only_good and l['score'] < 0:
                        continue
                    color = 'red' if l['score'] < 0 else 'blue'
                    where.axhline(y=l['price'], color=color, linestyle='-', linewidth=0.2 * abs(l['score']))
                else:
                    where.axhline(y=l['price'], color='black', linestyle='-')

    def plot_levels(self,X, levels, zigzag_percent=1, only_good=False, path=None):
        import matplotlib.pyplot as plt
        pivots = peak_valley_pivots(X, zigzag_percent / 100, -zigzag_percent / 100)
        plt.xlim(0, len(X))
        plt.ylim(X.min() * 0.995, X.max() * 1.005)
        plt.plot(np.arange(len(X)), X, 'k-', alpha=0.9)
        plt.plot(np.arange(len(X))[pivots != 0], X[pivots != 0], 'k:', alpha=0.5)

        plt.scatter(np.arange(len(X))[pivots == 1], X[pivots == 1], color='g')
        plt.scatter(np.arange(len(X))[pivots == -1], X[pivots == -1], color='r')

        self._plot_levels(plt, levels, only_good)
        if path:
            plt.savefig(path)
        else:
            plt.show()
        plt.close()

    def show(self):
        self.fig.show()
