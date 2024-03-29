from datetime import datetime

from plotly.subplots import make_subplots

from Connectors.dropbox_cache import BaseCache
from UI.base_viewer import BaseViewer
import plotly.graph_objects as go
import pandas as pd

class PlotlyViewer(BaseViewer):

    def __init__(self, cache: BaseCache):
        super().__init__()
        self.fig = None
        self.df = None
        self.df_eval = None
        self.title = ""
        self._level_list = []
        self._cache = cache

    def init(self, title, df, df_eval):
        self.df = df
        self.df_eval = df_eval
        self.title = title

    def _print_line(self, data: str, color: str):
        return go.Line(x=self.df.index, y=self.df[data], name=data,
                       line=dict(shape='linear', color=color))

    def print_graph(self):

        self.fig = make_subplots(specs=[[{"secondary_y": True}]])
        self.fig.add_trace(go.Candlestick(x=self.df.index,
                           open=self.df['open'],
                           high=self.df['high'],
                           low=self.df['low'],
                           close=self.df['close']))

        # self.fig.add_trace(self._print_line("EMA_10", "Red"))
        # self.fig.add_trace(self._print_line("EMA_20", "Orange"))
        # self.fig.add_trace(self._print_line("EMA_30", "Blue"))
        # self.fig.add_trace(go.Line(x=self.df.index,
        #                            y=self.df["MACD"],
        #                            line=dict(shape='linear', color="Blue")),
        #                             secondary_y=True)
        # self.fig.add_trace(go.Line(x=self.df.index,
        #                            y=self.df["SIGNAL"],
        #                            line=dict(shape='linear', color="Red")),
        #                    secondary_y=True)
        #
        # self.fig.update_yaxes(range=[self.df["MACD"].min(), self.df["MACD"].max() * 4], secondary_y=True)

        self.fig.update_layout(
            title=self.title,
            legend_title="Legend Title",
        )

    def update_title(self, additional_text: str):
        self.fig.update_layout(
            title=self.title + " " + additional_text
        )

    def _print_sell_buy(self, x, y, name, icon, add_text):
        self.fig.add_scatter(x=[x],
                             y=[y],
                             name=name,
                             marker=dict(
                                 color='Blue',
                                 size=10,
                                 line=dict(
                                     color='Black',
                                     width=2
                                 ),
                                 symbol=icon,
                             ),
                             hovertemplate=
                             '<i>Price</i>: $%{y:.4f}' +
                             '<br><b>X</b>: %{x}<br>' +
                             f'<b>{add_text}</b>',
                             )

    def print_buy(self, x, y, add_text: str = ""):
        self._print_sell_buy(x, y, "buy", "triangle-up", add_text)

    def print_sell(self, x, y, add_text: str = ""):
        self._print_sell_buy(x, y, "sell", "triangle-down", add_text)

    def print_won(self, x, y):
        self.fig.add_scatter(x=[x],
                             y=[y],
                             marker=dict(
                                 color='Green',
                                 size=10
                             ),
                             )

    def print_lost(self, x, y):
        self.fig.add_scatter(x=[x],
                             y=[y],
                             marker=dict(
                                 color='Red',
                                 size=10
                             ),
                             )

    def print_text(self, x, y, text):
        self.fig.add_trace(go.Scatter(
            x=[pd.to_datetime(x)],
            y=[y],
            mode="lines+markers+text",
            name="Lines, Markers and Text",
            text=[text],
            textposition="top center"
        ))

    def print_level(self, start, end, top, bottom, color="Black"):
        self.fig.add_scatter(x=[start, end, end, start],
                             y=[bottom, bottom, top, top],
                             fill="toself",
                             fillcolor=color,
                             mode='text',
                             opacity=0.3,
                             showlegend=False)

    def save(self, symbol):
        import tempfile
        filename = tempfile.NamedTemporaryFile().name
        self.fig.write_html(filename)
        time_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._cache.save_report_image(filename, f"Report/{symbol}_{time_str}.html")

    @staticmethod
    def _plot_levels(where, levels, only_good=False):
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

    def plot_levels(self, X, levels, zigzag_percent=1, only_good=False, path=None):
        pass
        # import matplotlib.pyplot as plt
        # pivots = peak_valley_pivots(X, zigzag_percent / 100, -zigzag_percent / 100)
        # plt.xlim(0, len(X))
        # plt.ylim(X.min() * 0.995, X.max() * 1.005)
        # plt.plot(np.arange(len(X)), X, 'k-', alpha=0.9)
        # plt.plot(np.arange(len(X))[pivots != 0], X[pivots != 0], 'k:', alpha=0.5)
        #
        # plt.scatter(np.arange(len(X))[pivots == 1], X[pivots == 1], color='g')
        # plt.scatter(np.arange(len(X))[pivots == -1], X[pivots == -1], color='r')
        #
        # self._plot_levels(plt, levels, only_good)
        # if path:
        #     plt.savefig(path)
        # else:
        #     plt.show()
        # plt.close()

    def print_points(self, x_list, y_list, color="black"):
        self.fig.add_trace(go.Scatter(
            x=pd.to_datetime(x_list),
            y=y_list,
            mode='markers',
            marker=dict(
                symbol='square',
                size=7,
                color='blue'
            )
        ))

    def print_highs(self, x_list, y_list):
        self.fig.add_trace(go.Scatter(
            x=pd.to_datetime(x_list),
            y=y_list,
            mode='markers',
            marker=dict(
                symbol='star-triangle-up',
                size=7,
                color='blue'
            )
        ))

    def print_lows(self, x_list, y_list):
        self.fig.add_trace(go.Scatter(
            x=pd.to_datetime(x_list),
            y=y_list,
            mode='markers',
            marker=dict(
                symbol='star-triangle-down',
                size=7,
                color='blue'
            )
        ))

    def print_line(self, x1, y1, x2, y2, color="Black"):
        self.fig.add_shape(type="line",
                           x0=pd.to_datetime(x1), y0=y1, x1=pd.to_datetime(x2), y1=y2,
                           line=dict(color=color, width=2)
                           )

    def show(self):
        self.fig.show()

    def custom_print(self, func, *kwargs):
        func(self.fig, *kwargs)
