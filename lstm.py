from lstm_bl import *
from Data.data_processor import DataProcessor
from Connectors.tiingo import Tiingo
from matplotlib import pyplot as plt

dataProcessor = DataProcessor()
symbol = "GBPUSD"
resolution = "1hour"
key = "7961E58Q0BJGJWWR"

ti = Tiingo()
df = ti.load_data_by_date(symbol, "2022-12-15", "2023-01-20", dataProcessor,resolution)

name = "Foo"
fx_data = df.drop(columns=["date"]).to_numpy().tolist()
lenXtest = int(len(fx_data) * 0.1)
fx_data.reverse()
preX_test = fx_data[len(fx_data)-lenXtest:]
preX_train = fx_data[0:len(fx_data)-lenXtest]


n_steps = 8
X,y,n_features = data_setup(n_steps,fx_data)
X_train, y_train, n_features = data_setup(n_steps,preX_train)
X_test, y_test, n_features = data_setup(n_steps,preX_test)
y = y.astype('float32')

model = initialize_network(n_steps, n_features, 'Nadam')
history = train_model(X_train, y_train, X_test, y_test, name, model, 5000, 0)
loss = model.evaluate(X_test, y_test)
pred = market_predict(model,n_features,n_steps,X_test)

open_prices = []
for term in preX_test:
    open_prices.append(term[0])

signals = get_signals(open_prices,pred)

plt.figure(figsize=(15, 6))
plt.cla()
plt.plot(open_prices)
buy_ticks = []
sell_ticks = []
sell_price = []
buy_price = []

for i in range(len(signals)):  # Todo: GetIndexes from Value
    if signals[i] == "buy":
        buy_ticks.append(i)
        buy_price.append(open_prices[i])
    else:
        sell_ticks.append(i)
        sell_price.append(open_prices[i])

# Markers: https://matplotlib.org/stable/gallery/lines_bars_and_markers/marker_reference.html#sphx-glr-gallery-lines-bars-and-markers-marker-reference-py
plt.plot(sell_ticks, sell_price, 'ro')
plt.plot(buy_ticks, buy_price, 'go')
plt.show(block=True)








