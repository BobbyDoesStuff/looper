import pathlib
import wave
import pytest
from unittest.mock import patch
from audio_looper import AudioLooper  # Replace with the actual module name

# Path to the output directory for testing
output_dir = pathlib.Path("/tmp/test_recordings")

# Initialize the AudioLooper instance
audio_looper = AudioLooper(output_dir)

def test_read_audio_data_caching(mocker):
    loop_index = 0
    
    # Mock wave.open to track calls and simulate reading a file
    mock_wave_open = mocker.patch("wave.open", autospec=True)
    mock_wave_open.return_value.__enter__.return_value.readframes.return_value = b"dummy_data"
    mock_wave_open.return_value.__enter__.return_value.getsampwidth.return_value = 2
    mock_wave_open.return_value.__enter__.return_value.getnchannels.return_value = 1
    mock_wave_open.return_value.__enter__.return_value.getframerate.return_value = 44100

    # First call to read_audio_data should call wave.open
    audio_info1 = audio_looper.read_audio_data(loop_index)
    assert audio_info1["data"] == b"dummy_data"
    assert audio_info1["sampwidth"] == 2
    assert audio_info1["channels"] == 1
    assert audio_info1["framerate"] == 44100
    mock_wave_open.assert_called_once()

    # Second call to read_audio_data with the same loop_index should use the cache
    audio_info2 = audio_looper.read_audio_data(loop_index)
    assert audio_info2 == audio_info1
    mock_wave_open.assert_called_once()  # wave.open should not be called here

    # Call with a different loop_index should call wave.open again
    audio_info3 = audio_looper.read_audio_data(1)
    assert audio_info3["data"] == b"dummy_data"
    assert audio_info3["sampwidth"] == 2
    assert audio_info3["channels"] == 1
    assert audio_info3["framerate"] == 44100
    assert mock_wave_open.call_count == 2  # wave.open should be called twice now

    # Additional call to the first loop_index to confirm cache usage
    audio_info4 = audio_looper.read_audio_data(loop_index)
    assert audio_info4 == audio_info1
    assert mock_wave_open.call_count == 2  # wave.open should still be called only twice

if __name__ == "__main__":
    pytest.main()
