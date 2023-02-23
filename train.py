import numpy as np
import pandas as pd

import os
import matplotlib.pyplot as plt
import datetime as dt

from sklearn.preprocessing import MinMaxScaler
from Connectors.tiingo import Tiingo
from Data.data_processor import DataProcessor
from keras.models import Sequential
from keras.layers import Dense, Dropout, LSTM
from keras.callbacks import ModelCheckpoint, EarlyStopping

train_data = Tiingo().load_data_by_date("GBPUSD", "2022-08-15", "2022-12-31",DataProcessor() , "1hour")

scaler = MinMaxScaler(feature_range=(0,1))
scaled_data = scaler.fit_transform(train_data['close'].values.reshape(-1,1))

# how many days do i want to base my predictions on ?
prediction_days = 60

x_train = []
y_train = []

for x in range(prediction_days, len(scaled_data)):
    x_train.append(scaled_data[x - prediction_days:x, 0])
    y_train.append(scaled_data[x, 0])

x_train, y_train = np.array(x_train), np.array(y_train)
x_train = np.reshape(x_train, (x_train.shape[0], x_train.shape[1], 1))


def LSTM_model():
    model = Sequential()

    model.add(LSTM(units=50, return_sequences=True, input_shape=(x_train.shape[1], 1)))
    model.add(Dropout(0.2))

    model.add(LSTM(units=50, return_sequences=True))
    model.add(Dropout(0.2))

    model.add(LSTM(units=50))
    model.add(Dropout(0.2))

    model.add(Dense(units=1))

    return model

model = LSTM_model()
model.summary()
model.compile(optimizer='adam',
              loss='mean_squared_error')

checkpointer = ModelCheckpoint(filepath = 'weights_best.hdf5',
                               verbose = 2,
                               save_best_only = True)

model.fit(x_train,
          y_train,
          epochs=5,
          batch_size = 32,
          callbacks = [checkpointer])

# test model accuracy on existing data
test_data  = Tiingo().load_data_by_date("GBPUSD", "2023-01-01", "2023-01-15",DataProcessor() , "1hour")
test_data = test_data["close"]

for i in range(30,1,-1):
    model_inputs = test_data[-1 * (prediction_days+i):-1 * i].values
    model_inputs = model_inputs.reshape(-1,1)
    model_inputs = scaler.transform(model_inputs)

    correct_val = test_data[-1 * i:-1 * (i-1)]

    # predicting next day
    real_data = [model_inputs[len(model_inputs) - prediction_days:len(model_inputs+1),0]]
    real_data = np.array(real_data)
    real_data = np.reshape(real_data, (real_data.shape[0], real_data.shape[1], 1))

    prediction = model.predict(real_data)
    prediction = scaler.inverse_transform(prediction)
    print(f"prediction: {prediction}")

