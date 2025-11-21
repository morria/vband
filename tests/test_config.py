"""Tests for configuration module."""

import pytest
from vband.config import VBandConfig, PaddleType


class TestVBandConfig:
    """Test VBandConfig class."""

    def test_default_config(self):
        """Test default configuration values."""
        config = VBandConfig()
        assert config.paddle_type == PaddleType.IAMBIC_B
        assert config.auto_wpm is True
        assert config.dit_duration == 0.06
        assert config.debounce_time == 0.005

    def test_wpm_conversion(self):
        """Test WPM to dit duration conversion."""
        config = VBandConfig()

        # Test standard conversions
        assert config.wpm_to_dit_duration(20) == pytest.approx(0.06, rel=1e-3)
        assert config.wpm_to_dit_duration(10) == pytest.approx(0.12, rel=1e-3)
        assert config.wpm_to_dit_duration(30) == pytest.approx(0.04, rel=1e-3)

        # Test reverse conversion
        assert config.dit_duration_to_wpm(0.06) == 20
        assert config.dit_duration_to_wpm(0.12) == 10
        assert config.dit_duration_to_wpm(0.04) == 30

    def test_set_wpm(self):
        """Test setting WPM."""
        config = VBandConfig()
        config.set_wpm(25)

        assert config.current_wpm == 25
        assert config.target_wpm == 25
        assert config.dit_duration == pytest.approx(0.048, rel=1e-3)

    def test_spacing_durations(self):
        """Test character and word spacing calculations."""
        config = VBandConfig()
        config.set_wpm(20)  # 0.06s dit duration

        # Default thresholds: 3x for char, 7x for word
        assert config.char_space_duration == pytest.approx(0.18, rel=1e-3)
        assert config.word_space_duration == pytest.approx(0.42, rel=1e-3)

    def test_custom_thresholds(self):
        """Test custom spacing thresholds."""
        config = VBandConfig(
            char_space_threshold=2.5,
            word_space_threshold=6.0,
        )
        config.set_wpm(20)

        assert config.char_space_duration == pytest.approx(0.15, rel=1e-3)
        assert config.word_space_duration == pytest.approx(0.36, rel=1e-3)

    def test_paddle_types(self):
        """Test all paddle type configurations."""
        for paddle_type in PaddleType:
            config = VBandConfig(paddle_type=paddle_type)
            assert config.paddle_type == paddle_type
