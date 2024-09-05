from pandas import DataFrame

from BL.eval_result import TradeResult


class BaseViewer:

    def __init__(self):
        pass

    def init(self, title, df, df_eval):
        pass

    def show(self):
        pass

    def save(self, file):
        pass

    def print_graph(self):
        pass

    def print_trade_result(self, trade_result:TradeResult, df:DataFrame):
        pass

    def print_buy(self, x, y, add_text: str = ""):
        pass

    def print_buy_2(self, x, y, add_text: str = ""):
        pass

    def print_sell(self, x, y, add_text: str = ""):
        pass

    def print_sell_2(self, x, y, add_text: str = ""):
        pass

    def print_won(self, x, y):
        pass

    def print_lost(self, x, y):
        pass

    def print_won_2(self, x, y):
        pass

    def print_lost_2(self, x, y):
        pass

    def print_text(self, x, y, text):
        pass

    def print_level(self, start, end, top, bottom, color="Black"):
        pass

    def plot_levels(self, X, levels, zigzag_percent=1, only_good=False, path=None):
        pass

    def print_points(self, xs, ys, color):
        pass

    def print_highs(self, xs, ys):
        pass

    def print_lows(self, xs, ys):
        pass

    def print_line(self, x1, y1, x2, y2, color="Black"):
        pass

    def custom_print(self, func, *kwargs):
        pass

    def update_title(self, text):
        pass
