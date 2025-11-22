"""Real-time streaming module for CW decoding."""

import time
import threading
from typing import Optional, Callable, Union
from .paddle import PaddleInterface, PaddleEvent
from .decoder import CWDecoder, CWElement, MorseDecoder, SpaceMarkDecoder, SpaceMarkPair
from .config import VBandConfig

# Try to import audio module, but make it optional
try:
    from .audio import play_element
    _AUDIO_AVAILABLE = True
except (ImportError, OSError):
    _AUDIO_AVAILABLE = False
    play_element = None


class CWStream:
    """
    Real-time stream of CW elements (dits and dahs).

    This class processes paddle events and produces a stream of
    CW elements in real-time.
    """

    def __init__(
        self,
        config: Optional[VBandConfig] = None,
        callback: Optional[Callable[[CWElement], None]] = None,
    ):
        """
        Initialize CW stream.

        Args:
            config: Configuration object, uses defaults if None
            callback: Optional callback function called for each CW element
        """
        self.config = config or VBandConfig()
        self.paddle = PaddleInterface(self.config)
        self.decoder = CWDecoder(self.config)
        self.callback = callback
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start the CW stream."""
        if self._running:
            return

        self._running = True
        self.paddle.start()
        self._thread = threading.Thread(target=self._process_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the CW stream."""
        if not self._running:
            return

        self._running = False
        self.paddle.stop()
        if self._thread:
            self._thread.join(timeout=1.0)
            self._thread = None

    def _process_loop(self) -> None:
        """Main processing loop."""
        while self._running:
            # Check if using keyer for iambic mode
            if self.paddle.has_keyer():
                # Get keyed element directly
                element = self.paddle.get_keyed_element(timeout=0.1)
                if element and self.callback:
                    self.callback(element)
            else:
                # Get paddle event with timeout
                event = self.paddle.get_event(timeout=0.1)
                if event is None:
                    continue

                # Process event to get CW element
                element = self.decoder.process_event(event)
                if element and self.callback:
                    self.callback(element)

    def is_running(self) -> bool:
        """Check if the stream is running."""
        return self._running

    def __enter__(self) -> "CWStream":
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.stop()


class DecodedStream:
    """
    Real-time stream of decoded morse code characters.

    This class processes paddle events through both CW and morse
    decoders to produce a real-time stream of characters.
    """

    def __init__(
        self,
        config: Optional[VBandConfig] = None,
        char_callback: Optional[Callable[[str], None]] = None,
        element_callback: Optional[Callable[[CWElement], None]] = None,
    ):
        """
        Initialize decoded stream.

        Args:
            config: Configuration object, uses defaults if None
            char_callback: Optional callback for decoded characters
            element_callback: Optional callback for CW elements (dits/dahs)
        """
        self.config = config or VBandConfig()
        self.paddle = PaddleInterface(self.config)
        self.cw_decoder = CWDecoder(self.config)
        self.morse_decoder = MorseDecoder(self.config)
        self.char_callback = char_callback
        self.element_callback = element_callback
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start the decoded stream."""
        if self._running:
            return

        self._running = True
        self.paddle.start()
        self._thread = threading.Thread(target=self._process_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the decoded stream."""
        if not self._running:
            return

        self._running = False
        self.paddle.stop()
        if self._thread:
            self._thread.join(timeout=1.0)
            self._thread = None

    def _process_loop(self) -> None:
        """Main processing loop."""
        last_check = time.time()

        while self._running:
            current_time = time.time()
            element = None

            # Check if using keyer for iambic mode
            if self.paddle.has_keyer():
                # Get keyed element directly
                element = self.paddle.get_keyed_element(timeout=0.05)
            else:
                # Get paddle event with timeout
                event = self.paddle.get_event(timeout=0.05)

                if event:
                    # Process event to get CW element
                    element = self.cw_decoder.process_event(event)

            if element:
                # Call element callback if configured
                if self.element_callback:
                    self.element_callback(element)

                # Decode to character
                char = self.morse_decoder.process_element(element, current_time)
                if char and self.char_callback:
                    self.char_callback(char)

            # Periodically check for character timeout
            if current_time - last_check > 0.1:
                char = self.morse_decoder.flush(current_time)
                if char and self.char_callback:
                    self.char_callback(char)
                last_check = current_time

    def is_running(self) -> bool:
        """Check if the stream is running."""
        return self._running

    def __enter__(self) -> "DecodedStream":
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.stop()


