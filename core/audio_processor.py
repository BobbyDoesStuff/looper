import numpy as np
from typing import List, Iterator

class AudioProcessor:
    CHUNK_SIZE = 1024
    SILENCE_THRESHOLD = 1000

    @staticmethod
    def trim_initial_silence(frames: List[bytes]) -> Iterator[bytes]:
        """
        This function checks if there is silence in the beginning of the recording.
        
        So if the Record Button is pressed, and nothing is played for a while, 
        the initial silence will get cut out until actual high range of sound is produced
        (hence the silence threshold parameter)
        """
        # Convert frames to a single NumPy array directly
        audio_data = np.frombuffer(b"".join(frames), dtype=np.int16)

        # Find the start index where the audio exceeds the silence threshold
        abs_audio_data = np.abs(audio_data)
        above_threshold_indices = np.where(abs_audio_data > AudioProcessor.SILENCE_THRESHOLD)[0]

        # If there are no indices above the threshold, use the length of audio_data
        start_index = (
            above_threshold_indices[0]
            if len(above_threshold_indices) > 0
            else len(audio_data)
        )

        # Adjust start_index to the nearest zero-crossing
        start_index = AudioProcessor.find_nearest_zero_crossing(audio_data, start_index)

        # Slice the array from the start index
        trimmed_audio_data = audio_data[start_index:]

        # Adjust the end of trimmed_audio_data to the nearest zero-crossing
        end_index = AudioProcessor.find_nearest_zero_crossing(
            trimmed_audio_data, len(trimmed_audio_data) - 1
        )
        trimmed_audio_data = trimmed_audio_data[: end_index + 1]

        return trimmed_audio_data



    @staticmethod
    def find_nearest_zero_crossing(audio_data: np.ndarray, start_index: int) -> int:
        """Find the nearest zero crossing for smooth audio transitions."""
        zero_crossings = np.where(np.diff(np.sign(audio_data)))[0]
        if len(zero_crossings) == 0:
            return start_index
        return zero_crossings[np.argmin(np.abs(zero_crossings - start_index))]

    @staticmethod
    def split_into_chunks(audio_data: np.ndarray) -> List[bytes]:
        return [audio_data[i:i+AudioProcessor.CHUNK_SIZE].tobytes() 
                for i in range(0, len(audio_data), AudioProcessor.CHUNK_SIZE)]