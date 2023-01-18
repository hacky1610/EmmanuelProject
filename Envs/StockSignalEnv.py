from Envs.stocksEnv import StocksEnv
class StockSignalEnv(StocksEnv):
    def add_signals(env):
        start = 0
        end = len(env.df)
        prices = env.df.loc[:, 'Low'].to_numpy()[start:end]
        signal_features = env.df.loc[:, ['Low', 'Volume', 'SMA', 'RSI', 'OBV']].to_numpy()[start:end]
        return prices, signal_features

    _process_data = add_signals


