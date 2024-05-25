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
RECORD_SECONDS = 5  # Duration of the recording in seconds
WAVE_OUTPUT_FILENAME = "output.wav"

p = pyaudio.PyAudio()

def record_audio():
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)

    print("* recording")

    frames = []

    for _ in range(int(RATE / CHUNK * RECORD_SECONDS)):
        data = stream.read(CHUNK)
        frames.append(data)

    print("* done recording")

    stream.stop_stream()
    stream.close()

    wf = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()

def play_audio():
    wf = wave.open(WAVE_OUTPUT_FILENAME, 'rb')

    stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                    channels=wf.getnchannels(),
                    rate=wf.getframerate(),
                    output=True)

    while data := wf.readframes(CHUNK):
        stream.write(data)
    stream.stop_stream()
    stream.close()

def start_recording():
    threading.Thread(target=record_audio).start()

def start_playing():
    threading.Thread(target=play_audio).start()

# GUI setup
app = tk.Tk()
app.title("Simple Voice Recorder")

record_btn = tk.Button(app, text="Record", command=start_recording)
record_btn.pack()

play_btn = tk.Button(app, text="Play", command=start_playing)
play_btn.pack()

app.mainloop()

p.terminate()
