#!/usr/bin/env python3
"""
Raw CW stream example.

This example shows how to access the raw dit/dah stream
without character decoding.
"""

import time
from vband import VBandConfig, CWStream, PaddleType
from vband.decoder import CWElement


def main():
    """Main function."""
    # Create configuration
    config = VBandConfig(
        paddle_type=PaddleType.IAMBIC_A,
        auto_wpm=False,  # Use fixed WPM
    )
    config.set_wpm(25)  # 25 WPM

    print("VBAND Raw CW Stream Example")
    print(f"Paddle Type: {config.paddle_type.value}")
    print(f"Speed: {config.current_wpm} WPM (fixed)")
    print(f"Dit Duration: {config.dit_duration * 1000:.1f}ms")
    print("\nReady to receive CW input (Ctrl+C to exit)...")
    print("=" * 50)
    print()

    def on_element(element: CWElement):
        """Handle CW element."""
        element_type = "DIT" if element.is_dit else "DAH"
        duration_ms = element.duration * 1000
        print(
            f"{element.to_morse()} ({element_type}: {duration_ms:.1f}ms)",
            flush=True,
        )

    # Create and start CW stream
    with CWStream(config=config, callback=on_element) as stream:
        try:
            # Keep running until interrupted
            while stream.is_running():
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n\nStopping...")

    print("Done!")


if __name__ == "__main__":
    main()
