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
from typing import List, Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AudioLooperGUI:
    def __init__(self, output_dir: pathlib.Path, root: tk.Tk, audio_handler: AsyncAudioHandler):
        self.output_dir = output_dir
        self.app = root
        self.audio_handler = audio_handler
        self.is_recording = asyncio.Event()
        self.loops: List[Dict[str, Any]] = []
        self.recording_count = 0
        self.playback_task = None
        self.shutdown_event = asyncio.Event()

        self._setup_ui()

    def _setup_ui(self):
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
        await self._cancel_all_tasks()
        logger.info("Cleanup complete")

    async def _cancel_all_tasks(self):
        for loop in self.loops:
            loop["is_playing"].clear()
            if loop["playback_task"] and not loop["playback_task"].done():
                loop["playback_task"].cancel()

        if self.playback_task and not self.playback_task.done():
            self.playback_task.cancel()

        await asyncio.sleep(0.5)

        tasks = [task for task in asyncio.all_tasks() if task is not asyncio.current_task()]
        for task in tasks:
            task.cancel()

    async def continuous_playback(self):
        try:
            while not self.shutdown_event.is_set():
                mixed_audio = await self._mix_active_loops()
                if mixed_audio is not None:
                    await self.audio_handler.write_chunk(mixed_audio.tobytes())
                else:
                    await asyncio.sleep(0.01)
        except asyncio.CancelledError:
            logger.info("Playback task cancelled")
        except Exception as e:
            logger.error(f"Error in continuous playback: {e}")

    async def _mix_active_loops(self) -> np.ndarray | None:
        active_loops = [loop for loop in self.loops if loop["is_playing"].is_set()]
        if not active_loops:
            return None

        chunks = []
        for loop in active_loops:
            try:
                chunk = loop["audio_queue"].get_nowait()
                chunks.append(np.frombuffer(chunk, dtype=np.int16))
            except asyncio.QueueEmpty:
                # If a queue is empty, use a silent chunk instead
                chunks.append(np.zeros(self.audio_handler.chunk_size, dtype=np.int16))

        if not chunks:
            return None

        mixed_audio = np.sum(chunks, axis=0, dtype=np.int32)
        return self._normalize_audio(mixed_audio)

    @staticmethod
    def _normalize_audio(audio: np.ndarray) -> np.ndarray:
        abs_max = np.abs(audio).max()
        if abs_max > 32767:
            return (audio * 32767 / abs_max).astype(np.int16)
        return audio.astype(np.int16)

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
            async for chunk in self._read_audio_chunks():
                frames.append(chunk)
            
            filename = await self.save_recording(frames)
            await self.create_loop_box(filename, autoplay=True)
        except Exception as e:
            logger.error(f"Error in recording audio: {e}")

    async def _read_audio_chunks(self):
        while self.is_recording.is_set():
            yield await self.audio_handler.read_chunk()

    async def save_recording(self, frames: List[bytes]) -> pathlib.Path:
        audio_data = AudioProcessor.trim_initial_silence(frames)
        filename = self.output_dir / f"output_{self.recording_count}.wav"
        self.recording_count += 1
        await asyncio.to_thread(self._save_wav, filename, audio_data)
        return filename

    def _save_wav(self, filename: pathlib.Path, audio_data: np.ndarray):
        with wave.open(str(filename), "wb") as wf:
            wf.setnchannels(self.audio_handler.channels)
            wf.setsampwidth(self.audio_handler.p.get_sample_size(self.audio_handler.format))
            wf.setframerate(self.audio_handler.rate)
            wf.writeframes(audio_data.tobytes())

    async def create_loop_box(self, filename: pathlib.Path, autoplay: bool = False):
        loop_index = len(self.loops)
        frame = self._create_loop_frame(loop_index)
        toggle_btn = self._create_toggle_button(frame, loop_index, autoplay)
        
        audio_data = await self.load_audio(filename)
        loop_info = self._create_loop_info(filename, toggle_btn, audio_data)
        self.loops.append(loop_info)

        if autoplay:
            await self.start_loop(loop_info)

    def _create_loop_frame(self, loop_index: int) -> tk.Frame:
        frame = tk.Frame(self.app, width=200, height=20, relief=tk.RIDGE, borderwidth=1)
        frame.pack(fill=tk.X, pady=2)
        frame.pack_propagate(False)
        tk.Label(frame, text=f"Recording {loop_index + 1}").pack(side=tk.LEFT)
        return frame

    def _create_toggle_button(self, frame: tk.Frame, loop_index: int, autoplay: bool) -> tk.Button:
        toggle_btn = tk.Button(
            frame,
            text="On" if autoplay else "Off",
            command=lambda idx=loop_index: asyncio.create_task(self.toggle_loop(idx))
        )
        toggle_btn.pack(side=tk.RIGHT)
        return toggle_btn

    def _create_loop_info(self, filename: pathlib.Path, toggle_btn: tk.Button, audio_data: np.ndarray) -> Dict[str, Any]:
        return {
            "filename": filename,
            "is_playing": asyncio.Event(),
            "toggle_btn": toggle_btn,
            "audio_data": audio_data,
            "audio_queue": asyncio.Queue(maxsize=10),
            "playback_task": None
        }

    async def toggle_loop(self, loop_index: int):
        loop = self.loops[loop_index]
        if loop["is_playing"].is_set():
            await self.stop_loop(loop)
        else:
            await self.start_loop(loop)

    async def start_loop(self, loop: Dict[str, Any]):
        loop["is_playing"].set()
        loop["toggle_btn"].config(text="On")
        loop["playback_task"] = asyncio.create_task(self.fill_audio_queue(loop))

    async def stop_loop(self, loop: Dict[str, Any]):
        loop["is_playing"].clear()
        loop["toggle_btn"].config(text="Off")
        if loop["playback_task"]:
            loop["playback_task"].cancel()
        loop["audio_queue"] = asyncio.Queue(maxsize=10)

    async def fill_audio_queue(self, loop: Dict[str, Any]):
        try:
            audio_data = loop["audio_data"]
            chunk_size = self.audio_handler.chunk_size
            
            # Convert all data to bytes at once
            byte_data = audio_data.tobytes()
            
            # Calculate total number of chunks
            total_chunks = len(byte_data) // (chunk_size * 2)
            
            chunk_index = 0
            while loop["is_playing"].is_set() and not self.shutdown_event.is_set():
                # Get the next chunk
                start = chunk_index * chunk_size * 2
                end = start + chunk_size * 2
                chunk = byte_data[start:end]
                
                # Try to add the chunk to the queue
                try:
                    await asyncio.wait_for(loop["audio_queue"].put(chunk), timeout=0.1)
                except asyncio.TimeoutError:
                    await asyncio.sleep(0.01)  # Short sleep if queue is full
                    continue
                
                # Move to the next chunk, wrapping around if necessary
                chunk_index = (chunk_index + 1) % total_chunks
                
                # Allow other coroutines to run
                await asyncio.sleep(0)

        except asyncio.CancelledError:
            logger.info("Playback task for loop cancelled")
        except Exception as e:
            logger.error(f"Error in fill_audio_queue: {e}")

    async def load_audio(self, filename: pathlib.Path) -> np.ndarray:
        return await asyncio.to_thread(self._load_wav, filename)

    def _load_wav(self, filename: pathlib.Path) -> np.ndarray:
        with wave.open(str(filename), "rb") as wf:
            return np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)

    def on_closing(self):
        logger.info("Closing application...")
        self.shutdown_event.set()
        self.app.quit()
        self.app.after(1000, lambda: os._exit(0))