import os
import numpy as np
from keras import callbacks, optimizers
from keras.layers import (LSTM, BatchNormalization, Dense, Flatten,
                          TimeDistributed)
from keras.layers.convolutional import Conv1D, MaxPooling1D
from keras.models import Sequential, load_model, model_from_json

def get_signals(open_prices,pred):
    insights = []

    for i in range(len(pred)):
        if float(open_prices[i]) > pred[i][0]:
            insights.append('sell')
        elif float(open_prices[i]) < pred[i][0]:
            insights.append('buy')
    return insights


def trading_simulator(open_prices,pred,y):
    profit = 0
    logs = []
    insights = get_signals(open_prices,pred)
    for i in range(len(insights)):
        if insights[i] == 'sell':
            if float(open_prices[i]) > y[i]:
                profit += 8
                logs.append(8)
            else:
                profit -= 10
                logs.append(-10)

        if insights[i] == 'buy':
            if float(open_prices[i]) < y[i]:
                profit += 8
                logs.append(8)
            else:
                profit -= 10
                logs.append(-10)

    return profit, logs

def market_predict(model,n_features,n_steps,data):
    pred_data = data.reshape((len(data),1, n_steps, n_features))
    pred = model.predict(pred_data)
    return pred

def load_keras_model(dataset, optimizer):
    dirx = 'YOUR DIRECTORY HERE'
    os.chdir(dirx)
    json_file = open(dataset + '_best_model' + '.json', 'r')
    loaded_model_json = json_file.read()
    json_file.close()
    model = model_from_json(loaded_model_json)
    model.compile(optimizer=optimizer, loss='mse')
    model.load_weights(dataset + '_best_model' + '.h5')
    return model

def train_model(X_train, y_train, X_test, y_test, symbol, model, epochs, verbosity):
    dirx = '/'
    os.chdir(dirx)
    h5 = symbol + '_best_model' + '.h5'
    checkpoint = callbacks.ModelCheckpoint(h5,
                                           monitor='val_loss',
                                           verbose=0,
                                           save_best_only=True,
                                           save_weights_only=True,
                                           mode='auto',
                                           period=1)
    es = callbacks.EarlyStopping(monitor='val_loss', mode='min', verbose=1, patience=epochs/10)
    callback = [checkpoint,es]
    json = symbol + '_best_model' + '.json'
    model_json = model.to_json()
    with open(json, "w") as json_file:
        json_file.write(model_json)
    history = model.fit(X_train,
                        y_train,
                        epochs=epochs,
                        batch_size=len(X_train) // 4,
                        validation_data = (X_test,y_test),
                        verbose=verbosity,
                        callbacks=callback)
    return history

def split_sequences(sequence, n_steps):
    X, y = list(), list()
    for i in range(len(sequence)):
        # find the end of this pattern
        end_ix = i + n_steps
#         check if we are beyond the sequence
        if end_ix > len(sequence)-1:
            break
        # gather input and output parts of the pattern
        seq_x, seq_y = sequence[i:end_ix], sequence[end_ix]
        X.append(seq_x)
        y.append(seq_y)
    return np.array(X), np.array(y)
def data_setup(n_steps,sequence):
    X, y = split_sequences(sequence, n_steps)
    n_features = X.shape[2]
    X = X.reshape((len(X), 1, n_steps, n_features))
    new_y = []
    for term in y:
        new_term = 2
        new_y.append(new_term)
    return X, np.array(new_y), n_features

def initialize_network(n_steps, n_features, optimizer):
    model = Sequential()
    model.add(TimeDistributed(Conv1D(filters=128, kernel_size=1, activation='relu'), input_shape=(None, n_steps, n_features)))
    model.add(TimeDistributed(MaxPooling1D(pool_size=2, strides=None)))
    model.add(TimeDistributed(Conv1D(filters=128, kernel_size=1, activation='relu')))
    model.add(TimeDistributed(Flatten()))
    model.add(LSTM(128,return_sequences = True))
    model.add(LSTM(64))
    model.add(BatchNormalization())
    model.add(Dense(1))
    model.compile(optimizer=optimizer, loss='mse')
    return model