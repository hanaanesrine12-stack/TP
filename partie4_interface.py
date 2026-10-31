"""Partie 4 — Interface : intégrité d'un message chiffré avec SHA-256.

Entity A (émetteur)  : chiffre le message (César / Playfair / Hill, partie 2),
                       calcule H = SHA256(C) et envoie C et H sur le canal.
Canal                : transporte C et H ; l'attaquant peut modifier C
                       (« Simulate tampering »), « Reset to original » annule.
Entity B (récepteur) : recalcule H' = SHA256(C'), compare avec H, et ne
                       déchiffre QUE si H = H'.

C est le message chiffré tel que transmis par la partie 2
(« code algo : sens : clé : texte chiffré »), pour que B puisse déchiffrer
automatiquement et pour que l'algorithme et la clé soient eux aussi protégés.
"""

import tkinter as tk
from tkinter import messagebox, ttk

import database
from partie2 import ciphers
from partie2_interface import COLORS, _auto_decrypt, _get_text, _set_text
from partie4 import integrity

DANGER = "#C0392B"


def _hill_key_matrix(key_text):
    try:
        numbers = [int(value.strip()) for value in key_text.split(",")]
    except ValueError as error:
        raise ValueError("La clé Hill doit être des entiers séparés par des virgules (ex: 3,3,2,5).") from error
    size = int(len(numbers) ** 0.5)
    if size < 2 or size * size != len(numbers):
        raise ValueError("La clé Hill doit former une matrice carrée (ex: 3,3,2,5).")
    return [numbers[index:index + size] for index in range(0, len(numbers), size)]


def _raw(box):
    """Contenu exact d'une zone de texte (sans strip : les espaces comptent dans le hash)."""
    return box.get("1.0", "end-1c")


def _make_box(parent, height, code=False, readonly=False):
    box = tk.Text(parent, height=height, width=18, wrap="char" if code else "word",
                  relief="flat", highlightthickness=1,
                  bg=COLORS["surface_dark"] if code else COLORS["surface"],
                  fg=COLORS["code"] if code else COLORS["text"],
                  insertbackground=COLORS["text"],
                  highlightbackground=COLORS["border"],
                  font=("Consolas", 9) if code else ("Segoe UI", 10))
    if readonly:
        box.config(state="disabled")
    return box


def _caption(parent, text):
    ttk.Label(parent, text=text, foreground=COLORS["muted"]).pack(anchor="w", pady=(8, 2))


