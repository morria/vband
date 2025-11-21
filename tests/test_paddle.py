"""Tests for paddle interface module."""

import pytest
import time
from vband.paddle import PaddleInterface, PaddleEvent
from vband.config import VBandConfig, PaddleType


class TestPaddleEvent:
    """Test PaddleEvent class."""

    def test_dit_event(self):
        """Test creating a dit event."""
        event = PaddleEvent(is_dit=True, is_pressed=True, timestamp=1.0)
        assert event.is_dit is True
        assert event.is_pressed is True
        assert event.timestamp == 1.0

    def test_dah_event(self):
        """Test creating a dah event."""
        event = PaddleEvent(is_dit=False, is_pressed=False, timestamp=2.0)
        assert event.is_dit is False
        assert event.is_pressed is False
        assert event.timestamp == 2.0

    def test_event_repr(self):
        """Test event string representation."""
        event = PaddleEvent(is_dit=True, is_pressed=True, timestamp=1.234)
        repr_str = repr(event)
        assert "DIT" in repr_str
        assert "DOWN" in repr_str
        assert "1.234" in repr_str


class TestPaddleInterface:
    """Test PaddleInterface class."""

    def test_initialization(self):
        """Test paddle interface initialization."""
        paddle = PaddleInterface()
        assert paddle.is_running() is False
        assert paddle.config is not None

    def test_custom_config(self):
        """Test initialization with custom config."""
        config = VBandConfig(paddle_type=PaddleType.STRAIGHT_KEY)
        paddle = PaddleInterface(config)
        assert paddle.config.paddle_type == PaddleType.STRAIGHT_KEY

    def test_get_state(self):
        """Test getting paddle state."""
        paddle = PaddleInterface()
        dit_state, dah_state = paddle.get_state()
        assert dit_state is False
        assert dah_state is False

    def test_context_manager(self):
        """Test using paddle as context manager."""
        config = VBandConfig()
        with PaddleInterface(config) as paddle:
            # Note: We can't actually test keyboard input in unit tests
            # but we can verify the interface is running
            assert paddle.is_running() is True

        # Should be stopped after context exit
        assert paddle.is_running() is False

    def test_start_stop(self):
        """Test starting and stopping the interface."""
        paddle = PaddleInterface()

        assert paddle.is_running() is False

        paddle.start()
        assert paddle.is_running() is True

        paddle.stop()
        assert paddle.is_running() is False

    def test_get_event_timeout(self):
        """Test getting event with timeout."""
        paddle = PaddleInterface()
        paddle.start()

        # Should timeout since no actual keyboard input
        event = paddle.get_event(timeout=0.1)
        assert event is None

        paddle.stop()

    def test_double_start(self):
        """Test that double start is safe."""
        paddle = PaddleInterface()
        paddle.start()
        paddle.start()  # Should not cause issues
        assert paddle.is_running() is True
        paddle.stop()

    def test_double_stop(self):
        """Test that double stop is safe."""
        paddle = PaddleInterface()
        paddle.start()
        paddle.stop()
        paddle.stop()  # Should not cause issues
        assert paddle.is_running() is False

    def test_iambic_mode_has_keyer(self):
        """Test that iambic mode B creates a keyer."""
        config = VBandConfig(paddle_type=PaddleType.IAMBIC_B)
        paddle = PaddleInterface(config)
        assert paddle.has_keyer() is True

    def test_dual_paddle_no_keyer(self):
        """Test that dual paddle mode does not create a keyer."""
        config = VBandConfig(paddle_type=PaddleType.DUAL_PADDLE)
        paddle = PaddleInterface(config)
        assert paddle.has_keyer() is False

    def test_get_keyed_element_without_keyer(self):
        """Test that getting keyed element without keyer raises error."""
        config = VBandConfig(paddle_type=PaddleType.DUAL_PADDLE)
        paddle = PaddleInterface(config)
        with pytest.raises(RuntimeError):
            paddle.get_keyed_element(timeout=0.1)

    def test_keyer_starts_with_paddle(self):
        """Test that keyer starts when paddle starts in iambic mode."""
        config = VBandConfig(paddle_type=PaddleType.IAMBIC_B)
        paddle = PaddleInterface(config)

        paddle.start()
        assert paddle.has_keyer() is True
        # Keyer should be running when paddle is running
        assert paddle.is_running() is True

        paddle.stop()
        assert paddle.is_running() is False
