import asyncio
import pathlib
import tkinter as tk
from audio_handler import AsyncAudioHandler
from audio_looper_gui import AudioLooperGUI
import logging
import signal
import os
import sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AsyncTk(tk.Tk):
    def __init__(self):
        super().__init__()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.shutdown_event = asyncio.Event()

    def on_closing(self):
        logger.info("Initiating shutdown...")
        self.shutdown_event.set()
        self.quit()
        # Force exit after a short delay
        self.after(1000, lambda: os._exit(0))

    async def update_async(self):
        while not self.shutdown_event.is_set():
            self.update()
            await asyncio.sleep(0.01)

async def main():
    script_dir = pathlib.Path(__file__).resolve().parent
    root_dir = script_dir.parent
    output_dir = root_dir / "recordings"
    output_dir.mkdir(parents=True, exist_ok=True)

    root = AsyncTk()
    root.title("Simple Audio Looper")

    def signal_handler():
        logger.info("Received termination signal")
        root.on_closing()

    # Set up signal handlers
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda signum, frame: signal_handler())

    async with AsyncAudioHandler() as audio_handler:
        looper_gui = AudioLooperGUI(output_dir, root, audio_handler)
        root.protocol("WM_DELETE_WINDOW", looper_gui.on_closing)
        
        # Run the Tkinter event loop and our async code concurrently
        try:
            await asyncio.gather(
                root.update_async(),
                looper_gui.run_async(),
                return_exceptions=True
            )
        except asyncio.CancelledError:
            logger.info("Tasks cancelled during shutdown")
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
        finally:
            logger.info("Main function completed")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except asyncio.CancelledError:
        logger.info("Application shut down successfully")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        sys.exit(0)