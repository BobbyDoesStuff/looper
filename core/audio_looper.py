import pathlib
import pyaudio
import wave
import tkinter as tk
import threading
import numpy as np
from functools import lru_cache

class AudioLooper:
    def __init__(
        self,
        output_dir: pathlib.Path,
        chunk=1024,
        format=pyaudio.paInt16,
        channels=1,
        rate=44100,
        silence_threshold=1000,
    ):
        self.chunk = chunk
        self.format = format
        self.channels = channels
        self.rate = rate
        self.silence_threshold = silence_threshold
        self.output_dir = output_dir

        self.p = pyaudio.PyAudio()
        self.is_recording = threading.Event()
        self.stop_all_playback = threading.Event()
        self.recording_count = 0
        self.loops = []
        self.playback_threads = []

        output_dir.mkdir(parents=True, exist_ok=True)

    @lru_cache(maxsize=100)
    def read_audio_data(self, loop_index):
        output_filename = self.output_dir / f"output_{loop_index + 1}.wav"
        with wave.open(str(output_filename), "rb") as wf:
            return {
                "data": wf.readframes(wf.getnframes()),
                "sampwidth": wf.getsampwidth(),
                "channels": wf.getnchannels(),
                "framerate": wf.getframerate()
            }

    def play_audio_loop(self, loop_index):
        try:
            audio_info = self.read_audio_data(loop_index)
            stream = self.open_audio_stream(audio_info)
            self.play_audio_stream(loop_index, audio_info["data"], stream)
        except wave.Error as wave_error:
            print(f"Wave error in playback loop: {wave_error}")
        except IOError as io_error:
            print(f"I/O error in playback loop: {io_error}")
        except Exception as e:
            print(f"Unexpected error in playback loop: {e}")

    def open_audio_stream(self, audio_info):
        return self.p.open(
            format=self.p.get_format_from_width(audio_info["sampwidth"]),
            channels=audio_info["channels"],
            rate=audio_info["framerate"],
            output=True,
        )

    def play_audio_stream(self, loop_index, audio_data, stream):
        try:
            start_index = 0
            while self.loops[loop_index]["is_playing"] and not self.stop_all_playback.is_set():
                end_index = start_index + self.chunk
                stream.write(audio_data[start_index:end_index])
                start_index += self.chunk
                if start_index >= len(audio_data):
                    start_index = 0
        finally:
            stream.stop_stream()
            stream.close()

    def record_audio(self):
        stream = self.p.open(
            format=self.format,
            channels=self.channels,
            rate=self.rate,
            input=True,
            frames_per_buffer=self.chunk,
        )

        print("* recording")

        def audio_stream_generator():
            try:
                while self.is_recording.is_set():
                    yield stream.read(self.chunk)
            finally:
                print("* done recording")
                stream.stop_stream()
                stream.close()

        trimmed_frames = self.trim_initial_silence(audio_stream_generator())

        output_filename = self.output_dir / f"output_{self.recording_count + 1}.wav"
        self.save_recording_to_wav(output_filename, trimmed_frames)

        self.recording_count += 1

        self.create_loop_box(self.recording_count - 1)
        self.start_playback(self.recording_count - 1)

    def trim_initial_silence(self, frames):
        """ This function checks if there is silence 
        in the beginning of the recording.
        
        So if the Record Button is pressed,
        and nothing is played for a while, the initial silence will
        get cut out until actual high range of sound is produced
        (hence the silence threshold parameter)"""

        # Convert frames to a single NumPy array directly
        audio_data = np.frombuffer(b"".join(frames), dtype=np.int16)

        # Find the start index where the audio exceeds the silence threshold
        abs_audio_data = np.abs(audio_data)
        above_threshold_indices = np.where(abs_audio_data > self.silence_threshold)[0]

        # If there are no indices above the threshold, use the length of audio_data
        start_index = (
            above_threshold_indices[0]
            if len(above_threshold_indices) > 0
            else len(audio_data)
        )

        # Adjust start_index to the nearest zero-crossing
        start_index = self.find_nearest_zero_crossing(audio_data, start_index)

        # Slice the array from the start index
        trimmed_audio_data = audio_data[start_index:]

        # Adjust the end of trimmed_audio_data to the nearest zero-crossing
        end_index = self.find_nearest_zero_crossing(
            trimmed_audio_data, len(trimmed_audio_data) - 1
        )
        trimmed_audio_data = trimmed_audio_data[: end_index + 1]

        # Convert back to chunks
        trimmed_frames = np.array_split(
            trimmed_audio_data,
            np.arange(self.chunk, len(trimmed_audio_data), self.chunk),
        )
        return list(trimmed_frames)

    def find_nearest_zero_crossing(self, audio_data, start_index):
        """Apply crossfade.

        This when the audio ends and starts again in a formed loop,
        a slight audio off and then on silence can be heard which
        happens so quickly that it resembles a clicking sound.
        This function makes it slightly less noticeable.
        """

        zero_crossings = np.where(np.diff(np.sign(audio_data)))[0]
        if len(zero_crossings) == 0:
            return start_index
        return zero_crossings[np.argmin(np.abs(zero_crossings - start_index))]

    def start_recording(self):
        print("Starting recording...")
        self.is_recording.set()
        threading.Thread(target=self.record_audio).start()

    def stop_recording(self):
        print("Stopping recording...")
        self.is_recording.clear()

    def create_loop_box(self, loop_index):
        frame = tk.Frame(self.app, width=200, height=20, relief=tk.RIDGE, borderwidth=1)
        frame.pack(fill=tk.X, pady=2)
        frame.pack_propagate(False)

        label = tk.Label(frame, text=f"Recording number {loop_index + 1}")
        label.pack(side=tk.LEFT)

        loop_toggle_btn = tk.Button(
            frame,
            text="On",
            command=lambda: self.toggle_loop(loop_index, loop_toggle_btn),
        )
        loop_toggle_btn.pack(side=tk.RIGHT)

        self.loops.append(
            {"is_playing": True, "toggle_btn": loop_toggle_btn, "thread": None}
        )

    def toggle_loop(self, loop_index, button):
        loop = self.loops[loop_index]
        loop["is_playing"] = not loop["is_playing"]
        button.config(text="On" if loop["is_playing"] else "Off")
        if loop["is_playing"]:
            if loop["thread"] is None or not loop["thread"].is_alive():
                loop["thread"] = threading.Thread(
                    target=self.play_audio_loop, args=(loop_index,)
                )
                loop["thread"].start()
        else:
            self.stop_playback(loop_index)

    def start_playback(self, loop_index):
        self.loops[loop_index]["is_playing"] = True
        if (
            self.loops[loop_index]["thread"] is None
            or not self.loops[loop_index]["thread"].is_alive()
        ):
            playback_thread = threading.Thread(
                target=self.play_audio_loop, args=(loop_index,)
            )
            self.loops[loop_index]["thread"] = playback_thread
            playback_thread.start()

    def stop_playback(self, loop_index):
        self.loops[loop_index]["is_playing"] = False
        if self.loops[loop_index]["thread"] is not None:
            self.loops[loop_index]["thread"].join()

    def save_recording_to_wav(self, file_path, frames):
        with wave.open(str(file_path), "wb") as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(self.p.get_sample_size(self.format))
            wf.setframerate(self.rate)
            wf.writeframes(b"".join(frames))

    def on_closing(self):
        self.stop_all_playback.set()
        [loop.update({"is_playing": False}) for loop in self.loops]
        threads = [loop["thread"] for loop in self.loops if loop["thread"] is not None]
        for thread in threads:
            thread.join()
        self.p.terminate()
        self.app.destroy()

    def run(self):
        self.app = tk.Tk()
        self.app.title("Simple Audio Looper")
        self.app.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.app.bind("<space>", lambda event: self.toggle_recording())
        self.record_btn = tk.Button(
            self.app, text="Record", command=self.toggle_recording
        )
        self.record_btn.pack()
        self.app.mainloop()

    def toggle_recording(self, event=None):
        if self.is_recording.is_set():
            self.stop_recording()
            self.record_btn.config(text="Record")
        else:
            self.start_recording()
            self.record_btn.config(text="Stop Recording")

if __name__ == "__main__":
    script_dir = pathlib.Path(__file__).resolve().parent
    root_dir = script_dir.parent
    output_dir = root_dir / "recordings"
    looper = AudioLooper(output_dir)
    looper.run()
