import tkinter as tk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.animation as animation
import pyaudio
import numpy as np
import threading
import wave

# Audio settings
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
p = pyaudio.PyAudio()

# Global variables
xdata = np.arange(0, CHUNK)
ydata = np.zeros(CHUNK)
recorded_frames = []
loops = []
is_recording = False

# GUI setup
app = tk.Tk()
app.title("Loop Pedal Simulator")

fig = Figure(figsize=(5, 3))
ax = fig.add_subplot(111)
line, = ax.plot([], [], lw=2)
canvas = FigureCanvasTkAgg(fig, master=app)
canvas_widget = canvas.get_tk_widget()
canvas_widget.pack(fill=tk.BOTH, expand=True)

# Initialize plot for live updating
def init():
    ax.set_ylim(-32768, 32767)  # 16-bit PCM range
    ax.set_xlim(0, CHUNK)
    line.set_data(xdata, ydata)
    return line,

# Update plot function
def update(frame):
    global recorded_frames
    data = stream.read(CHUNK)
    ydata = np.frombuffer(data, dtype=np.int16)
    line.set_data(xdata, ydata)
    recorded_frames.append(data)
    return line,

# Start recording
def start_recording():
    global stream, ani, recorded_frames, is_recording
    recorded_frames = []
    is_recording = True
    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
    ani = animation.FuncAnimation(fig, update, init_func=init, blit=True, interval=30, cache_frame_data=False)
    canvas.draw()

# Stop recording and start looping
def stop_recording():
    global stream, ani, is_recording
    is_recording = False
    stream.stop_stream()
    stream.close()
    ani.event_source.stop()
    create_loop_box()
    save_recording_to_wav("loop_recording.wav")
    play_loop_in_background()

# Toggle record/stop button
def toggle_record():
    if is_recording:
        record_btn.config(text="Record")
        stop_recording()
    else:
        record_btn.config(text="Stop")
        start_recording()

# Create a new loop box in the UI
def create_loop_box():
    frame = tk.Frame(app)
    frame.pack(fill=tk.X)
    loop_toggle_btn = tk.Button(frame, text="On", command=lambda: toggle_loop(loop_toggle_btn))
    loop_toggle_btn.pack(side=tk.LEFT)
    loops.append({"frames": recorded_frames.copy(), "is_playing": True, "toggle_btn": loop_toggle_btn})

# Toggle loop on/off
def toggle_loop(button):
    loop = next(loop for loop in loops if loop["toggle_btn"] == button)
    loop["is_playing"] = not loop["is_playing"]
    button.config(text="On" if loop["is_playing"] else "Off")

# Play recorded audio in a loop
def play_loop():
    while True:
        for loop in loops:
            if loop["is_playing"]:
                stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, output=True)
                for frame in loop["frames"]:
                    if not loop["is_playing"]:
                        break
                    stream.write(frame)
                stream.close()

# Play loop in a separate thread
def play_loop_in_background():
    threading.Thread(target=play_loop, daemon=True).start()

# Save recording to WAV file for debugging
def save_recording_to_wav(file_path):
    wf = wave.open(file_path, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(recorded_frames))
    wf.close()

# Control buttons
record_btn = tk.Button(app, text="Record", command=toggle_record)
record_btn.pack()

app.mainloop()

p.terminate()
