"""Tests for decoder module."""

import pytest
import time
from vband.decoder import CWDecoder, MorseDecoder, CWElement, MORSE_CODE
from vband.paddle import PaddleEvent
from vband.config import VBandConfig


class TestCWElement:
    """Test CWElement class."""

    def test_dit_creation(self):
        """Test creating a dit element."""
        element = CWElement(is_dit=True, duration=0.06, timestamp=1.0)
        assert element.is_dit is True
        assert element.duration == 0.06
        assert element.timestamp == 1.0
        assert element.to_morse() == "."

    def test_dah_creation(self):
        """Test creating a dah element."""
        element = CWElement(is_dit=False, duration=0.18, timestamp=1.0)
        assert element.is_dit is False
        assert element.duration == 0.18
        assert element.timestamp == 1.0
        assert element.to_morse() == "-"


class TestCWDecoder:
    """Test CWDecoder class."""

    def test_dit_decode(self):
        """Test decoding a dit."""
        decoder = CWDecoder()

        # Key down
        event_down = PaddleEvent(is_dit=True, is_pressed=True, timestamp=1.0)
        result = decoder.process_event(event_down)
        assert result is None

        # Key up after 60ms
        event_up = PaddleEvent(is_dit=True, is_pressed=False, timestamp=1.06)
        result = decoder.process_event(event_up)

        assert result is not None
        assert result.is_dit is True
        assert result.duration == pytest.approx(0.06, rel=1e-3)

    def test_dah_decode(self):
        """Test decoding a dah."""
        decoder = CWDecoder()

        # Key down
        event_down = PaddleEvent(is_dit=False, is_pressed=True, timestamp=1.0)
        result = decoder.process_event(event_down)
        assert result is None

        # Key up after 180ms (3x dit)
        event_up = PaddleEvent(is_dit=False, is_pressed=False, timestamp=1.18)
        result = decoder.process_event(event_up)

        assert result is not None
        assert result.is_dit is False
        assert result.duration == pytest.approx(0.18, rel=1e-3)

    def test_multiple_elements(self):
        """Test decoding multiple elements in sequence."""
        decoder = CWDecoder()
        elements = []

        # Dit
        decoder.process_event(PaddleEvent(True, True, 1.0))
        result = decoder.process_event(PaddleEvent(True, False, 1.06))
        if result:
            elements.append(result)

        # Dah
        decoder.process_event(PaddleEvent(False, True, 1.2))
        result = decoder.process_event(PaddleEvent(False, False, 1.38))
        if result:
            elements.append(result)

        # Dit
        decoder.process_event(PaddleEvent(True, True, 1.5))
        result = decoder.process_event(PaddleEvent(True, False, 1.56))
        if result:
            elements.append(result)

        assert len(elements) == 3
        assert elements[0].is_dit is True
        assert elements[1].is_dit is False
        assert elements[2].is_dit is True


class TestMorseDecoder:
    """Test MorseDecoder class."""

    def test_single_character(self):
        """Test decoding a single character (E = .)."""
        config = VBandConfig()
        config.set_wpm(20)
        decoder = MorseDecoder(config)

        # Single dit for 'E'
        element = CWElement(is_dit=True, duration=0.06, timestamp=1.0)
        result = decoder.process_element(element, current_time=1.06)
        assert result is None  # Character not complete yet

        # Flush after character spacing
        result = decoder.flush(current_time=1.06 + config.char_space_duration)
        assert result == "E"

    def test_multi_element_character(self):
        """Test decoding multi-element character (A = .-)."""
        config = VBandConfig()
        config.set_wpm(20)
        decoder = MorseDecoder(config)

        # Dit
        element1 = CWElement(is_dit=True, duration=0.06, timestamp=1.0)
        result = decoder.process_element(element1, current_time=1.06)
        assert result is None

        # Dah (within character spacing)
        element2 = CWElement(is_dit=False, duration=0.18, timestamp=1.12)
        result = decoder.process_element(element2, current_time=1.30)
        assert result is None

        # Flush to get character
        result = decoder.flush(current_time=1.30 + config.char_space_duration)
        assert result == "A"

    def test_word_spacing(self):
        """Test word spacing detection."""
        config = VBandConfig()
        config.set_wpm(20)
        decoder = MorseDecoder(config)

        # First character: E (.)
        element1 = CWElement(is_dit=True, duration=0.06, timestamp=1.0)
        result = decoder.process_element(element1, current_time=1.06)
        assert result is None

        # Second character after word space: T (-)
        element2 = CWElement(
            is_dit=False,
            duration=0.18,
            timestamp=1.0 + config.word_space_duration + 0.1,
        )
        result = decoder.process_element(element2, current_time=element2.timestamp + 0.18)

        # Should return 'E' + space
        assert result == "E "

    def test_morse_code_table(self):
        """Test that morse code table is complete."""
        # Check some common characters
        assert MORSE_CODE[".-"] == "A"
        assert MORSE_CODE["-..."] == "B"
        assert MORSE_CODE["."] == "E"
        assert MORSE_CODE["-"] == "T"

        # Check numbers
        assert MORSE_CODE[".----"] == "1"
        assert MORSE_CODE["-----"] == "0"

        # Check punctuation
        assert MORSE_CODE[".-.-.-"] == "."
        assert MORSE_CODE["--..--"] == ","

    def test_invalid_morse(self):
        """Test handling of invalid morse sequences."""
        config = VBandConfig()
        decoder = MorseDecoder(config)

        # Create invalid sequence
        element1 = CWElement(is_dit=True, duration=0.06, timestamp=1.0)
        decoder.process_element(element1)
        element2 = CWElement(is_dit=True, duration=0.06, timestamp=1.1)
        decoder.process_element(element2)
        element3 = CWElement(is_dit=True, duration=0.06, timestamp=1.2)
        decoder.process_element(element3)
        element4 = CWElement(is_dit=True, duration=0.06, timestamp=1.3)
        decoder.process_element(element4)
        element5 = CWElement(is_dit=True, duration=0.06, timestamp=1.4)
        decoder.process_element(element5)
        element6 = CWElement(is_dit=True, duration=0.06, timestamp=1.5)
        decoder.process_element(element6)

        result = decoder.flush(current_time=2.0)
        # Should return unknown sequence in brackets
        assert result.startswith("<") and result.endswith(">")

    def test_reset(self):
        """Test decoder reset functionality."""
        decoder = MorseDecoder()

        # Add some elements
        element = CWElement(is_dit=True, duration=0.06, timestamp=1.0)
        decoder.process_element(element)

        # Reset
        decoder.reset()

        # Should have no pending character
        result = decoder.flush(current_time=10.0)
        assert result is None
