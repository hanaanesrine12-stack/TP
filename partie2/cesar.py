import string


ALPHA = string.ascii_uppercase
CAESAR_ALPHABET = string.ascii_uppercase + string.ascii_lowercase
CAESAR_MASK_MARKER = "L"


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


def caesar_prepare(text):
    letters = []
    mask = []
    for character in text:
        if character in CAESAR_ALPHABET:
            letters.append(character)
            mask.append(CAESAR_MASK_MARKER)
        else:
            mask.append(character)
    return "".join(letters), "".join(mask)


def caesar_restore(text, mask):
    letters = iter(text)
    result = []
    for character in mask:
        if character == CAESAR_MASK_MARKER:
            try:
                result.append(next(letters))
            except StopIteration as error:
                raise ValueError("le masque César ne correspond pas au texte") from error
        else:
            result.append(character)
    if next(letters, None) is not None:
        raise ValueError("le masque César ne correspond pas au texte")
    return "".join(result)
