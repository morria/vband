"""CW decoder module for converting paddle events to morse code."""

import time
from typing import Optional, List, Dict
from collections import deque
from .paddle import PaddleEvent
from .config import VBandConfig


# International Morse Code table
MORSE_CODE: Dict[str, str] = {
    ".-": "A",
    "-...": "B",
    "-.-.": "C",
    "-..": "D",
    ".": "E",
    "..-.": "F",
    "--.": "G",
    "....": "H",
    "..": "I",
    ".---": "J",
    "-.-": "K",
    ".-..": "L",
    "--": "M",
    "-.": "N",
    "---": "O",
    ".--.": "P",
    "--.-": "Q",
    ".-.": "R",
    "...": "S",
    "-": "T",
    "..-": "U",
    "...-": "V",
    ".--": "W",
    "-..-": "X",
    "-.--": "Y",
    "--..": "Z",
    "-----": "0",
    ".----": "1",
    "..---": "2",
    "...--": "3",
    "....-": "4",
    ".....": "5",
    "-....": "6",
    "--...": "7",
    "---..": "8",
    "----.": "9",
    ".-.-.-": ".",
    "--..--": ",",
    "..--..": "?",
    ".----.": "'",
    "-.-.--": "!",
    "-..-.": "/",
    "-.--.": "(",
    "-.--.-": ")",
    ".-...": "&",
    "---...": ":",
    "-.-.-.": ";",
    "-...-": "=",
    ".-.-.": "+",
    "-....-": "-",
    "..--.-": "_",
    ".-..-.": '"',
    "...-..-": "$",
    ".--.-.": "@",
    # Prosigns
    "...-.-": "<SK>",  # End of contact
    ".-.-.": "<AR>",  # End of message
    "-...-": "<BT>",  # Break
    "-.-.-": "<KA>",  # Starting signal
    "...-.": "<VE>",  # Understood
    ".......": "<ERROR>",  # Error
}


class CWElement:
    """Represents a single CW element (dit or dah)."""

    def __init__(self, is_dit: bool, duration: float, timestamp: float):
        """
        Initialize CW element.

        Args:
            is_dit: True for dit, False for dah
            duration: Element duration in seconds
            timestamp: Element start timestamp
        """
        self.is_dit = is_dit
        self.duration = duration
        self.timestamp = timestamp

    def to_morse(self) -> str:
        """Convert to morse code character."""
        return "." if self.is_dit else "-"

    def __repr__(self) -> str:
        return f"{'DIT' if self.is_dit else 'DAH'}({self.duration:.3f}s)"


class CWDecoder:
    """
    Decodes paddle events into CW elements (dits and dahs).

    This class handles timing analysis and converts raw key presses
    into properly timed morse code elements.
    """

    def __init__(self, config: Optional[VBandConfig] = None):
        """
        Initialize CW decoder.

        Args:
            config: Configuration object, uses defaults if None
        """
        self.config = config or VBandConfig()
        self._press_time: Dict[bool, Optional[float]] = {True: None, False: None}
        self._recent_durations: deque = deque(maxlen=10)

    def process_event(self, event: PaddleEvent) -> Optional[CWElement]:
        """
        Process a paddle event and return a CW element if complete.

        Args:
            event: Paddle event to process

        Returns:
            CWElement if key was released (element complete), None otherwise
        """
        key_type = event.is_dit  # True for dit, False for dah

        if event.is_pressed:
            # Key down - record press time
            self._press_time[key_type] = event.timestamp
            return None
        else:
            # Key up - calculate duration and create element
            press_time = self._press_time[key_type]
            if press_time is None:
                return None

            duration = event.timestamp - press_time
            self._press_time[key_type] = None

            # Update recent durations for auto-WPM
            if self.config.auto_wpm:
                self._update_timing(duration, event.is_dit)

            return CWElement(is_dit=event.is_dit, duration=duration, timestamp=press_time)

    def _update_timing(self, duration: float, is_dit: bool) -> None:
        """
        Update timing estimates based on recent input.

        Args:
            duration: Duration of the element
            is_dit: True if this was a dit
        """
        self._recent_durations.append((duration, is_dit))

        # Only adjust based on dits (more consistent)
        dit_durations = [d for d, is_d in self._recent_durations if is_d]

        if len(dit_durations) >= 3:
            # Use median to avoid outliers
            sorted_dits = sorted(dit_durations)
            median_dit = sorted_dits[len(sorted_dits) // 2]

            # Smooth the adjustment
            current_dit = self.config.dit_duration
            new_dit = current_dit * 0.7 + median_dit * 0.3

            # Only update if change is significant (>10%)
            if abs(new_dit - current_dit) / current_dit > 0.1:
                self.config.dit_duration = new_dit


class MorseDecoder:
    """
    Decodes CW elements into characters and words.

    This class handles element-to-character conversion and
    spacing detection for word boundaries.
    """

    def __init__(self, config: Optional[VBandConfig] = None):
        """
        Initialize Morse decoder.

        Args:
            config: Configuration object, uses defaults if None
        """
        self.config = config or VBandConfig()
        self._current_char: List[str] = []
        self._last_element_time: Optional[float] = None
        self._morse_to_char = MORSE_CODE

    def process_element(
        self, element: CWElement, current_time: Optional[float] = None
    ) -> Optional[str]:
        """
        Process a CW element and return decoded character if ready.

        Args:
            element: CW element to process
            current_time: Current time for spacing detection

        Returns:
            Decoded character, space, or None if character incomplete
        """
        if current_time is None:
            current_time = time.time()

        # Check for character or word spacing
        if self._last_element_time is not None:
            gap = element.timestamp - self._last_element_time

            # Word space detected
            if gap >= self.config.word_space_duration:
                result = self._flush_character()
                self._current_char = [element.to_morse()]
                self._last_element_time = element.timestamp
                return (result + " ") if result else " "

            # Character space detected
            elif gap >= self.config.char_space_duration:
                result = self._flush_character()
                self._current_char = [element.to_morse()]
                self._last_element_time = element.timestamp
                return result

        # Add element to current character
        self._current_char.append(element.to_morse())
        self._last_element_time = element.timestamp
        return None

    def flush(self, current_time: Optional[float] = None) -> Optional[str]:
        """
        Flush any pending character.

        Args:
            current_time: Current time for spacing detection

        Returns:
            Decoded character or None
        """
        if current_time is None:
            current_time = time.time()

        # Check if enough time has passed for character spacing
        if (
            self._last_element_time is not None
            and current_time - self._last_element_time >= self.config.char_space_duration
        ):
            return self._flush_character()

        return None

    def _flush_character(self) -> Optional[str]:
        """
        Decode and return the current character buffer.

        Returns:
            Decoded character or None
        """
        if not self._current_char:
            return None

        morse_code = "".join(self._current_char)
        char = self._morse_to_char.get(morse_code, f"<{morse_code}>")
        self._current_char = []
        return char

    def reset(self) -> None:
        """Reset decoder state."""
        self._current_char = []
        self._last_element_time = None
