from .cesar import ALPHA, clean


def playfair_square(key):
    letters = []
    for ch in clean(key).replace("J", "I") + ALPHA.replace("J", ""):
        if ch not in letters:
            letters.append(ch)
    return letters


def playfair_prepare(text):
    letters = clean(text).replace("J", "I")
    pairs = []
    padding_positions = []
    i = 0
    while i < len(letters):
        first = letters[i]
        if i + 1 >= len(letters):
            second = "X"
            padding_positions.append(len(pairs) * 2 + 1)
            i += 1
        elif first == letters[i + 1]:
            second = "X"
            padding_positions.append(len(pairs) * 2 + 1)
            i += 1
        else:
            second = letters[i + 1]
            i += 2
        pairs.append((first, second))
    return pairs, padding_positions


def playfair_j_positions(text):
    return [
        index
        for index, character in enumerate(clean(text))
        if character == "J"
    ]


def playfair_restore_j(text, j_positions):
    letters = list(text)
    for index in j_positions:
        if index < len(letters) and letters[index] == "I":
            letters[index] = "J"
    return "".join(letters)


def playfair_pairs(text):
    return playfair_prepare(text)[0]


def playfair_swap(a, b, square, step):
    row_a, col_a = divmod(square.index(a), 5)
    row_b, col_b = divmod(square.index(b), 5)
    if row_a == row_b:
        col_a = (col_a + step) % 5
        col_b = (col_b + step) % 5
    elif col_a == col_b:
        row_a = (row_a + step) % 5
        row_b = (row_b + step) % 5
    else:
        col_a, col_b = col_b, col_a
    return square[row_a * 5 + col_a] + square[row_b * 5 + col_b]


def playfair_encrypt(text, key):
    square = playfair_square(key)
    return "".join(playfair_swap(a, b, square, 1) for a, b in playfair_pairs(text))


def playfair_decrypt(text, key):
    square = playfair_square(key)
    letters = clean(text).replace("J", "I")
    if len(letters) % 2 != 0:
        raise ValueError("la longueur du chiffré doit être paire")
    return "".join(
        playfair_swap(letters[i], letters[i + 1], square, -1)
        for i in range(0, len(letters), 2)
    )


def playfair_strip_padding(text, padding_positions=None):
    if padding_positions is not None:
        return "".join(
            character
            for index, character in enumerate(text)
            if index not in padding_positions
        )
    result = ""
    for i, ch in enumerate(text):
        between_equal = 0 < i < len(text) - 1 and text[i - 1] == text[i + 1]
        if ch == "X" and between_equal:
            continue
        result += ch
    if result.endswith("X"):
        result = result[:-1]
    return result


def digram_counts(text):
    letters = clean(text)
    counts = {}
    for i in range(0, len(letters) - 1, 2):
        pair = letters[i:i + 2]
        counts[pair] = counts.get(pair, 0) + 1
    return sorted(counts.items(), key=lambda item: -item[1])