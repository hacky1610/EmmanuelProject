

class BaseViewer:

    def __init__(self):
        pass

    def init(self,title, df,df_eval):
        pass

    def show(self):
        pass

    def print_graph(self):
        pass

    def print_buy(self,x,y):
        pass

    def print_sell(self, x, y):
        pass

    def print_won(self, x, y):
        pass

    def print_lost(self, x, y):
        pass

    def print_text(self, x, y, text):
        pass

    def print_level(self,start,end,top,bottom,color="Black"):
        pass

    def plot_levels(self,X, levels, zigzag_percent=1, only_good=False, path=None):
        pass

