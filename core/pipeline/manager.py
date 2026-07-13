import threading
import uuid
import time
import logging
from core.pipeline.events import PipelineEvents
from core.pipeline.packets import PacketType, StreamPacket
from core.pipeline.context import PipelineContext, CancellationToken
from brain.infra.event_bus import bus

class PipelineManager:
    def __init__(self, stt_provider, llm_provider=None, tts_provider=None):
        self.stt = stt_provider
        self.llm = llm_provider
        self.tts = tts_provider
        
        # Metrics
        self.metrics = {}

    def start_listening(self):
        """Starts the Milestone 2A Microphone -> STT stream."""
        request_id = uuid.uuid4().hex[:8]
        context = PipelineContext.create(request_id)
        
        bus.emit(PipelineEvents.STT_STARTED, {"request_id": request_id})
        self.metrics[request_id] = {"start_time": time.time()}

        def run_pipeline():
            from core.audio.mic_stream import MicrophoneStream
            mic = MicrophoneStream()
            audio_gen = mic.stream_audio(context)
            
            try:
                # We feed the audio generator to the STT provider
                stt_gen = self.stt.transcribe_stream(audio_gen, context)
                
                first_word = False
                
                for packet in stt_gen:
                    if packet.type == PacketType.PARTIAL_TRANSCRIPT:
                        if not first_word:
                            first_word = True
                            latency = time.time() - self.metrics[request_id]["start_time"]
                            bus.emit(PipelineEvents.METRIC_UPDATED, {"stt_latency": latency})
                            
                        bus.emit(PipelineEvents.TRANSCRIPT_UPDATED, packet)
                        
                    elif packet.type == PacketType.TRANSCRIPT:
                        bus.emit(PipelineEvents.TRANSCRIPT_FINAL, packet)
                        # For Milestone 2A, we stop the pipeline here after one utterance
                        context.cancel_token.cancel("UTTERANCE_COMPLETE")
                        break
                        
                    elif packet.type == PacketType.ERROR:
                        bus.emit(PipelineEvents.ERROR, packet)
                        break

            except Exception as e:
                logging.error(f"Pipeline error: {e}")
                bus.emit(PipelineEvents.ERROR, {"error": str(e)})
            finally:
                bus.emit(PipelineEvents.STT_FINISHED, {"request_id": request_id})

        threading.Thread(target=run_pipeline, daemon=True).start()
        return context.cancel_token
