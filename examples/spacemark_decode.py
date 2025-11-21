#!/usr/bin/env python3
"""
Near Real-Time CW Decoding Example using Space/Mark Architecture

This example demonstrates the vband.org reference implementation's
space/mark decoding approach, which provides near real-time character
decoding with adaptive WPM detection.

The SpaceMarkStream processes timing pairs directly from the keyer,
allowing immediate decoding with aggressive adaptive learning.
"""

import time
from vband import VBandConfig, SpaceMarkStream, PaddleType


def print_char(char: str) -> None:
    """Print decoded character."""
    print(char, end="", flush=True)


def main():
    """Run the near real-time decoder."""
    # Create configuration
    config = VBandConfig(
        paddle_type=PaddleType.IAMBIC_B,
        auto_wpm=True,  # Adaptive WPM detection
    )

    # Set initial WPM (will adapt automatically)
    config.set_wpm(20)

    print("VBAND Near Real-Time CW Decoder")
    print("=" * 50)
    print(f"Mode: {config.paddle_type.value}")
    print(f"Initial WPM: {config.current_wpm}")
    print(f"Adaptive WPM: {config.auto_wpm}")
    print()
    print("Press Left Ctrl = Dit, Right Ctrl = Dah")
    print("Press Ctrl+C to exit")
    print("=" * 50)
    print()

    # Create and start the space/mark stream
    with SpaceMarkStream(config=config, char_callback=print_char) as stream:
        try:
            while stream.is_running():
                time.sleep(0.5)

                # Periodically show WPM
                wpm = stream.get_wpm()
                dit_ms = stream.get_dit_length_ms()
                print(f"\r[{wpm} | Dit: {dit_ms:.1f}ms]", end="", flush=True)
                time.sleep(0.5)
                print("\r" + " " * 50 + "\r", end="", flush=True)

        except KeyboardInterrupt:
            print("\n\n" + "=" * 50)
            print("Session complete!")
            print(f"Final WPM: {stream.get_wpm()}")
            print(f"Decoded text:\n{stream.get_text()}")
            print("=" * 50)


if __name__ == "__main__":
    main()
