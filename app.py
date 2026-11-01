"""
Framework de chiffrement - SSAD TP1
===================================

Interface unique regroupant :
- Onglet "Messagerie"     : Partie 1 & 2 (chiffrement / déchiffrement A -> B)
- Onglet "Mots de passe"  : Partie 3 (stockage, connexion, attaques)

La logique des deux parties n'a pas été modifiée : les modules `partie2` et
`passwords` sont importés tels quels, et le code des onglets reprend fidèlement
celui des deux applications d'origine. Seul le conteneur change : la partie 3,
qui était une fenêtre `tk.Tk` autonome, devient un `ttk.Frame` (onglet).
"""

import time
import itertools
import tkinter as tk
from tkinter import ttk, messagebox

from partie2 import ciphers
import database
import passwords
from passwords import caesar, db
from partie2_interface import Partie2Page, InboxPage, NotificationsPage
from partie3_interface import Partie3Page
from partie4_interface import Partie4Page

COLORS = {
    "background": "#EAF3FF",
    "surface": "#FFFFFF",
    "surface_dark": "#F4F8FD",
    "text": "#1D2A3A",
    "muted": "#637083",
    "accent": "#2F75D6",
    "success": "#2DAA68",
    "border": "#C5D6EA",
    "code_text": "#176B3A",
}


def configure_style(window):
    style = ttk.Style(window)
    style.theme_use("clam")
    style.configure(".",
                    background=COLORS["background"],
                    foreground=COLORS["text"],
                    font=("Segoe UI", 10))
    style.configure("TFrame", background=COLORS["background"])
    style.configure("Surface.TFrame", background=COLORS["surface"])
    style.configure("TLabel", background=COLORS["background"], foreground=COLORS["text"])
    style.configure("Muted.TLabel", background=COLORS["surface"], foreground=COLORS["muted"])
    style.configure("TLabelframe", background=COLORS["surface"], foreground=COLORS["text"])
    style.configure("TLabelframe.Label", background=COLORS["surface"], foreground=COLORS["text"],
                    font=("Segoe UI", 10, "bold"))
    style.configure("TEntry", fieldbackground=COLORS["surface_dark"], foreground=COLORS["text"])
    style.configure("TCombobox", fieldbackground=COLORS["surface_dark"], foreground=COLORS["text"])
    style.map("TCombobox", fieldbackground=[("readonly", COLORS["surface_dark"])])
    style.configure("TNotebook", background=COLORS["background"], borderwidth=0)
    style.configure("TNotebook.Tab", background=COLORS["surface"], foreground=COLORS["muted"],
                    padding=(18, 8), font=("Segoe UI", 10, "bold"))
    style.map("TNotebook.Tab", background=[("selected", COLORS["accent"])],
              foreground=[("selected", "white")])
    style.configure("Primary.TButton", background=COLORS["accent"], foreground="white",
                    padding=(14, 8), font=("Segoe UI", 10, "bold"), borderwidth=0)
    style.map("Primary.TButton", background=[("active", "#6EA4FF")])
    style.configure("Success.TButton", background=COLORS["success"], foreground="#102419",
                    padding=(14, 8), font=("Segoe UI", 10, "bold"), borderwidth=0)
    style.map("Success.TButton", background=[("active", "#5DE29A")])


def read_hill_key(text):
    if "," in text:
        numbers = [int(x) for x in text.split(",")]
        size = int(len(numbers) ** 0.5)
        if size * size != len(numbers):
            raise ValueError("la matrice doit être carrée")
        return [numbers[i * size:(i + 1) * size] for i in range(size)]
    return ciphers.key_from_text(text)


def make_text_box(parent, height, code=False):
    box = tk.Text(
        parent,
        height=height,
        wrap="word",
        bg=COLORS["surface_dark"] if code else "#FFFFFF",
        fg=COLORS["code_text"] if code else COLORS["text"],
        insertbackground=COLORS["text"],
        selectbackground=COLORS["accent"],
        relief="flat",
        borderwidth=0,
        highlightthickness=1,
        highlightbackground=COLORS["border"],
        highlightcolor=COLORS["accent"],
        font=("Consolas", 10) if code else ("Segoe UI", 10),
    )
    box.pack(fill="both", expand=True)
    return box


