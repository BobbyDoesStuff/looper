import librosa
import numpy as np
import soundfile as sf
import matplotlib.pyplot as plt

# Load the audio file with a correctly formatted path
y, sr = librosa.load(r'C:\projects\looper\recordings\output_13.wav')

# Estimate the tempo
tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)

# Ensure tempo is a scalar value
tempo = tempo.item() if isinstance(tempo, np.ndarray) else tempo

# Set the desired tempo
desired_tempo = 120  # Your desired tempo in BPM (change this value as needed)
tempo_ratio = float(desired_tempo) / tempo

# Print out the variables for debugging
print(f"Original Tempo: {tempo}")
print(f"Desired Tempo: {desired_tempo}")
print(f"Tempo Ratio: {tempo_ratio}")

# Find beat timings in seconds
beat_times = librosa.frames_to_time(beat_frames, sr=sr)

# Calculate the target beat intervals based on the desired tempo
desired_beat_interval = 60.0 / desired_tempo

# Define the crossfade duration in samples (e.g., 50 milliseconds)
crossfade_duration = int(0.05 * sr)

# Function to apply crossfade
def crossfade(a, b, fade_length):
    fade_in = np.linspace(0, 1, fade_length)
    fade_out = np.linspace(1, 0, fade_length)
    return a * fade_out + b * fade_in

# Create a time-stretch function that varies the stretch factor for each interval
def variable_time_stretch(y, sr, beat_frames, tempo_ratio, crossfade_duration):
    y_stretched = np.array([])
    num_beats = len(beat_frames)
    
    # Debug: print the number of beats and beat frames
    print(f"Number of beats: {num_beats}")
    print(f"Beat frames: {beat_frames}")

    for i in range(num_beats - 1):
        start_sample = librosa.frames_to_samples(beat_frames[i])
        end_sample = librosa.frames_to_samples(beat_frames[i + 1])
        interval = y[start_sample:end_sample]
        interval_duration = librosa.get_duration(y=interval, sr=sr)
        stretch_factor = tempo_ratio
        
        # Debug: print the stretch factor for each interval
        print(f"Interval {i}: start_sample={start_sample}, end_sample={end_sample}, duration={interval_duration}, stretch_factor={stretch_factor}")
        
        stretched_interval = librosa.effects.time_stretch(interval, rate=stretch_factor)
        
        if len(y_stretched) > 0:
            overlap = crossfade(y_stretched[-crossfade_duration:], stretched_interval[:crossfade_duration], crossfade_duration)
            y_stretched = np.concatenate((y_stretched[:-crossfade_duration], overlap, stretched_interval[crossfade_duration:]))
        else:
            y_stretched = stretched_interval

    # Handle the last interval
    last_start_sample = librosa.frames_to_samples(beat_frames[-1])
    last_interval = y[last_start_sample:]
    if len(last_interval) > 0:
        last_interval_duration = librosa.get_duration(y=last_interval, sr=sr)
        last_stretch_factor = tempo_ratio
        
        # Debug: print the stretch factor for the last interval
        print(f"Last interval: start_sample={last_start_sample}, duration={last_interval_duration}, stretch_factor={last_stretch_factor}")
        
        stretched_last_interval = librosa.effects.time_stretch(last_interval, rate=last_stretch_factor)
        
        if len(y_stretched) > 0:
            overlap = crossfade(y_stretched[-crossfade_duration:], stretched_last_interval[:crossfade_duration], crossfade_duration)
            y_stretched = np.concatenate((y_stretched[:-crossfade_duration], overlap, stretched_last_interval[crossfade_duration:]))
        else:
            y_stretched = stretched_last_interval

    return y_stretched

# Apply variable time stretching with crossfade
y_adjusted = variable_time_stretch(y, sr, beat_frames, tempo_ratio, crossfade_duration)

# Ensure the first beat is included by adding the first interval explicitly
first_end_sample = librosa.frames_to_samples(beat_frames[1])
first_interval = y[:first_end_sample]
first_interval_duration = librosa.get_duration(y=first_interval, sr=sr)
first_stretch_factor = tempo_ratio
stretched_first_interval = librosa.effects.time_stretch(first_interval, rate=first_stretch_factor)

# Combine the first stretched interval with the rest
y_adjusted = np.concatenate((stretched_first_interval, y_adjusted))

# Save the adjusted audio
sf.write('guitar_rhythm_adjusted.wav', y_adjusted, sr)

