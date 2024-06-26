import asyncio
import pathlib
import tkinter as tk
from audio_handler import AsyncAudioHandler
from audio_looper_gui import AudioLooperGUI
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AsyncTk(tk.Tk):
    def __init__(self):
        super().__init__()
        self.loop = asyncio.get_event_loop()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_closing(self):
        self.loop.stop()
        self.quit()

    def run(self, coro):
        self.loop.run_until_complete(coro)

    async def update_async(self):
        while True:
            self.update()
            await asyncio.sleep(0.01)  # Sleep for a short time to allow other coroutines to run

async def main():
    script_dir = pathlib.Path(__file__).resolve().parent
    root_dir = script_dir.parent
    output_dir = root_dir / "recordings"
    output_dir.mkdir(parents=True, exist_ok=True)

    root = AsyncTk()
    root.title("Simple Audio Looper")

    async with AsyncAudioHandler() as audio_handler:
        looper_gui = AudioLooperGUI(output_dir, root, audio_handler)
        
        # Run the Tkinter event loop and our async code concurrently
        await asyncio.gather(
            root.update_async(),
            looper_gui.run_async()
        )

if __name__ == "__main__":
    asyncio.run(main())