def set_text(box, text):
    box.config(state="normal")
    box.delete("1.0", "end")
    box.insert("1.0", text)
    box.config(state="disabled")


def get_text(box):
    return box.get("1.0", "end").strip()


def update_monitor(box, text):
    box.config(state="normal")
    box.delete("1.0", "end")
    box.insert("1.0", text)
    box.config(state="disabled")
    box.update_idletasks()


def fmt_duration(seconds):
    """Formatage uniforme d'une durée mesurée."""
    if seconds < 1e-3:
        return "%.3f ms" % (seconds * 1e3)
    if seconds < 1:
        return "%.1f ms" % (seconds * 1e3)
    if seconds < 60:
        return "%.2f s" % seconds
    if seconds < 3600:
        return "%.1f min" % (seconds / 60)
    return "%.1f h" % (seconds / 3600)


CASES = passwords.CASES


class MessagingTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, padding=10)
        self.build_settings()
        self.build_entity_a()
        self.build_channel()
        self.build_entity_b()
        self.change_algorithm()

    def build_settings(self):
        settings = ttk.Frame(self)
        settings.pack(fill="x")
        ttk.Label(settings, text="Algorithme").grid(row=0, column=0)
        self.algorithm = ttk.Combobox(
            settings, values=["Caesar", "Hill", "Playfair"],
            state="readonly", width=12,
        )
        self.algorithm.current(0)
        self.algorithm.grid(row=0, column=1, padx=6)
        self.algorithm.bind("<<ComboboxSelected>>", self.change_algorithm)
        ttk.Label(settings, text="Clé secrète de A").grid(row=0, column=2)
        self.key_a = ttk.Entry(settings, width=22)
        self.key_a.grid(row=0, column=3, padx=6)
        ttk.Label(settings, text="Sens").grid(row=0, column=4)
        self.direction = ttk.Combobox(
            settings, values=["droite", "gauche"], state="readonly", width=8,
        )
        self.direction.current(0)
        self.direction.grid(row=0, column=5, padx=6)

    def build_entity_a(self):
        frame = ttk.LabelFrame(self, text="Entité A", padding=6)
        frame.pack(fill="both", expand=True, pady=6)
        self.message = make_text_box(frame, 4)
        self.message.insert("1.0", "Retrouve-moi a la bibliotheque a midi")
        ttk.Button(frame, text="🔒 Chiffrer et envoyer", style="Primary.TButton", command=self.send).pack(
            anchor="e", pady=4
        )

    def build_channel(self):
        channel = ttk.LabelFrame(self, text="Canal", padding=6)
        channel.pack(fill="both", expand=True, pady=6)
        self.channel_info = ttk.Label(channel, text="Aucun message envoyé.", style="Muted.TLabel")
        self.channel_info.pack(anchor="w", pady=(0, 4))
        self.cipher_box = make_text_box(channel, 3, code=True)
        self.cipher_box.config(state="disabled")

    def build_entity_b(self):
        frame = ttk.LabelFrame(self, text="Entité B", padding=6)
        frame.pack(fill="both", expand=True, pady=6)
        settings = ttk.Frame(frame)
        settings.pack(fill="x", pady=(0, 4))
        ttk.Label(settings, text="Algorithme détecté automatiquement").pack(side="left")
        self.algorithm_b = ttk.Label(settings, text="non détecté", width=12)
        self.algorithm_b.pack(side="left", padx=6)
        ttk.Label(settings, text="Sens détecté").pack(side="left")
        self.direction_b = ttk.Label(settings, text="non applicable", width=8)
        self.direction_b.pack(side="left", padx=6)

        key_frame = ttk.Frame(frame)
        key_frame.pack(fill="x", pady=(0, 4))
        ttk.Label(key_frame, text="Clé détectée dans le canal :").pack(side="left")
        self.key_b = ttk.Label(key_frame, text="non détectée")
        self.key_b.pack(side="left", padx=6)
        self.result_box = make_text_box(frame, 4, code=True)
        self.result_box.config(state="disabled")
        bottom = ttk.Frame(frame)
        bottom.pack(fill="x", pady=4)
        self.status = ttk.Label(bottom)
        self.status.pack(side="left")
        ttk.Button(bottom, text="🔓 Déchiffrer", style="Success.TButton", command=self.receive).pack(side="right")

        self.sent_ciphertext = ""
        self.sent_algorithm = ""
        self.sent_direction = ""
        self.hill_format_positions = []
        self.hill_padding = 0
        self.playfair_format_positions = []
        self.playfair_padding_positions = []
        self.playfair_j_positions = []
        self.caesar_mask = ""

    def change_algorithm(self, event=None):
        name = self.algorithm.get()
        settings = {
            "Caesar": ("3", "readonly"),
            "Hill": ("3,3,2,5", "disabled"),
            "Playfair": ("monarchy", "disabled"),
        }
        key, direction_state = settings[name]
        self.key_a.delete(0, "end")
        self.key_a.insert(0, key)
        self.direction.config(state=direction_state)
        set_text(self.result_box, "")

    def encrypt(self, text, key_text):
        name = self.algorithm.get()
        key = key_text
        if name == "Caesar":
            try:
                shift = int(key)
            except ValueError as error:
                raise ValueError("la clé César doit être un entier") from error
            ciphers.validate_key(shift)
            letters, caesar_mask = ciphers.caesar_prepare(text)
            encrypted = ciphers.caesar(letters, shift, self.direction.get())
            self.caesar_mask = caesar_mask
            return encrypted
        if name == "Hill":
            hill_key = read_hill_key(key)
            letters = ciphers.clean(text)
            hill_format_positions = ciphers.format_positions(text.upper())
            hill_padding = (-len(letters)) % len(hill_key)
            encrypted = ciphers.hill_encrypt(text, hill_key)
            self.hill_format_positions = hill_format_positions
            self.hill_padding = hill_padding
            return encrypted
        playfair_format_positions = ciphers.format_positions(text.upper())
        playfair_padding_positions = ciphers.playfair_prepare(text)[1]
        playfair_j_positions = ciphers.playfair_j_positions(text)
        encrypted = ciphers.playfair_encrypt(text, key)
        self.playfair_format_positions = playfair_format_positions
        self.playfair_padding_positions = playfair_padding_positions
        self.playfair_j_positions = playfair_j_positions
        return encrypted

    def decrypt(self, text):
        name = self.sent_algorithm
        key_text = self.key_b.cget("text")
        if not name or key_text == "non détectée":
            raise ValueError("aucune clé dans le canal : déchiffrement automatique impossible")
        if name == "Caesar":
            decrypted = ciphers.dechiffrement_automatique(text, key_text)
            return ciphers.caesar_restore(decrypted, self.caesar_mask)
        if name == "Hill":
            decrypted = ciphers.dechiffrement_automatique(
                text,
                key_text,
                hill_key=read_hill_key(key_text),
            )
            if self.hill_padding:
                decrypted = decrypted[:-self.hill_padding]
            return ciphers.restore_format(decrypted, self.hill_format_positions)
        decrypted = ciphers.dechiffrement_automatique(text, key_text)
        decrypted = ciphers.playfair_strip_padding(
            decrypted,
            self.playfair_padding_positions,
        )
        decrypted = ciphers.playfair_restore_j(
            decrypted,
            self.playfair_j_positions,
        )
        return ciphers.restore_format(decrypted, self.playfair_format_positions)

    def detect_channel(self, channel_message):
        name, direction, key_text, _ = ciphers.decode_channel_message(channel_message)
        if not key_text:
            raise ValueError("aucune clé dans le canal : déchiffrement automatique impossible")
        self.sent_algorithm = name
        self.sent_direction = {"r": "droite", "l": "gauche"}.get(direction, "")
        self.algorithm_b.config(text=name)
        self.direction_b.config(text=self.sent_direction or "non applicable")
        self.key_b.config(text=key_text)

    def send(self):
        key = self.key_a.get().strip()
        text = get_text(self.message)
        if not ciphers.clean(text):
            messagebox.showerror("Erreur", "Le message doit contenir au moins une lettre.")
            return
        try:
            encrypted = self.encrypt(text, key)
            self.sent_algorithm = self.algorithm.get()
            self.sent_direction = self.direction.get()
            channel_message = ciphers.build_channel_message(
                self.sent_algorithm,
                self.sent_direction,
                encrypted,
                key,
            )
        except ValueError as error:
            messagebox.showerror("Erreur", str(error))
            return
        set_text(self.cipher_box, channel_message)
        self.sent_ciphertext = channel_message
        try:
            self.detect_channel(channel_message)
        except ValueError as error:
            messagebox.showerror("Erreur", str(error))
            return
        direction = self.sent_direction if self.sent_algorithm == "Caesar" else "non applicable"
        self.channel_info.config(
            text="Message chiffré | algorithme : %s | sens : %s | clé transmise"
                 % (self.sent_algorithm, direction)
        )
        self.status.config(text="message envoyé", foreground="green")

    def receive(self):
        encrypted = get_text(self.cipher_box)
        if not self.sent_ciphertext:
            messagebox.showerror("Erreur", "Aucun message n'a été envoyé par l'entité A.")
            return
        if not encrypted:
            messagebox.showerror("Erreur", "Le canal est vide : rien à déchiffrer.")
            return
        try:
            decrypted = self.decrypt(encrypted)
        except ValueError as error:
            messagebox.showerror("Erreur", str(error))
            return
        self.status.config(text="message déchiffré", foreground="green")
        set_text(self.result_box, decrypted)


