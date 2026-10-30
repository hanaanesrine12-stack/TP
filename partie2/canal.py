ALGORITHM_CODES = {
    "Caesar": "000",
    "Hill": "001",
    "Playfair": "010",
}
CODE_ALGORITHMS = {code: name for name, code in ALGORITHM_CODES.items()}


def build_channel_message(algorithm, direction, ciphertext, key=None):
    if key is not None and ":" in key:
        raise ValueError("la clé ne doit pas contenir ':'")
    try:
        code = ALGORITHM_CODES[algorithm]
    except KeyError as error:
        raise ValueError("algorithme inconnu") from error

    if algorithm == "Caesar":
        direction_code = {"droite": "r", "right": "r", "gauche": "l", "left": "l"}.get(direction)
        if direction_code is None:
            raise ValueError("la direction de César doit être r ou l")
    else:
        direction_code = ""
    if key is None:
        return "%s:%s:%s" % (code, direction_code, ciphertext)
    return "%s:%s:%s:%s" % (code, direction_code, key, ciphertext)


def decode_channel_message(channel_message):
    parts = channel_message.split(":", 3)
    if len(parts) == 3:
        code, direction, ciphertext = parts
        key = ""
    elif len(parts) == 4:
        code, direction, key, ciphertext = parts
    else:
        raise ValueError("message du canal invalide : métadonnées manquantes")
    try:
        algorithm = CODE_ALGORITHMS[code]
    except KeyError as error:
        raise ValueError("code binaire d'algorithme inconnu") from error
    if algorithm == "Caesar":
        if direction not in ("r", "l"):
            raise ValueError("direction César invalide : utilisez r ou l")
    elif direction:
        raise ValueError("une direction est interdite pour cet algorithme")
    if not ciphertext:
        raise ValueError("le message chiffré est vide")
    return algorithm, direction, key, ciphertext


def dechiffrement_automatique(channel_message, key, hill_key=None):
    algorithm, direction, channel_key, ciphertext = decode_channel_message(channel_message)
    key = channel_key or key
    if not key and hill_key is None:
        raise ValueError("la clé est requise pour le déchiffrement")
    if algorithm == "Caesar":
        direction_name = "droite" if direction == "r" else "gauche"
        return caesar_decrypt(ciphertext, int(key), direction_name)
    if algorithm == "Hill":
        if hill_key is None:
            raise ValueError("la clé Hill est requise pour le déchiffrement")
        return hill_decrypt(ciphertext, hill_key)
    return playfair_decrypt(ciphertext, key)


from .cesar import caesar_decrypt
from .hill import hill_decrypt
from .playfair import playfair_decrypt
