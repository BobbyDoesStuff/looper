import tkinter as tk
import asyncio
import contextlib
import wave
import numpy as np
from audio_handler import AsyncAudioHandler
from audio_processor import AudioProcessor
import pathlib
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AudioLooperGUI:
    def __init__(self, output_dir: pathlib.Path, root: tk.Tk, audio_handler: AsyncAudioHandler):
        self.output_dir = output_dir
        self.app = root
        self.audio_handler = audio_handler
        self.is_recording = asyncio.Event()
        self.loops = []
        self.recording_count = 0
        self.playback_task = None
        self.shutdown_event = asyncio.Event()

        self.app.bind("<space>", lambda event: asyncio.create_task(self.toggle_recording()))
        self.record_btn = tk.Button(self.app, text="Record", command=lambda: asyncio.create_task(self.toggle_recording()))
        self.record_btn.pack()

    async def run_async(self):
        self.playback_task = asyncio.create_task(self.continuous_playback())
        try:
            await self.shutdown_event.wait()
        finally:
            await self.cleanup()

    async def cleanup(self):
        logger.info("Cleaning up...")
        for loop in self.loops:
            loop["is_playing"].clear()
            if loop["playback_task"] and not loop["playback_task"].done():
                loop["playback_task"].cancel()

        if self.playback_task and not self.playback_task.done():
            self.playback_task.cancel()

        # Wait for a short time for tasks to cancel
        await asyncio.sleep(0.5)

        # Force cancel any remaining tasks
        tasks = [task for task in asyncio.all_tasks() if task is not asyncio.current_task()]
        for task in tasks:
            task.cancel()

        logger.info("Cleanup complete")

    async def continuous_playback(self):
        try:
            while not self.shutdown_event.is_set():
                mixed_audio = np.zeros(self.audio_handler.chunk_size, dtype=np.int32)
                active_loops = [loop for loop in self.loops if loop["is_playing"].is_set()]

                if not active_loops:
                    await asyncio.sleep(0.01)
                    continue

                for loop in active_loops:
                    with contextlib.suppress(asyncio.QueueEmpty):
                        chunk = loop["audio_queue"].get_nowait()
                        mixed_audio += np.frombuffer(chunk, dtype=np.int16).astype(np.int32)
                # Scale down the mixed audio to prevent clipping
                max_value = np.max(np.abs(mixed_audio))
                if max_value > 32767:
                    scale_factor = 32767 / max_value
                    mixed_audio = (mixed_audio * scale_factor).astype(np.int16)
                else:
                    mixed_audio = mixed_audio.astype(np.int16)

                await self.audio_handler.write_chunk(mixed_audio.tobytes())
        except asyncio.CancelledError:
            logger.info("Playback task cancelled")
        except Exception as e:
            logger.error(f"Error in continuous playback: {e}")

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
        try:
            while self.is_recording.is_set():
                chunk = await self.audio_handler.read_chunk()
                frames.append(chunk)
            
            filename = await self.save_recording(frames)
            await self.create_loop_box(filename, autoplay=True)
        except Exception as e:
            logger.error(f"Error in recording audio: {e}")

    async def save_recording(self, frames):
        audio_data = AudioProcessor.trim_initial_silence(frames)
        
        filename = self.output_dir / f"output_{self.recording_count}.wav"
        self.recording_count += 1

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._save_wav, filename, audio_data)
        
        return filename

    def _save_wav(self, filename, audio_data):
        with wave.open(str(filename), "wb") as wf:
            wf.setnchannels(self.audio_handler.channels)
            wf.setsampwidth(self.audio_handler.p.get_sample_size(self.audio_handler.format))
            wf.setframerate(self.audio_handler.rate)
            wf.writeframes(audio_data.tobytes())

    async def create_loop_box(self, filename, autoplay=False):
        loop_index = len(self.loops)
        
        frame = tk.Frame(self.app, width=200, height=20, relief=tk.RIDGE, borderwidth=1)
        frame.pack(fill=tk.X, pady=2)
        frame.pack_propagate(False)

        label = tk.Label(frame, text=f"Recording {loop_index + 1}")
        label.pack(side=tk.LEFT)

        toggle_btn = tk.Button(frame, text="On" if autoplay else "Off", command=lambda idx=loop_index: asyncio.create_task(self.toggle_loop(idx)))
        toggle_btn.pack(side=tk.RIGHT)

        audio_data = await self.load_audio(filename)
        audio_queue = asyncio.Queue(maxsize=10)  # Limit queue size to prevent memory issues
        loop_info = {
            "filename": filename,
            "is_playing": asyncio.Event(),
            "toggle_btn": toggle_btn,
            "audio_data": audio_data,
            "audio_queue": audio_queue,
            "playback_task": None
        }
        self.loops.append(loop_info)

        if autoplay:
            await self.start_loop(loop_info)

    async def toggle_loop(self, loop_index):
        loop = self.loops[loop_index]
        if loop["is_playing"].is_set():
            await self.stop_loop(loop)
        else:
            await self.start_loop(loop)

    async def start_loop(self, loop):
        loop["is_playing"].set()
        loop["toggle_btn"].config(text="On")
        loop["playback_task"] = asyncio.create_task(self.fill_audio_queue(loop))

    async def stop_loop(self, loop):
        loop["is_playing"].clear()
        loop["toggle_btn"].config(text="Off")
        if loop["playback_task"]:
            loop["playback_task"].cancel()
        loop["audio_queue"] = asyncio.Queue(maxsize=10)  # Reset the queue

    async def fill_audio_queue(self, loop):
        audio_data = loop["audio_data"]
        chunk_size = self.audio_handler.chunk_size

        try:
            while loop["is_playing"].is_set() and not self.shutdown_event.is_set():
                for i in range(0, len(audio_data), chunk_size):
                    if not loop["is_playing"].is_set() or self.shutdown_event.is_set():
                        break
                    chunk = audio_data[i:i+chunk_size]
                    if len(chunk) < chunk_size:
                        chunk = np.pad(chunk, (0, chunk_size - len(chunk)), 'constant')
                    try:
                        await asyncio.wait_for(loop["audio_queue"].put(chunk.tobytes()), timeout=0.1)
                    except asyncio.TimeoutError:
                        continue  # Skip this chunk if the queue is full

                # If we've reached the end of the audio, start over
                await asyncio.sleep(0)  # Yield control to allow other coroutines to run
        except asyncio.CancelledError:
            logger.info("Playback task for loop cancelled")
        except Exception as e:
            logger.error(f"Error in fill_audio_queue: {e}")

    async def load_audio(self, filename):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._load_wav, filename)

    def _load_wav(self, filename):
        with wave.open(str(filename), "rb") as wf:
            return np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)

    def on_closing(self):
        logger.info("Closing application...")
        self.shutdown_event.set()
        self.app.quit()
        # Force exit after a short delay
        self.app.after(1000, lambda: os._exit(0))