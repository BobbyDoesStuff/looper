import core.librosa_dtw as librosa_dtw
import numpy as np
import soundfile as sf
from scipy.spatial.distance import cdist

# Load reference and target audio files
ref_y, ref_sr = librosa_dtw.load('reference_tempo.wav')
target_y, target_sr = librosa_dtw.load('off_tempo_guitar.wav')

# Extract features (e.g., MFCC)
ref_mfcc = librosa_dtw.feature.mfcc(ref_y, sr=ref_sr)
target_mfcc = librosa_dtw.feature.mfcc(target_y, sr=target_sr)

# Calculate DTW
D, wp = librosa_dtw.sequence.dtw(X=ref_mfcc.T, Y=target_mfcc.T, metric='euclidean')

# Warp the target audio to match the reference tempo
target_aligned = librosa_dtw.effects.time_stretch(target_y, wp)

# Save the adjusted audio
sf.write('aligned_guitar.wav', target_aligned, target_sr)
