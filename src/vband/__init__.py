"""
VBAND - Python interface for VBAND USB CW paddle with real-time morse code decoding.

This package provides a simple interface to work with VBAND USB paddle interfaces,
supporting various paddle types and real-time CW decoding.
"""

from .paddle import PaddleType, PaddleInterface
from .decoder import CWDecoder, MorseDecoder
from .stream import CWStream, DecodedStream
from .config import VBandConfig
from .keyer import IambicKeyer

# Audio module is optional (requires PortAudio)
try:
    from .audio import CWAudio
    _audio_available = True
except (ImportError, OSError):
    CWAudio = None
    _audio_available = False

__version__ = "0.1.0"
__all__ = [
    "PaddleType",
    "PaddleInterface",
    "CWDecoder",
    "MorseDecoder",
    "CWStream",
    "DecodedStream",
    "VBandConfig",
    "IambicKeyer",
]

if _audio_available:
    __all__.append("CWAudio")
