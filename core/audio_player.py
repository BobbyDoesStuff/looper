import wave
import threading
from typing import Dict, Any
from functools import lru_cache
import numpy as np
import pyaudio
from audio_handler import AsyncAudioHandler, CHUNK_SIZE
import logging

logger = logging.getLogger(__name__)

class AudioPlayer:
    def __init__(self):
        self.stop_all_playback = threading.Event()

    @lru_cache(maxsize=32)
    def read_audio_data(self, filename: str) -> Dict[str, Any]:
        with wave.open(filename, "rb") as wf:
            return {
                "data": np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16),
                "sampwidth": wf.getsampwidth(),
                "channels": wf.getnchannels(),
                "framerate": wf.getframerate()
            }

    def play_audio_loop(self, filename: str, audio_handler: AsyncAudioHandler, is_playing: threading.Event):
        try:
            audio_info = self.read_audio_data(filename)
            stream = audio_handler.open_output_stream(audio_info)
            self._play_audio_stream(audio_info["data"], stream, is_playing)
        except wave.Error as wave_error:
            logger.error(f"Wave error in playback loop: {wave_error}")
        except IOError as io_error:
            logger.error(f"I/O error in playback loop: {io_error}")
        except Exception as e:
            logger.error(f"Unexpected error in playback loop: {e}")
        finally:
            stream.stop_stream()
            stream.close()

    def _play_audio_stream(self, audio_data: np.ndarray, stream: pyaudio.Stream, is_playing: threading.Event):
        audio_length = len(audio_data)
        start_index = 0

        while is_playing.is_set() and not self.stop_all_playback.is_set():
            end_index = start_index + CHUNK_SIZE

            if end_index >= audio_length:
                # Play the remaining audio and loop back to the start
                stream.write(audio_data[start_index:].tobytes())
                start_index = 0
            else:
                stream.write(audio_data[start_index:end_index].tobytes())
                start_index = end_index