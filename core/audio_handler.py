import asyncio
import pyaudio

class AsyncAudioHandler:
    def __init__(self):
        self.p = pyaudio.PyAudio()
        self.input_stream = None
        self.output_stream = None
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 44100
        self.chunk_size = 1024

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def open_input_stream(self):
        loop = asyncio.get_running_loop()
        self.input_stream = await loop.run_in_executor(
            None, 
            lambda: self.p.open(format=self.format,
                                channels=self.channels,
                                rate=self.rate,
                                input=True,
                                frames_per_buffer=self.chunk_size)
        )

    async def open_output_stream(self):
        loop = asyncio.get_running_loop()
        self.output_stream = await loop.run_in_executor(
            None, 
            lambda: self.p.open(format=self.format,
                                channels=self.channels,
                                rate=self.rate,
                                output=True,
                                frames_per_buffer=self.chunk_size)
        )

    async def read_chunk(self):
        if not self.input_stream:
            raise ValueError("Input stream is not open")
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.input_stream.read, self.chunk_size)

    async def write_chunk(self, chunk):
        if not self.output_stream:
            await self.open_output_stream()
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self.output_stream.write, chunk)

    async def close(self):
        loop = asyncio.get_running_loop()
        if self.input_stream:
            await loop.run_in_executor(None, self.input_stream.stop_stream)
            await loop.run_in_executor(None, self.input_stream.close)
        if self.output_stream:
            await loop.run_in_executor(None, self.output_stream.stop_stream)
            await loop.run_in_executor(None, self.output_stream.close)
        self.p.terminate()