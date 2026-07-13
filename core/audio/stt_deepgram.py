import threading
import queue
from typing import Generator
from deepgram import (
    DeepgramClient,
    DeepgramClientOptions,
    LiveTranscriptionEvents,
    LiveOptions,
)
from core.pipeline.interfaces import SpeechRecognizer
from core.pipeline.packets import StreamPacket, PacketType
from core.pipeline.context import PipelineContext
from core.config.config import config
import logging

class DeepgramSTTProvider(SpeechRecognizer):
    def __init__(self):
        self.api_key = config.get_secret("deepgram_api_key")
        if not self.api_key:
            logging.error("Deepgram API Key not found.")
            
        self.client = DeepgramClient(self.api_key)

    def transcribe_stream(self, audio_generator: Generator[bytes, None, None], context: PipelineContext) -> Generator[StreamPacket, None, None]:
        if not self.api_key:
            yield StreamPacket(type=PacketType.ERROR, data="Deepgram API key missing", timestamp=context.timestamp, sequence=0, request_id=context.request_id)
            return

        out_queue = queue.Queue()
        sequence = 0
        connection_closed = threading.Event()

        # Connect to Deepgram
        try:
            dg_connection = self.client.listen.live.v("1")

            def on_message(self, result, **kwargs):
                nonlocal sequence
                sentence = result.channel.alternatives[0].transcript
                if len(sentence) == 0:
                    return
                if result.is_final:
                    out_queue.put(StreamPacket(
                        type=PacketType.TRANSCRIPT,
                        data=sentence,
                        timestamp=result.start,
                        sequence=sequence,
                        request_id=context.request_id
                    ))
                else:
                    out_queue.put(StreamPacket(
                        type=PacketType.PARTIAL_TRANSCRIPT,
                        data=sentence,
                        timestamp=result.start,
                        sequence=sequence,
                        request_id=context.request_id
                    ))
                sequence += 1

            def on_error(self, error, **kwargs):
                out_queue.put(StreamPacket(
                    type=PacketType.ERROR,
                    data=str(error),
                    timestamp=0.0,
                    sequence=sequence,
                    request_id=context.request_id
                ))

            def on_close(self, close, **kwargs):
                connection_closed.set()

            dg_connection.on(LiveTranscriptionEvents.Transcript, on_message)
            dg_connection.on(LiveTranscriptionEvents.Error, on_error)
            dg_connection.on(LiveTranscriptionEvents.Close, on_close)

            options = LiveOptions(
                model="nova-2",
                language="en-US",
                smart_format=True,
                encoding="linear16",
                channels=1,
                sample_rate=16000,
                interim_results=True,
            )

            if not dg_connection.start(options):
                yield StreamPacket(type=PacketType.ERROR, data="Failed to connect to Deepgram", timestamp=context.timestamp, sequence=0, request_id=context.request_id)
                return

            # Start a thread to feed audio chunks
            def feed_audio():
                try:
                    for chunk in audio_generator:
                        if context.cancel_token.is_cancelled:
                            break
                        # Assuming chunk is a StreamPacket or raw bytes
                        audio_data = chunk.data if isinstance(chunk, StreamPacket) else chunk
                        dg_connection.send(audio_data)
                except Exception as e:
                    logging.error(f"Error feeding audio to Deepgram: {e}")
                finally:
                    dg_connection.finish()

            feed_thread = threading.Thread(target=feed_audio, daemon=True)
            feed_thread.start()

            # Yield from queue
            while not connection_closed.is_set() or not out_queue.empty():
                if context.cancel_token.is_cancelled:
                    break
                    
                try:
                    packet = out_queue.get(timeout=0.1)
                    yield packet
                except queue.Empty:
                    continue

        except Exception as e:
            logging.error(f"Deepgram stream error: {e}")
            yield StreamPacket(type=PacketType.ERROR, data=str(e), timestamp=context.timestamp, sequence=sequence, request_id=context.request_id)
