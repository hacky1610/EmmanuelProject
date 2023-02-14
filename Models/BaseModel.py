from keras.models import Sequential


class BaseModel:
    _model: Sequential

    def __init__(self, config:dict):
        self._window_size = config.get("window_size",16)
        self._num_features = config.get("num_features",12)

    def save(self,path):
        self._model.save(path)

    def load(self,path):
        self._model.load_weights(path)

    def compile(self,optimizer):
        self._model.compile(optimizer=optimizer, loss="mean_squared_error")

    def fit(self,x_train, y_train,batch_size:int,epochs:int):
        return self._model.fit(x_train, y_train, batch_size=batch_size, epochs=epochs)

    def predict(self, data):
        return self._model.predict(data)


