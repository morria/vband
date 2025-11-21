"""Configuration module for VBAND package."""

from dataclasses import dataclass
from typing import Optional
from enum import Enum


class PaddleType(Enum):
    """Supported paddle types."""

    STRAIGHT_KEY = "straight"  # Single lever, manual timing
    DUAL_PADDLE = "dual"  # Two levers, manual timing
    IAMBIC_A = "iambic_a"  # Squeeze priority
    IAMBIC_B = "iambic_b"  # Squeeze memory
    SINGLE_PADDLE = "single"  # Dit only or Dah only


@dataclass
class VBandConfig:
    """Configuration for VBAND paddle interface."""

    # Paddle configuration
    paddle_type: PaddleType = PaddleType.IAMBIC_B

    # Timing parameters (in seconds)
    dit_duration: float = 0.06  # Default ~20 WPM
    debounce_time: float = 0.005  # 5ms debounce

    # Character spacing detection
    char_space_threshold: float = 3.0  # Multiple of dit duration
    word_space_threshold: float = 7.0  # Multiple of dit duration

    # Decoding options
    auto_decode: bool = True  # Automatically decode to characters
    output_dits_dahs: bool = False  # Also output raw dit/dah stream

    # WPM calculation
    auto_wpm: bool = True  # Automatically adjust to operator's speed
    target_wpm: Optional[int] = None  # Fixed WPM if auto_wpm is False

    # Key mappings (for VBAND USB interface)
    dit_key: str = "ctrl_l"  # Left control key
    dah_key: str = "ctrl_r"  # Right control key

    def wpm_to_dit_duration(self, wpm: int) -> float:
        """
        Convert WPM to dit duration in seconds.

        Standard: PARIS = 50 dit units, so 1 WPM = 50 dit units per minute
        Dit duration = 60 / (50 * WPM) = 1.2 / WPM

        Args:
            wpm: Words per minute

        Returns:
            Dit duration in seconds
        """
        return 1.2 / wpm

    def dit_duration_to_wpm(self, dit_duration: float) -> int:
        """
        Convert dit duration to WPM.

        Args:
            dit_duration: Dit duration in seconds

        Returns:
            Words per minute (rounded)
        """
        return round(1.2 / dit_duration)

    @property
    def char_space_duration(self) -> float:
        """Get character space duration in seconds."""
        return self.dit_duration * self.char_space_threshold

    @property
    def word_space_duration(self) -> float:
        """Get word space duration in seconds."""
        return self.dit_duration * self.word_space_threshold

    @property
    def current_wpm(self) -> int:
        """Get current WPM based on dit duration."""
        return self.dit_duration_to_wpm(self.dit_duration)

    def set_wpm(self, wpm: int) -> None:
        """
        Set operating speed in WPM.

        Args:
            wpm: Words per minute (typically 5-60)
        """
        self.dit_duration = self.wpm_to_dit_duration(wpm)
        self.target_wpm = wpm
