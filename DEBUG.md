# VBAND Debugging Guide

This guide will help you debug character decoding issues in VBAND.

## Enabling Debug Logging

To enable comprehensive debug logging throughout the decoding pipeline, set the `VBAND_DEBUG` environment variable:

```bash
export VBAND_DEBUG=1
python -m vband
```

Or run it inline:

```bash
VBAND_DEBUG=1 python -m vband
```

## What Gets Logged

When debug logging is enabled, you'll see detailed information from three main components:

### 1. PaddleInterface (Keyboard Input)

Shows raw keyboard events as they're captured:

```
[PaddleInterface] Starting paddle interface
[PaddleInterface] Using SpaceMarkKeyer
[PaddleInterface] Paddle type: STRAIGHT_KEY
[PaddleInterface] DIT pressed at 1234.567s
[PaddleInterface] DIT released at 1234.627s
[PaddleInterface] DAH pressed at 1234.700s
[PaddleInterface] DAH released at 1234.880s
```

**What to look for:**
- Are key presses being detected?
- Are there unexpected debounce messages?
- Is the correct paddle type being used?

### 2. SpaceMarkKeyer (Timing Generation)

Shows the state machine and space/mark pairs being generated:

```
[SpaceMarkKeyer] Starting keyer for 20 WPM (dit=60.0ms)
[SpaceMarkKeyer] Paddle mode: STRAIGHT_KEY
[SpaceMarkKeyer] Initial state: 0 (0=IDLE, 1=MARK, 2=INTER_ELEMENT)
[SpaceMarkKeyer] Dit pressed, updating memory
[SpaceMarkKeyer] Paddle state: DIT, memory: DIT
[SpaceMarkKeyer] Generated DIT: space=0.0ms, mark=60.0ms
[SpaceMarkKeyer] Generated DAH: space=10.0ms, mark=180.0ms
```

**What to look for:**
- Are space/mark pairs being generated?
- Are the timings reasonable? (dit ~60ms at 20 WPM, dah ~180ms)
- Is the paddle state being updated correctly?
- For iambic modes, is the memory working as expected?

### 3. SpaceMarkDecoder (Character Decoding)

Shows the complete decoding process including state tree navigation:

```
[SpaceMarkDecoder] Initialized for 20 WPM: dit=60.0ms, char_space=180.0ms
[SpaceMarkDecoder] Morse tree navigation: start at index 1, dit=*2, dah=*2+1

[SpaceMarkDecoder] Processing pair: space=0.0ms, mark=60.0ms (tree pos=1)
[SpaceMarkDecoder] INTER-ELEMENT space 0.0ms (threshold=120.0ms)
[SpaceMarkDecoder] Decoded DIT (60.0ms, threshold=102.0ms)
[SpaceMarkDecoder] Tree position: 1 -> 2, pattern so far: .

[SpaceMarkDecoder] Processing pair: space=10.0ms, mark=180.0ms (tree pos=2)
[SpaceMarkDecoder] INTER-ELEMENT space 10.0ms (threshold=120.0ms)
[SpaceMarkDecoder] Decoded DAH (180.0ms, threshold=102.0ms)
[SpaceMarkDecoder] Tree position: 2 -> 5, pattern so far: .-

[SpaceMarkDecoder] Processing pair: space=200.0ms, mark=60.0ms (tree pos=5)
[SpaceMarkDecoder] Space 200.0ms > threshold 120.0ms - flushing character
[SpaceMarkDecoder] FLUSHED CHARACTER: 'A' (pattern=.-, tree_pos=5)
[SpaceMarkDecoder] Current timing: dit=60.0ms, char_space=180.0ms, WPM=20.0/20.0 WPM
```

**What to look for:**
- Is the decoder receiving space/mark pairs?
- Are dits and dahs being classified correctly? (DIT vs DAH based on 1.7x threshold)
- Is the tree position advancing correctly? (dit=multiply by 2, dah=multiply by 2 and add 1)
- Are characters being flushed when spaces exceed the threshold?
- Is the morse pattern building up correctly?
- Are timing parameters adapting to your sending speed?

## Understanding the Morse Tree

The decoder uses a binary tree where each position represents a morse pattern:

