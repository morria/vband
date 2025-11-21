"""Audio feedback for CW paddle input.

Generates audio tones for dit and dah elements.
"""

import numpy as np
import sounddevice as sd
from typing import Optional


class CWAudio:
    """Audio feedback generator for CW (Morse code) elements."""

    def __init__(
        self,
        frequency: int = 700,
        dit_duration: float = 0.08,
        sample_rate: int = 44100,
        volume: float = 0.3,
    ):
        """Initialize CW audio generator.

        Args:
            frequency: Tone frequency in Hz (default 700 Hz)
            dit_duration: Duration of a dit in seconds (default 0.08s / 80ms)
            sample_rate: Audio sample rate in Hz (default 44100)
            volume: Volume level from 0.0 to 1.0 (default 0.3)
        """
        self.frequency = frequency
        self.dit_duration = dit_duration
        self.dah_duration = dit_duration * 3  # Dah is 3x dit length
        self.sample_rate = sample_rate
        self.volume = volume

    def _generate_tone(self, duration: float) -> np.ndarray:
        """Generate a sine wave tone with envelope.

        Args:
            duration: Duration in seconds

        Returns:
            NumPy array of audio samples
        """
        # Generate time array
        t = np.linspace(0, duration, int(self.sample_rate * duration), False)

        # Generate sine wave
        tone = np.sin(2 * np.pi * self.frequency * t)

        # Apply envelope to avoid clicks (5ms rise/fall)
        envelope_samples = int(0.005 * self.sample_rate)
        if len(tone) > envelope_samples * 2:
            # Rising envelope
            tone[:envelope_samples] *= np.linspace(0, 1, envelope_samples)
            # Falling envelope
            tone[-envelope_samples:] *= np.linspace(1, 0, envelope_samples)

        # Apply volume
        tone *= self.volume

        return tone.astype(np.float32)

    def play_dit(self) -> None:
        """Play a dit (short) tone."""
        tone = self._generate_tone(self.dit_duration)
        sd.play(tone, self.sample_rate)

    def play_dah(self) -> None:
        """Play a dah (long) tone."""
        tone = self._generate_tone(self.dah_duration)
        sd.play(tone, self.sample_rate)

    def play_element(self, is_dit: bool) -> None:
        """Play audio for a CW element.

        Args:
            is_dit: True for dit, False for dah
        """
        if is_dit:
            self.play_dit()
        else:
            self.play_dah()

    def stop(self) -> None:
        """Stop all audio playback."""
        sd.stop()


# Singleton instance for easy use
_audio_instance: Optional[CWAudio] = None


def get_audio_instance() -> CWAudio:
    """Get or create the global CW audio instance.

    Returns:
        Global CWAudio instance
    """
    global _audio_instance
    if _audio_instance is None:
        _audio_instance = CWAudio()
    return _audio_instance


def play_dit() -> None:
    """Play a dit tone using the global audio instance."""
    get_audio_instance().play_dit()


def play_dah() -> None:
    """Play a dah tone using the global audio instance."""
    get_audio_instance().play_dah()


def play_element(is_dit: bool) -> None:
    """Play audio for a CW element using the global audio instance.

    Args:
        is_dit: True for dit, False for dah
    """
    get_audio_instance().play_element(is_dit)


def stop_audio() -> None:
    """Stop all audio playback."""
    if _audio_instance is not None:
        _audio_instance.stop()
