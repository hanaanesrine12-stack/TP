"""Attaque par force brute — compare les digests (plus rapide)."""
import itertools
import time
from .crypto import fingerprint_bytes


def brute_force(target_hash, charset, length, max_attempts=None, max_seconds=None):
    """Parcourt tout l'espace de recherche à la recherche du mot de passe.

    Retourne (mot_trouvé_ou_None, nb_essais, secondes, raison_arret) :
    - raison_arret vaut None si le mot de passe a été trouvé ;
    - "time_limit" si max_seconds a été atteint ;
    - "attempt_limit" si max_attempts a été atteint ;
    - "exhausted" si tout l'espace de recherche a été parcouru sans succès.
    """
    target = bytes.fromhex(target_hash)
    start = time.perf_counter()
    attempts = 0
    for tup in itertools.product(charset, repeat=length):
        attempts += 1
        if fingerprint_bytes("".join(tup)) == target:
            return "".join(tup), attempts, time.perf_counter() - start, None
        if max_seconds is not None and (time.perf_counter() - start) >= max_seconds:
            return None, attempts, time.perf_counter() - start, "time_limit"
        if max_attempts is not None and attempts >= max_attempts:
            return None, attempts, time.perf_counter() - start, "attempt_limit"
    return None, attempts, time.perf_counter() - start, "exhausted"