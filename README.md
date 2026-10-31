# Framework de chiffrement (SSAD TP1) — Parties 1, 2 & 3

Travail pratique du cours SSAD, USTHB 2026-2027. Python 3, bibliothèque standard uniquement.

Ce dépôt regroupe dans **une seule interface** :

- **Partie 1 & 2** — interface de messagerie entre une entité A (émetteur) et une
  entité B (récepteur), avec les chiffrements César, Hill et Playfair.
- **Partie 3** — gestion des mots de passe : stockage sécurisé, connexion avec
  verrouillage, et simulation d'attaques (dictionnaire, force brute, combinée).

La logique des deux parties **n'a pas été modifiée**. Les modules `partie2/` et
`passwords/` sont repris tels quels depuis les dépôts d'origine. L'intégration se
limite à réunir les deux applications dans un seul `app.py` à deux onglets : la
partie 3, qui était une fenêtre `tk.Tk` autonome, devient un onglet (`ttk.Frame`).

## Lancement

```
python app.py
python tests_partie2.py
```

## Contenu

| Fichier | Rôle |
|---------|------|
| `app.py` | Interface Tkinter à deux onglets (Messagerie + Mots de passe) |
| `partie2/` | Package de la partie 2 (César, Hill, Playfair et leurs outils) |
| `passwords/` | Package de la partie 3 (stockage, attaques, protection) |
| `tests_partie2.py` | Tests des chiffrements de la partie 2 |

### Partie 2 — `partie2/`

| Fichier | Rôle |
|---------|------|
| `ciphers.py` | Façade commune pour César, Hill, Playfair et leurs outils d'analyse |
| `cesar.py` | Chiffrement de César et analyse de fréquence |
| `hill.py` | Chiffrement de Hill et attaque à clair connu |
| `playfair.py` | Chiffrement de Playfair et comptage des digrammes |
| `canal.py` | Encodage/décodage du canal `code:direction:chiffré` |

### Partie 3 — `passwords/`

| Fichier | Rôle |
|---------|------|
| `charsets.py` | Alphabets et définition des 3 cas du sujet |
| `crypto.py` | Stockage des identifiants (sel + chiffré César), empreintes de démo |
| `caesar.py` | Chiffrement César sur ASCII imprimable + dérivation de clé |
| `dictionary.py` | Attaque par dictionnaire |
| `brute_force.py` | Attaque par force brute |
| `attacks.py` | Attaque combinée (dictionnaire puis force brute) |
| `protection.py` | Politique de robustesse + verrouillage des tentatives |
| `utils.py` | Fonctions utilitaires partagées |

## Onglet « Messagerie » (Partie 1 & 2)

- L'entité A saisit un message en clair, choisit l'algorithme, la clé et le sens (César).
- **Chiffrer et envoyer** place le résultat dans le canal.
- L'entité B récupère le message chiffré et utilise **Déchiffrer**.
- Le canal contient le code binaire de l'algorithme, la direction pour César et le
  texte chiffré ; la clé secrète n'est pas transmise par le chiffrement lui-même.

## Onglet « Mots de passe » (Partie 3)

- **Zone A (serveur)** : choix du cas du TP (3 car. 0/1, 4 car. 1..4, ou libre),
  création de compte, affichage du stockage (sel, chiffré) — le mot de passe en
  clair n'est jamais stocké.
- **Zone B (utilisateur légitime)** : connexion, mesure du temps de vérification,
  verrouillage après plusieurs échecs.
- **Zone C (attaquant hors-ligne)** : attaque par dictionnaire, force brute ou
  combinée sur le chiffré volé, avec moniteur en temps réel.

## Remarque

La partie 4 (Authenticité / Intégrité) n'est pas incluse dans ce dépôt.