class PasswordsTab(ttk.Frame):
    """Onglet reprenant la fenêtre `App` de la partie 3 (zones A, B, C)."""

    def __init__(self, parent):
        super().__init__(parent, padding=(6, 0))

        self.account = {
            "username": None, "password": None, "record": None,
            "iterations": 200_000, "case": None
        }

        self._build_header()
        self._build_body()

    def _build_header(self):
        header = ttk.Frame(self, padding=(10, 6))
        header.pack(fill="x")
        ttk.Label(header, text="MOTS DE PASSE",
                  font=("TkDefaultFont", 14, "bold")).pack(side="left")

        ttk.Button(header, text="↺ Réinitialiser",
                   command=self.reset_demo).pack(side="right", padx=10)

    def _build_body(self):
        body = ttk.Frame(self, padding=(6, 0))
        body.pack(fill="both", expand=True)

        body.columnconfigure(0, weight=1, uniform="col")
        body.columnconfigure(1, weight=1, uniform="col")
        body.columnconfigure(2, weight=1, uniform="col")
        body.rowconfigure(0, weight=1)

        self.zone_a = ZoneA(body, self)
        self.zone_a.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)

        self.zone_b = ZoneB(body, self)
        self.zone_b.grid(row=0, column=1, sticky="nsew", padx=4, pady=4)

        self.zone_c = ZoneC(body, self)
        self.zone_c.grid(row=0, column=2, sticky="nsew", padx=4, pady=4)

    def require_account(self):
        if self.account["record"] is None:
            messagebox.showinfo("Aucun compte", "Créez d'abord un compte dans la zone A.")
            return False
        return True

    def reset_demo(self):
        db.clear_all_users()
        self.account = {"username": None, "password": None, "record": None, "iterations": 200_000, "case": None}
        self.zone_a.reset()
        self.zone_b.reset()
        self.zone_c.reset()


