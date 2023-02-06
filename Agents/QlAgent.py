import keras
from keras.models import Sequential
from keras.models import load_model
from keras.layers import Dense,InputLayer
from keras.optimizers import Adam
import numpy as np
import random
from collections import deque
import tensorflow as tf


class QlAgent:
	def __init__(self, shape, is_eval=False,model_path:str="", gamma:float=0.95,lr:float=0.001,hiddens=[32,16,8],beta1:float=0.9,beta2:float=0.99,epsilon:float=None,decay:float=0. ):
		self.shape = shape #TODO:
		self.action_size = 2 # sit, buy, sell
		self.memory = deque(maxlen=1000)
		self.inventory = []
		self.is_eval = is_eval

		self.gamma = gamma
		self.epsilon = 1.0
		self.epsilon_min = 0.01
		self.epsilon_decay = 0.995
		self.lr = lr
		self.hiddens = hiddens
		self.opt_beta_1 = beta1
		self.opt_beta_2 = beta2
		self.opt_epsilon = epsilon
		self.opt_decay = decay

		self.model = load_model(model_path) if is_eval else self._model()
		tf.logging.set_verbosity(tf.logging.ERROR)


	def _model(self):
		model = Sequential()
		model.add(InputLayer(input_shape=(11,)))
		model.add(Dense(units=self.hiddens[0], activation="relu"))
		model.add(Dense(units=self.hiddens[1], activation="relu"))
		model.add(Dense(units=self.hiddens[2], activation="relu"))
		model.add(Dense(self.action_size, activation="linear"))
		model.compile(loss="mse", optimizer=Adam(lr=self.lr,beta_1=self.opt_beta_1,beta_2=self.opt_beta_2,epsilon=self.opt_epsilon,decay=self.opt_decay))

		return model

	def act(self, state):
		if not self.is_eval and random.random() <= self.epsilon:
			return random.randrange(self.action_size)

		options = self.model.predict(state) #Array von allen möglichen Aktionen
		return np.argmax(options[0]) #argmax sucht nach dem Index mit dem höchsten wert

	def expReplay(self, batch_size):
		mini_batch = []
		l = len(self.memory)
		for i in range(l - batch_size + 1, l):
			mini_batch.append(self.memory[i])

		mini_batch = random.choices(mini_batch,k=len(mini_batch))

		for state, action, reward, next_state, done in mini_batch:
			target = reward
			if not done:
				target = reward + self.gamma * np.amax(self.model.predict(next_state)[0])

			target_f = self.model.predict(state)
			target_f[0][action] = target
			self.model.fit(state, target_f, epochs=1, verbose=0)

		if self.epsilon > self.epsilon_min:
			self.epsilon *= self.epsilon_decay