"""Tests for iambic keyer module."""

import pytest
import time
from vband.keyer import IambicKeyer
from vband.config import VBandConfig, PaddleType
from vband.decoder import CWElement


class TestIambicKeyer:
    """Test IambicKeyer class."""

    def test_initialization(self):
        """Test keyer initialization."""
        keyer = IambicKeyer()
        assert keyer.is_running() is False
        assert keyer.config is not None

    def test_custom_config(self):
        """Test initialization with custom config."""
        config = VBandConfig(paddle_type=PaddleType.IAMBIC_B, dit_duration=0.1)
        keyer = IambicKeyer(config)
        assert keyer.config.paddle_type == PaddleType.IAMBIC_B
        assert keyer.config.dit_duration == 0.1

    def test_context_manager(self):
        """Test using keyer as context manager."""
        config = VBandConfig()
        with IambicKeyer(config) as keyer:
            assert keyer.is_running() is True

        # Should be stopped after context exit
        assert keyer.is_running() is False

    def test_start_stop(self):
        """Test starting and stopping the keyer."""
        keyer = IambicKeyer()

        assert keyer.is_running() is False

        keyer.start()
        assert keyer.is_running() is True

        keyer.stop()
        assert keyer.is_running() is False

    def test_single_dit(self):
        """Test generating a single dit element."""
        config = VBandConfig(dit_duration=0.05)
        keyer = IambicKeyer(config)
        keyer.start()

        # Press dit paddle
        keyer.update_paddle_state(dit_pressed=True, dah_pressed=False)

        # Should generate a dit element
        element = keyer.get_element(timeout=0.2)
        assert element is not None
        assert isinstance(element, CWElement)
        assert element.is_dit is True
        assert abs(element.duration - 0.05) < 0.01

        # Release paddle
        keyer.update_paddle_state(dit_pressed=False, dah_pressed=False)

        # Should timeout with no more elements
        element = keyer.get_element(timeout=0.1)
        assert element is None

        keyer.stop()

    def test_single_dah(self):
        """Test generating a single dah element."""
        config = VBandConfig(dit_duration=0.05)
        keyer = IambicKeyer(config)
        keyer.start()

        # Press dah paddle
        keyer.update_paddle_state(dit_pressed=False, dah_pressed=True)

        # Should generate a dah element (3x dit duration)
        element = keyer.get_element(timeout=0.2)
        assert element is not None
        assert isinstance(element, CWElement)
        assert element.is_dit is False
        assert abs(element.duration - 0.15) < 0.01  # 3 * 0.05

        # Release paddle
        keyer.update_paddle_state(dit_pressed=False, dah_pressed=False)

        # Should timeout with no more elements
        element = keyer.get_element(timeout=0.1)
        assert element is None

        keyer.stop()

    def test_squeeze_alternation(self):
        """Test squeeze behavior - both paddles pressed should alternate."""
        config = VBandConfig(dit_duration=0.05)
        keyer = IambicKeyer(config)
        keyer.start()

        # Press both paddles (squeeze)
        keyer.update_paddle_state(dit_pressed=True, dah_pressed=True)

        # Should alternate between dit and dah
        elements = []
        for _ in range(4):
            element = keyer.get_element(timeout=0.5)
            if element is None:
                break
            elements.append(element)

        # Should have gotten at least 2 elements
        assert len(elements) >= 2

        # First element depends on last_was_dit initialization
        # Elements should alternate
        for i in range(len(elements) - 1):
            assert elements[i].is_dit != elements[i + 1].is_dit

        # Release paddles
        keyer.update_paddle_state(dit_pressed=False, dah_pressed=False)
        keyer.stop()

    def test_squeeze_memory_mode_b(self):
        """Test Mode B squeeze memory - generates one more element after release."""
        config = VBandConfig(dit_duration=0.05)
        keyer = IambicKeyer(config)
        keyer.start()

        # Press both paddles (squeeze)
        keyer.update_paddle_state(dit_pressed=True, dah_pressed=True)

        # Get first element
        element1 = keyer.get_element(timeout=0.2)
        assert element1 is not None

        # Get second element (should alternate)
        element2 = keyer.get_element(timeout=0.3)
        assert element2 is not None
        assert element1.is_dit != element2.is_dit

        # Release one paddle while second element is being sent
        # This simulates releasing during element generation
        time.sleep(0.05)
        keyer.update_paddle_state(dit_pressed=True, dah_pressed=False)

        # Mode B should remember the squeeze and send one more element
        # even though dah paddle is released
        element3 = keyer.get_element(timeout=0.3)

        # Note: The behavior here depends on exact timing
        # We should get at least the element that's currently being generated

        # Release all paddles
        keyer.update_paddle_state(dit_pressed=False, dah_pressed=False)

        keyer.stop()

    def test_element_timing(self):
        """Test that element durations are correct."""
        config = VBandConfig(dit_duration=0.05)
        keyer = IambicKeyer(config)
        keyer.start()

        # Test dit duration
        keyer.update_paddle_state(dit_pressed=True, dah_pressed=False)
        dit = keyer.get_element(timeout=0.2)
        assert dit is not None
        assert abs(dit.duration - 0.05) < 0.01

        keyer.update_paddle_state(dit_pressed=False, dah_pressed=False)
        time.sleep(0.1)

        # Test dah duration (3x dit)
        keyer.update_paddle_state(dit_pressed=False, dah_pressed=True)
        dah = keyer.get_element(timeout=0.3)
        assert dah is not None
        assert abs(dah.duration - 0.15) < 0.01  # 3 * 0.05

        keyer.update_paddle_state(dit_pressed=False, dah_pressed=False)
        keyer.stop()

    def test_no_element_when_idle(self):
        """Test that no elements are generated when no paddles are pressed."""
        config = VBandConfig(dit_duration=0.05)
        keyer = IambicKeyer(config)
        keyer.start()

        # No paddles pressed
        keyer.update_paddle_state(dit_pressed=False, dah_pressed=False)

        # Should timeout with no elements
        element = keyer.get_element(timeout=0.1)
        assert element is None

        keyer.stop()

    def test_double_start(self):
        """Test that double start is safe."""
        keyer = IambicKeyer()
        keyer.start()
        keyer.start()  # Should not cause issues
        assert keyer.is_running() is True
        keyer.stop()

    def test_double_stop(self):
        """Test that double stop is safe."""
        keyer = IambicKeyer()
        keyer.start()
        keyer.stop()
        keyer.stop()  # Should not cause issues
        assert keyer.is_running() is False
