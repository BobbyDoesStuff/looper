import pathlib
from audio_handler import AudioHandler
from audio_looper_gui import AudioLooperGUI

def main():
    script_dir = pathlib.Path(__file__).resolve().parent
    root_dir = script_dir.parent
    output_dir = root_dir / "recordings"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    with AudioHandler():
        looper_gui = AudioLooperGUI(output_dir)
        looper_gui.run()

if __name__ == "__main__":
    main()