class ZoneA(ttk.LabelFrame):
    def __init__(self, parent, app):
        super().__init__(parent, text="ZONE A — Le serveur", padding=8)
        self.app = app

        ttk.Label(self, text="Cas du TP :", font=("TkDefaultFont", 9, "bold")).pack(anchor="w")
        self.case_var = tk.StringVar(value=list(CASES)[0])
        case_frame = ttk.Frame(self)
        case_frame.pack(fill="x", pady=(2, 6))
        for name in CASES:
            ttk.Radiobutton(case_frame, text=name, value=name,
                            variable=self.case_var,
                            command=self.on_case_change).pack(anchor="w")

        form = ttk.Frame(self)
        form.pack(fill="x", pady=(4, 4))
        ttk.Label(form, text="Utilisateur :").grid(row=0, column=0, sticky="w")
        self.username = ttk.Entry(form, width=22)
        self.username.insert(0, "etudiant")
        self.username.grid(row=0, column=1, sticky="ew", padx=4)

        ttk.Label(form, text="Mot de passe :").grid(row=1, column=0, sticky="w", pady=2)
        self.password = ttk.Entry(form, width=22, show="•")
        self.password.insert(0, "111")
        self.password.grid(row=1, column=1, sticky="ew", padx=4, pady=2)
        ttk.Button(form, text="👁", width=3,
                   command=self.toggle_show).grid(row=1, column=2)

        self.strength_bar = ttk.Progressbar(self, orient="horizontal", mode="determinate", maximum=100)
        self.strength_bar.pack(fill="x", pady=(6, 2))
        self.strength_label = ttk.Label(self, text="—", foreground="#555")
        self.strength_label.pack(anchor="w")

        self.problems_box = tk.Text(self, height=3, wrap="word", state="disabled",
                                    font=("TkDefaultFont", 8), bg="#f6f6f6")
        self.problems_box.pack(fill="x", pady=(4, 6))

        ttk.Button(self, text="Créer le compte", command=self.create_account).pack(fill="x", pady=(0, 8))

        ttk.Label(self, text="Base de données (stockage) :", font=("TkDefaultFont", 9, "bold")).pack(anchor="w")
        storage = ttk.Frame(self)
        storage.pack(fill="x", pady=(2, 6))

        self.storage_labels = {}
        rows = [
            ("Algorithme", "algo"),
            ("Sel (Salt)", "salt"),
            ("Chiffré (DB)", "hash"),
            ("Master (Hors DB)", "master"),
            ("Pepper (Hors DB)", "pepper"),
            ("Mot de passe clair", "clear")
        ]

        for i, (label, key) in enumerate(rows):
            ttk.Label(storage, text=label + " :").grid(row=i, column=0, sticky="w")
            v = ttk.Label(storage, text="—", font=("Courier", 8), foreground="#333")
            v.grid(row=i, column=1, sticky="w", padx=4)
            self.storage_labels[key] = v

        ttk.Label(self, text="🔒 Le mot de passe en clair n'est JAMAIS stocké.",
                  foreground="#a00", font=("TkDefaultFont", 8, "italic")).pack(anchor="w")

        self.password.bind("<KeyRelease>", lambda e: self.update_strength())
        self.update_strength()

    def on_case_change(self):
        charset, length = CASES[self.case_var.get()]
        if length is not None:
            self.password.delete(0, "end")
            self.password.insert(0, charset[1] * length)
        self.update_strength()

    def toggle_show(self):
        self.password.config(show="" if self.password.cget("show") else "•")

    def update_strength(self):
        pwd = self.password.get()
        charset, length = CASES[self.case_var.get()]

        if length is not None:
            problems = []
            if len(pwd) != length:
                problems.append("Doit contenir exactement %d caractères." % length)
            if not set(pwd) <= set(charset):
                problems.append("Caractères autorisés : %s" % charset)

            case_num = "1" if length == 3 else "2"
            if problems:
                self.strength_bar["value"] = 0
                self.strength_label.config(text="❌ Non conforme", foreground="#b00")
                set_text(self.problems_box, "")
                self.problems_box.config(state="normal")
                for p in problems:
                    self.problems_box.insert("end", "• " + p + "\n")
                self.problems_box.config(state="disabled")
            else:
                self.strength_bar["value"] = 100
                self.strength_label.config(text="✅ Conforme au cas %s" % case_num, foreground="#070")
                set_text(self.problems_box, "")
            return

        if not pwd:
            self.strength_bar["value"] = 0
            self.strength_label.config(text="—", foreground="#555")
            set_text(self.problems_box, "")
            return

        problems = passwords.strength_problems(pwd)
        score = max(0, 100 - (12 * len(problems)))
        self.strength_bar["value"] = score
        if problems:
            self.strength_label.config(text="❌ Faible — %d problème(s)" % len(problems), foreground="#b00")
        else:
            self.strength_label.config(text="✅ Robuste", foreground="#070")

        set_text(self.problems_box, "")
        if problems:
            self.problems_box.config(state="normal")
            for p in problems:
                self.problems_box.insert("end", "• " + p + "\n")
            self.problems_box.config(state="disabled")

    def create_account(self):
        username = self.username.get().strip()
        password = self.password.get()
        if not username or not password:
            messagebox.showwarning("Compte", "Renseignez l'utilisateur et le mot de passe.")
            return

        charset, length = CASES[self.case_var.get()]

        if length is not None:
            if len(password) != length or not set(password) <= set(charset):
                messagebox.showwarning("Mot de passe invalide",
                                       "Le mot de passe ne respecte pas les règles du cas sélectionné.")
                return

        if length is None:
            problems = passwords.strength_problems(password)
            if problems:
                if not messagebox.askyesno("Mot de passe faible",
                                           "La politique signale :\n" + "\n".join(problems) +
                                           "\n\nCréer le compte quand même ?"):
                    return

        record = passwords.make_record(username, password)

        if record is None:
            messagebox.showerror("Erreur", "Ce nom d'utilisateur est déjà pris !")
            return

        self.app.account.update({
            "username": username,
            "password": password,
            "record": record,
            "iterations": record["iterations"],
            "case": self.case_var.get()
        })

        salt_hex = record["salt"].hex()
        hash_hex = record["hash"].hex()
        master_hex, pepper_hex = caesar.get_secrets()

        self.storage_labels["algo"].config(text=record["algo"])
        self.storage_labels["salt"].config(text=salt_hex)
        self.storage_labels["hash"].config(text=hash_hex)
        self.storage_labels["master"].config(text=master_hex, foreground="#0055aa")
        self.storage_labels["pepper"].config(text=pepper_hex, foreground="#0055aa")
        self.storage_labels["clear"].config(text="JAMAIS STOCKÉ", foreground="#a00", font=("TkDefaultFont", 8, "bold"))

        self.app.zone_b.on_account_ready(username)

    def reset(self):
        self.username.delete(0, "end")
        self.username.insert(0, "etudiant")
        self.password.delete(0, "end")
        self.password.insert(0, "111")
        for v in self.storage_labels.values():
            v.config(text="—", foreground="#333")
        self.update_strength()


