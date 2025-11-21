"""Paddle interface module for handling keyboard input from VBAND USB device."""

import time
import threading
from typing import Callable, Optional, Dict, Tuple, TYPE_CHECKING
from queue import Queue, Empty
from pynput import keyboard
from .config import VBandConfig, PaddleType

if TYPE_CHECKING:
    from .keyer import IambicKeyer


class PaddleEvent:
    """Represents a paddle event (key press or release)."""

    def __init__(self, is_dit: bool, is_pressed: bool, timestamp: float):
        """
        Initialize paddle event.

        Args:
            is_dit: True for dit, False for dah
            is_pressed: True for key down, False for key up
            timestamp: Event timestamp in seconds
        """
        self.is_dit = is_dit
        self.is_pressed = is_pressed
        self.timestamp = timestamp

    def __repr__(self) -> str:
        key_type = "DIT" if self.is_dit else "DAH"
        action = "DOWN" if self.is_pressed else "UP"
        return f"PaddleEvent({key_type} {action} @ {self.timestamp:.3f}s)"


class PaddleInterface:
    """
    Interface for VBAND USB paddle that simulates keyboard control keys.

    The VBAND USB adapter simulates:
    - Left Control = Dit (tip connection)
    - Right Control = Dah (ring connection)
    """

    def __init__(self, config: Optional[VBandConfig] = None):
        """
        Initialize paddle interface.

        Args:
            config: Configuration object, uses defaults if None
        """
        self.config = config or VBandConfig()
        self._event_queue: Queue[PaddleEvent] = Queue()
        self._listener: Optional[keyboard.Listener] = None
        self._running = False

        # Track key states for debouncing
        self._dit_pressed = False
        self._dah_pressed = False
        self._last_dit_time = 0.0
        self._last_dah_time = 0.0

        # Iambic mode state
        self._iambic_state: Dict[str, bool] = {
            "dit_pending": False,
            "dah_pending": False,
            "last_was_dit": True,
        }

        # Initialize keyer for iambic modes
        self._keyer: Optional["IambicKeyer"] = None
        if self.config.paddle_type in (PaddleType.IAMBIC_A, PaddleType.IAMBIC_B):
            # Local import to avoid circular dependency
            from .keyer import IambicKeyer
            self._keyer = IambicKeyer(self.config)

    def start(self) -> None:
        """Start listening for paddle input."""
        if self._running:
            return

        self._running = True
        self._listener = keyboard.Listener(
            on_press=self._on_key_press, on_release=self._on_key_release
        )
        self._listener.start()

        # Start keyer if using iambic mode
        if self._keyer:
            self._keyer.start()

    def stop(self) -> None:
        """Stop listening for paddle input."""
        if not self._running:
            return

        self._running = False
        if self._listener:
            self._listener.stop()
            self._listener = None

        # Stop keyer if using iambic mode
        if self._keyer:
            self._keyer.stop()

    def _is_dit_key(self, key: keyboard.Key) -> bool:
        """Check if key is the dit key (left control)."""
        return key == keyboard.Key.ctrl_l

    def _is_dah_key(self, key: keyboard.Key) -> bool:
        """Check if key is the dah key (right control)."""
        return key == keyboard.Key.ctrl_r

    def _on_key_press(self, key: keyboard.Key) -> None:
        """
        Handle key press events.

        Args:
            key: The key that was pressed
        """
        if not self._running:
            return

        current_time = time.time()

        # Check for dit key
        if self._is_dit_key(key):
            # Debounce
            if current_time - self._last_dit_time < self.config.debounce_time:
                return
            self._last_dit_time = current_time

            if not self._dit_pressed:
                self._dit_pressed = True
                event = PaddleEvent(is_dit=True, is_pressed=True, timestamp=current_time)
                self._event_queue.put(event)

                # Update keyer state if using iambic mode
                if self._keyer:
                    self._keyer.update_paddle_state(self._dit_pressed, self._dah_pressed)

        # Check for dah key
        elif self._is_dah_key(key):
            # Debounce
            if current_time - self._last_dah_time < self.config.debounce_time:
                return
            self._last_dah_time = current_time

            if not self._dah_pressed:
                self._dah_pressed = True
                event = PaddleEvent(is_dit=False, is_pressed=True, timestamp=current_time)
                self._event_queue.put(event)

                # Update keyer state if using iambic mode
                if self._keyer:
                    self._keyer.update_paddle_state(self._dit_pressed, self._dah_pressed)

    def _on_key_release(self, key: keyboard.Key) -> None:
        """
        Handle key release events.

        Args:
            key: The key that was released
        """
        if not self._running:
            return

        current_time = time.time()

        # Check for dit key
        if self._is_dit_key(key):
            if self._dit_pressed:
                self._dit_pressed = False
                event = PaddleEvent(is_dit=True, is_pressed=False, timestamp=current_time)
                self._event_queue.put(event)

                # Update keyer state if using iambic mode
                if self._keyer:
                    self._keyer.update_paddle_state(self._dit_pressed, self._dah_pressed)

        # Check for dah key
        elif self._is_dah_key(key):
            if self._dah_pressed:
                self._dah_pressed = False
                event = PaddleEvent(is_dit=False, is_pressed=False, timestamp=current_time)
                self._event_queue.put(event)

                # Update keyer state if using iambic mode
                if self._keyer:
                    self._keyer.update_paddle_state(self._dit_pressed, self._dah_pressed)

    def get_event(self, timeout: Optional[float] = None) -> Optional[PaddleEvent]:
        """
        Get the next paddle event from the queue.

        Args:
            timeout: Maximum time to wait in seconds, None for blocking

        Returns:
            PaddleEvent or None if timeout
        """
        try:
            return self._event_queue.get(timeout=timeout)
        except Empty:
            return None

    def get_state(self) -> Tuple[bool, bool]:
        """
        Get current paddle state.

        Returns:
            Tuple of (dit_pressed, dah_pressed)
        """
        return (self._dit_pressed, self._dah_pressed)

    def has_keyer(self) -> bool:
        """
        Check if this interface has an active keyer.

        Returns:
            True if using iambic mode with keyer
        """
        return self._keyer is not None

    def get_keyed_element(self, timeout: Optional[float] = None):
        """
        Get the next keyed element from the iambic keyer.

        Only available when using iambic mode (A or B).

        Args:
            timeout: Maximum time to wait in seconds, None for blocking

        Returns:
            CWElement or None if timeout or not using keyer

        Raises:
            RuntimeError: If called when not using iambic mode
        """
        if not self._keyer:
            raise RuntimeError("Keyer not available - not in iambic mode")
        return self._keyer.get_element(timeout=timeout)

    def is_running(self) -> bool:
        """Check if the interface is running."""
        return self._running

    def __enter__(self) -> "PaddleInterface":
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.stop()
