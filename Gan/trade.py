from Connectors.tiingo import Tiingo
from Data.data_processor import DataProcessor
from Gan.bl import *
from pickle import load
import tensorflow as tf
from datetime import date, timedelta
from Connectors.IG import IG
import time


ig = IG()
time.sleep(60 * 6)
while True:
    #load
    #####################################
    df = Tiingo().load_data_by_date("GBPUSD",(date.today() - timedelta(days=20)).strftime("%Y-%m-%d"),
                                              None, DataProcessor(),"1hour",False,False)
    T_df = get_technical_indicators(df)
    # Drop the first 21 rows
    # For doing the fourier
    pre_dataset = T_df.iloc[20:, :].reset_index(drop=True)
    # Get Fourier features
    dataset_F = get_fourier_transfer(pre_dataset)
    Final_data = pd.concat([pre_dataset, dataset_F], axis=1)

    #Preprocess


    # Replace 0 by NA
    Final_data.replace(0, np.nan, inplace=True)
    Final_data.to_csv("dataset.csv", index=False)


    # Check NA and fill them
    Final_data.isnull().sum()
    Final_data.iloc[:, 1:] = pd.concat([Final_data.iloc[:, 1:].ffill(), Final_data.iloc[:, 1:].bfill()]).groupby(level=0).mean()


    # Set the date to datetime data
    datetime_series = pd.to_datetime(Final_data['date'])
    datetime_index = pd.DatetimeIndex(datetime_series.values)
    dataset = Final_data.set_index(datetime_index)
    dataset = dataset.sort_values(by='date')
    dataset = dataset.drop(columns='date')

    # Get features and target
    X_value = pd.DataFrame(dataset.iloc[:, :])



    # Normalized the data
    X_scaler = load(open('X_scaler.pkl', 'rb'))
    X_scaler.fit(X_value)

    X_scale_dataset = X_scaler.fit_transform(X_value)

    # Reshape the data
    '''Set the data input steps and output steps, 
        we use 30 days data to predict 1 day price here, 
        reshape it to (None, input_step, number of features) used for LSTM input'''
    n_steps_in = 3
    n_features = X_value.shape[1]
    n_steps_out = 1


    # Get data and check shape
    X_now = get_X_now(X_scale_dataset,n_steps_in)
    X_yesterday = get_X_yesterday(X_scale_dataset,n_steps_in)

    G_model = tf.keras.models.load_model('gen_GRU_model_89.h5')
    pred_now = G_model(X_now)
    pred_yesterday = G_model(X_yesterday)
    print(pred_now)
    print(pred_yesterday)

    if ig.has_opened_positions():
        time.sleep(60 * 60)
        break

    if ig.get_spread("CS.D.GBPUSD.CFD.IP") > 6:
        time.sleep(60 * 60)
        break

    if pred_now > pred_yesterday:
        print("Buy")
        ig.buy("CS.D.GBPUSD.CFD.IP")
    else:
        print("Sell")
        ig.sell("CS.D.GBPUSD.CFD.IP")

    time.sleep(60 * 60)
