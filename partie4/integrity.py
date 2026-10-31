"""Partie 4 — Intégrité d'un message chiffré avec SHA-256.

Principe (H = SHA256(C), où C est le message chiffré) :
- Émetteur (Alice) : chiffre son message (partie 2), calcule H = SHA256(C)
  et transmet C et H sur le canal.
- Récepteur (Bob)  : reçoit C' et H, recalcule H' = SHA256(C') et compare.
      H == H'  ->  intégrité vérifiée, le déchiffrement est autorisé
      H != H'  ->  message modifié, le déchiffrement est bloqué

Aucune dépendance externe : uniquement hashlib / hmac de la bibliothèque standard.
"""

import hashlib
import hmac


def sha256_hex(message):
    """Empreinte SHA-256 (64 caractères hexadécimaux) d'un texte."""
    return hashlib.sha256(message.encode("utf-8")).hexdigest()


def verify_hash(received_message, received_hash):
    """Recalcule H' = SHA256(C') et le compare à H (comparaison à temps constant)."""
    computed = sha256_hex(received_message)
    return hmac.compare_digest(computed, (received_hash or "").strip().lower())