```
Position 1: Root (start)
Position 2: E (dit from root: 1*2=2)
Position 3: T (dah from root: 1*2+1=3)
Position 4: I (dit from E: 2*2=4)
Position 5: A (dah from E: 2*2+1=5)
Position 6: N (dit from T: 3*2=6)
Position 7: M (dah from T: 3*2+1=7)
...and so on
```

**Navigation rules:**
- Start at position 1 (morse_ch=1)
- DIT: multiply position by 2
- DAH: multiply position by 2, then add 1
- Lookup character when flushed: MORSE_TREE[morse_ch]

**Example - Decoding "A" (.-):**
```
Start:  morse_ch = 1
DIT:    morse_ch = 1*2 = 2          (pattern: .)
DAH:    morse_ch = 2*2+1 = 5        (pattern: .-)
Flush:  MORSE_TREE[5] = 'A'
```

## Common Issues and Solutions

### Issue: No characters are being decoded

**Diagnosis steps:**

1. **Check if keyboard events are detected:**
   ```
   grep "PaddleInterface.*pressed" stderr.log
   ```
   - If you see nothing, the paddle isn't being detected
   - Check if you're using the correct keys (Left Ctrl = dit, Right Ctrl = dah)

2. **Check if space/mark pairs are generated:**
   ```
   grep "SpaceMarkKeyer.*Generated" stderr.log
   ```
   - If you see nothing, the keyer isn't working
   - Check paddle type configuration

3. **Check if decoder is receiving pairs:**
   ```
   grep "SpaceMarkDecoder.*Processing pair" stderr.log
   ```
   - If you see nothing, pairs aren't reaching the decoder
   - Check the stream setup

4. **Check if marks are being decoded:**
   ```
   grep "SpaceMarkDecoder.*Decoded" stderr.log
   ```
   - If you see nothing, the decoder isn't processing marks
   - Check if mark durations are within reasonable range

5. **Check if characters are being flushed:**
   ```
   grep "SpaceMarkDecoder.*FLUSHED" stderr.log
   ```
   - If you see "Decoded DIT/DAH" but no flushes, spacing is the issue
   - You need longer pauses between characters

### Issue: Wrong characters are decoded

**Diagnosis:**

1. Look at the morse pattern in flush messages:
   ```
   [SpaceMarkDecoder] FLUSHED CHARACTER: 'X' (pattern=-..-., tree_pos=...)
   ```

2. Check if the pattern matches what you sent:
   - If pattern is wrong, check the DIT/DAH classifications
   - Look for threshold messages to see if timing is off

3. Check for adaptive timing changes:
   ```
   grep "ADAPTIVE" stderr.log
   ```
   - Rapid WPM changes can cause misclassification
   - Try more consistent sending speeds

### Issue: Characters are combined or split incorrectly

**Diagnosis:**

1. Check inter-character spacing:
   ```
   grep "INTER-CHAR\|INTER-WORD" stderr.log
   ```

2. Look at char_space values:
   - Default is 3x dit_length (e.g., 180ms at 20 WPM)
   - If char_space is too large, characters split too easily
   - If char_space is too small, characters combine

3. Check flush timing:
   - Characters flush when space > dit_length * 2.0
   - Make sure you're pausing long enough between characters

### Issue: Decoding is too slow

**Diagnosis:**

1. Check WPM calculations in flush messages:
   ```
   [SpaceMarkDecoder] Current timing: dit=60.0ms, char_space=180.0ms, WPM=20.0/20.0 WPM
   ```

2. The format is `dit_wpm/effective_wpm`:
   - dit_wpm: Based on mark duration (1200ms / dit_length_ms)
   - effective_wpm: Includes spacing

3. If WPM is too low:
   - Speed up your sending
   - The decoder will adapt within a few characters

## Viewing the Stream of Dits and Dahs

To see just the stream of dits and dahs as they're decoded:

```bash
VBAND_DEBUG=1 python -m vband 2>&1 | grep "Decoded DIT\|Decoded DAH"
```

Output will look like:
```
[SpaceMarkDecoder] Decoded DIT (58.2ms, threshold=102.0ms)
[SpaceMarkDecoder] Decoded DAH (175.3ms, threshold=102.0ms)
[SpaceMarkDecoder] Decoded DIT (61.1ms, threshold=102.0ms)
```

## Viewing State Tree Navigation

To see how the decoder navigates the morse tree:

