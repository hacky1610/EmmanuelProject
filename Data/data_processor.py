from pandas import DataFrame
from finta import TA
import numpy as np
import  pandas as pd

class DataProcessor:

    def addSignals(self, df: DataFrame):
        df['SMA7'] = TA.SMA(df, 5)
        df['EMA'] = TA.EMA(df)
        bb= TA.BBANDS(df)
        df['BB_UPPER'] = bb['BB_UPPER']
        df['BB_MIDDLE'] = bb['BB_MIDDLE']
        df['BB_LOWER'] = bb['BB_LOWER']
        df['ROC'] = TA.ROC(df, period=5)
        df['%R'] = TA.WILLIAMS(df, period=5)
        md = TA.MACD(df)
        df['MACD'] = md['MACD']
        df['SIGNAL'] = md['SIGNAL']

    def clean_data(self, df: DataFrame):
        DataProcessor.drop_column(df, "Volume")
        DataProcessor.drop_column(df, "Dividends")
        DataProcessor.drop_column(df, "Stock Splits")
        df.dropna(0, inplace=True)

    @staticmethod
    def drop_column(df: DataFrame, name: str):
        if name in df.columns:
            df.drop(columns=[name], inplace=True)


class DataProcessorGan:

    def addSignals(self, data: DataFrame):
        # Create 7 and 21 days Moving Average
        data['MA7'] = data.close[:].rolling(window=7).mean()
        data['MA21'] = data.close[:].rolling(window=21).mean()

        # Create MACD
        data['MACD'] = data.close[:].ewm(span=26).mean() - data.open[:].ewm(span=12, adjust=False).mean()

        # Create Bollinger Bands
        data['20SD'] = data.close[:].rolling(20).std()
        data['upper_band'] = data['MA21'] + (data['20SD'] * 2)
        data['lower_band'] = data['MA21'] - (data['20SD'] * 2)

        # Create Exponential moving average
        data['EMA'] = data.close[:].ewm(com=0.5).mean()

        # Create LogMomentum
        data['logmomentum'] = np.log(data.close[:] - 1)

        dataset = data.iloc[20:, :].reset_index(drop=True)
        # Get Fourier features
        dataset_F = get_fourier_transfer(dataset)
        Final_data = pd.concat([dataset, dataset_F], axis=1)

        # Check NA and fill them
        Final_data.iloc[:, 1:] = pd.concat([dataset.iloc[:, 1:].ffill(), Final_data.iloc[:, 1:].bfill()]).groupby(
            level=0).mean()

        # Set the date to datetime data
        datetime_series = pd.to_datetime(Final_data['date'])
        datetime_index = pd.DatetimeIndex(datetime_series.values)
        Final_data = Final_data.set_index(datetime_index)
        Final_data = Final_data.sort_values(by='date')
        Final_data = Final_data.drop(columns='date')

        return Final_data

    def clean_data(self, dataset: DataFrame):
        dataset.replace(0, np.nan)
        return dataset

    @staticmethod
    def drop_column(df: DataFrame, name: str):
        if name in df.columns:
            df.drop(columns=[name], inplace=True)

def get_fourier_transfer(dataset):
    # Get the columns for doing fourier
    data_FT = dataset[['date', 'close']]

    close_fft = np.fft.fft(np.asarray(data_FT['close'].tolist()))
    fft_df = pd.DataFrame({'fft': close_fft})
    fft_df['absolute'] = fft_df['fft'].apply(lambda x: np.abs(x))
    fft_df['angle'] = fft_df['fft'].apply(lambda x: np.angle(x))

    fft_list = np.asarray(fft_df['fft'].tolist())
    fft_com_df = pd.DataFrame()
    for num_ in [3, 6, 9]:
        fft_list_m10 = np.copy(fft_list);
        fft_list_m10[num_:-num_] = 0
        fft_ = np.fft.ifft(fft_list_m10)
        fft_com = pd.DataFrame({'fft': fft_})
        fft_com['absolute of ' + str(num_) + ' comp'] = fft_com['fft'].apply(lambda x: np.abs(x))
        fft_com['angle of ' + str(num_) + ' comp'] = fft_com['fft'].apply(lambda x: np.angle(x))
        fft_com = fft_com.drop(columns='fft')
        fft_com_df = pd.concat([fft_com_df, fft_com], axis=1)

    return fft_com_df