class Partie4Page(ttk.Frame):
    """Démonstrateur : chiffrement -> SHA-256 -> canal (attaquable) -> vérification -> déchiffrement."""

    def __init__(self, parent, user):
        super().__init__(parent, padding=14)
        self.user = user
        self.original_message = ""   # C tel qu'envoyé par A
        self.original_hash = ""      # H tel qu'envoyé par A
        self._build()
        self.refresh_users()

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------
    def _build(self):
        ttk.Label(self, text="Partie 4 — Intégrité avec SHA-256",
                  font=("Segoe UI", 18, "bold")).pack(anchor="w")
        ttk.Label(self, text="Alice envoie C et H = SHA256(C). Bob recalcule H' = SHA256(C') : "
                             "il ne déchiffre que si H = H'.",
                  foreground=COLORS["muted"]).pack(anchor="w", pady=(3, 10))

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)
        for column in range(3):
            body.columnconfigure(column, weight=1, uniform="p4")
        body.rowconfigure(0, weight=1)

        self.frame_a = ttk.LabelFrame(body, text="Entity A — Sender", padding=10)
        self.frame_a.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        self.frame_c = ttk.LabelFrame(body, text="Transmission Channel", padding=10)
        self.frame_c.grid(row=0, column=1, sticky="nsew", padx=6)
        self.frame_b = ttk.LabelFrame(body, text="Entity B — Receiver", padding=10)
        self.frame_b.grid(row=0, column=2, sticky="nsew", padx=(6, 0))

        self._build_sender(self.frame_a)
        self._build_channel(self.frame_c)
        self._build_receiver(self.frame_b)

    def _build_sender(self, frame):
        _caption(frame, "Récepteur")
        row = ttk.Frame(frame)
        row.pack(fill="x")
        self.receiver = ttk.Combobox(row, state="readonly", width=12)
        self.receiver.pack(side="left", fill="x", expand=True)
        ttk.Button(row, text="↻", width=3, command=self.refresh_users).pack(side="left", padx=(6, 0))

        _caption(frame, "Algorithme")
        self.algorithm = ttk.Combobox(frame, state="readonly", values=("Caesar", "Playfair", "Hill"))
        self.algorithm.current(0)
        self.algorithm.pack(fill="x")
        self.algorithm.bind("<<ComboboxSelected>>", self.change_algorithm)

        _caption(frame, "Clé de chiffrement")
        self.key = ttk.Entry(frame)
        self.key.pack(fill="x")
        _caption(frame, "Sens (César)")
        self.direction = ttk.Combobox(frame, state="readonly", values=("droite", "gauche"))
        self.direction.current(0)
        self.direction.pack(fill="x")
        self.change_algorithm()

        _caption(frame, "Message original")
        self.message = _make_box(frame, 3)
        self.message.pack(fill="x")
        self.message.insert("1.0", "Retrouve-moi a la bibliotheque a midi")

        ttk.Button(frame, text="🔒 Chiffrer et envoyer", style="Primary.TButton",
                   command=self.send).pack(fill="x", pady=(10, 0))

        _caption(frame, "Message chiffré généré")
        self.cipher_box = _make_box(frame, 3, code=True, readonly=True)
        self.cipher_box.pack(fill="x")
        _caption(frame, "Generated SHA-256 Hash")
        self.hash_box = _make_box(frame, 3, code=True, readonly=True)
        self.hash_box.pack(fill="x")

    def _build_channel(self, frame):
        _caption(frame, "Message chiffré (C)")
        self.channel_c = _make_box(frame, 5, code=True, readonly=True)
        self.channel_c.pack(fill="x")
        _caption(frame, "Hash transmis (H)")
        self.channel_h = _make_box(frame, 3, code=True, readonly=True)
        self.channel_h.pack(fill="x")

        ttk.Button(frame, text="⚠ Simulate tampering", command=self.simulate_tampering).pack(fill="x", pady=(14, 4))
        ttk.Button(frame, text="↺ Reset to original", command=self.reset_to_original).pack(fill="x")

        self.channel_info = ttk.Label(frame, text="Aucun message sur le canal.",
                                      foreground=COLORS["muted"], wraplength=250, justify="left")
        self.channel_info.pack(anchor="w", pady=(12, 0))

    def _build_receiver(self, frame):
        _caption(frame, "Message chiffré reçu (C')")
        self.received_c = _make_box(frame, 4, code=True, readonly=True)
        self.received_c.pack(fill="x")
        _caption(frame, "Hash reçu (H)")
        self.received_h = _make_box(frame, 3, code=True, readonly=True)
        self.received_h.pack(fill="x")
        _caption(frame, "Computed SHA-256 Hash (H')")
        self.computed_h = _make_box(frame, 3, code=True, readonly=True)
        self.computed_h.pack(fill="x")

        ttk.Button(frame, text="🔓 Vérifier et déchiffrer", style="Primary.TButton",
                   command=self.verify_and_decrypt).pack(fill="x", pady=(10, 0))
        self.verdict = ttk.Label(frame, text="Aucun message reçu.", foreground=COLORS["muted"],
                                 font=("Segoe UI", 10, "bold"), wraplength=250, justify="left")
        self.verdict.pack(anchor="w", pady=(8, 0))

        _caption(frame, "Message déchiffré")
        self.decrypted = _make_box(frame, 3, readonly=True)
        self.decrypted.pack(fill="x")

    # ------------------------------------------------------------------
    # Entity A
    # ------------------------------------------------------------------
    def change_algorithm(self, event=None):
        defaults = {"Caesar": ("3", "readonly"), "Playfair": ("monarchy", "disabled"),
                    "Hill": ("3,3,2,5", "disabled")}
        key, direction_state = defaults[self.algorithm.get()]
        self.key.delete(0, "end")
        self.key.insert(0, key)
        self.direction.config(state=direction_state)

    def refresh_users(self):
        try:
            users = [row["pseudo"] for row in database.list_users()
                     if row["pseudo"] != self.user.get("pseudo")]
        except database.DatabaseError as error:
            messagebox.showerror("Destinataires", str(error))
            users = []
        self.receiver["values"] = users
        if users:
            self.receiver.current(0)

    def _encrypt(self, text, name, key, direction):
        if name == "Caesar":
            try:
                shift = int(key)
            except ValueError as error:
                raise ValueError("La clé César doit être un entier.") from error
            return ciphers.caesar(text, shift, direction)
        if name == "Hill":
            return ciphers.hill_encrypt(text, _hill_key_matrix(key))
        return ciphers.playfair_encrypt(text, key)

    def send(self):
        text = _get_text(self.message)
        name = self.algorithm.get()
        key = self.key.get().strip()
        if not self.receiver.get():
            messagebox.showwarning("Message", "Choisissez un récepteur.")
            return
        if not ciphers.clean(text):
            messagebox.showwarning("Message", "Le message doit contenir au moins une lettre.")
            return
        direction = self.direction.get() if name == "Caesar" else ""
        try:
            encrypted = self._encrypt(text, name, key, direction)
            channel_message = ciphers.build_channel_message(name, direction, encrypted, key)
        except ValueError as error:
            messagebox.showerror("Chiffrement impossible", str(error))
            return

        digest = integrity.sha256_hex(channel_message)          # H = SHA256(C)
        self.original_message, self.original_hash = channel_message, digest
        _set_text(self.cipher_box, channel_message)
        _set_text(self.hash_box, digest)
        self._publish(channel_message, digest)
        self.channel_info.config(text="Message envoyé à %s. Canal intact." % self.receiver.get(),
                                 foreground=COLORS["success"])

    # ------------------------------------------------------------------
    # Canal
    # ------------------------------------------------------------------
    def _publish(self, message, digest):
        """Met C et H sur le canal puis les délivre à B."""
        _set_text(self.channel_c, message)
        _set_text(self.channel_h, digest)
        self._deliver()

    def _deliver(self):
        """B reçoit C' et H, et calcule tout de suite H' = SHA256(C')."""
        received = _raw(self.channel_c)
        _set_text(self.received_c, received)
        _set_text(self.received_h, _raw(self.channel_h))
        _set_text(self.computed_h, integrity.sha256_hex(received))
        _set_text(self.decrypted, "")
        self.verdict.config(text="Message reçu : cliquez sur « Vérifier et déchiffrer ».",
                            foreground=COLORS["muted"])

    @staticmethod
    def _mutate(value):
        """Change un seul caractère (première lettre ou chiffre). Retourne (nouveau, index, ancien, nouveau_car)."""
        for index, char in enumerate(value):
            if char.isascii() and char.isalpha():
                base = "A" if char.isupper() else "a"
                new_char = chr((ord(char) - ord(base) + 1) % 26 + ord(base))
            elif char.isdigit():
                new_char = str((int(char) + 1) % 10)
            else:
                continue
            return value[:index] + new_char + value[index + 1:], index + 1, char, new_char
        return None

    def simulate_tampering(self):
        if not self.original_message:
            messagebox.showinfo("Canal", "Aucun message sur le canal : chiffrez et envoyez d'abord un message.")
            return
        # C = « code : sens : clé : texte chiffré » -> l'attaquant modifie le texte chiffré.
        parts = _raw(self.channel_c).split(":", 3)
        mutated = self._mutate(parts[3]) if len(parts) == 4 else None
        if mutated is None:
            messagebox.showinfo("Canal", "Impossible de modifier ce message.")
            return
        parts[3], position, old, new = mutated
        _set_text(self.channel_c, ":".join(parts))
        self._deliver()          # le hash H, lui, n'est pas modifié
        self.channel_info.config(
            text="⚠ Modifié en transit : caractère n°%d du chiffré « %s » → « %s ». "
                 "Le hash transmis est resté celui d'origine." % (position, old, new),
            foreground=DANGER)

    def reset_to_original(self):
        if not self.original_message:
            messagebox.showinfo("Canal", "Aucun message envoyé.")
            return
        self._publish(self.original_message, self.original_hash)
        self.channel_info.config(text="Message d'origine restauré sur le canal.",
                                 foreground=COLORS["success"])

    # ------------------------------------------------------------------
    # Entity B
    # ------------------------------------------------------------------
    def verify_and_decrypt(self):
        received = _raw(self.received_c)
        if not received:
            messagebox.showinfo("Réception", "Aucun message reçu.")
            return
        sent_hash = _raw(self.received_h)
        _set_text(self.computed_h, integrity.sha256_hex(received))   # H'
        _set_text(self.decrypted, "")

        if not integrity.verify_hash(received, sent_hash):           # H != H'
            self.verdict.config(
                text="❌ Message modifié : H ≠ H'. Déchiffrement bloqué.", foreground=DANGER)
            return

        try:
            algorithm, plaintext = _auto_decrypt(received)
        except ValueError as error:
            self.verdict.config(text="⚠ Intégrité vérifiée, mais déchiffrement impossible.",
                                foreground=DANGER)
            messagebox.showerror("Déchiffrement", str(error))
            return
        self.verdict.config(text="✅ Intégrité vérifiée : H = H'. Déchiffré (%s)." % algorithm,
                            foreground=COLORS["success"])
        _set_text(self.decrypted, plaintext)