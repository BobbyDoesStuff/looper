import pyaudio
import wave
import tkinter as tk
from tkinter import messagebox
import threading

# Audio settings
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
p = pyaudio.PyAudio()

# Global variables
is_recording = threading.Event()
is_playing = threading.Event()
recording_count = 0
recordings = []

# Function to record audio
def record_audio():
    global recording_count, recordings
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)

    print("* recording")

    frames = []

    while is_recording.is_set():
        data = stream.read(CHUNK)
        frames.append(data)

    print("* done recording")

    stream.stop_stream()
    stream.close()

    recording_filename = f"recording_{recording_count}.wav"
    wf = wave.open(recording_filename, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()

    recordings.append(recording_filename)
    recording_count += 1
    create_recording_box(recording_filename)

# Function to play audio in a loop
def play_audio_loop(filename):
    wf = wave.open(filename, 'rb')

    while is_playing.is_set():
        wf.rewind()  # Reset to the beginning of the file
        stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                        channels=wf.getnchannels(),
                        rate=wf.getframerate(),
                        output=True)

        data = wf.readframes(CHUNK)
        while data and is_playing.is_set():
            stream.write(data)
            data = wf.readframes(CHUNK)

        stream.stop_stream()
        stream.close()

def toggle_recording():
    if is_recording.is_set():
        stop_recording()
    else:
        start_recording()

def start_recording():
    is_recording.set()
    is_playing.clear()
    record_btn.config(text="Stop Recording")
    threading.Thread(target=record_audio).start()

def stop_recording():
    is_recording.clear()
    record_btn.config(text="Record")

def toggle_playback(filename):
    if is_playing.is_set():
        stop_playback()
    else:
        start_playback(filename)

def start_playback(filename):
    is_playing.set()
    threading.Thread(target=play_audio_loop, args=(filename,)).start()

def stop_playback():
    is_playing.clear()

def create_recording_box(filename):
    frame = tk.Frame(app, width=10, height=5, bg="lightgrey")
    frame.pack_propagate(False)  # Ensure frame doesn't resize to fit contents
    frame.pack(pady=2)

    label = tk.Label(frame, text=f"Recording number {recording_count}", bg="lightgrey")
    label.pack(side=tk.LEFT, padx=5)

    play_btn = tk.Button(frame, text="Play", command=lambda: toggle_playback(filename))
    play_btn.pack(side=tk.LEFT)

# GUI setup
app = tk.Tk()
app.title("Loop Pedal Simulator")

record_btn = tk.Button(app, text="Record", command=toggle_recording)
record_btn.pack()

app.mainloop()

p.terminate()
