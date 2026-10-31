
from partie2 import ciphers

from .hachage import sha256_hex, sha256_manuel

ALGORITHMES = ["Caesar", "Hill", "Playfair"]
CLES_PAR_DEFAUT = {"Caesar": "3", "Hill": "3,3,2,5", "Playfair": "monarchy"}


def lire_cle_hill(texte):
    if "," in texte:
        nombres = [int(x) for x in texte.split(",")]
        taille = int(len(nombres) ** 0.5)
        if taille * taille != len(nombres):
            raise ValueError("la matrice de Hill doit être carrée")
        return [nombres[i * taille:(i + 1) * taille] for i in range(taille)]
    return ciphers.key_from_text(texte)


class Chiffrement:
    """Chiffre et déchiffre avec César, Hill ou Playfair (partie 2).

    Comme dans l'interface de la partie 2, les positions des espaces, de la
    ponctuation et des lettres ajoutées sont mémorisées au chiffrement puis
    réutilisées au déchiffrement. Ce sont des métadonnées publiques : la clé
    n'est jamais placée dans le canal.
    """

    def __init__(self):
        self.positions_format = []
        self.remplissage_hill = 0
        self.positions_x = []
        self.positions_j = []

    def chiffrer(self, algorithme, texte, cle, sens="droite"):
        """Retourne le message du canal C, au format code:sens:chiffré."""
        if algorithme == "Caesar":
            chiffre = ciphers.caesar(texte, int(cle), sens)
        elif algorithme == "Hill":
            cle_hill = lire_cle_hill(cle)
            self.positions_format = ciphers.format_positions(texte.upper())
            self.remplissage_hill = (-len(ciphers.clean(texte))) % len(cle_hill)
            chiffre = ciphers.hill_encrypt(texte, cle_hill)
        elif algorithme == "Playfair":
            self.positions_format = ciphers.format_positions(texte.upper())
            self.positions_x = ciphers.playfair_prepare(texte)[1]
            self.positions_j = ciphers.playfair_j_positions(texte)
            chiffre = ciphers.playfair_encrypt(texte, cle)
        else:
            raise ValueError("algorithme inconnu")
        return ciphers.build_channel_message(algorithme, sens, chiffre)

    def dechiffrer(self, message_canal, cle):
        algorithme = ciphers.decode_channel_message(message_canal)[0]
        if algorithme == "Caesar":
            return ciphers.dechiffrement_automatique(message_canal, int(cle))
        if algorithme == "Hill":
            clair = ciphers.dechiffrement_automatique(message_canal, cle, hill_key=lire_cle_hill(cle))
            if self.remplissage_hill:
                clair = clair[:-self.remplissage_hill]
            return ciphers.restore_format(clair, self.positions_format)
        clair = ciphers.dechiffrement_automatique(message_canal, cle)
        clair = ciphers.playfair_strip_padding(clair, self.positions_x)
        clair = ciphers.playfair_restore_j(clair, self.positions_j)
        return ciphers.restore_format(clair, self.positions_format)


def envoyer(chiffrement, algorithme, message, cle, sens="droite"):
    """Entité A : retourne (C, H) avec H = SHA256(C)."""
    c = chiffrement.chiffrer(algorithme, message, cle, sens)
    return c, sha256_hex(c)


def verifier(c_recu, h_recu):
    """Entité B : retourne (H = H', H') avec H' = SHA256(C')."""
    h_calcule = sha256_hex(c_recu)
    return h_calcule == h_recu.strip().lower(), h_calcule


def recevoir(chiffrement, c_recu, h_recu, cle):
    """Entité B : vérifie l'empreinte puis déchiffre seulement si H = H'.

    Retourne (intègre, H', message déchiffré ou None).
    """
    integre, h_calcule = verifier(c_recu, h_recu)
    if not integre:
        return False, h_calcule, None
    return True, h_calcule, chiffrement.dechiffrer(c_recu, cle)


def suivante(lettre):
    base = ord("A") if lettre.isupper() else ord("a")
    return chr(base + (ord(lettre) - base + 1) % 26)


def falsifier(message_canal):
    """Simule un attaquant : change la première lettre du chiffré (X -> Y).

    Le hash transmis n'est pas modifié. Retourne (C modifié, n° du caractère,
    ancienne lettre, nouvelle lettre).
    """
    prefixe, separateur, chiffre = message_canal.rpartition(":")
    for i, lettre in enumerate(chiffre):
        if lettre.isalpha():
            nouvelle = suivante(lettre)
            modifie = chiffre[:i] + nouvelle + chiffre[i + 1:]
            return prefixe + separateur + modifie, i + 1, lettre, nouvelle
    raise ValueError("aucune lettre à modifier dans le message chiffré")


__all__ = [
    "ALGORITHMES", "CLES_PAR_DEFAUT", "Chiffrement", "envoyer", "verifier", "recevoir",
    "falsifier", "sha256_hex", "sha256_manuel",
]