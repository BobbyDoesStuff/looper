import os
import pyaudio
import wave
import tkinter as tk
import threading

# Audio settings
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100

p = pyaudio.PyAudio()

# Global variables
is_recording = threading.Event()
stop_all_playback = threading.Event()
recording_count = 0
loops = []
playback_threads = []

# Directory where the recordings will be saved
output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

def record_audio():
    global recorded_frames
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

    # Save the recording to a uniquely named file
    output_filename = os.path.join(output_dir, f"output_{recording_count}.wav")
    save_recording_to_wav(output_filename)

def play_audio_loop(loop_index):
    try:
        output_filename = os.path.join(output_dir, f"output_{loop_index + 1}.wav")
        wf = wave.open(output_filename, 'rb')

        while loops[loop_index]["is_playing"] and not stop_all_playback.is_set():
            wf.rewind()  # Reset to the beginning of the file
            stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                            channels=wf.getnchannels(),
                            rate=wf.getframerate(),
                            output=True)

            data = wf.readframes(CHUNK)
            while data and loops[loop_index]["is_playing"] and not stop_all_playback.is_set():
                stream.write(data)
                data = wf.readframes(CHUNK)

            stream.stop_stream()
            stream.close()
    except Exception as e:
        print(f"Error in playback loop: {e}")

def toggle_recording():
    if is_recording.is_set():
        stop_recording()
    else:
        start_recording()

def start_recording():
    global recorded_frames
    recorded_frames = []
    is_recording.set()
    record_btn.config(text="Stop Recording")
    threading.Thread(target=record_audio).start()

def stop_recording():
    global recording_count
    is_recording.clear()
    record_btn.config(text="Record")

    # Save the recording to a uniquely named file
    recording_count += 1
    output_filename = os.path.join(output_dir, f"output_{recording_count}.wav")
    save_recording_to_wav(output_filename)
    
    # Automatically start playback
    create_loop_box(recording_count - 1)
    start_playback(recording_count - 1)

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
def save_recording_to_wav(file_path):
    wf = wave.open(file_path, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(recorded_frames))
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

record_btn = tk.Button(app, text="Record", command=toggle_recording)
record_btn.pack()

app.mainloop()
