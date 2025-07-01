from datetime import timedelta, datetime

import pandas as pd
from pandas import DataFrame, Timestamp
from tqdm import tqdm

from BL.datatypes import TradeAction
from BL.indicators import Indicators
from Connectors.dropbox_cache import DropBoxCache


class Simulation:
    def __init__(self, cache:DropBoxCache, analytics):
        self._cache = cache
        self._analytics = analytics

    def simulate(self, df: DataFrame, df_eval: DataFrame,
                 symbol: str, time_frame: int,
                 factor_stop:float, factor_limit:float, force=False):
        buy_path = f"simulation_buy{symbol}_{time_frame}{factor_stop}{factor_limit}h10_v2.csv"
        sell_path = f"simulation_sell{symbol}_{time_frame}{factor_stop}{factor_limit}h10_v2.csv"

        if not self._cache.simulation_exist(buy_path) or force:
            buy = self._simulate_fixed_timeframe(action="buy",
                                                    df=df, df_eval=df_eval, timeframe_hours=time_frame,
                                                   stop_factor=factor_stop, limit_factor=factor_limit)
            if buy is not None and force == False:
                self._cache.save_simulation(buy,buy_path)
        else:
            buy = self._cache.load_simulation(buy_path)

        if not self._cache.simulation_exist(sell_path) or force:
            sell = self._simulate_fixed_timeframe(action="sell",
                                            df=df, df_eval=df_eval,  timeframe_hours=time_frame, stop_factor=factor_stop, limit_factor=factor_limit)
            if sell is not None and force == False:
                self._cache.save_simulation(sell,sell_path)
        else:
            sell = self._cache.load_simulation(sell_path)
        return buy, sell

    def get_signals(self, symbol: str, df: DataFrame, indicators: Indicators, predictor_class, force=False):
        for indicator in indicators.get_all_indicator_names():
            path = f"signal_{symbol}_{indicator}.csv"
            if not self._cache.signal_exist(path):
                predictor = predictor_class(symbol=symbol, indicators=indicators)
                predictor.setup({"_indicator_names": [indicator], "_stop": 50, "_limit": 50})
                trades = predictor.get_signals(df, self._analytics)
                self._cache.save_signal(trades, path)

    def get_signals_by_indicatornames(self, symbol: str, df: DataFrame, features: [], indicators,predictor_class, force=False):
        for indicator in features:
            path = f"signal_{symbol}_{indicator}.csv"
            predictor = predictor_class(symbol=symbol, indicators=indicators)
            predictor.setup({"_indicator_names": [indicator], "_stop": 50, "_limit": 50})
            trades = predictor.get_signals(df, self._analytics)
            self._cache.save_signal(trades, path)

    def create_combined_indicator_data(self, indicators: Indicators, symbol: str) -> DataFrame:
        # Liste für DataFrames mit einem gemeinsamen Index 'chart_index'
        df_list = []

        # Durchlaufe alle Indikatornamen und lade die entsprechenden DataFrames
        for indicator in indicators.get_all_indicator_names():
            try:
                df = self._cache.load_signal(f"signal_{symbol}_{indicator}.csv")

                # Füge eine Spalte für den Indikatornamen hinzu
                df = df.rename(columns={"action": indicator})
                df = df[["chart_index", indicator]]

                # Setze 'chart_index' als Index
                df.set_index("chart_index", inplace=True)

                # Hänge den DataFrame zur Liste hinzu
                df_list.append(df)
            except Exception as e:
                print(f"Error: {e}")

        # Konkateniere alle DataFrames anhand des Index 'chart_index', fülle fehlende Werte mit 'none'
        merged_df = pd.concat(df_list, axis=1, join="outer").fillna("none")

        return merged_df

    def create_combined_indicator_data_by_features (self, features, symbol: str) -> DataFrame:
        # Liste für DataFrames mit einem gemeinsamen Index 'chart_index'
        df_list = []

        # Durchlaufe alle Indikatornamen und lade die entsprechenden DataFrames
        for indicator in features:
            try:
                df = self._cache.load_signal(f"signal_{symbol}_{indicator}.csv")

                # Füge eine Spalte für den Indikatornamen hinzu
                df = df.rename(columns={"action": indicator})
                df = df[["chart_index", indicator]]

                # Setze 'chart_index' als Index
                df.set_index("chart_index", inplace=True)

                # Hänge den DataFrame zur Liste hinzu
                df_list.append(df)
            except Exception as e:
                print(f"Error: {e}")

        # Konkateniere alle DataFrames anhand des Index 'chart_index', fülle fehlende Werte mit 'none'
        merged_df = pd.concat(df_list, axis=1, join="outer").fillna("none")

        return merged_df

    def _simulate_fixed_timeframe(self,
                                 action: str,
                                 df: DataFrame,
                                 df_eval: DataFrame,
                                 stop_factor: float,
                                 limit_factor: float,
                                 timeframe_hours: int = 4) -> DataFrame:
        """
        Simuliert Trades mit einem festen Zeitrahmen oder bis ein Stop/Limit erreicht wird.

        Parameters:
            action (str): "BUY" oder "SELL".
            df (DataFrame): DataFrame mit den Einstiegsdaten (1-Stunden-Raster).
            df_eval (DataFrame): DataFrame mit den zukünftigen Kursdaten (5-Minuten-Raster).
            stop_loss (float): Stop-Loss in Preisabweichung.
            take_profit (float): Take-Profit in Preisabweichung.
            timeframe_hours (int): Zeitrahmen in Stunden, nach dem der Trade geschlossen wird.

        Returns:
            DataFrame: Ergebnisse der Simulation mit den Profiten.
        """
        # Absicherungen
        required_columns = {"date", "close"}
        assert required_columns.issubset(df.columns), "df is missing required columns"
        assert required_columns.issubset(df_eval.columns), "df_eval is missing required columns"

        if len(df) == 0 or len(df_eval) == 0:
            raise ValueError("Input DataFrames must not be empty")

        # Konvertiere Datumsspalten
        df["date"] = pd.to_datetime(df["date"])
        df_eval["date"] = pd.to_datetime(df_eval["date"])

        simulation_result = []

        for i in range(len(df)):
            entry_time = df.date.iloc[i]
            entry_price = df.close.iloc[i]

            # Filter future prices ab der nächsten 5-Minuten-Periode
            future = df_eval[df_eval["date"] >= entry_time + timedelta(days=1, minutes=5)]
            if len(future) == 0:
                continue

            # Initialisiere Variablen für die Iteration
            exit_time = None
            exit_price = None
            profit = None
            accumulated_time = timedelta(0)
            max_timeframe = timedelta(hours=timeframe_hours)

            stop_loss = df.ATR.iloc[i] * stop_factor
            take_profit = df.ATR.iloc[i] * limit_factor

            for j in range(len(future)):
                row = future.iloc[j]
                current_time = row.date
                current_price = row.close

                # Berechne die Zeitdifferenz zur vorherigen Iteration
                if j > 0:
                    time_diff = timedelta(hours=1)
                    accumulated_time += time_diff

                # Prüfe Stop-Loss und Take-Profit
                if action == "buy":
                    if current_price <= entry_price - stop_loss:
                        exit_time = current_time
                        exit_price = current_price
                        profit = -stop_loss
                        break
                    elif current_price >= entry_price + take_profit:
                        exit_time = current_time
                        exit_price = current_price
                        profit = take_profit
                        break
                elif action == "sell":
                    if current_price >= entry_price + stop_loss:
                        exit_time = current_time
                        exit_price = current_price
                        profit = -stop_loss
                        break
                    elif current_price <= entry_price - take_profit:
                        exit_time = current_time
                        exit_price = current_price
                        profit = take_profit
                        break
                else:
                    raise ValueError(f"Unknown action: {action}")

            # Falls kein Exit-Bedingung getroffen wurde, setze Defaults
            if exit_time is None:
                exit_time = future.iloc[-1].date
                exit_price = future.iloc[-1].close
                profit = (exit_price - entry_price) if action == TradeAction.BUY else (entry_price - exit_price)

            # Speichere das Ergebnis
            simulation_result.append({
                "action": action,
                "entry_time": entry_time,
                "exit_time": exit_time,
                "entry_price": entry_price,
                "exit_price": exit_price,
                "result": profit,
                "chart_index": i,
                "used_time":accumulated_time.total_seconds() / 60 / 60 / 24
            })

        return pd.DataFrame(simulation_result)

    def evaluate_fixed_timeframe(self,
                                 predictor,
                                 df: DataFrame,
                                 df_eval: DataFrame,
                                 stop_loss_factor: float = 1.5,
                                 take_profit_factor: float = 1.5,
                                 timeframe_hours: int = 4) -> DataFrame:
        """
        Simuliert Trades mit einem festen Zeitrahmen oder bis ein Stop/Limit erreicht wird.

        Parameters:
            action (str): "BUY" oder "SELL".
            df (DataFrame): DataFrame mit den Einstiegsdaten (1-Stunden-Raster).
            df_eval (DataFrame): DataFrame mit den zukünftigen Kursdaten (5-Minuten-Raster).
            stop_loss (float): Stop-Loss in Preisabweichung.
            take_profit (float): Take-Profit in Preisabweichung.
            timeframe_hours (int): Zeitrahmen in Stunden, nach dem der Trade geschlossen wird.

        Returns:
            DataFrame: Ergebnisse der Simulation mit den Profiten.
        """
        # Absicherungen
        required_columns = {"date", "close"}
        assert required_columns.issubset(df.columns), "df is missing required columns"
        assert required_columns.issubset(df_eval.columns), "df_eval is missing required columns"

        if len(df) == 0 or len(df_eval) == 0:
            raise ValueError("Input DataFrames must not be empty")

        # Konvertiere Datumsspalten
        df["date"] = pd.to_datetime(df["date"])
        df_eval["date"] = pd.to_datetime(df_eval["date"])

        simulation_result = []

        for i in range(len(df)):
            entry_time = df.date.iloc[i]
            ts = Timestamp(year=2025, month=3, day=3, hour=15, minute=0)
            entry_price = df.close.iloc[i]

            # Filter future prices ab der nächsten 5-Minuten-Periode
            future = df_eval[df_eval["date"] >= entry_time + timedelta(hours=1, minutes=5)]
            if len(future) == 0:
                continue

            # Initialisiere Variablen für die Iteration
            exit_time = None
            exit_price = None
            profit = None
            accumulated_time = timedelta(0)
            max_timeframe = timedelta(hours=timeframe_hours)

            stop_loss = df.ATR.iloc[i] * stop_loss_factor
            take_profit = df.ATR.iloc[i] * take_profit_factor

            actions = {}

            for indicator_name in predictor._features:
                action = Indicators().predict_single(df[:i+1], indicator_name)
                actions[indicator_name] = action
            actions_df = DataFrame([actions])

            buy_actions_df = actions_df.replace({'none': 0, 'both': 1, 'buy': 1, 'sell': 0}).infer_objects(copy=False).astype(int)
            sell_actions_df = actions_df.replace({'none': 0, 'both': 1, 'buy': 0, 'sell': 1}).infer_objects(copy=False).astype(int)

            action = predictor.predict(buy_actions_df,sell_actions_df)
            for j in range(len(future)):
                row = future.iloc[j]
                current_time = row.date
                current_price = row.close

                # Berechne die Zeitdifferenz zur vorherigen Iteration
                if j > 0:
                    time_diff = timedelta(minutes=5)
                    accumulated_time += time_diff

                # Prüfe Stop-Loss und Take-Profit
                if action == "buy":
                    if current_price <= entry_price - stop_loss:
                        exit_time = current_time
                        exit_price = current_price
                        profit = -stop_loss
                        break
                    elif current_price >= entry_price + take_profit:
                        exit_time = current_time
                        exit_price = current_price
                        profit = take_profit
                        break
                elif action == "sell":
                    if current_price >= entry_price + stop_loss:
                        exit_time = current_time
                        exit_price = current_price
                        profit = -stop_loss
                        break
                    elif current_price <= entry_price - take_profit:
                        exit_time = current_time
                        exit_price = current_price
                        profit = take_profit
                        break

            # Falls kein Exit-Bedingung getroffen wurde, setze Defaults
            if exit_time is None:
                exit_time = future.iloc[-1].date
                exit_price = future.iloc[-1].close
                profit = (exit_price - entry_price) if action == "BUY" else (entry_price - exit_price)

            # Speichere das Ergebnis
            simulation_result.append({
                "action": action,
                "entry_time": entry_time,
                "exit_time": exit_time,
                "entry_price": entry_price,
                "exit_price": exit_price,
                "result": profit,
                "chart_index": i,
            })

        return pd.DataFrame(simulation_result)
