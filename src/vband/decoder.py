"""CW decoder module for converting paddle events to morse code."""

import time
import threading
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


# Binary tree-encoded morse table from reference implementation
# Each character's position in the tree is encoded by its morse pattern
# Starting at index 1, left (dit) = 2*i, right (dah) = 2*i+1
MORSE_TREE = (
    "**ETIANMSURWDKGOHVF\x9cL\xc4PJBXCYZQ\xd6\xe454\x9d3\xc9*\xc22&\xc8+*\xde\xc3\xf434" +
    "16=/*\xc6^(*7\xbb\xe3\xd18*90" +
    "*****|******?_****\"*\xb6.****@***'**-********;!*)****\xb9,****:*******"
)


class SpaceMarkPair:
    """Represents a space/mark timing pair for CW decoding."""

    def __init__(self, space_ms: float, mark_ms: float):
        """
        Initialize space/mark pair.

        Args:
            space_ms: Duration of space before mark in milliseconds
            mark_ms: Duration of mark in milliseconds
        """
        self.space_ms = space_ms
        self.mark_ms = mark_ms

    def __repr__(self) -> str:
        return f"SpaceMarkPair(space={self.space_ms:.1f}ms, mark={self.mark_ms:.1f}ms)"


class SpaceMarkDecoder:
    """
    Near real-time CW decoder using space/mark pairs.

    This decoder implements the adaptive algorithm from the vband.org reference
    implementation, providing near real-time character decoding with automatic
    WPM adjustment.
    """

    def __init__(self, config: Optional[VBandConfig] = None):
        """
        Initialize space/mark decoder.

        Args:
            config: Configuration object, uses defaults if None
        """
        self.config = config or VBandConfig()

        # Timing parameters (in milliseconds)
        # Use config's dit_duration (convert from seconds to milliseconds)
        self.dit_length = self.config.dit_duration * 1000.0
        self.last_mark = self.dit_length * 1.2  # Slightly longer than a dit
        self.char_space = self.dit_length * 3.0  # Character space is 3x dit

        # Decoder state
        self.morse_ch = 1  # Current character in binary tree
        self.decoded_text = ""
        self._flush_timer: Optional[threading.Timer] = None
        self._timer_lock = threading.Lock()

        # History for analysis
        self.history: List[Dict] = []
        self._save_space_type: Optional[int] = None
        self._save_space_duration: float = 0.0

    def decode_space_mark(self, space_ms: float, mark_ms: float) -> Optional[str]:
        """
        Decode a space/mark pair and return any completed characters.

        This is the main entry point that processes timing pairs in real-time.

        Args:
            space_ms: Duration of space before mark in milliseconds
            mark_ms: Duration of mark in milliseconds

        Returns:
            Decoded character(s) or None if character incomplete
        """
        # Process the space
        space_result = self._decode_space(space_ms)

        # Process the mark
        self._decode_mark(mark_ms)

        return space_result

    def _decode_space(self, duration: float) -> Optional[str]:
        """
        Decode a space and return characters if spacing threshold crossed.

        Args:
            duration: Space duration in milliseconds

        Returns:
            Decoded character(s), space, or None
        """
        self._clear_flush_timer()
        space_type = 2  # INTER_ELEMENT
        result = None

        # Check for end of character
        if duration > self.dit_length * 2.0:
            result = self._flush_character()

            # Determine if inter-char or inter-word space
            word_space = (self.char_space / 3.0) * 5.5
            max_time = 3000.0  # Maximum tracked time

            if duration >= word_space or duration >= max_time:
                # Inter-word space
                if result:
                    result += " "
                else:
                    result = " "

                # Slow down char spacing slightly (helps with consistency)
                self.char_space *= 1.03
                space_type = 4  # INTER_WORD
            else:
                # Inter-character space - adjust char_space adaptively
                if duration < self.char_space:
                    # Approach smaller value quicker
                    self.char_space = self.char_space * 0.5 + duration * 0.5
                else:
                    # Approach larger value slower
                    self.char_space = self.char_space * 0.8 + duration * 0.2
                space_type = 3  # INTER_CHAR

        self._add_to_history(space_type, duration, is_mark=False)
        return result

    def _decode_mark(self, duration: float) -> None:
        """
        Decode a mark (dit or dah) and update character state.

        Args:
            duration: Mark duration in milliseconds
        """
        self.morse_ch *= 2

        # Determine dit or dah
        mark_type = 0  # DIT
        if duration > self.dit_length * 1.7:
            mark_type = 1  # DAH
            self.morse_ch += 1

        # Adaptive learning: when current and last mark differ by 2X,
        # average and divide by 2 to get new dit length
        if duration > 2.0 * self.last_mark or self.last_mark > 2.0 * duration:
            new_dit = ((self.last_mark + duration) / 4.0 + self.dit_length) / 2.0
            self.dit_length = new_dit

            # Ensure char_space is at least 2.5 * dit_length
            if self.char_space < self.dit_length * 2.5:
                self.char_space = self.dit_length * 2.5

        self.last_mark = duration

        # Set flush timer for automatic character completion
        self._clear_flush_timer()
        with self._timer_lock:
            self._flush_timer = threading.Timer(
                self.dit_length * 8.0 / 1000.0,  # Convert to seconds
                self._flush_timer_expired
            )
            self._flush_timer.daemon = True
            self._flush_timer.start()

        self._add_to_history(mark_type, duration, is_mark=True)

    def _flush_character(self) -> Optional[str]:
        """
        Flush the current character and return it.

        Returns:
            Decoded character or None
        """
        self._clear_flush_timer()

        if self.morse_ch <= 1:
            return None

        ch = "*"  # Unknown character marker

        # Handle special extended characters
        if self.morse_ch == 0x89:
            # $ = ...-..-  (binary: 1000 1001)
            ch = "$"
        elif self.morse_ch == 0xc5:
            # <BK> ~ = -...-.-  (binary: 1100 0101)
            ch = "~"
        elif self.morse_ch < len(MORSE_TREE):
            ch = MORSE_TREE[self.morse_ch]

        self.decoded_text += ch
        self.morse_ch = 1
        return ch

    def _flush_timer_expired(self) -> None:
        """Callback when flush timer expires."""
        self._flush_character()

    def _clear_flush_timer(self) -> None:
        """Clear the flush timer if active."""
        with self._timer_lock:
            if self._flush_timer is not None:
                self._flush_timer.cancel()
                self._flush_timer = None

    def _add_to_history(self, type_: int, duration: float, is_mark: bool) -> None:
        """
        Add timing information to history.

        Args:
            type_: Type code (0=DIT, 1=DAH, 2=INTER_ELEMENT, 3=INTER_CHAR, 4=INTER_WORD)
            duration: Duration in milliseconds
            is_mark: True if this is a mark, False if space
        """
        if is_mark:
            # Add mark with saved space
            self.history.append({
                'space_type': self._save_space_type,
                'space_duration': self._save_space_duration,
                'mark_type': type_,
                'mark_duration': duration,
            })
            self._save_space_type = None
            self._save_space_duration = 0.0
        else:
            # Save space for next mark
            self._save_space_type = type_
            self._save_space_duration = duration

    def get_text(self) -> str:
        """
        Get all decoded text.

        Returns:
            Decoded text string
        """
        return self.decoded_text

    def get_wpm_string(self) -> str:
        """
        Get current WPM as a formatted string.

        Returns:
            WPM string in format "dit_wpm/eff_wpm WPM"
        """
        dit_wpm = 1200.0 / self.dit_length
        char_wpm = (3.0 * 1200.0) / self.char_space
        eff_wpm = (50.0 / (31.0 / dit_wpm + 19.0 / char_wpm))
        return f"{dit_wpm:.1f}/{eff_wpm:.1f} WPM"

    def get_dit_length_ms(self) -> float:
        """Get current dit length in milliseconds."""
        return self.dit_length

    def get_char_space_ms(self) -> float:
        """Get current character space in milliseconds."""
        return self.char_space

    def clear(self) -> None:
        """Clear all decoder state."""
        self._clear_flush_timer()
        self.decoded_text = ""
        self.morse_ch = 1
        self.history = []
        self._save_space_type = None
        self._save_space_duration = 0.0

    def flush(self) -> Optional[str]:
        """
        Manually flush any pending character.

        Returns:
            Decoded character or None
        """
        return self._flush_character()
