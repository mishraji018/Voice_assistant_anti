import pyaudio
import threading
from typing import Generator
from core.pipeline.packets import StreamPacket, PacketType
from core.pipeline.context import PipelineContext
import time

class MicrophoneStream:
    def __init__(self, rate=16000, chunk=1024):
        self.rate = rate
        self.chunk = chunk
        self.p = pyaudio.PyAudio()

    def stream_audio(self, context: PipelineContext) -> Generator[StreamPacket, None, None]:
        stream = self.p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.rate,
            input=True,
            frames_per_buffer=self.chunk
        )
        
        sequence = 0
        try:
            while not context.cancel_token.is_cancelled:
                data = stream.read(self.chunk, exception_on_overflow=False)
                yield StreamPacket(
                    type=PacketType.AUDIO_CHUNK,
                    data=data,
                    timestamp=time.time(),
                    sequence=sequence,
                    request_id=context.request_id
                )
                sequence += 1
        finally:
            stream.stop_stream()
            stream.close()
