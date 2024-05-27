import os
import pyaudio
import wave
import tkinter as tk
import threading
import numpy as np
import time

# Audio settings
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
SILENCE_THRESHOLD = 500  # Adjust this threshold based on your audio levels

p = pyaudio.PyAudio()

# Global variables
is_recording = threading.Event()
stop_all_playback = threading.Event()
recording_count = 0
loops = []
playback_threads = []

# Directory where the recordings will be saved
script_dir = os.path.dirname(__file__)
root_dir = os.path.abspath(os.path.join(script_dir, '..'))
output_dir = os.path.join(root_dir, 'recordings')

# Ensure the recordings directory exists
os.makedirs(output_dir, exist_ok=True)

def record_audio():
    global recorded_frames, recording_count
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)

    print("* recording")

    recorded_frames = []

    while is_recording.is_set():
        data = stream.read(CHUNK)
        recorded_frames.append(data)

    print("* done recording")

    stream.stop_stream()
    stream.close()

    # Process recorded frames to remove initial silence
    trimmed_frames = trim_initial_silence(recorded_frames)

    # Save the trimmed recording to a uniquely named file
    output_filename = os.path.join(output_dir, f"output_{recording_count + 1}.wav")
    save_recording_to_wav(output_filename, trimmed_frames)

    # Increment the recording count after saving the file
    recording_count += 1

    # Automatically start playback
    create_loop_box(recording_count - 1)
    start_playback(recording_count - 1)

def trim_initial_silence(frames):
    # Convert frames to a single numpy array
    audio_data = np.frombuffer(b''.join(frames), dtype=np.int16)
    # Find the index where the sound starts
    start_index = 0
    for i in range(0, len(audio_data), CHUNK):
        chunk = audio_data[i:i+CHUNK]
        if np.max(np.abs(chunk)) > SILENCE_THRESHOLD:
            start_index = i
            break
    # Return trimmed frames
    trimmed_audio_data = audio_data[start_index:]
    return [
        trimmed_audio_data[i : i + CHUNK].tobytes()
        for i in range(0, len(trimmed_audio_data), CHUNK)
    ]

def play_audio_loop(loop_index):
    try:
        output_filename = os.path.join(output_dir, f"output_{loop_index + 1}.wav")
        wf = wave.open(output_filename, 'rb')

        # Preload all audio data into memory
        audio_data = wf.readframes(wf.getnframes())

        while loops[loop_index]["is_playing"] and not stop_all_playback.is_set():
            stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                            channels=wf.getnchannels(),
                            rate=wf.getframerate(),
                            output=True)

            # Play the preloaded audio data in a loop
            start_time = time.time()
            while loops[loop_index]["is_playing"] and not stop_all_playback.is_set():
                stream.write(audio_data)
                elapsed_time = time.time() - start_time
                if elapsed_time < len(audio_data) / (RATE * 2):  # Ensure it doesn't loop too early
                    time.sleep((len(audio_data) / (RATE * 2)) - elapsed_time)

            stream.stop_stream()
            stream.close()
    except Exception as e:
        print(f"Error in playback loop: {e}")

def toggle_recording(event=None):
    if is_recording.is_set():
        stop_recording()
    else:
        start_recording()

def start_recording():
    global recorded_frames
    print("Starting recording...")
    recorded_frames = []
    is_recording.set()
    record_btn.config(text="Stop Recording")
    threading.Thread(target=record_audio).start()

def stop_recording():
    print("Stopping recording...")
    is_recording.clear()
    record_btn.config(text="Record")

def create_loop_box(loop_index):
    frame = tk.Frame(app, width=200, height=20, relief=tk.RIDGE, borderwidth=1)
    frame.pack(fill=tk.X, pady=2)
    frame.pack_propagate(False)  # Prevent frame from resizing to fit the label

    label = tk.Label(frame, text=f"Recording number {loop_index + 1}")
    label.pack(side=tk.LEFT)

    loop_toggle_btn = tk.Button(frame, text="On", command=lambda: toggle_loop(loop_index, loop_toggle_btn))
    loop_toggle_btn.pack(side=tk.RIGHT)

    loops.append({"is_playing": True, "toggle_btn": loop_toggle_btn})

def toggle_loop(loop_index, button):
    loop = loops[loop_index]
    loop["is_playing"] = not loop["is_playing"]
    button.config(text="On" if loop["is_playing"] else "Off")
    if loop["is_playing"]:
        start_playback(loop_index)
    else:
        stop_playback(loop_index)

def start_playback(loop_index):
    loops[loop_index]["is_playing"] = True
    playback_thread = threading.Thread(target=play_audio_loop, args=(loop_index,))
    playback_threads.append(playback_thread)
    playback_thread.start()

def stop_playback(loop_index):
    loops[loop_index]["is_playing"] = False

# Save recording to WAV file
def save_recording_to_wav(file_path, frames):
    wf = wave.open(file_path, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()

def on_closing():
    stop_all_playback.set()
    for loop in loops:
        loop["is_playing"] = False
    for thread in playback_threads:
        thread.join()
    p.terminate()
    app.destroy()

# GUI setup
app = tk.Tk()
app.title("Simple Voice Recorder")
app.protocol("WM_DELETE_WINDOW", on_closing)

# Bind spacebar to toggle recording
app.bind('<space>', toggle_recording)

record_btn = tk.Button(app, text="Record", command=toggle_recording)
record_btn.pack()

app.mainloop()
