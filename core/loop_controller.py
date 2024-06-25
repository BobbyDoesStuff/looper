import threading
import os

class LoopController:
    def __init__(self, filename: str):
        self.filename = filename
        self.is_playing = threading.Event()
        self.is_playing.set()
        self.thread = None
        self.last_size = os.path.getsize(filename)

    def toggle(self):
        if self.is_playing.is_set():
            self.stop()
        else:
            self.start()

    def start(self):
        self.is_playing.set()

    def stop(self):
        self.is_playing.clear()
        if self.thread:
            self.thread.join()