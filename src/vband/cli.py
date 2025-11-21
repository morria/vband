"""Command-line interface for VBAND package."""

import sys
import argparse
import signal
from typing import Optional
from .config import VBandConfig, PaddleType
from .stream import DecodedStream, CWStream, SpaceMarkStream, print_element, print_character, play_audio_element


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser for CLI."""
    parser = argparse.ArgumentParser(
        description="VBAND - USB CW Paddle Interface and Decoder",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Decode morse code to characters at 20 WPM
  vband --wpm 20

  # Show raw dit/dah stream with audio feedback
  vband --raw --audio

  # Decode with audio feedback
  vband --audio

  # Use iambic mode A with auto-WPM detection
  vband --paddle iambic_a --auto-wpm

  # Straight key mode
  vband --paddle straight

Paddle Types:
  straight    - Straight key (single lever)
  dual        - Dual paddle (manual timing)
  iambic_a    - Iambic mode A (squeeze priority)
  iambic_b    - Iambic mode B (squeeze memory, default)
  single      - Single paddle (dit or dah only)
        """,
    )

    parser.add_argument(
        "--paddle",
        type=str,
        choices=["straight", "dual", "iambic_a", "iambic_b", "single"],
        default="iambic_b",
        help="Paddle type (default: iambic_b)",
    )

    parser.add_argument(
        "--wpm", type=int, default=20, help="Words per minute (default: 20)"
    )

    parser.add_argument(
        "--auto-wpm",
        action="store_true",
        default=True,
        help="Automatically adjust to operator speed (default: enabled)",
    )

    parser.add_argument(
        "--no-auto-wpm",
        action="store_false",
        dest="auto_wpm",
        help="Disable automatic WPM adjustment",
    )

    parser.add_argument(
        "--raw",
        action="store_true",
        help="Show raw dit/dah stream instead of decoded characters",
    )

    parser.add_argument(
        "--both",
        action="store_true",
        help="Show both raw dit/dah and decoded characters",
    )

    parser.add_argument(
        "--audio",
        action="store_true",
        help="Enable audio feedback for dits and dahs",
    )

    parser.add_argument(
        "--char-space",
        type=float,
        default=3.0,
        help="Character spacing threshold (multiple of dit duration, default: 3.0)",
    )

    parser.add_argument(
        "--word-space",
        type=float,
        default=7.0,
        help="Word spacing threshold (multiple of dit duration, default: 7.0)",
    )

    parser.add_argument(
        "--version", action="version", version="%(prog)s 0.1.0"
    )

    return parser


def signal_handler(signum, frame):
    """Handle interrupt signal."""
    print("\n\nStopping VBAND...", file=sys.stderr)
    sys.exit(0)


def print_pair(pair):
    """Print a space/mark pair to stdout."""
    print(f"({pair.space_ms:.0f},{pair.mark_ms:.0f}) ", end="", flush=True)


def main() -> int:
    """Main entry point for CLI."""
    parser = create_parser()
    args = parser.parse_args()

    # Setup signal handler
    signal.signal(signal.SIGINT, signal_handler)

    # Create configuration
    config = VBandConfig(
        paddle_type=PaddleType(args.paddle),
        auto_wpm=args.auto_wpm,
        char_space_threshold=args.char_space,
        word_space_threshold=args.word_space,
    )
    config.set_wpm(args.wpm)

    print(f"VBAND CW Paddle Interface", file=sys.stderr)
    print(f"Paddle Type: {args.paddle}", file=sys.stderr)
    print(f"Speed: {args.wpm} WPM", file=sys.stderr)
    print(f"Auto-WPM: {'Enabled' if args.auto_wpm else 'Disabled'}", file=sys.stderr)
    print("", file=sys.stderr)
    print("Ready to receive CW input (Ctrl+C to exit)...", file=sys.stderr)
    print("=" * 50, file=sys.stderr)
    print("", file=sys.stderr)

    # Determine which stream to use based on keyer configuration
    use_spacemark = getattr(config, 'use_spacemark_keyer', True)

    try:
        if args.raw:
            # Show only raw dit/dah stream
            def raw_callback(element):
                print_element(element)
                if args.audio:
                    play_audio_element(element)

            with CWStream(config=config, callback=raw_callback) as stream:
                while stream.is_running():
                    signal.pause()

        elif args.both:
            # Show both raw and decoded
            if use_spacemark:
                # Use SpaceMarkStream
                print("Raw: ", end="", flush=True)

                def both_pair(pair):
                    print_pair(pair)

                def both_char_sm(char):
                    print(f"\nDecoded: {char}", flush=True)
                    print("Raw: ", end="", flush=True)

                with SpaceMarkStream(
                    config=config, char_callback=both_char_sm, pair_callback=both_pair
                ) as stream:
                    while stream.is_running():
                        signal.pause()
            else:
                # Use DecodedStream (legacy)
                print("Raw: ", end="", flush=True)

                def both_element(element):
                    print_element(element)
                    if args.audio:
                        play_audio_element(element)

                def both_char(char):
                    print(f"\nDecoded: {char}", flush=True)
                    print("Raw: ", end="", flush=True)

                with DecodedStream(
                    config=config, char_callback=both_char, element_callback=both_element
                ) as stream:
                    while stream.is_running():
                        signal.pause()

        else:
            # Show only decoded characters (default)
            if use_spacemark:
                # Use SpaceMarkStream
                with SpaceMarkStream(
                    config=config,
                    char_callback=print_character,
                ) as stream:
                    while stream.is_running():
                        signal.pause()
            else:
                # Use DecodedStream (legacy)
                element_callback = play_audio_element if args.audio else None
                with DecodedStream(
                    config=config,
                    char_callback=print_character,
                    element_callback=element_callback,
                ) as stream:
                    while stream.is_running():
                        signal.pause()

    except KeyboardInterrupt:
        print("\n\nStopping VBAND...", file=sys.stderr)
        return 0
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
