from datetime import timedelta, datetime
import pandas as pd
from pandas import DataFrame, Timestamp
from tqdm import tqdm

from BL.datatypes import TradeAction
from BL.indicators import Indicators
from Connectors.dropbox_cache import DropBoxCache


class Simulation:
    def __init__(self, cache: DropBoxCache, analytics):
        self._cache = cache
        self._analytics = analytics

    def simulate(self, df: DataFrame, df_eval: DataFrame,
                 symbol: str,
                 factor_stop: float, factor_limit: float, force: bool = False) -> tuple[DataFrame, DataFrame]:
        buy_path = f"simulation_buy{symbol}_16{factor_stop}{factor_limit}h10_v2.csv"
        sell_path = f"simulation_sell{symbol}_16{factor_stop}{factor_limit}h10_v2.csv"

        if not self._cache.simulation_exist(buy_path) or force:
            buy = self._simulate_fixed_timeframe(
                action="buy",
                df=df, df_eval=df_eval,
                stop_factor=factor_stop, limit_factor=factor_limit
            )
            if buy is not None and not force:
                self._cache.save_simulation(buy, buy_path)
        else:
            buy = self._cache.load_simulation(buy_path)

        if not self._cache.simulation_exist(sell_path) or force:
            sell = self._simulate_fixed_timeframe(
                action="sell",
                df=df, df_eval=df_eval,
                stop_factor=factor_stop, limit_factor=factor_limit
            )
            if sell is not None and not force:
                self._cache.save_simulation(sell, sell_path)
        else:
            sell = self._cache.load_simulation(sell_path)
        return buy, sell

    def get_signals(self, symbol: str, df: DataFrame, indicators: Indicators, predictor_class, force: bool = False) -> None:
        for indicator in indicators.get_all_indicator_names():
            path = f"signal_{symbol}_{indicator}.csv"
            if not self._cache.signal_exist(path) or force:
                predictor = predictor_class(symbol=symbol, indicators=indicators)
                predictor.setup({"_indicator_names": [indicator], "_stop": 50, "_limit": 50})
                trades = predictor.get_signals(df, self._analytics)
                self._cache.save_signal(trades, path)

    def get_signals_by_indicatornames(self, symbol: str, df: DataFrame, features: list, indicators, predictor_class, force: bool = False) -> None:
        for indicator in features:
            path = f"signal_{symbol}_{indicator}test.csv"
            predictor = predictor_class(symbol=symbol, indicators=indicators)
            predictor.setup({"_indicator_names": [indicator], "_stop": 50, "_limit": 50})
            trades = predictor.get_signals(df, self._analytics)
            self._cache.save_signal(trades, path)

    def create_combined_indicator_data(self, indicators: Indicators, symbol: str) -> DataFrame:
        df_list = []
        for indicator in indicators.get_all_indicator_names():
            try:
                df = self._cache.load_signal(f"signal_{symbol}_{indicator}.csv")
                df = df.rename(columns={"action": indicator})[["chart_index", indicator]]
                df.set_index("chart_index", inplace=True)
                df_list.append(df)
            except Exception as e:
                print(f"Fehler beim Laden von {indicator}: {e}")
        if not df_list:
            return pd.DataFrame()
        merged_df = pd.concat(df_list, axis=1, join="outer").fillna("none")
        return merged_df

    def create_combined_indicator_data_by_features(self, features: list, symbol: str, suffix: str = "") -> DataFrame:
        df_list = []
        for indicator in features:
            try:
                df = self._cache.load_signal(f"signal_{symbol}_{indicator}{suffix}.csv")
                df = df.rename(columns={"action": indicator})[["chart_index", indicator]]
                df.set_index("chart_index", inplace=True)
                df_list.append(df)
            except Exception as e:
                print(f"Fehler beim Laden von {indicator}: {e}")
        if not df_list:
            return pd.DataFrame()
        merged_df = pd.concat(df_list, axis=1, join="outer").fillna("none")
        return merged_df

    def _simulate_fixed_timeframe(self,
                                 action: str,
                                 df: DataFrame,
                                 df_eval: DataFrame,
                                 stop_factor: float,
                                 limit_factor: float) -> DataFrame:
        """
        Simuliert Trades mit festem Zeitrahmen oder bis Stop/Limit erreicht wird.
        """
        required_columns = {"date", "close"}
        if not required_columns.issubset(df.columns) or not required_columns.issubset(df_eval.columns):
            raise ValueError("DataFrames müssen die Spalten 'date' und 'close' enthalten.")
        if df.empty or df_eval.empty:
            raise ValueError("Input DataFrames dürfen nicht leer sein.")

        df = df.copy()
        df_eval = df_eval.copy()
        df["date"] = pd.to_datetime(df["date"])
        df_eval["date"] = pd.to_datetime(df_eval["date"])

        simulation_result = []
        for i, row in df.iterrows():
            entry_time = row["date"]
            entry_price = row["close"]
            atr = row.get("ATR", None)
            if atr is None:
                continue

            future = df_eval[df_eval["date"] >= entry_time + timedelta(days=1, minutes=5)]
            if future.empty:
                continue

            stop_loss = atr * stop_factor
            take_profit = atr * limit_factor
            exit_time = None
            exit_price = None
            profit = None
            accumulated_time = timedelta(0)

            for j, future_row in future.iterrows():
                current_time = future_row["date"]
                current_price = future_row["close"]
                if j > 0:
                    accumulated_time += timedelta(hours=1)
                if action == "buy":
                    if current_price <= entry_price - stop_loss:
                        exit_time, exit_price, profit = current_time, current_price, -stop_loss
                        break
                    elif current_price >= entry_price + take_profit:
                        exit_time, exit_price, profit = current_time, current_price, take_profit
                        break
                elif action == "sell":
                    if current_price >= entry_price + stop_loss:
                        exit_time, exit_price, profit = current_time, current_price, -stop_loss
                        break
                    elif current_price <= entry_price - take_profit:
                        exit_time, exit_price, profit = current_time, current_price, take_profit
                        break
                else:
                    raise ValueError(f"Unbekannte Aktion: {action}")

            if exit_time is None:
                last_row = future.iloc[-1]
                exit_time = last_row["date"]
                exit_price = last_row["close"]
                profit = (exit_price - entry_price) if action == TradeAction.BUY else (entry_price - exit_price)

            simulation_result.append({
                "action": action,
                "entry_time": entry_time,
                "exit_time": exit_time,
                "entry_price": entry_price,
                "exit_price": exit_price,
                "result": profit,
                "chart_index": i,
                "used_time": accumulated_time.total_seconds() / 60 / 60 / 24
            })

        return pd.DataFrame(simulation_result)
