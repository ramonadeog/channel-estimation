import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2' 

from tensorflow import keras
from sklearn.model_selection import train_test_split
import matplotlib.pyplot as plt
import numpy as np
from resnet import ResnetBlock
import pickle
from tensorflow.keras.models import load_model

import cbn_recv_datagen as dg

# N: receiver antennas
# K: users
# L: bits
# freq: frequency
# snr between 5 and 30
def train_model(N, K, L, freq = 2.4e9, snr = [5, 30], resolution = 180, training_size = 500000, validation_size = 0.1, learning_rate = 0.001):
    training_labels, training_data, validation_labels, validation_data = dg.data_initialization(training_size, N, K, L, freq, resolution, snr, cache=False)    
    print(len(training_data))
    training_size = int(len(training_data)/L)
    
    training_data = dg.apply_wgn(training_data, L, snr)
    training_data = training_data.reshape((training_size, N*L))
    training_data = np.concatenate((training_data.real,training_data.imag), axis=1)
    training_data = training_data / np.max(np.abs(training_data), axis=1).reshape((training_size,1))
    """
    validation_size = int(len(validation_data)/L)
    
    validation_data = dg.apply_wgn(validation_data, L, snr)
    validation_data = training_data.reshape((validation_size, N*L))
    validation_data = np.concatenate((validation_data.real,validation_data.imag), axis=1)
    validation_data = validation_data / np.max(np.abs(validation_data), axis=1).reshape((validation_size,1))
    """
    
    ae = load_model(f"models/AE_N={N}_K={K}_L={L}")
    
    encoded = ae.get_layer('sequential_14')
                
    # define model
    model = keras.Sequential([
            encoded,
            keras.layers.Dense(128, activation='relu'),
            keras.layers.Dense(128, activation='relu'),
            keras.layers.Dense(resolution, activation='sigmoid')
            ])
    
    adaptive_learning_rate = lambda epoch: learning_rate/(2**np.floor(epoch/10))
    
    adam = keras.optimizers.Adam(learning_rate=learning_rate, beta_1=0.9, beta_2=0.999)
    
    stopping = keras.callbacks.EarlyStopping(monitor='val_loss', patience=5, min_delta=1e-5)
    lrate = keras.callbacks.LearningRateScheduler(adaptive_learning_rate)

    model.compile(optimizer=adam,
                  loss='binary_crossentropy')
    
    m = model.fit(training_data, training_labels, batch_size=32, epochs=300, validation_data=(validation_data, validation_labels), callbacks=[stopping, lrate])

    with open(f"history/CBN_ae_N={N}_K={K}_L={L}", 'wb') as f:
        pickle.dump(m.history, f)

    model.save(f"models/CBN_recv_N={N}_K={K}_L={L}")

    return model