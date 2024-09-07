import numpy as np
from pandas import DataFrame
from finta import TA


class DataProcessor:

    @staticmethod
    def addSignals(df: DataFrame):
        df['SMA_10'] = TA.SMA(df, 10)
        df['SMA_10_LOW'] = TA.SMA(df, 10, column="low")
        df['SMA_10_HIGH'] = TA.SMA(df, 10, column="high")
        df['EMA'] = TA.EMA(df)
        df['EMA_5'] = TA.EMA(df, 5)
        df['EMA_8'] = TA.EMA(df, 8)
        df['EMA_10'] = TA.EMA(df, 10)
        df['EMA_13'] = TA.EMA(df, 13)
        df['EMA_14'] = TA.EMA(df, 14)
        df['EMA_20'] = TA.EMA(df, 20)
        df['EMA_20_HIGH'] = TA.EMA(df, 20,"high")
        df['EMA_20_LOW'] = TA.EMA(df, 20, "low")
        df['EMA_30'] = TA.EMA(df, 30)
        df['EMA_50'] = TA.EMA(df, 50)
        #df['EMA_200'] = TA.EMA(df, 200)

        df['SMMA_20'] = TA.SMMA(df, 20)

        bb = TA.BBANDS(df)
        df['BB_UPPER'] = bb['BB_UPPER']
        df['BB_MIDDLE'] = bb['BB_MIDDLE']
        df['BB_LOWER'] = bb['BB_LOWER']
        bb1 = TA.BBANDS(df, std_multiplier=1)
        df['BB1_UPPER'] = bb1['BB_UPPER']
        df['BB1_MIDDLE'] = bb1['BB_MIDDLE']
        df['BB1_LOWER'] = bb1['BB_LOWER']

        df['RSI'] = TA.RSI(df, period=14)
        df['RSI_SMOOTH'] = TA.SMA(df, column="RSI")
        df['RSI_7'] = TA.RSI(df, period=7)
        df['RSI_21'] = TA.RSI(df, period=21)
        df['ROC'] = TA.ROC(df, period=10)
        df['WILLIAMS'] = TA.WILLIAMS(df, period=14)
        md = TA.MACD(df)
        df['MACD'] = md['MACD']
        df['SIGNAL'] = md['SIGNAL']
        df["CCI"] = TA.CCI(df)
        df["CCI_7"] = TA.CCI(df, 7)

        df["STOCHK"] = TA.STOCH(df)
        df["STOCHD"] = TA.STOCHD(df, stoch_period=5)
        df["STOCHD_21"] = TA.STOCH(df, period=21)
        df["STOCHD_30"] = TA.STOCH(df, period=21)
        df["ADX"] = TA.ADX(df, period=9)
        df["ADX_21"] = TA.ADX(df, period=21)
        df["ADX_48"] = TA.ADX(df, period=48)
        psar = TA.PSAR(df)
        df["PSAR"] = psar["psar"]


        df["ATR"] = TA.ATR(df)

        ichi = TA.ICHIMOKU(df)
        df["TENKAN"] = ichi["TENKAN"]
        df["KIJUN"] = ichi["KIJUN"]
        df["SENKOU_A"] = ichi["senkou_span_a"]
        df["SENKOU_B"] = ichi["SENKOU"]

        df["TII"] = DataProcessor._tii(df,10)

        pivot  = TA.PIVOT(df)
        df["PIVOT"] = pivot["pivot"]
        df["S1"] = pivot["s1"]
        df["S2"] = pivot["s2"]
        df["R1"] = pivot["r1"]
        df["R2"] = pivot["r2"]

        pivot = TA.PIVOT_FIB(df)
        df["PIVOT_FIB"] = pivot["pivot"]
        df["S1_FIB"] = pivot["s1"]
        df["S2_FIB"] = pivot["s2"]
        df["R1_FIB"] = pivot["r1"]
        df["R2_FIB"] = pivot["r2"]

        #Keltner
        lengthKC = 20
        kc = TA.KC(df, period=lengthKC, kc_mult=1.5)
        df['KC_UPPER'] = kc['KC_UPPER']
        df['KC_LOWER'] = kc['KC_LOWER']

        # Squeeze
        df['Squeeze_On'] = (df['BB_LOWER'] > df['KC_LOWER']) & (df['BB_UPPER'] < df['KC_UPPER'])
        df['Squeeze_Off'] = (df['BB_LOWER'] < df['KC_LOWER']) & (df['BB_UPPER'] > df['KC_UPPER'])
        df['No_Squeeze'] = (~df['Squeeze_Off']) & (~df['Squeeze_On'])

        # Momentum-Berechnung
        avg_price = (df['high'].rolling(window=lengthKC).max() + df['low'].rolling(window=lengthKC).min()) / 2
        linreg = df['close'] - avg_price.rolling(window=lengthKC).mean()
        df['Squeeze_Val'] = linreg.rolling(window=lengthKC).apply(lambda x: np.polyfit(range(len(x)), x, 1)[0], raw=True)

        DataProcessor.prepare_supertrend(df)

        return

    @staticmethod
    def addSignals_big_tf(df: DataFrame):

        df['RSI'] = TA.RSI(df)
        ichi = TA.ICHIMOKU(df)
        df["KIJUN"] = ichi["KIJUN"]
        md = TA.MACD(df)
        df['MACD'] = md['MACD']
        df['CCI'] = TA.CCI(df)
        df["ADX"] = TA.ADX(df, period=9)
        bb1 = TA.BBANDS(df)
        df['BB_UPPER'] = bb1['BB_UPPER']
        df['BB_MIDDLE'] = bb1['BB_MIDDLE']
        df['BB_LOWER'] = bb1['BB_LOWER']
        df['WILLIAMS'] = TA.WILLIAMS(df, period=14)
        pivot = TA.PIVOT(df)
        df["PIVOT"] = pivot["pivot"]
        df["S1"] = pivot["s1"]
        df["S2"] = pivot["s2"]
        df["R1"] = pivot["r1"]
        df["R2"] = pivot["r2"]

        pivot = TA.PIVOT_FIB(df)
        df["PIVOT_FIB"] = pivot["pivot"]
        df["S1_FIB"] = pivot["s1"]
        df["S2_FIB"] = pivot["s2"]
        df["R1_FIB"] = pivot["r1"]
        df["R2_FIB"] = pivot["r2"]
        return

    @staticmethod
    def prepare_supertrend(df, multiplier=3.0):
        """
        Prepares the DataFrame by adding the necessary columns for Supertrend calculation.

        Parameters:
        df (pd.DataFrame): DataFrame containing OHLC data and an 'ATR' column.
        multiplier (float): The ATR multiplier used to calculate the Supertrend levels.

        Returns:
        pd.DataFrame: The DataFrame with additional columns ('hl2', 'upperband', 'lowerband', 'trend').
        """
        # Ensure DataFrame has the necessary columns
        if not all(col in df.columns for col in ['high', 'low', 'close', 'ATR']):
            raise ValueError("DataFrame must contain 'high', 'low', 'close', and 'ATR' columns")

        # Calculate HL2 (average of high and low)
        df['hl2'] = (df['high'] + df['low']) / 2

        # Calculate the Supertrend levels
        df['upperband'] = df['hl2'] - (multiplier * df['ATR'])
        df['lowerband'] = df['hl2'] + (multiplier * df['ATR'])

        # Initialize the trend column
        df['trend'] = 0

        # Determine the trend direction based on previous close and upper/lower bands
        for i in range(1, len(df)):
            if df['close'].iloc[i - 1] > df['upperband'].iloc[i - 1]:
                df['trend'].iloc[i] = 1  # Uptrend
            elif df['close'].iloc[i - 1] < df['lowerband'].iloc[i - 1]:
                df['trend'].iloc[i] = -1  # Downtrend
            else:
                df['trend'].iloc[i] = df['trend'].iloc[i - 1]  # No change

            # Adjust the upper and lower bands based on the trend
            if df['trend'].iloc[i] == 1 and df['upperband'].iloc[i] < df['upperband'].iloc[i - 1]:
                df['upperband'].iloc[i] = df['upperband'].iloc[i - 1]
            if df['trend'].iloc[i] == -1 and df['lowerband'].iloc[i] > df['lowerband'].iloc[i - 1]:
                df['lowerband'].iloc[i] = df['lowerband'].iloc[i - 1]



    @staticmethod
    def clean_data(df: DataFrame):
        DataProcessor.drop_column(df, "Volume")
        DataProcessor.drop_column(df, "Dividends")
        DataProcessor.drop_column(df, "Stock Splits")
        df.dropna(inplace=True)
        df.reset_index(inplace=True)
        df.drop(columns=["index"], inplace=True)
        df.reset_index(inplace=True)

    @staticmethod
    def drop_column(df: DataFrame, name: str):
        if name in df.columns:
            df.drop(columns=[name], inplace=True)

    @staticmethod
    def _tii(df, P):
        # Define the parameters
        n = 60  # Period for SMA
        m = n // 2  # Period for sum of deviations (half of SMA period)
        k = 10  # Period for EMA of TII

        # Calculate SMA of the closing prices
        df['SMA'] = df['close'].rolling(n).mean()

        # Calculate Positive and Negative deviations
        df['Dev'] = df['close'] - df['SMA']
        df['posDev'] = df['Dev'].apply(lambda x: x if x > 0 else 0)
        df['negDev'] = df['Dev'].apply(lambda x: abs(x) if x < 0 else 0)

        # Calculate sum of Positive and Negative deviations for the shorter period
        df['SDpos'] = df['posDev'].rolling(m).sum()
        df['SDneg'] = df['negDev'].rolling(m).sum()

        # Calculate Trend Intensity Index (TII)
        df['TII'] = 100 * df['SDpos'] / (df['SDpos'] + df['SDneg'])
        return df["TII"]

