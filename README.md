# Framework de chiffrement (SSAD TP1)

Travail pratique du cours SSAD, USTHB 2026-2027. Python 3, bibliothèque standard uniquement.

Ce dépôt contient une interface de messagerie entre une entité A (émetteur) et
une entité B (récepteur), ainsi que les implémentations des chiffrements de la
partie 2.

## Lancement

```
python app.py
python tests_partie2.py
```

## Contenu

| Fichier | Rôle |
|---------|------|
| `partie2/__init__.py` | Package Python de la partie 2 |
| `partie2/ciphers.py` | Facade commune pour César, Hill, Playfair et leurs outils d'analyse |
| `partie2/cesar.py` | Chiffrement de César et analyse de fréquence |
| `partie2/hill.py` | Chiffrement de Hill et attaque à clair connu |
| `partie2/playfair.py` | Chiffrement de Playfair et comptage des digrammes |
| `app.py` | Interface Tkinter de messagerie entre A et B |
| `tests_partie2.py` | Tests des chiffrements |
| `code_interface.pdf` | Code de la partie 1 |
| `code_chiffrements.pdf` | Code de la partie 2 avec explications |
| `report.pdf` | Rapport |

## Fonctionnement de l'interface

- L'entité A saisit un message en clair et choisit l'algorithme, la clé et le sens pour César.
- Le bouton **Chiffrer et envoyer** place le résultat dans le canal.
- L'entité B récupère le message chiffré et utilise **Déchiffrer** pour afficher le message original.
- Le canal contient le code binaire de l'algorithme, la direction pour César et le texte chiffré ; il ne contient pas la clé secrète.
- B reçoit automatiquement l'algorithme et la direction du message, puis saisit sa clé séparément.
- L'interface ne contient plus d'onglet ni de bouton dédié à la simulation d'attaques.

## Remarques

- Le code de l'algorithme est une métadonnée publique et ne constitue pas une protection cryptographique.
- Pour Hill, le canal contient uniquement les lettres chiffrées. Les positions des espaces et de la ponctuation sont mémorisées séparément, puis réutilisées après le déchiffrement.
- Playfair utilise maintenant la même méthode : le canal contient uniquement les lettres chiffrées, puis les positions mémorisées restaurent les espaces et la ponctuation après le déchiffrement.
- Playfair mémorise également les positions exactes des `X` ajoutés pendant la préparation des paires. Ainsi, un vrai `X` du message n'est pas supprimé par erreur lors du déchiffrement.
- Playfair mémorise les positions des `J` remplacés par `I` dans la grille 5x5, puis restaure ces `J` après le déchiffrement. La liste de positions est une métadonnée publique ; la clé secrète n'est pas transmise.
- Hill peut ajouter `X` pour compléter son dernier bloc, et Playfair peut ajouter `X` pour préparer ses paires. L'interface retire ces remplissages au déchiffrement ; un véritable `X` final peut donc nécessiter une convention supplémentaire.
- L'interface ne propose pas de fonctionnalité d'attaque par force brute.
- Le message du canal utilise le format `code:direction:chiffré` : `000` pour César, `001` pour Hill et `010` pour Playfair. La direction vaut `r` ou `l` uniquement pour César. La fonction `dechiffrement_automatique()` lit ces métadonnées et choisit automatiquement le déchiffrement sans transmettre la clé secrète.
- Les fichiers `code_interface.pdf` et `report.pdf` décrivent une version plus complète (mots de passe, HMAC, `tests.py`) dont les fichiers ne sont pas dans ce dépôt.

## Répartition du travail

| Membre | Tâche |
|--------|-------|
| 1 | Chiffrement de César et ses attaques |
| 2 | Chiffrement de Hill et attaque à clair connu |
| 3 | Chiffrement de Playfair et analyse des digrammes |
| 4 | Interface et tests |