class ZoneB(ttk.LabelFrame):
    def __init__(self, parent, app):
        super().__init__(parent, text="ZONE B — L'utilisateur légitime", padding=8)
        self.app = app
        self.guard = None

        ttk.Label(self, text="Connexion :", font=("TkDefaultFont", 9, "bold")).pack(anchor="w")

        form = ttk.Frame(self)
        form.pack(fill="x", pady=4)
        ttk.Label(form, text="Utilisateur :").grid(row=0, column=0, sticky="w")
        self.username = ttk.Entry(form, width=20)
        self.username.grid(row=0, column=1, sticky="ew", padx=4)

        ttk.Label(form, text="Mot de passe :").grid(row=1, column=0, sticky="w", pady=2)
        self.password = ttk.Entry(form, width=20, show="•")
        self.password.grid(row=1, column=1, sticky="ew", padx=4, pady=2)

        ttk.Button(self, text="Se connecter", command=self.login).pack(fill="x", pady=(4, 6))

        ttk.Label(self, text="Temps de vérification :", font=("TkDefaultFont", 9, "bold")).pack(anchor="w", pady=(6, 0))
        self.time_bar = ttk.Progressbar(self, orient="horizontal", mode="determinate", maximum=100)
        self.time_bar.pack(fill="x", pady=2)
        self.time_label = ttk.Label(self, text="—", font=("Courier", 11, "bold"))
        self.time_label.pack(anchor="w")

    def on_account_ready(self, username):
        self.username.delete(0, "end")
        self.username.insert(0, username)
        self.password.delete(0, "end")
        self.password.insert(0, self.app.account["password"] or "")

    def login(self):
        if not self.app.require_account():
            return
        username = self.username.get().strip()
        password = self.password.get()
        if not username or not password:
            messagebox.showwarning("Connexion", "Veuillez remplir tous les champs.")
            return

        start = time.perf_counter()
        success = passwords.verify_password(username, password)
        duration = time.perf_counter() - start

        duration_str = fmt_duration(duration)
        self.time_label.config(text=duration_str)
        self.time_bar["value"] = min(100, duration * 50)

        if success:
            messagebox.showinfo("Succès", f"Connexion réussie !\nTemps de vérification : {duration_str}")
        else:
            messagebox.showerror("Échec", f"Mot de passe incorrect.\nTemps de vérification : {duration_str}")

    def reset(self):
        self.username.delete(0, "end")
        self.username.insert(0, "etudiant")
        self.password.delete(0, "end")
        self.password.insert(0, "111")
        self.time_bar["value"] = 0
        self.time_label.config(text="—")


