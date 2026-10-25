import string


ALPHA = string.ascii_uppercase
CAESAR_ALPHABET = string.ascii_uppercase + string.ascii_lowercase


def clean(text):
    return "".join(c for c in text.upper() if c in ALPHA)


def caesar(text, n, direction="right"):
    shift = n % len(CAESAR_ALPHABET)
    if direction in ("left", "gauche"):
        shift = -shift
    result = ""
    for ch in text:
        if ch in CAESAR_ALPHABET:
            index = CAESAR_ALPHABET.index(ch)
            result += CAESAR_ALPHABET[(index + shift) % len(CAESAR_ALPHABET)]
        else:
            result += ch
    return result


def caesar_decrypt(text, n, direction="right"):
    if direction in ("left", "gauche"):
        return caesar(text, n, "right")
    return caesar(text, n, "left")


def caesar_frequency_guess(text):
    letters = clean(text)
    if not letters:
        return 0
    most_common = max(ALPHA, key=letters.count)
    return (ALPHA.index(most_common) - ALPHA.index("E")) % 26