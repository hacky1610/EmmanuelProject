from UI.base_viewer import BaseViewer
import plotly.graph_objects as go
import pandas as pd


class PlotlyViewer(BaseViewer):



    def __init__(self):
        super().__init__()
        self.fig = None
        self.df = None
        self.df_eval = None
        self.title = ""

    def init(self, title, df, df_eval):
        self.df = df
        self.df_eval = df_eval
        self.title = title


    def print_graph(self):
        self.fig = go.Figure(data=[
            go.Line(x=self.df['date'], y=self.df["BB_LOWER"],
                    line=dict(shape='linear', color='Orange')),
            go.Line(x=self.df['date'], y=self.df["BB_UPPER"],
                    line=dict(shape='linear', color='Orange')),
            go.Candlestick(x=self.df_eval['date'],
                           open=self.df_eval['open'],
                           high=self.df_eval['high'],
                           low=self.df_eval['low'],
                           close=self.df_eval['close']),
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

    def show(self):
        self.fig.show()
