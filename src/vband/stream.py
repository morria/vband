"""Real-time streaming module for CW decoding."""

import time
import threading
from typing import Optional, Callable, Union
from .paddle import PaddleInterface, PaddleEvent
from .decoder import CWDecoder, CWElement, MorseDecoder
from .config import VBandConfig


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
            # Get paddle event with timeout
            event = self.paddle.get_event(timeout=0.05)

            current_time = time.time()

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
