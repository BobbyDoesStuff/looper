import numpy as np
import librosa
import soundfile as sf

def load_audio(file_path):
    y, sr = librosa.load(file_path, sr=None)
    print(f"Audio loaded: {file_path}, Sample Rate: {sr}, Duration: {len(y) / sr} seconds")
    return y, sr

def detect_beats(y, sr):
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
    beat_times = librosa.frames_to_time(beats, sr=sr)
    print(f"Detected Tempo: {tempo} BPM, Number of Beats: {len(beat_times)}")
    return tempo, beat_times

def adjust_tempo(y, sr, beat_times, target_tempo):
    D = librosa.stft(y)
    hop_length = 512  # Default hop length for librosa.stft
    beat_frames = librosa.time_to_frames(beat_times, sr=sr, hop_length=hop_length)
    original_tempo = 60 / np.mean(np.diff(beat_times))
    target_interval = (60 / target_tempo) * sr / hop_length  # Target interval in frames per beat
    print(f"Original Tempo: {original_tempo} BPM")
    print(f"Target Interval: {target_interval} frames")

    adjusted_D = []

    for i in range(len(beat_frames) + 1):
        if i == 0:
            start_frame = 0
        else:
            start_frame = beat_frames[i-1]

        if i < len(beat_frames):
            end_frame = beat_frames[i]
        else:
            end_frame = D.shape[1]
        
        if end_frame <= start_frame or start_frame >= D.shape[1] or end_frame > D.shape[1]:
            print(f"Skipping invalid segment from {start_frame} to {end_frame}")
            continue

        segment = D[:, start_frame:end_frame]
        if segment.shape[1] == 0:
            print(f"Skipping empty segment from {start_frame} to {end_frame}")
            continue

        current_interval = end_frame - start_frame
        time_stretch_factor = target_interval / current_interval
        print(f"Processing segment from {start_frame} to {end_frame}")
        print(f"  Current interval: {current_interval} frames")
        print(f"  Target interval: {target_interval} frames")
        print(f"  Calculated time stretch factor: {time_stretch_factor}")
        print(f"  Segment shape before stretching: {segment.shape}")

        if time_stretch_factor > 0:
            stretched_segment = librosa.phase_vocoder(segment, rate=time_stretch_factor)
            print(f"  Segment shape after stretching: {stretched_segment.shape}")
            adjusted_D.append(stretched_segment)
        else:
            print(f"Skipping segment from {start_frame} to {end_frame} due to invalid stretch factor: {time_stretch_factor}")

    if len(adjusted_D) == 0:
        print("No valid segments to concatenate")
        return y  # Return the original audio if no segments were adjusted

    adjusted_D = np.hstack(adjusted_D)
    adjusted_y = librosa.istft(adjusted_D, hop_length=hop_length)
    print(f"Adjusted audio duration: {len(adjusted_y) / sr} seconds")
    return adjusted_y

def save_audio(y, sr, output_path):
    sf.write(output_path, y, sr)
    print(f"Audio saved: {output_path}")

def main(input_path, output_path, target_tempo):
    y, sr = load_audio(input_path)
    _, beat_times = detect_beats(y, sr)
    adjusted_y = adjust_tempo(y, sr, beat_times, target_tempo)
    save_audio(adjusted_y, sr, output_path)

if __name__ == "__main__":
    input_path = r'C:\projects\looper\recordings\output_13.wav'
    output_path = 'output_audio.wav'
    target_tempo = 120
    main(input_path, output_path, target_tempo)
