# VBAND - USB CW Paddle Interface

A Python package for interfacing with the VBAND USB CW paddle adapter, providing real-time morse code decoding and configurable paddle modes.

## Features

- **Multiple Paddle Types**: Support for straight keys, dual paddles, and iambic modes (A & B)
- **Real-time Decoding**: Live conversion of CW input to characters
- **Auto-WPM Detection**: Automatically adjusts to operator's sending speed
- **Flexible Output**: Choose between raw dit/dah stream or decoded characters
- **Configurable Timing**: Adjustable character and word spacing thresholds
- **Simple API**: Easy-to-use Python interface and CLI tool

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

- `basic_usage.py` - Simple character decoding
- `realtime_decode.py` - Shows both raw and decoded output
- `raw_stream.py` - Raw dit/dah stream only

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
