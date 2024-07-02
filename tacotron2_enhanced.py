# -*- coding: utf-8 -*-
"""Tacotron2_enhanced.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/125d3Df944x2o3xEkEB7hyBKCZyjv3bWJ
"""

import tensorflow as tf
from tensorflow.keras.layers import Input, Embedding, Dense, LSTM, Dropout, TimeDistributed, Conv1D, BatchNormalization
from tensorflow.keras.models import Model
import numpy as np
import librosa
import soundfile as sf
import matplotlib.pyplot as plt
from tensorflow.keras.preprocessing.text import Tokenizer

import tensorflow as tf
from tensorflow.keras.layers import Embedding, LSTM, TimeDistributed, Dense, Conv1D, BatchNormalization, Dropout
from tensorflow.keras import Model

class PreNet(tf.keras.layers.Layer):
    def __init__(self, units, dropout_rate):
        super(PreNet, self).__init__()
        self.dense1 = Dense(units, activation='relu')
        self.dense2 = Dense(units, activation='relu')
        self.dropout = Dropout(dropout_rate)

    def call(self, inputs, training=False):
        x = self.dense1(inputs)
        x = self.dropout(x, training=training)
        x = self.dense2(inputs)
        x = self.dropout(x, training=training)
        return x

class PostNet(tf.keras.layers.Layer):
    def __init__(self, num_filters, kernel_size):
        super(PostNet, self).__init__()
        self.conv1 = Conv1D(num_filters, kernel_size, padding='same', activation='relu')
        self.bn1 = BatchNormalization()
        self.conv2 = Conv1D(num_filters, kernel_size, padding='same', activation='relu')
        self.bn2 = BatchNormalization()
        self.conv3 = Conv1D(num_filters, kernel_size, padding='same', activation='relu')
        self.bn3 = BatchNormalization()
        self.conv4 = Conv1D(num_filters, kernel_size, padding='same', activation='relu')
        self.bn4 = BatchNormalization()
        self.conv5 = Conv1D(num_filters, kernel_size, padding='same', activation='relu')
        self.bn5 = BatchNormalization()
        self.conv6 = Conv1D(1, kernel_size, padding='same')

    def call(self, inputs, training=False):
        x = self.conv1(inputs)
        x = self.bn1(x, training=training)
        x = self.conv2(x)
        x = self.bn2(x, training=training)
        x = self.conv3(x)
        x = self.bn3(x, training=training)
        x = self.conv4(x)
        x = self.bn4(x, training=training)
        x = self.conv5(x)
        x = self.bn5(x, training=training)
        x = self.conv6(x)
        return x

class Tacotron2(Model):
    def __init__(self, vocab_size, embedding_dim, encoder_dim, decoder_dim, mel_dim, prenet_units, prenet_dropout, postnet_filters, postnet_kernel_size):
        super(Tacotron2, self).__init__()
        self.embedding = Embedding(vocab_size, embedding_dim, mask_zero=True)
        self.encoder_lstm = LSTM(encoder_dim, return_sequences=True, return_state=True)
        self.prenet = PreNet(prenet_units, prenet_dropout)
        self.decoder_lstm = LSTM(decoder_dim, return_sequences=True, return_state=True)
        self.dense = TimeDistributed(Dense(mel_dim))
        self.postnet = PostNet(postnet_filters, postnet_kernel_size)

    def call(self, inputs, training=False):
        sequences, decoder_input = inputs
        embedded_sequences = self.embedding(sequences)
        encoder_outputs, state_h, state_c = self.encoder_lstm(embedded_sequences)
        prenet_outputs = self.prenet(encoder_outputs, training=training)
        decoder_outputs, _, _ = self.decoder_lstm(decoder_input, initial_state=[state_h, state_c])
        mel_outputs = self.dense(decoder_outputs)
        postnet_outputs = self.postnet(mel_outputs, training=training)
        return mel_outputs, postnet_outputs







import os
def load_ljs(data_path):
    metadata_file = os.path.join(data_path, 'list.txt')
    with open(metadata_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    metadata = []
    for line in lines:
        parts = line.strip().split('|')
        if len(parts) == 2:
            metadata.append(parts)
        else:
            print("Skipping line due to some error")
    return metadata

def normalize_text(text):
    text = text.lower()
    text = text.replace('.', ' ')
    return text

def text_to_sequences(texts, tokenizer):
    sequences = tokenizer.texts_to_sequences(texts)
    return sequences

def audio_to_mel(audio_path):
    y, sr = librosa.load(audio_path, sr=22050)
    mel = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=80)
    mel_db = librosa.power_to_db(mel, ref=np.max)
    return mel_db

def preprocess_dataset(data_path, tokenizer):
    metadata = load_ljs(data_path)
    texts = [normalize_text(m[1]) for m in metadata]
    audio_paths = [os.path.join(data_path, m[0]) for m in metadata]
    sequences = text_to_sequences(texts, tokenizer)
    mels = [audio_to_mel(audio_path) for audio_path in audio_paths]
    return sequences, mels