```bash
VBAND_DEBUG=1 python -m vband 2>&1 | grep "Tree position"
```

Output will show:
```
[SpaceMarkDecoder] Tree position: 1 -> 2, pattern so far: .
[SpaceMarkDecoder] Tree position: 2 -> 5, pattern so far: .-
[SpaceMarkDecoder] Tree position: 1 -> 2, pattern so far: .
```

## Full Debug Session Example

Here's what a complete debug session looks like when sending "A" (.-):

```
[PaddleInterface] Starting paddle interface
[PaddleInterface] Using SpaceMarkKeyer
[PaddleInterface] Paddle type: STRAIGHT_KEY
[SpaceMarkKeyer] Starting keyer for 20 WPM (dit=60.0ms)
[SpaceMarkKeyer] Paddle mode: STRAIGHT_KEY
[SpaceMarkKeyer] Initial state: 0 (0=IDLE, 1=MARK, 2=INTER_ELEMENT)
[SpaceMarkDecoder] Initialized for 20 WPM: dit=60.0ms, char_space=180.0ms
[SpaceMarkDecoder] Morse tree navigation: start at index 1, dit=*2, dah=*2+1

[PaddleInterface] DIT pressed at 100.000s
[PaddleInterface] DIT released at 100.060s
[SpaceMarkKeyer] Straight key: space=0.0ms, mark=60.0ms

[SpaceMarkDecoder] Processing pair: space=0.0ms, mark=60.0ms (tree pos=1)
[SpaceMarkDecoder] INTER-ELEMENT space 0.0ms (threshold=120.0ms)
[SpaceMarkDecoder] Decoded DIT (60.0ms, threshold=102.0ms)
[SpaceMarkDecoder] Tree position: 1 -> 2, pattern so far: .

[PaddleInterface] DAH pressed at 100.070s
[PaddleInterface] DAH released at 100.250s
[SpaceMarkKeyer] Straight key: space=10.0ms, mark=180.0ms

[SpaceMarkDecoder] Processing pair: space=10.0ms, mark=180.0ms (tree pos=2)
[SpaceMarkDecoder] INTER-ELEMENT space 10.0ms (threshold=120.0ms)
[SpaceMarkDecoder] Decoded DAH (180.0ms, threshold=102.0ms)
[SpaceMarkDecoder] Tree position: 2 -> 5, pattern so far: .-

[Long pause...]

[SpaceMarkDecoder] Space 200.0ms > threshold 120.0ms - flushing character
[SpaceMarkDecoder] FLUSHED CHARACTER: 'A' (pattern=.-, tree_pos=5)
[SpaceMarkDecoder] Current timing: dit=60.0ms, char_space=180.0ms, WPM=20.0/20.0 WPM

A
```

## Timing Reference

Standard morse timing at different WPM:

| WPM | Dit (ms) | Dah (ms) | Char Space (ms) | Word Space (ms) |
|-----|----------|----------|-----------------|-----------------|
| 10  | 120      | 360      | 360             | 840             |
| 15  | 80       | 240      | 240             | 560             |
| 20  | 60       | 180      | 180             | 420             |
| 25  | 48       | 144      | 144             | 336             |
| 30  | 40       | 120      | 120             | 280             |

**Thresholds used by decoder:**
- Dit/Dah threshold: 1.7 × dit_length
- Character space threshold: 2.0 × dit_length
- Word space threshold: 5.5 × (char_space / 3)

## Advanced: Logging to a File

To save debug output to a file for analysis:

```bash
VBAND_DEBUG=1 python -m vband 2> vband_debug.log
```

Then analyze with:
```bash
# See all state tree navigation
grep "Tree position" vband_debug.log

# See all character flushes
grep "FLUSHED CHARACTER" vband_debug.log

# See timing adaptations
grep "ADAPTIVE" vband_debug.log

# See spacing decisions
grep "INTER-CHAR\|INTER-WORD\|INTER-ELEMENT" vband_debug.log
```

## Getting Help

If you're still having issues after reviewing the debug output:

1. Save your debug log: `VBAND_DEBUG=1 python -m vband 2> debug.log`
2. Note what you were trying to send vs. what was decoded
3. Check the GitHub issues: https://github.com/morria/vband/issues
4. Include relevant portions of the debug log in your issue report
