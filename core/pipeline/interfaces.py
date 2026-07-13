from abc import ABC, abstractmethod
from typing import Generator
from core.pipeline.packets import StreamPacket
from core.pipeline.context import PipelineContext

class SpeechRecognizer(ABC):
    @abstractmethod
    def transcribe_stream(self, audio_generator, context: PipelineContext) -> Generator[StreamPacket, None, None]:
        """Consumes raw audio chunks and yields WORD or TRANSCRIPT packets."""
        pass

class LLMProvider(ABC):
    @abstractmethod
    def generate_stream(self, prompt: str, context: PipelineContext) -> Generator[StreamPacket, None, None]:
        """Consumes a prompt and yields TOKEN or SENTENCE packets."""
        pass

class TextToSpeech(ABC):
    @abstractmethod
    def speak_stream(self, packet_generator, context: PipelineContext):
        """Consumes SENTENCE packets and plays audio chunks."""
        pass
