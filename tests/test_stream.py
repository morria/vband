"""Tests for stream module."""

import pytest
import time
from vband.stream import CWStream, DecodedStream
from vband.decoder import CWElement
from vband.config import VBandConfig, PaddleType


class TestCWStream:
    """Test CWStream class."""

    def test_initialization(self):
        """Test CW stream initialization."""
        stream = CWStream()
        assert stream.is_running() is False
        assert stream.config is not None
        assert stream.paddle is not None
        assert stream.decoder is not None

    def test_custom_config(self):
        """Test initialization with custom config."""
        config = VBandConfig(paddle_type=PaddleType.STRAIGHT_KEY)
        stream = CWStream(config)
        assert stream.config.paddle_type == PaddleType.STRAIGHT_KEY

    def test_callback(self):
        """Test stream with callback."""
        elements = []

        def callback(element: CWElement):
            elements.append(element)

        stream = CWStream(callback=callback)
        assert stream.callback is not None

    def test_start_stop(self):
        """Test starting and stopping the stream."""
        stream = CWStream()

        assert stream.is_running() is False

        stream.start()
        assert stream.is_running() is True

        # Give it a moment to initialize
        time.sleep(0.1)

        stream.stop()
        assert stream.is_running() is False

    def test_context_manager(self):
        """Test using stream as context manager."""
        with CWStream() as stream:
            assert stream.is_running() is True

        assert stream.is_running() is False

    def test_double_start(self):
        """Test that double start is safe."""
        stream = CWStream()
        stream.start()
        stream.start()  # Should not cause issues
        assert stream.is_running() is True
        stream.stop()

    def test_double_stop(self):
        """Test that double stop is safe."""
        stream = CWStream()
        stream.start()
        stream.stop()
        stream.stop()  # Should not cause issues
        assert stream.is_running() is False


class TestDecodedStream:
    """Test DecodedStream class."""

    def test_initialization(self):
        """Test decoded stream initialization."""
        stream = DecodedStream()
        assert stream.is_running() is False
        assert stream.config is not None
        assert stream.paddle is not None
        assert stream.cw_decoder is not None
        assert stream.morse_decoder is not None

    def test_custom_config(self):
        """Test initialization with custom config."""
        config = VBandConfig(paddle_type=PaddleType.IAMBIC_A)
        stream = DecodedStream(config)
        assert stream.config.paddle_type == PaddleType.IAMBIC_A

    def test_char_callback(self):
        """Test stream with character callback."""
        chars = []

        def char_callback(char: str):
            chars.append(char)

        stream = DecodedStream(char_callback=char_callback)
        assert stream.char_callback is not None

    def test_element_callback(self):
        """Test stream with element callback."""
        elements = []

        def element_callback(element: CWElement):
            elements.append(element)

        stream = DecodedStream(element_callback=element_callback)
        assert stream.element_callback is not None

    def test_both_callbacks(self):
        """Test stream with both callbacks."""
        chars = []
        elements = []

        def char_callback(char: str):
            chars.append(char)

        def element_callback(element: CWElement):
            elements.append(element)

        stream = DecodedStream(
            char_callback=char_callback,
            element_callback=element_callback,
        )
        assert stream.char_callback is not None
        assert stream.element_callback is not None

    def test_start_stop(self):
        """Test starting and stopping the decoded stream."""
        stream = DecodedStream()

        assert stream.is_running() is False

        stream.start()
        assert stream.is_running() is True

        # Give it a moment to initialize
        time.sleep(0.1)

        stream.stop()
        assert stream.is_running() is False

    def test_context_manager(self):
        """Test using decoded stream as context manager."""
        with DecodedStream() as stream:
            assert stream.is_running() is True

        assert stream.is_running() is False

    def test_double_start(self):
        """Test that double start is safe."""
        stream = DecodedStream()
        stream.start()
        stream.start()  # Should not cause issues
        assert stream.is_running() is True
        stream.stop()

    def test_double_stop(self):
        """Test that double stop is safe."""
        stream = DecodedStream()
        stream.start()
        stream.stop()
        stream.stop()  # Should not cause issues
        assert stream.is_running() is False
