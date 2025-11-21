# VBAND - USB CW Paddle Interface

A Python package for interfacing with the VBAND USB CW paddle adapter, providing real-time morse code decoding and configurable paddle modes.

## Features

- **Multiple Paddle Types**: Support for straight keys, dual paddles, and iambic modes (A & B)
- **Near Real-Time Decoding**: Space/mark pair architecture based on vband.org reference implementation
- **Adaptive WPM Detection**: Aggressively learns operator's speed using timing analysis
- **Flexible Output**: Choose between raw dit/dah stream, space/mark pairs, or decoded characters
- **Configurable Timing**: Adjustable character and word spacing thresholds
- **Simple API**: Easy-to-use Python interface and CLI tool
- **Binary Tree Morse Decoder**: Fast character lookup using bit-encoded morse patterns

## Installation

```bash
pip install -e .
```

### Development Installation

```bash
pip install -e ".[dev]"
```

## Quick Start

### Command Line Interface

```bash
# Basic usage - decode morse code at 20 WPM
vband --wpm 20

# Show raw dit/dah stream
vband --raw

# Use iambic mode A with auto-WPM detection
vband --paddle iambic_a --auto-wpm

# Show both raw and decoded output
vband --both --wpm 15
```

### Python API

#### Near Real-Time Decoding (Recommended)

Uses space/mark pair architecture for optimal performance:

```python
from vband import VBandConfig, SpaceMarkStream, PaddleType

# Create configuration
config = VBandConfig(
    paddle_type=PaddleType.IAMBIC_B,
    auto_wpm=True,
)
config.set_wpm(20)

# Define callback for decoded characters
def on_character(char: str):
    print(char, end="", flush=True)

# Start near real-time decoding stream
with SpaceMarkStream(config=config, char_callback=on_character) as stream:
    while stream.is_running():
        time.sleep(0.1)
        print(f"WPM: {stream.get_wpm()}")
```

#### Standard Decoding

Traditional element-based decoding:

```python
from vband import VBandConfig, DecodedStream, PaddleType

# Create configuration
config = VBandConfig(
    paddle_type=PaddleType.IAMBIC_B,
    auto_wpm=True,
)
config.set_wpm(20)

# Define callback for decoded characters
def on_character(char: str):
    print(char, end="", flush=True)

# Start decoding stream
with DecodedStream(config=config, char_callback=on_character) as stream:
    while stream.is_running():
        time.sleep(0.1)
```

## Hardware Setup

The VBAND USB paddle interface connects to your computer via USB and simulates keyboard control keys:

- **Left Control** = Dit (tip of 3.5mm jack)
- **Right Control** = Dah (ring of 3.5mm jack)

### Wiring

- **Straight Key**: Connect tip to one side, sleeve to other side, leave ring unconnected
- **Paddle**: Connect tip to "dit", ring to "dah", sleeve to common/ground

## Paddle Types

### Straight Key (`straight`)
Single lever key for manual timing of both dits and dahs.

### Dual Paddle (`dual`)
Two-lever paddle with manual timing - operator controls both dit and dah timing.

### Iambic Mode A (`iambic_a`)
Automatic dit/dah generation with squeeze priority - when both levers are pressed, the last pressed lever takes priority.

### Iambic Mode B (`iambic_b`)
Automatic dit/dah generation with squeeze memory - remembers both levers being pressed and alternates automatically.

### Single Paddle (`single`)
Single-lever paddle for either dit or dah only.

## Configuration Options

```python
config = VBandConfig(
    paddle_type=PaddleType.IAMBIC_B,  # Paddle type
    auto_wpm=True,                     # Auto-detect WPM
    dit_duration=0.06,                 # Dit duration in seconds (~20 WPM)
    char_space_threshold=3.0,          # Multiplier for character spacing
    word_space_threshold=7.0,          # Multiplier for word spacing
    debounce_time=0.005,               # Key debounce time (5ms)
)

# Set WPM directly
config.set_wpm(25)  # 25 words per minute
```

