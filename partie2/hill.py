from math import gcd

from .cesar import ALPHA, clean

def det(m):
    if len(m) == 1:
        return m[0][0]
    total = 0
    for j in range(len(m)):
        minor = [row[:j] + row[j + 1:] for row in m[1:]]
        total += (-1) ** j * m[0][j] * det(minor)
    return total

def mat_inverse_mod(m):
    n = len(m)
    d = det(m) % 26
    if gcd(d, 26) != 1:
        raise ValueError("la matrice clé n'est pas inversible modulo 26")
    d_inv = pow(d, -1, 26)
    if n == 1:
        return [[d_inv]]
    inverse = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            minor = [row[:j] + row[j + 1:] for k, row in enumerate(m) if k != i]
            cofactor = (-1) ** (i + j) * det(minor)
            inverse[j][i] = cofactor * d_inv % 26
    return inverse

def key_from_text(word):
    letters = clean(word)
    size = int(len(letters) ** 0.5)
    if size < 2 or size * size != len(letters):
        raise ValueError("la clé doit avoir 4 ou 9 lettres")
    numbers = [ALPHA.index(c) for c in letters]
    return [numbers[i * size:(i + 1) * size] for i in range(size)]

def hill_apply(text, key):
    n = len(key)
    numbers = [ALPHA.index(c) for c in text]
    result = ""
    for start in range(0, len(numbers), n):
        block = numbers[start:start + n]
        for row in key:
            result += ALPHA[sum(a * b for a, b in zip(row, block)) % 26]
    return result

def format_positions(text):
    positions = []
    letter_index = 0
    for character in text:
        if character in ALPHA:
            letter_index += 1
        else:
            positions.append((letter_index, character))
    return positions

def restore_format(text, positions):
    result = []
    position_index = 0
    for letter_index, character in enumerate(text):
        while (
            position_index < len(positions)
            and positions[position_index][0] == letter_index
        ):
            result.append(positions[position_index][1])
            position_index += 1
        result.append(character)
    while position_index < len(positions):
        result.append(positions[position_index][1])
        position_index += 1
    return "".join(result)

def hill_encrypt(text, key):
    mat_inverse_mod(key)
    letters = clean(text)
    while len(letters) % len(key) != 0:
        letters += "X"
    return hill_apply(letters, key)

def hill_decrypt(text, key):
    inverse = mat_inverse_mod(key)
    letters = clean(text)
    if len(letters) % len(key) != 0:
        raise ValueError("la longueur du chiffré doit être un multiple de %d" % len(key))
    return hill_apply(letters, inverse)

def block_matrix(text, start, n):
    numbers = [ALPHA.index(c) for c in text[start:start + n * n]]
    return [[numbers[i * n + j] for i in range(n)] for j in range(n)]

def mat_mul_mod(a, b):
    size = len(a)
    return [[sum(a[i][k] * b[k][j] for k in range(size)) % 26 for j in range(size)] for i in range(size)]

def hill_known_plaintext(plain, cipher, n=2):
    plain = clean(plain)
    cipher = clean(cipher)
    if len(plain) < n * n or len(cipher) < n * n:
        raise ValueError("il faut au moins n*n lettres")
    for start in range(0, len(plain) - n * n + 1, n):
        P = block_matrix(plain, start, n)
        C = block_matrix(cipher, start, n)
        try:
            return mat_mul_mod(C, mat_inverse_mod(P))
        except ValueError:
            continue
    raise ValueError("aucun bloc de clair inversible trouvé")
    