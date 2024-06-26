import librosa
import soundfile as sf
import numpy as np
import sys

def load_audio(file_path):
    """Load an audio file."""
    try:
        y, sr = librosa.load(file_path)
        return y, sr
    except Exception as e:
        print(f"Error loading audio file: {e}")
        sys.exit(1)

def detect_tempo(y, sr):
    """Detect the tempo of the audio."""
    try:
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        if hasattr(tempo, '__len__'):
            print(f"Warning: Multiple tempo values detected: {tempo}")
            tempo = np.mean(tempo)  # Take the average if multiple tempos
        return float(tempo)
    except Exception as e:
        print(f"Error detecting tempo: {e}")
        return None

def correct_rhythm(y, sr, original_tempo, target_tempo):
    """Correct the rhythm of the audio to match the target tempo."""
    try:
        # Calculate the time stretch factor
        stretch_factor = target_tempo / original_tempo
        print(f"Stretch factor: {stretch_factor}")
        
        # Use librosa's time_stretch function
        y_stretched = librosa.effects.time_stretch(y, rate=stretch_factor)
        
        return y_stretched
    except Exception as e:
        print(f"Error correcting rhythm: {e}")
        return None

def save_audio(y, sr, file_path):
    """Save the processed audio to a file."""
    try:
        sf.write(file_path, y, sr)
    except Exception as e:
        print(f"Error saving audio file: {e}")

def main():
    input_file = r"C:\projects\looper\recordings\output_5.wav"
    output_file = "output_corrected.wav"
    target_bpm = 300  # Set your desired BPM here

    # Load the audio
    y, sr = load_audio(input_file)
    if y is None or sr is None:
        return

    print(f"Audio loaded. Shape: {y.shape}, Sample rate: {sr}")

    # Detect original tempo
    original_tempo = detect_tempo(y, sr)
    if original_tempo is None:
        return
    print(f"Original tempo: {original_tempo:.2f} BPM")

    # Correct the rhythm
    corrected_audio = correct_rhythm(y, sr, original_tempo, target_bpm)
    if corrected_audio is None:
        return

    print(f"Corrected audio shape: {corrected_audio.shape}")

    # Save the processed audio
    save_audio(corrected_audio, sr, output_file)

    print(f"Processed audio saved to {output_file}")
    print(f"Target tempo: {target_bpm} BPM")

if __name__ == "__main__":
    main()