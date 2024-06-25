import tkinter as tk
import threading
import pathlib
import os
from typing import List
from audio_handler import AudioHandler
from audio_recorder import AudioRecorder
from audio_player import AudioPlayer
from loop_controller import LoopController

class AudioLooperGUI:
    def __init__(self, output_dir: pathlib.Path):
        self.output_dir = output_dir
        self.audio_handler = AudioHandler()
        self.audio_recorder = AudioRecorder(output_dir)
        self.audio_player = AudioPlayer()
        self.loops: List[LoopController] = []

        self.app = tk.Tk()
        self.app.title("Simple Audio Looper")
        self.app.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.app.bind("<space>", lambda event: self.toggle_recording())
        self.record_btn = tk.Button(self.app, text="Record", command=self.toggle_recording)
        self.record_btn.pack()

    def run(self):
        self.app.mainloop()

    def toggle_recording(self, event=None):
        if self.audio_recorder.is_recording.is_set():
            self.stop_recording()
        else:
            self.start_recording()

    def start_recording(self):
        self.audio_recorder.is_recording.set()
        self.record_btn.config(text="Stop Recording")
        threading.Thread(target=self._record_audio_thread).start()

    def stop_recording(self):
        self.audio_recorder.is_recording.clear()
        self.record_btn.config(text="Record")

    def _record_audio_thread(self):
        filename = self.audio_recorder.record_audio(self.audio_handler)
        self.app.after(0, self.create_loop_box, filename)

    def create_loop_box(self, filename: str):
        loop_controller = LoopController(filename)
        loop_index = len(self.loops)
        self.loops.append(loop_controller)

        frame = tk.Frame(self.app, width=200, height=20, relief=tk.RIDGE, borderwidth=1)
        frame.pack(fill=tk.X, pady=2)
        frame.pack_propagate(False)

        label = tk.Label(frame, text=f"Recording number {loop_index + 1}")
        label.pack(side=tk.LEFT)

        loop_toggle_btn = tk.Button(frame, text="On")
        loop_toggle_btn.pack(side=tk.RIGHT)

        # Now that loop_toggle_btn is defined, we can use it in the command
        loop_toggle_btn.config(
            command=lambda idx=loop_index, btn=loop_toggle_btn: self.toggle_loop(idx, btn)
        )

        self.start_playback(loop_index)

    def toggle_loop(self, loop_index: int, button: tk.Button):
        loop = self.loops[loop_index]
        loop.toggle()
        button.config(text="On" if loop.is_playing.is_set() else "Off")
        if loop.is_playing.is_set():
            self.start_playback(loop_index)
        else:
            self.stop_playback(loop_index)

    def start_playback(self, loop_index: int):
        loop = self.loops[loop_index]
        if loop.thread is None or not loop.thread.is_alive():
            loop.thread = threading.Thread(
                target=self.audio_player.play_audio_loop,
                args=(loop.filename, self.audio_handler, loop.is_playing),
            )
            loop.thread.start()

    def stop_playback(self, loop_index: int):
        loop = self.loops[loop_index]
        loop.stop()

    def on_closing(self):
        self.audio_player.stop_all_playback.set()
        for loop in self.loops:
            loop.stop()
        self.app.destroy()