"""Compatibility facade for the Caesar, Hill, and Playfair modules."""

from .canal import (
    ALGORITHM_CODES,
    build_channel_message,
    decode_channel_message,
    dechiffrement_automatique,
)
from .cesar import (
    ALPHA,
    caesar,
    caesar_prepare,
    caesar_decrypt,
    caesar_restore,
    clean,
    validate_key,
)
from .hill import (
    det,
    format_positions,
    hill_apply,
    hill_decrypt,
    hill_encrypt,
    key_from_text,
    mat_inverse_mod,
    restore_format,
)
from .playfair import (
    playfair_decrypt,
    playfair_encrypt,
    playfair_j_positions,
    playfair_prepare,
    playfair_pairs,
    playfair_restore_j,
    playfair_square,
    playfair_strip_padding,
    playfair_swap,
)
