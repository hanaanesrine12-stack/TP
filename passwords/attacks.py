"""Attaque combinée : dictionnaire d'abord, force brute ensuite."""
from .dictionary import dictionary_attack
from .brute_force import brute_force


def combined_attack(target_hash, charset, length, max_attempts=5_000_000, max_seconds=None):
    """Lance le dictionnaire puis, en cas d'échec, la force brute.

    Retourne (mot_trouvé_ou_None, tentatives_totales, secondes_totales,
    methode, raison_arret) :
    - methode vaut "dictionnaire" ou "force brute" selon la phase où la
      recherche s'est arrêtée (trouvé ou non) ;
    - raison_arret est None si trouvé, "dictionary_exhausted" si le
      dictionnaire était épuisé sans passer à la force brute (ne devrait pas
      arriver ici car on enchaîne toujours), sinon la raison renvoyée par
      brute_force ("time_limit", "attempt_limit", "exhausted").
    """
    found, t1, s1 = dictionary_attack(target_hash)
    if found is not None:
        return found, t1, s1, "dictionnaire", None
    found, t2, s2, reason = brute_force(
        target_hash, charset, length,
        max_attempts=max_attempts, max_seconds=max_seconds,
    )
    return found, t1 + t2, s1 + s2, "force brute", reason