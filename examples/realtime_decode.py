#!/usr/bin/env python3
"""
Real-time decoding example with both raw and decoded output.

This example shows how to display both the raw dit/dah stream
and the decoded characters simultaneously.
"""

import time
from vband import VBandConfig, DecodedStream, PaddleType
from vband.decoder import CWElement


def main():
    """Main function."""
    # Create configuration for straight key mode
    config = VBandConfig(
        paddle_type=PaddleType.DUAL_PADDLE,
        auto_wpm=True,
        char_space_threshold=3.0,
        word_space_threshold=7.0,
    )
    config.set_wpm(15)  # Start at 15 WPM

    print("VBAND Real-Time Decoder")
    print(f"Paddle Type: {config.paddle_type.value}")
    print(f"Initial Speed: {config.current_wpm} WPM")
    print("\nReady to receive CW input (Ctrl+C to exit)...")
    print("=" * 50)
    print()

    # Buffer for current morse sequence
    current_morse = []

    def on_element(element: CWElement):
        """Handle CW element (dit or dah)."""
        morse_char = element.to_morse()
        current_morse.append(morse_char)
        print(morse_char, end="", flush=True)

    def on_character(char: str):
        """Handle decoded character."""
        # Clear the morse buffer
        current_morse.clear()

        # Handle spaces
        if char == " ":
            print(" / ", end="", flush=True)
        else:
            print(f" = {char}  ", end="", flush=True)

        # Show current WPM if auto-adjust is enabled
        if config.auto_wpm:
            wpm = config.current_wpm
            if wpm != 15:  # Only show if changed from initial
                print(f"[{wpm} WPM] ", end="", flush=True)

    # Create and start decoded stream with both callbacks
    with DecodedStream(
        config=config, char_callback=on_character, element_callback=on_element
    ) as stream:
        try:
            # Keep running until interrupted
            while stream.is_running():
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n\nStopping...")

    print("\nDone!")


if __name__ == "__main__":
    main()
