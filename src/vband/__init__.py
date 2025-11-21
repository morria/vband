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
