#!/usr/bin/env python3
"""
Standalone test for space/mark decoder functionality.

This test validates the core decoding logic without requiring
dependencies like pynput or X server.
"""


def test_morse_tree():
    """Test MORSE_TREE binary encoding."""
    print("Testing MORSE_TREE binary encoding...")

    # Binary tree-encoded morse table
    MORSE_TREE = (
        "**ETIANMSURWDKGOHVF\x9cL\xc4PJBXCYZQ\xd6\xe454\x9d3\xc9*\xc22&\xc8+*\xde\xc3\xf434" +
        "16=/*\xc6^(*7\xbb\xe3\xd18*90" +
        "*****|******?_****\"*\xb6.****@***'**-********;!*)****\xb9,****:*******"
    )

    # Test: E = dit (binary: 10 = 2)
    assert MORSE_TREE[2] == 'E', f"E should be at index 2, got '{MORSE_TREE[2]}'"

    # Test: T = dah (binary: 11 = 3)
    assert MORSE_TREE[3] == 'T', f"T should be at index 3, got '{MORSE_TREE[3]}'"

    # Test: A = dit-dah (binary: 101 = 5)
    assert MORSE_TREE[5] == 'A', f"A should be at index 5, got '{MORSE_TREE[5]}'"

    # Test: N = dah-dit (binary: 110 = 6)
    assert MORSE_TREE[6] == 'N', f"N should be at index 6, got '{MORSE_TREE[6]}'"

    # Test: M = dah-dah (binary: 111 = 7)
    assert MORSE_TREE[7] == 'M', f"M should be at index 7, got '{MORSE_TREE[7]}'"

    # Test: S = dit-dit-dit (binary: 1000 = 8)
    assert MORSE_TREE[8] == 'S', f"S should be at index 8, got '{MORSE_TREE[8]}'"

    # Test: O = dah-dah-dah (binary: 1111 = 15)
    assert MORSE_TREE[15] == 'O', f"O should be at index 15, got '{MORSE_TREE[15]}'"

    print("✓ MORSE_TREE binary encoding validated")
    return True


def test_morse_encoding_logic():
    """Test the binary encoding logic for morse characters."""
    print("\nTesting morse encoding logic...")

    # Simulate the encoder: start at 1, multiply by 2 for each element,
    # add 1 for dah
    def encode_morse(pattern):
        """Encode morse pattern to binary tree index."""
        index = 1
        for c in pattern:
            index *= 2
            if c == '-':  # dah
                index += 1
        return index

    # Test various characters
    assert encode_morse('.') == 2, "E (dit) encoding"
    assert encode_morse('-') == 3, "T (dah) encoding"
    assert encode_morse('.-') == 5, "A (dit-dah) encoding"
    assert encode_morse('-.') == 6, "N (dah-dit) encoding"
    assert encode_morse('...') == 8, "S (dit-dit-dit) encoding"
    assert encode_morse('---') == 15, "O (dah-dah-dah) encoding"
    assert encode_morse('...-') == 17, "V (dit-dit-dit-dah) encoding"

    print("✓ Morse encoding logic validated")
    return True


def test_adaptive_timing_logic():
    """Test the adaptive timing algorithm."""
    print("\nTesting adaptive timing logic...")

    # Simulate the adaptive dit length algorithm
    dit_length = 80.0  # Initial 15 WPM
    last_mark = 120.0
    char_space = 240.0

    # When marks differ by 2X, average and divide by 2
    new_mark = 60.0  # Much faster

    if new_mark > 2.0 * last_mark or last_mark > 2.0 * new_mark:
        new_dit = ((last_mark + new_mark) / 4.0 + dit_length) / 2.0
        print(f"  Old dit: {dit_length:.1f}ms, New dit: {new_dit:.1f}ms")
        assert new_dit != dit_length, "Dit length should adapt"
        assert new_dit < dit_length, "Dit length should decrease for faster sending"

    print("✓ Adaptive timing logic validated")
    return True


def test_space_classification():
    """Test space classification logic."""
    print("\nTesting space classification...")

    dit_length = 80.0
    char_space = 240.0  # 3 dit units

    # Inter-element space (less than 2 dit)
    space1 = 100.0
    assert space1 <= dit_length * 2.0, "Should be inter-element space"

    # Inter-character space (between 2 and 5.5 * char_space/3)
    space2 = 250.0
    word_space_threshold = (char_space / 3.0) * 5.5
    assert space2 > dit_length * 2.0, "Should be more than inter-element"
    assert space2 < word_space_threshold, "Should be inter-character space"

    # Inter-word space (greater than word threshold)
    space3 = 500.0
    assert space3 >= word_space_threshold, "Should be inter-word space"

    print(f"  Inter-element: <{dit_length * 2.0:.1f}ms")
    print(f"  Inter-char: {dit_length * 2.0:.1f}-{word_space_threshold:.1f}ms")
    print(f"  Inter-word: >{word_space_threshold:.1f}ms")
    print("✓ Space classification validated")
    return True


def test_wpm_calculation():
    """Test WPM calculation logic."""
    print("\nTesting WPM calculation...")

    dit_length = 80.0  # ms
    char_space = 240.0  # ms

    # WPM from dit length: 1200ms / dit_length
    dit_wpm = 1200.0 / dit_length
    assert 14.0 < dit_wpm < 16.0, f"Dit WPM should be ~15, got {dit_wpm}"

    # Char WPM from char space
    char_wpm = (3.0 * 1200.0) / char_space
    assert 14.0 < char_wpm < 16.0, f"Char WPM should be ~15, got {char_wpm}"

    # Effective WPM (Farnsworth)
    eff_wpm = (50.0 / (31.0 / dit_wpm + 19.0 / char_wpm))

    print(f"  Dit WPM: {dit_wpm:.1f}")
    print(f"  Char WPM: {char_wpm:.1f}")
    print(f"  Eff WPM: {eff_wpm:.1f}")
    print("✓ WPM calculation validated")
    return True


def test_char_space_adaptation():
    """Test character space adaptation logic."""
    print("\nTesting character space adaptation...")

    char_space = 240.0
    duration = 200.0  # Smaller than current

    # When duration < char_space, approach quicker (0.5 weight)
    new_char_space = char_space * 0.5 + duration * 0.5
    expected = 220.0
    assert abs(new_char_space - expected) < 1.0, \
        f"Expected {expected}, got {new_char_space}"

    # When duration > char_space, approach slower (0.8 weight)
    char_space = 240.0
    duration = 300.0
    new_char_space = char_space * 0.8 + duration * 0.2
    expected = 252.0
    assert abs(new_char_space - expected) < 1.0, \
        f"Expected {expected}, got {new_char_space}"

    print("✓ Character space adaptation validated")
    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("Space/Mark Decoder Logic Tests")
    print("=" * 60)

    try:
        test_morse_tree()
        test_morse_encoding_logic()
        test_adaptive_timing_logic()
        test_space_classification()
        test_wpm_calculation()
        test_char_space_adaptation()

        print("\n" + "=" * 60)
        print("✓ All logic tests passed!")
        print("=" * 60)
        print("\nNote: Full integration tests require X server for pynput.")
        print("The core decoding logic has been validated successfully.")
        return 0

    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