class ZoneC(ttk.LabelFrame):
    def __init__(self, parent, app):
        super().__init__(parent, text="ZONE C — L'attaquant", padding=8)
        self.app = app

        ttk.Label(self, text="Attaque par dictionnaire / force brute :", font=("TkDefaultFont", 9, "bold")).pack(
            anchor="w")

        attack_frame = ttk.Frame(self)
        attack_frame.pack(fill="x", pady=6)

        ttk.Button(attack_frame, text="Lancer Attaque Dictionnaire", command=self.run_dictionary_attack).pack(fill="x",
                                                                                                              pady=2)
        ttk.Button(attack_frame, text="Lancer Attaque Force Brute", command=self.run_brute_force).pack(fill="x", pady=2)

        ttk.Label(self, text="Résultats de l'attaque :", font=("TkDefaultFont", 9, "bold")).pack(anchor="w",
                                                                                                 pady=(6, 0))
        self.result_box = make_text_box(self, 8, code=True)

    def run_dictionary_attack(self):
        if not self.app.require_account():
            return
        username = self.app.account["username"]
        start = time.perf_counter()
        found, attempts, duration = passwords.dictionary_attack(username)

        res = "--- Attaque Dictionnaire ---\n"
        if found:
            res += f"✅ Mot de passe trouvé : '{found}'\n"
        else:
            res += "❌ Échec : Non trouvé dans le dictionnaire.\n"
        res += f"Tentatives : {attempts}\n"
        res += f"Durée : {fmt_duration(duration)}\n"
        set_text(self.result_box, res)

    def run_brute_force(self):
        if not self.app.require_account():
            return
        username = self.app.account["username"]
        case = self.app.account["case"]

        start = time.perf_counter()
        found, attempts, duration = passwords.brute_force_attack(username, case)

        res = f"--- Attaque Force Brute ({case}) ---\n"
        if found:
            res += f"✅ Mot de passe trouvé : '{found}'\n"
        else:
            res += "❌ Échec / Interrompu.\n"
        res += f"Tentatives : {attempts}\n"
        res += f"Durée : {fmt_duration(duration)}\n"
        set_text(self.result_box, res)

    def reset(self):
        set_text(self.result_box, "")


