"""Iambic keyer module for automatic dit/dah generation."""

import time
import threading
from typing import Optional, Tuple
from queue import Queue, Empty
from .decoder import CWElement
from .config import VBandConfig, PaddleType


class IambicKeyer:
    """
    Iambic keyer for automatic dit/dah generation with timing control.

    Implements Iambic Mode B (squeeze memory) behavior:
    - When a paddle is pressed, generates an element of configured duration
    - When both paddles are pressed (squeezed), alternates between dit and dah
    - Remembers squeeze state and generates one more element after release
    """

    def __init__(self, config: Optional[VBandConfig] = None):
        """
        Initialize iambic keyer.

        Args:
            config: Configuration object, uses defaults if None
        """
        self.config = config or VBandConfig()
        self._element_queue: Queue[CWElement] = Queue()
        self._running = False
        self._thread: Optional[threading.Thread] = None

        # Paddle state
        self._dit_pressed = False
        self._dah_pressed = False
        self._state_lock = threading.Lock()

        # Keyer state for Mode B
        self._last_was_dit = True  # Track alternation
        self._squeeze_memory = False  # Remember if both were pressed
        self._current_element_start: Optional[float] = None

    def start(self) -> None:
        """Start the keyer thread."""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._keyer_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the keyer thread."""
        if not self._running:
            return

        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
            self._thread = None

    def update_paddle_state(self, dit_pressed: bool, dah_pressed: bool) -> None:
        """
        Update the current paddle state.

        Args:
            dit_pressed: True if dit paddle is pressed
            dah_pressed: True if dah paddle is pressed
        """
        with self._state_lock:
            self._dit_pressed = dit_pressed
            self._dah_pressed = dah_pressed

    def get_element(self, timeout: Optional[float] = None) -> Optional[CWElement]:
        """
        Get the next keyed element.

        Args:
            timeout: Maximum time to wait in seconds, None for blocking

        Returns:
            CWElement or None if timeout
        """
        try:
            return self._element_queue.get(timeout=timeout)
        except Empty:
            return None

    def _keyer_loop(self) -> None:
        """
        Main keyer loop that generates timed elements based on paddle state.

        Implements Iambic Mode B logic:
        1. Check paddle state
        2. If a paddle is pressed, generate the appropriate element
        3. If both paddles were pressed (squeeze), remember to alternate
        4. Generate elements with proper timing based on dit_duration
        """
        while self._running:
            with self._state_lock:
                dit_pressed = self._dit_pressed
                dah_pressed = self._dah_pressed

            # Determine what to send based on Mode B logic
            element_to_send = self._get_next_element_mode_b(dit_pressed, dah_pressed)

            if element_to_send is not None:
                # Generate the element
                is_dit = element_to_send
                timestamp = time.time()

                # Calculate duration (dit = 1 unit, dah = 3 units)
                duration = self.config.dit_duration if is_dit else (self.config.dit_duration * 3)

                # Create and queue the element
                element = CWElement(is_dit=is_dit, duration=duration, timestamp=timestamp)
                self._element_queue.put(element)

                # Wait for element duration plus inter-element space (1 dit unit)
                time.sleep(duration + self.config.dit_duration)

                # Update alternation tracking
                self._last_was_dit = is_dit
            else:
                # No element to send, short sleep to avoid busy waiting
                time.sleep(0.01)

    def _get_next_element_mode_b(self, dit_pressed: bool, dah_pressed: bool) -> Optional[bool]:
        """
        Determine next element to send using Iambic Mode B logic.

        Args:
            dit_pressed: Current dit paddle state
            dah_pressed: Current dah paddle state

        Returns:
            True for dit, False for dah, None for no element
        """
        both_pressed = dit_pressed and dah_pressed

        # Update squeeze memory
        if both_pressed:
            self._squeeze_memory = True

        # Case 1: Both paddles pressed (squeeze) - alternate
        if both_pressed:
            # Alternate based on what we sent last
            return not self._last_was_dit

        # Case 2: Squeeze memory active - send one more alternating element
        if self._squeeze_memory and (dit_pressed or dah_pressed):
            self._squeeze_memory = False  # Clear after using
            # Send the opposite of what the current paddle would send
            if dit_pressed:
                # Dit is pressed, but we had squeeze, so send dah if last was dit
                return False if self._last_was_dit else True
            else:
                # Dah is pressed, but we had squeeze, so send dit if last was dah
                return True if not self._last_was_dit else False

        # Clear squeeze memory if no paddles pressed
        if not dit_pressed and not dah_pressed:
            self._squeeze_memory = False
            return None

        # Case 3: Single paddle pressed - send that element
        if dit_pressed:
            return True
        if dah_pressed:
            return False

        return None

    def is_running(self) -> bool:
        """Check if the keyer is running."""
        return self._running

    def __enter__(self) -> "IambicKeyer":
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.stop()
