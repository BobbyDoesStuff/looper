import librosa
import numpy as np
import soundfile as sf

# Load the audio file
y, sr = librosa.load('guitar_rhythm.wav')

# Estimate the tempo
tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)

# Adjust the tempo
desired_tempo = 120  # Your desired tempo in BPM
tempo_ratio = desired_tempo / tempo
y_fast = librosa.effects.time_stretch(y, tempo_ratio)

# Save the adjusted audio
sf.write('guitar_rhythm_adjusted.wav', y_fast, sr)
