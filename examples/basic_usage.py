#!/usr/bin/env python3
"""
Basic usage example for VBAND package.

This example shows how to use the VBAND package to decode
morse code from a USB paddle interface.
"""

import time
from vband import VBandConfig, DecodedStream, PaddleType


def main():
    """Main function."""
    # Create configuration
    config = VBandConfig(
        paddle_type=PaddleType.IAMBIC_B,  # Use iambic mode B
        auto_wpm=True,  # Automatically adjust to operator speed
    )
    config.set_wpm(20)  # Start at 20 WPM

    print("VBAND Basic Usage Example")
    print(f"Paddle Type: {config.paddle_type.value}")
    print(f"Speed: {config.current_wpm} WPM")
    print(f"Auto-WPM: {config.auto_wpm}")
    print("\nReady to receive CW input (Ctrl+C to exit)...")
    print("=" * 50)
    print()

    # Define callback function for decoded characters
    def on_character(char: str):
        print(char, end="", flush=True)

    # Create and start decoded stream
    with DecodedStream(config=config, char_callback=on_character) as stream:
        try:
            # Keep running until interrupted
            while stream.is_running():
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n\nStopping...")

    print("Done!")


if __name__ == "__main__":
    main()
