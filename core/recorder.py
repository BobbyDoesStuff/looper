import pathlib
import pyaudio
import wave
import tkinter as tk
import threading
import numpy as np


class AudioLooper:
    def __init__(
        self,
        output_dir: pathlib.Path,
        chunk: int = 1024,
        format: int = pyaudio.paInt16,
        channels: int = 1,
        rate: int = 44100,
        silence_threshold: int = 300000,
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
        audio_data = np.frombuffer(b"".join(frames), dtype=np.int16)
        start_index = 0
        for i in range(0, len(audio_data), self.chunk):
            chunk = audio_data[i: i + self.chunk]
            if np.max(np.abs(chunk)) > self.silence_threshold:
                start_index = i
                break
        trimmed_audio_data = audio_data[start_index:]
        return [
            trimmed_audio_data[i: i + self.chunk].tobytes()
            for i in range(0, len(trimmed_audio_data), self.chunk)
        ]

    def play_audio_loop(self, loop_index):
        try:
            output_filename = self.output_dir / f"output_{loop_index + 1}.wav"
            with wave.open(output_filename, "rb") as wf:
                audio_data = wf.readframes(wf.getnframes())

            while (
                self.loops[loop_index]["is_playing"]
                and not self.stop_all_playback.is_set()
            ):
                stream = self.p.open(
                    format=self.p.get_format_from_width(2),
                    channels=self.channels,
                    rate=self.rate,
                    output=True,
                )

                start_index = 0
                while (
                    self.loops[loop_index]["is_playing"]
                    and not self.stop_all_playback.is_set()
                ):
                    stream.write(audio_data[start_index: start_index + self.chunk])
                    start_index += self.chunk
                    if start_index >= len(audio_data):
                        start_index = 0
                stream.stop_stream()
                stream.close()
        except Exception as e:
            print(f"Error in playback loop: {e}")

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
        with wave.open(file_path, "wb") as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(self.p.get_sample_size(self.format))
            wf.setframerate(self.rate)
            wf.writeframes(b"".join(frames))

    def on_closing(self):
        self.stop_all_playback.set()
        for loop in self.loops:
            loop["is_playing"] = False
        for loop in self.loops:
            if loop["thread"] is not None:
                loop["thread"].join()
        self.p.terminate()
        self.app.destroy()

    def run(self):
        self.app = tk.Tk()
        self.app.title("Simple Voice Recorder")
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
