from enum import Enum
from dataclasses import dataclass
from typing import Any

class PacketType(Enum):
    # STT Packets
    WORD = "WORD"                     # Partial word from STT
    PARTIAL_TRANSCRIPT = "PARTIAL_TRANSCRIPT" # Running sentence fragment
    TRANSCRIPT = "TRANSCRIPT"         # Finalized sentence/utterance
    
    # LLM Packets
    TOKEN = "TOKEN"                   # Single chunk from LLM
    SENTENCE = "SENTENCE"             # Complete parsed sentence from LLM
    
    # Audio Packets
    AUDIO_CHUNK = "AUDIO_CHUNK"       # Raw or synthesized audio bytes
    
    # System Packets
    STATUS = "STATUS"
    ERROR = "ERROR"
    METRIC = "METRIC"

@dataclass
class StreamPacket:
    type: PacketType
    data: Any
    timestamp: float
    sequence: int
    request_id: str
