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
    caesar_decrypt,
    caesar_frequency_guess,
    clean,
)
from .hill import (
    block_matrix,
    det,
    format_positions,
    hill_apply,
    hill_decrypt,
    hill_encrypt,
    hill_known_plaintext,
    key_from_text,
    mat_inverse_mod,
    mat_mul_mod,
    restore_format,
)
from .playfair import (
    digram_counts,
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