data_path = '/content/drive/MyDrive/tts_COPY_data/wavs'
tokenizer = Tokenizer(char_level=True)
texts = [normalize_text(m[1]) for m in load_ljs(data_path)]
tokenizer.fit_on_texts(texts)
sequences, mels = preprocess_dataset(data_path, tokenizer)

def normalize_mel(mel):
    mean = np.mean(mel, axis=0)
    std = np.std(mel, axis=0)
    return (mel - mean) / std

def data_generator(sequences, mels, batch_size, mel_dim, max_len):
    while True:
        for i in range(0, len(sequences), batch_size):
            batch_sequences = sequences[i:i + batch_size]
            batch_mels = mels[i:i + batch_size]

            # Pad sequences to the max_len
            padded_sequences = tf.keras.preprocessing.sequence.pad_sequences(batch_sequences, maxlen=max_len, padding='post')
            padded_mels = tf.keras.preprocessing.sequence.pad_sequences(batch_mels, maxlen=max_len, padding='post', dtype='float32')

            yield ([padded_sequences, padded_mels], padded_mels)


def scheduler(epoch, lr):
    if epoch < 10:
        return lr
    else:
        return lr * tf.math.exp(-0.1)

# Training parameters
vocab_size = len(tokenizer.word_index) + 1
embedding_dim = 256
encoder_dim = 256
decoder_dim = 256
mel_dim = 80
batch_size = 32
epochs = 100
prenet_units = 128
prenet_dropout = 0.5
postnet_filters = 512
postnet_kernel_size = 5
max_len = 500  # Adjust based on your dataset

# Initialize and compile the model
tacotron2 = Tacotron2(vocab_size, embedding_dim, encoder_dim, decoder_dim, mel_dim, prenet_units=prenet_units,
    prenet_dropout=prenet_dropout,
    postnet_filters=postnet_filters,
    postnet_kernel_size=postnet_kernel_size
)
tacotron2.compile(optimizer='adam', loss='mse')

steps_per_epoch = int(np.ceil(len(sequences) / batch_size))

# Learning rate scheduler callback
lr_callback = tf.keras.callbacks.LearningRateScheduler(scheduler)

# Training
history = tacotron2.fit(
    data_generator(sequences, mels, batch_size, mel_dim, max_len),
    steps_per_epoch=steps_per_epoch,
    epochs=epochs,
    callbacks=[lr_callback]
)

# Plot training loss
plt.plot(history.history['loss'])
plt.xlabel('Epoch')
plt.ylabel('Loss')
plt.title('Training Loss')
plt.show()

# Training parameters
vocab_size = len(tokenizer.word_index) + 1
embedding_dim = 256
encoder_dim = 256
decoder_dim = 256
mel_dim = 80
batch_size = 32
epochs = 100
max_len = 500


# Initialize and compile the model
tacotron2 = Tacotron2(vocab_size, embedding_dim, encoder_dim, decoder_dim, mel_dim)
tacotron2.compile(optimizer='adam', loss='mse')

steps_per_epoch = int(np.ceil(len(sequences) / batch_size))

# Learning rate scheduler callback
lr_callback = tf.keras.callbacks.LearningRateScheduler(scheduler)

# Training
history = tacotron2.fit(
    data_generator(sequences, mels, batch_size, mel_dim, max_len),
    steps_per_epoch=steps_per_epoch,
    epochs=epochs,
    callbacks=[lr_callback]
)

# Plot training loss
plt.plot(history.history['loss'])
plt.xlabel('Epoch')
plt.ylabel('Loss')
plt.title('Training Loss')
plt.show()

def generate_mel(text, tokenizer, model, max_len_seq=100, n_mels=80):
    sequence = text_to_sequences([normalize_text(text)], tokenizer)
    sequence_padded = np.pad(sequence[0], (0, max_len_seq - len(sequence[0])), 'constant')
    sequence_padded = np.expand_dims(sequence_padded, axis=0)

    decoder_input = np.zeros((1, max_len_seq, n_mels), dtype=np.float32)

    mel, attention_weights = model.predict([sequence_padded, decoder_input])
    return mel[0], attention_weights

def mel_to_audio(mel, sr=22050, n_iter=32):
    mel = np.exp(mel)
    audio = librosa.feature.inverse.mel_to_audio(mel, sr=sr, n_iter=n_iter)
    return audio

# Example usage
text = "Your example text here"

# Generate mel spectrogram from text
mel, attention_weights = generate_mel(text, tokenizer, tacotron2)

# Display mel spectrogram
plt.imshow(mel.T, aspect='auto', origin='lower')
plt.title('Mel Spectrogram')
plt.show()

# Convert mel spectrogram to audio
audio = mel_to_audio(mel)

# Save audio to file
sf.write('output.wav', audio, 22050)

# Optionally, play audio
import IPython.display as ipd
ipd.Audio(audio, rate=22050)