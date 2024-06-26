import tkinter as tk
import asyncio
import wave
import numpy as np
from audio_handler import AsyncAudioHandler
from audio_processor import AudioProcessor
import pathlib

class AudioLooperGUI:
    def __init__(self, output_dir: pathlib.Path, root: tk.Tk, audio_handler: AsyncAudioHandler):
        self.output_dir = output_dir
        self.app = root
        self.audio_handler = audio_handler
        self.is_recording = asyncio.Event()
        self.loops = []
        self.recording_count = 0

        self.app.bind("<space>", lambda event: asyncio.create_task(self.toggle_recording()))
        self.record_btn = tk.Button(self.app, text="Record", command=lambda: asyncio.create_task(self.toggle_recording()))
        self.record_btn.pack()

    async def run_async(self):
        # This method will be called from main.py to start the GUI's async operations
        pass

    async def toggle_recording(self):
        if self.is_recording.is_set():
            await self.stop_recording()
        else:
            await self.start_recording()

    async def start_recording(self):
        await self.audio_handler.open_input_stream()
        self.is_recording.set()
        self.record_btn.config(text="Stop Recording")
        asyncio.create_task(self.record_audio())

    async def stop_recording(self):
        self.is_recording.clear()
        self.record_btn.config(text="Record")

    async def record_audio(self):
        frames = []
        while self.is_recording.is_set():
            chunk = await self.audio_handler.read_chunk()
            frames.append(chunk)
        
        # Process and save the recorded audio
        filename = await self.save_recording(frames)
        
        # Create a loop box and start playback
        await self.create_loop_box(filename)

    async def save_recording(self, frames):
        audio_data = np.frombuffer(b''.join(frames), dtype=np.int16)
        processed_audio = AudioProcessor.trim_initial_silence(audio_data)
        
        filename = self.output_dir / f"output_{self.recording_count}.wav"
        self.recording_count += 1

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._save_wav, filename, processed_audio)
        
        return filename

    def _save_wav(self, filename, audio_data):
        with wave.open(str(filename), "wb") as wf:
            wf.setnchannels(self.audio_handler.channels)
            wf.setsampwidth(self.audio_handler.p.get_sample_size(self.audio_handler.format))
            wf.setframerate(self.audio_handler.rate)
            wf.writeframes(audio_data.tobytes())

    async def create_loop_box(self, filename):
        loop_index = len(self.loops)
        
        frame = tk.Frame(self.app, width=200, height=20, relief=tk.RIDGE, borderwidth=1)
        frame.pack(fill=tk.X, pady=2)
        frame.pack_propagate(False)

        label = tk.Label(frame, text=f"Recording {loop_index + 1}")
        label.pack(side=tk.LEFT)

        toggle_btn = tk.Button(frame, text="On", command=lambda idx=loop_index: asyncio.create_task(self.toggle_loop(idx)))
        toggle_btn.pack(side=tk.RIGHT)

        self.loops.append({"filename": filename, "is_playing": asyncio.Event(), "toggle_btn": toggle_btn})
        
        # Start playback
        await self.start_playback(loop_index)

    async def toggle_loop(self, loop_index):
        loop = self.loops[loop_index]
        if loop["is_playing"].is_set():
            loop["is_playing"].clear()
            loop["toggle_btn"].config(text="Off")
        else:
            loop["is_playing"].set()
            loop["toggle_btn"].config(text="On")
            await self.start_playback(loop_index)

    async def start_playback(self, loop_index):
        loop = self.loops[loop_index]
        loop["is_playing"].set()
        asyncio.create_task(self.play_audio_loop(loop_index))

    async def play_audio_loop(self, loop_index):
        loop = self.loops[loop_index]
        audio_data = await self.load_audio(loop["filename"])
        
        while loop["is_playing"].is_set():
            for chunk in AudioProcessor.split_into_chunks(audio_data):
                if not loop["is_playing"].is_set():
                    break
                await self.audio_handler.write_chunk(chunk)

    async def load_audio(self, filename):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._load_wav, filename)

    def _load_wav(self, filename):
        with wave.open(str(filename), "rb") as wf:
            return np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)