## API Reference

### Classes

#### `VBandConfig`
Configuration object for paddle interface and decoder settings.

#### `PaddleInterface`
Low-level interface for capturing paddle events from USB device.

#### `SpaceMarkStream` (Recommended)
Near real-time stream of decoded morse code using space/mark pairs. Implements the vband.org reference architecture for optimal performance with adaptive WPM detection.

#### `SpaceMarkDecoder`
Adaptive decoder that processes space/mark timing pairs. Features aggressive WPM learning and binary tree morse lookup.

#### `SpaceMarkKeyer`
State machine keyer that generates space/mark timing pairs for all paddle types (straight key, bug, iambic A/B).

#### `CWDecoder`
Converts paddle events into CW elements (dits and dahs) with timing analysis.

#### `MorseDecoder`
Converts CW elements into characters using international morse code.

#### `CWStream`
Real-time stream of CW elements with callback support.

#### `DecodedStream`
Real-time stream of decoded characters with optional element callbacks.

## Examples

See the `examples/` directory for complete examples:

- `spacemark_decode.py` - Near real-time decoding with space/mark architecture (recommended)
- `basic_usage.py` - Simple character decoding
- `realtime_decode.py` - Shows both raw and decoded output
- `raw_stream.py` - Raw dit/dah stream only

## Architecture

### Space/Mark Decoding (vband.org Reference Implementation)

The recommended `SpaceMarkStream` uses a space/mark pair architecture based on the vband.org web application:

1. **SpaceMarkKeyer** - Tracks paddle state transitions and generates timing pairs:
   - Each pair contains: `(space_duration, mark_duration)` in milliseconds
   - Works with all paddle types: straight key, bug, iambic A/B

2. **SpaceMarkDecoder** - Processes timing pairs with adaptive learning:
   - **Aggressive WPM Detection**: Compares consecutive marks that differ by 2X to learn dit length
   - **Adaptive Spacing**: Learns inter-character spacing from observed gaps
   - **Binary Tree Lookup**: Uses bit-encoded morse patterns for fast character decoding
   - **Auto-Flush Timer**: Completes characters automatically after timing threshold

3. **Near Real-Time Performance**: By processing complete timing pairs immediately, decoding happens as soon as each element completes, providing the fastest possible character output.

### Traditional Element-Based Decoding

The original `DecodedStream` uses a traditional approach:
1. Captures key press/release events
2. Builds CW elements (dits/dahs)
3. Waits for gaps to decode characters

This approach works well but has slightly higher latency compared to space/mark decoding.

## Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=vband --cov-report=html
```

## Troubleshooting

### No Input Detected

1. Ensure the VBAND USB device is connected
2. Check that your OS recognizes it as a keyboard device
3. Disable "Sticky Keys" on Windows if using control keys
4. Try running with elevated privileges if needed

### Incorrect Decoding

1. Adjust WPM to match your sending speed
2. Enable auto-WPM detection with `--auto-wpm`
3. Adjust character/word spacing thresholds
4. Check paddle type configuration matches your physical paddle

### Permission Issues

On Linux, you may need to add udev rules for USB access without root.

## License

MIT License - see LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues.

## Morse Code Reference

```
A .-    B -...  C -.-.  D -..   E .     F ..-.
G --.   H ....  I ..    J .---  K -.-   L .-..
M --    N -.    O ---   P .--.  Q --.-  R .-.
S ...   T -     U ..-   V ...-  W .--   X -..-
Y -.--  Z --..

0 ----- 1 .---- 2 ..--- 3 ...-- 4 ....-
5 ..... 6 -.... 7 --... 8 ---.. 9 ----.

. .-.-.-  , --..--  ? ..--..  / -..-.
```

## Credits

Designed for use with the VBAND USB Paddle Interface (https://vband.org).
