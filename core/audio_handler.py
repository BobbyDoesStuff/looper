import pyaudio
from typing import Dict, Any

# Constants
CHUNK_SIZE = 1024
AUDIO_FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100

class AudioHandler:
    def __init__(self):
        self.p = pyaudio.PyAudio()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.p.terminate()

    def open_input_stream(self) -> pyaudio.Stream:
        return self.p.open(
            format=AUDIO_FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK_SIZE,
        )

    def open_output_stream(self, audio_info: Dict[str, Any]) -> pyaudio.Stream:
        return self.p.open(
            format=self.p.get_format_from_width(audio_info["sampwidth"]),
            channels=audio_info["channels"],
            rate=audio_info["framerate"],
            output=True,
            frames_per_buffer=CHUNK_SIZE
        )

    def close_stream(self, stream: pyaudio.Stream):
        stream.stop_stream()
        stream.close()