def print_element(element: CWElement) -> None:
    """
    Print a CW element.

    Args:
        element: CW element to print
    """
    print(element.to_morse(), end="", flush=True)


def print_character(char: str) -> None:
    """
    Print a decoded character.

    Args:
        char: Character to print
    """
    print(char, end="", flush=True)


def play_audio_element(element: CWElement) -> None:
    """
    Play audio for a CW element.

    Args:
        element: CW element to play audio for
    """
    if _AUDIO_AVAILABLE and play_element is not None:
        play_element(element.is_dit)


class SpaceMarkStream:
    """
    Near real-time stream of decoded morse code using space/mark pairs.

    This stream implements the vband.org reference architecture for
    near real-time decoding with adaptive WPM detection. It processes
    space/mark timing pairs directly from the keyer and decodes them
    immediately using the adaptive algorithm.
    """

    def __init__(
        self,
        config: Optional[VBandConfig] = None,
        char_callback: Optional[Callable[[str], None]] = None,
        pair_callback: Optional[Callable[[SpaceMarkPair], None]] = None,
    ):
        """
        Initialize space/mark decoded stream.

        Args:
            config: Configuration object, uses defaults if None
            char_callback: Optional callback for decoded characters
            pair_callback: Optional callback for space/mark pairs
        """
        self.config = config or VBandConfig()
        self.paddle = PaddleInterface(self.config)
        self.decoder = SpaceMarkDecoder(self.config)
        self.char_callback = char_callback
        self.pair_callback = pair_callback
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start the space/mark stream."""
        if self._running:
            return

        self._running = True
        self.paddle.start()
        self._thread = threading.Thread(target=self._process_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the space/mark stream."""
        if not self._running:
            return

        self._running = False
        self.paddle.stop()
        if self._thread:
            self._thread.join(timeout=1.0)
            self._thread = None

    def _process_loop(self) -> None:
        """Main processing loop for space/mark pairs."""
        while self._running:
            # Check if using space/mark keyer
            if self.paddle.has_spacemark_keyer():
                # Get space/mark pair directly
                pair = self.paddle.get_space_mark_pair(timeout=0.05)

                if pair:
                    # Call pair callback if configured
                    if self.pair_callback:
                        self.pair_callback(pair)

                    # Decode the pair
                    char = self.decoder.decode_space_mark(pair.space_ms, pair.mark_ms)

                    # Debug logging
                    import sys
                    if char is not None:
                        print(f"\n[DEBUG] Decoded: {repr(char)}", file=sys.stderr)

                    if char and self.char_callback:
                        self.char_callback(char)
            else:
                # Fallback: not using space/mark keyer
                time.sleep(0.05)

    def get_text(self) -> str:
        """
        Get all decoded text so far.

        Returns:
            Decoded text string
        """
        return self.decoder.get_text()

    def get_wpm(self) -> str:
        """
        Get current WPM as formatted string.

        Returns:
            WPM string in format "dit_wpm/eff_wpm WPM"
        """
        return self.decoder.get_wpm_string()

    def get_dit_length_ms(self) -> float:
        """
        Get current dit length in milliseconds.

        Returns:
            Dit length in milliseconds
        """
        return self.decoder.get_dit_length_ms()

    def clear(self) -> None:
        """Clear all decoded text."""
        self.decoder.clear()

    def is_running(self) -> bool:
        """Check if the stream is running."""
        return self._running

    def __enter__(self) -> "SpaceMarkStream":
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.stop()