class MainApp(tk.Tk):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.logged_out = False
        self.title("CryptoLink")
        self.geometry("1100x720")
        self.minsize(900, 600)
        configure_style(self)
        self.configure(bg=COLORS["background"])
        self.current_page = None
        self._build_shell()
        self.show_page("partie2")
        self.refresh_notifications()

    def _build_shell(self):
        header = ttk.Frame(self, padding=(22, 16))
        header.pack(fill="x")
        ttk.Label(header, text="CRYPTO", foreground=COLORS["accent"],
                  font=("Segoe UI", 18, "bold")).pack(side="left")
        ttk.Label(header, text="LINK", foreground=COLORS["text"],
                  font=("Segoe UI", 18, "bold")).pack(side="left")
        ttk.Label(header, text="Connecté en tant que %s" % self.user.get("pseudo", ""),
                  foreground=COLORS["muted"]).pack(side="left", padx=22)
        ttk.Button(header, text="Déconnexion", command=self.ask_logout).pack(side="right")

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)
        self.sidebar = ttk.Frame(body, padding=10, style="Surface.TFrame")
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        self.content = ttk.Frame(body, style="Surface.TFrame")
        self.content.grid(row=0, column=1, sticky="nsew")
        ttk.Label(self.sidebar, text="ESPACE DE TRAVAIL", foreground=COLORS["muted"],
                  font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(2, 12))
        ttk.Button(self.sidebar, text="Envoyer un message", command=lambda: self.show_page("partie2"),
                   style="Primary.TButton").pack(fill="x", pady=4)
        ttk.Button(self.sidebar, text="Boîte de réception", command=lambda: self.show_page("inbox")).pack(fill="x", pady=4)
        self.notifications_button = ttk.Button(self.sidebar, text="Notifications",
                                               command=lambda: self.show_page("notifications"))
        self.notifications_button.pack(fill="x", pady=4)
        ttk.Separator(self.sidebar).pack(fill="x", pady=12)
        ttk.Button(self.sidebar, text=" Mots de passe", command=lambda: self.show_page("partie3")).pack(fill="x", pady=4)
        ttk.Button(self.sidebar, text=" Intégrité ", command=lambda: self.show_page("partie4")).pack(fill="x", pady=4)
        ttk.Separator(self.sidebar).pack(fill="x", pady=18)
        ttk.Label(self.sidebar, text="Votre espace est protégé par une connexion authentifiée.",
                  wraplength=180, foreground=COLORS["muted"]).pack(anchor="w")

    def show_page(self, page_name):
        if self.current_page is not None:
            self.current_page.destroy()
        if page_name == "partie2":
            self.current_page = Partie2Page(self.content, self.user, self.refresh_notifications)
        elif page_name == "inbox":
            self.current_page = InboxPage(self.content, self.user, self.refresh_notifications)
        elif page_name == "notifications":
            self.current_page = NotificationsPage(self.content, self.user, self.refresh_notifications)
        elif page_name == "partie4":
            self.current_page = Partie4Page(self.content, self.user)
        else:
            self.current_page = Partie3Page(self.content)
        self.current_page.pack(fill="both", expand=True)

    def refresh_notifications(self):
        try:
            count = database.unread_count(self.user.get("pseudo", ""))
        except database.DatabaseError:
            count = 0
        self.notifications_button.config(text="Notifications%s" % ("  (%d)" % count if count else ""))

    def ask_logout(self):
        dialog = tk.Toplevel(self)
        dialog.title("Déconnexion")
        dialog.geometry("360x190")
        dialog.transient(self)
        dialog.grab_set()
        ttk.Label(dialog, text="Quitter CryptoLink ?", font=("Segoe UI", 15, "bold")).pack(pady=(24, 8))
        ttk.Label(dialog, text="Votre session sera fermée.", foreground=COLORS["muted"]).pack()
        actions = ttk.Frame(dialog)
        actions.pack(fill="x", padx=24, pady=24)
        ttk.Button(actions, text="Annuler", command=dialog.destroy).pack(side="left", expand=True, fill="x", padx=(0, 6))
        ttk.Button(actions, text="Oui, me déconnecter", style="Primary.TButton",
                   command=lambda: self.logout(dialog)).pack(side="left", expand=True, fill="x", padx=(6, 0))

    def logout(self, dialog):
        dialog.destroy()
        self.logged_out = True
        self.destroy()


def main(user=None):
    if user is None:
        from interface import run_auth
        user = run_auth()
    while user is not None:
        root = MainApp(user)
        root.mainloop()
        if not root.logged_out:
            return
        from interface import run_auth
        user = run_auth()


if __name__ == "__main__":
    main()