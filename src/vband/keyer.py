"""Iambic keyer module for automatic dit/dah generation."""

import time
import threading
from typing import Optional, Tuple, Callable
from queue import Queue, Empty
from .decoder import CWElement, SpaceMarkPair
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


class SpaceMarkKeyer:
    """
    Space/Mark keyer that generates timing pairs for near real-time decoding.

    This keyer implements the same state machine as the vband.org reference
    implementation, outputting (space, mark) pairs that can be decoded in real-time.
    """

    # Keyer states
    STATE_IDLE = 0
    STATE_MARK = 1
    STATE_INTER_ELEMENT = 2

    def __init__(self, config: Optional[VBandConfig] = None):
        """
        Initialize space/mark keyer.

        Args:
            config: Configuration object, uses defaults if None
        """
        self.config = config or VBandConfig()
        self._running = False
        self._thread: Optional[threading.Thread] = None

        # Paddle state
        self._dit_pressed = False
        self._dah_pressed = False
        self._state_lock = threading.Lock()

        # Keyer state machine
        self._state = self.STATE_IDLE
        self._start_time = 0.0  # Time when current state started
        self._cur_paddle = 0  # 0=DIT, 1=DAH
        self._paddle_memory = [False, False]  # Memory for iambic modes

        # Timing
        self._timer: Optional[threading.Timer] = None
        self._timer_lock = threading.Lock()

        # Output queue
        self._pair_queue: Queue[SpaceMarkPair] = Queue()

        # Bug mode state
        self._bug_dit_mode = 0  # 0=OFF, 1=MARK, 2=SPACE
        self._straight_sending = False
        self._straight_space_time = 0.0

        # Timeout timer to reset paddle state
        self._timeout_timer: Optional[threading.Timer] = None

    def start(self) -> None:
        """Start the keyer thread."""
        if self._running:
            return

        self._running = True
        self._start_time = self._get_ms()
        self._thread = threading.Thread(target=self._keyer_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the keyer thread."""
        if not self._running:
            return

        self._running = False
        self._cancel_timer()
        self._cancel_timeout()

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
            # Handle mode-specific logic
            DIT = 0
            DAH = 1

            # Update memory on press
            if not self._dit_pressed and dit_pressed:
                if self.config.paddle_type == PaddleType.IAMBIC_A:
                    # In ultimatic mode, current is latest pressed
                    self._cur_paddle = DIT
                self._paddle_memory[DIT] = True
                self._reset_timeout()

            if not self._dah_pressed and dah_pressed:
                if self.config.paddle_type == PaddleType.IAMBIC_A:
                    self._cur_paddle = DAH
                self._paddle_memory[DAH] = True
                self._reset_timeout()

            self._dit_pressed = dit_pressed
            self._dah_pressed = dah_pressed

    def get_space_mark_pair(self, timeout: Optional[float] = None) -> Optional[SpaceMarkPair]:
        """
        Get the next space/mark pair.

        Args:
            timeout: Maximum time to wait in seconds, None for blocking

        Returns:
            SpaceMarkPair or None if timeout
        """
        try:
            return self._pair_queue.get(timeout=timeout)
        except Empty:
            return None

    def _get_ms(self) -> float:
        """Get current time in milliseconds."""
        return time.time() * 1000.0

    def _keyer_loop(self) -> None:
        """Main keyer loop."""
        while self._running:
            self._update()
            time.sleep(0.001)  # 1ms update rate

    def _update(self) -> None:
        """Update keyer state machine."""
        # Get dit duration in ms
        dit_length = self.config.dit_duration * 1000.0

        # Handle different paddle modes
        if self.config.paddle_type == PaddleType.STRAIGHT_KEY:
            self._update_straight_key()
            return
        elif self.config.paddle_type == PaddleType.DUAL_PADDLE:
            # Dual paddle is like bug mode
            self._update_bug(dit_length)
            return

        # Iambic modes (A and B)
        with self._state_lock:
            dit_pressed = self._dit_pressed
            dah_pressed = self._dah_pressed
            state = self._state

        # Wait for timer if running
        if self._is_timer_running():
            return

        DIT = 0
        DAH = 1

        if state == self.STATE_MARK:
            # Mark completed, transition to inter-element space
            self._state = self.STATE_INTER_ELEMENT
            self._start_time = self._get_ms()
            self._start_timer(dit_length)

        else:
            # In inter-element or idle state
            if self.config.paddle_type == PaddleType.IAMBIC_B and state == self.STATE_INTER_ELEMENT:
                # Reset paddle memory based on mode
                self._paddle_memory[self._cur_paddle] = self._dit_pressed if self._cur_paddle == DIT else self._dah_pressed

            # Check for next element
            for _ in range(2):
                # For iambic modes, alternate
                if self.config.paddle_type != PaddleType.IAMBIC_A:
                    self._cur_paddle = 1 - self._cur_paddle

                if self._paddle_memory[self._cur_paddle] or (
                    self._dit_pressed if self._cur_paddle == DIT else self._dah_pressed
                ):
                    # Clear memory for ultimatic mode
                    if self.config.paddle_type == PaddleType.IAMBIC_A:
                        self._paddle_memory[self._cur_paddle] = False

                    # Generate mark
                    mark_duration = dit_length if self._cur_paddle == DIT else dit_length * 3.0
                    self._state = self.STATE_MARK

                    # Output space/mark pair
                    space_duration = self._get_ms() - self._start_time
                    pair = SpaceMarkPair(space_duration, mark_duration)
                    self._pair_queue.put(pair)

                    self._start_time = self._get_ms()
                    self._start_timer(mark_duration)
                    break

                # For ultimatic, only look at other side if current not pressed
                if self.config.paddle_type == PaddleType.IAMBIC_A:
                    self._cur_paddle = 1 - self._cur_paddle

            # If no mark generated, go idle
            if self._state != self.STATE_MARK:
                self._state = self.STATE_IDLE

    def _update_straight_key(self) -> None:
        """Update straight key mode."""
        with self._state_lock:
            pressed = self._dit_pressed or self._dah_pressed

        if pressed != self._straight_sending:
            last_time = self._get_ms() - self._start_time
            self._straight_sending = pressed
            self._start_time = self._get_ms()

            if pressed:
                self._straight_space_time = last_time
            else:
                # Output space/mark pair
                pair = SpaceMarkPair(self._straight_space_time, last_time)
                self._pair_queue.put(pair)

    def _update_bug(self, dit_length: float) -> None:
        """Update bug mode (automatic dits, manual dahs)."""
        BUG_DIT_OFF = 0
        BUG_DIT_MARK = 1
        BUG_DIT_SPACE = 2

        with self._state_lock:
            dit_pressed = self._dit_pressed
            dah_pressed = self._dah_pressed

        # Handle automatic dits
        if not dit_pressed:
            self._bug_dit_mode = BUG_DIT_OFF
        else:
            if not self._is_timer_running():
                self._start_timer(dit_length)
                if self._bug_dit_mode == BUG_DIT_MARK:
                    self._bug_dit_mode = BUG_DIT_SPACE
                else:
                    self._bug_dit_mode = BUG_DIT_MARK
            else:
                if self._bug_dit_mode == BUG_DIT_OFF:
                    self._bug_dit_mode = BUG_DIT_MARK

        # Use straight key logic with automatic dit state
        auto_pressed = self._bug_dit_mode == BUG_DIT_MARK or dah_pressed
        if auto_pressed != self._straight_sending:
            last_time = self._get_ms() - self._start_time
            self._straight_sending = auto_pressed
            self._start_time = self._get_ms()

            if auto_pressed:
                self._straight_space_time = last_time
            else:
                # Output space/mark pair
                pair = SpaceMarkPair(self._straight_space_time, last_time)
                self._pair_queue.put(pair)

    def _start_timer(self, duration_ms: float) -> None:
        """Start the keyer timer."""
        with self._timer_lock:
            if self._timer is not None:
                return  # Timer already running

            self._timer = threading.Timer(
                duration_ms / 1000.0,
                self._timer_expired
            )
            self._timer.daemon = True
            self._timer.start()

    def _timer_expired(self) -> None:
        """Callback when timer expires."""
        with self._timer_lock:
            self._timer = None

    def _is_timer_running(self) -> bool:
        """Check if timer is running."""
        with self._timer_lock:
            return self._timer is not None

    def _cancel_timer(self) -> None:
        """Cancel the current timer."""
        with self._timer_lock:
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None

    def _reset_timeout(self) -> None:
        """Reset the paddle timeout timer."""
        # Cancel existing timeout
        if self._timeout_timer is not None:
            self._timeout_timer.cancel()

        # Start new timeout (5 seconds)
        self._timeout_timer = threading.Timer(5.0, self._timeout_expired)
        self._timeout_timer.daemon = True
        self._timeout_timer.start()

    def _timeout_expired(self) -> None:
        """Callback when timeout expires - reset paddle state."""
        with self._state_lock:
            self._dit_pressed = False
            self._dah_pressed = False
        self._timeout_timer = None

    def _cancel_timeout(self) -> None:
        """Cancel the timeout timer."""
        if self._timeout_timer is not None:
            self._timeout_timer.cancel()
            self._timeout_timer = None

    def is_running(self) -> bool:
        """Check if the keyer is running."""
        return self._running

    def __enter__(self) -> "SpaceMarkKeyer":
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.stop()
