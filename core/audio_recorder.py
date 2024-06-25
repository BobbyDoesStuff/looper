import pathlib
import wave
import threading
from typing import List
import logging
from audio_handler import AudioHandler, AUDIO_FORMAT, CHANNELS, RATE, CHUNK_SIZE
from audio_processor import AudioProcessor

logger = logging.getLogger(__name__)

class AudioRecorder:
    def __init__(self, output_dir: pathlib.Path):
        self.output_dir = output_dir
        self.is_recording = threading.Event()
        self.recording_count = 0

    def record_audio(self, audio_handler: AudioHandler) -> str:
        stream = audio_handler.open_input_stream()
        frames: List[bytes] = []
        try:
            logger.info("Recording started")
            self.is_recording.set()
            while self.is_recording.is_set():
                try:
                    frames.append(stream.read(CHUNK_SIZE))
                except OSError as e:
                    logger.error(f"Error reading from stream: {e}")
                    break
            logger.info("Recording finished")
        finally:
            stream.close()
            self.is_recording.clear()

        output_filename = self.output_dir / f"output_{self.recording_count + 1}.wav"
        self._save_recording_to_wav(output_filename, frames, audio_handler)
        self.recording_count += 1
        return str(output_filename)

    def _save_recording_to_wav(self, file_path: pathlib.Path, frames: List[bytes], audio_handler: AudioHandler):
        trimmed_frames = AudioProcessor.trim_initial_silence(frames)
        with wave.open(str(file_path), "wb") as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(audio_handler.p.get_sample_size(AUDIO_FORMAT))
            wf.setframerate(RATE)
            wf.writeframes(b"".join(trimmed_frames))