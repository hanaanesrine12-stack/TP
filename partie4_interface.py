
import tkinter as tk
from tkinter import messagebox, ttk

import database
from partie4 import integrity as integrite

BG = "#FFFFFF"
PANEL = "#FFFFFF"
FIELD = "#F4F8FD"
LABEL_BG = "#EAF3FF"
BLUE = "#2F75D6"
DARK = "#1D2A3A"
GREEN_TEXT = "#176B3A"
RED = "#C0392B"
GREY = "#637083"
BORDER = "#C5D6EA"
FONT = "Segoe UI"


def set_text(box, text):
    box.config(state="normal")
    box.delete("1.0", "end")
    box.insert("1.0", text)
    box.config(state="disabled")


def get_text(box):
    return box.get("1.0", "end").strip()


def field_label(parent, text):
    tk.Label(parent, text=text, bg=LABEL_BG, fg=GREY, font=(FONT, 9), anchor="w").pack(
        fill="x", pady=(6, 1)
    )


def code_box(parent, height, editable=False):
    box = tk.Text(
        parent, height=height, width=18, wrap="char", bg=FIELD, fg=GREEN_TEXT, relief="flat",
        highlightthickness=1, highlightbackground=BORDER, font=("Consolas", 9), padx=4, pady=4,
    )
    box.pack(fill="x")
    if not editable:
        box.config(state="disabled")
    return box


def blue_button(parent, text, command):
    return tk.Button(
        parent, text=text, command=command, bg=BLUE, fg="white", activebackground="#245fb0",
        activeforeground="white", relief="flat", font=(FONT, 9, "bold"), pady=6, cursor="hand2",
    )


def light_button(parent, text, command):
    return tk.Button(
        parent, text=text, command=command, bg=FIELD, fg=DARK, relief="solid", bd=1,
        font=(FONT, 9), pady=4, cursor="hand2",
    )


class Partie4Page(tk.Frame):
    """A envoie C et H = SHA256(C) ; B recalcule H' = SHA256(C') et ne
    déchiffre que si H = H'."""

    def __init__(self, parent, user=None):
        super().__init__(parent, bg=BG)
        self.user = user or {}
        self.chiffrement = integrite.Chiffrement()
        self.original = None
        body = self.build_scroll_area()
        tk.Label(body, text="Partie 4 — Intégrité avec SHA-256", bg=BG, fg=DARK,
                 font=(FONT, 16, "bold")).pack(anchor="w")
        columns = tk.Frame(body, bg=BG)
        columns.pack(fill="both", expand=True)
        for i in range(3):
            columns.columnconfigure(i, weight=1, uniform="col")
        columns.rowconfigure(0, weight=1)
        self.build_entity_a(self.column(columns, 0, "Entité A — Émetteur"))
        self.build_channel(self.column(columns, 1, "Canal"))
        self.build_entity_b(self.column(columns, 2, "Entité B — Récepteur"))
        self.change_algorithm()
        self.refresh_users()

    def build_scroll_area(self):
        """La fenêtre de l'application fait 720 px de haut : la page défile verticalement."""
        canvas = tk.Canvas(self, bg=BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        body = tk.Frame(canvas, bg=BG, padx=14, pady=14)
        window = canvas.create_window(0, 0, window=body, anchor="nw")
        body.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(window, width=e.width))
        wheel = lambda e: canvas.yview_scroll(-int(e.delta / 120), "units")
        self.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", wheel))
        self.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))
        self.bind("<Destroy>", lambda e: canvas.unbind_all("<MouseWheel>") if e.widget is self else None)
        self.canvas = canvas
        return body

    def column(self, parent, index, title):
        frame = tk.LabelFrame(parent, text=title, bg=PANEL, fg=DARK, font=(FONT, 9, "bold"),
                              relief="solid", bd=1, labelanchor="nw")
        frame.grid(row=0, column=index, sticky="nsew", padx=5)
        inner = tk.Frame(frame, bg=PANEL)
        inner.pack(fill="both", expand=True, padx=10, pady=(0, 8))
        return inner

    def build_entity_a(self, frame):
        field_label(frame, "Récepteur")
        row = tk.Frame(frame, bg=PANEL)
        row.pack(fill="x")
        self.receiver = ttk.Combobox(row, state="readonly", width=12)
        self.receiver.pack(side="left", fill="x", expand=True)
        ttk.Button(row, text="↻", width=3, command=self.refresh_users).pack(side="left", padx=(6, 0))
        field_label(frame, "Algorithme")
        self.algorithm = ttk.Combobox(frame, values=integrite.ALGORITHMES, state="readonly")
        self.algorithm.current(0)
        self.algorithm.pack(fill="x")
        self.algorithm.bind("<<ComboboxSelected>>", self.change_algorithm)
        field_label(frame, "Clé de chiffrement")
        self.key = tk.Entry(frame, bg=FIELD, relief="flat", highlightthickness=1,
                            highlightbackground=BORDER, font=(FONT, 9))
        self.key.pack(fill="x", ipady=2)
        field_label(frame, "Sens (César)")
        self.direction = ttk.Combobox(frame, values=["droite", "gauche"], state="readonly")
        self.direction.current(0)
        self.direction.pack(fill="x")
        field_label(frame, "Message original")
        self.message = tk.Text(frame, height=2, width=18, wrap="word", bg=PANEL, relief="flat",
                               highlightthickness=1, highlightbackground=BORDER, font=(FONT, 9),
                               padx=4, pady=4)
        self.message.pack(fill="x")
        self.message.insert("1.0", "Retrouve-moi a la bibliotheque a midi")
        blue_button(frame, "\U0001F512  Chiffrer et envoyer", self.send).pack(fill="x", pady=(8, 0))
        field_label(frame, "Message chiffré généré")
        self.cipher_a = code_box(frame, 3)
        field_label(frame, "Hash SHA-256")
        self.hash_a = code_box(frame, 4)

    def build_channel(self, frame):
        field_label(frame, "Message chiffré (C) — modifiable")
        self.channel_c = code_box(frame, 3, editable=True)
        field_label(frame, "Hash transmis (H)")
        self.channel_h = code_box(frame, 4)
        light_button(frame, "⚠  Modifier le message", self.tamper).pack(fill="x", pady=(12, 4))
        light_button(frame, "↻  Réinitialiser", self.reset).pack(fill="x")
        self.channel_status = tk.Label(frame, bg=PANEL, fg=RED, font=(FONT, 9), justify="left",
                                       anchor="w", wraplength=230)
        self.channel_status.pack(fill="x", pady=(10, 0))

    def build_entity_b(self, frame):
        field_label(frame, "Message chiffré reçu (C')")
        self.cipher_b = code_box(frame, 3)
        field_label(frame, "Hash reçu (H)")
        self.hash_b = code_box(frame, 4)
        field_label(frame, "Hash calculé (H')")
        self.hash_computed = code_box(frame, 4)
        blue_button(frame, "\U0001F513  Vérifier et déchiffrer", self.verify).pack(fill="x", pady=(12, 0))
        self.status = tk.Label(frame, bg=PANEL, font=(FONT, 9, "bold"), justify="left", anchor="w",
                               wraplength=230)
        self.status.pack(fill="x", pady=(8, 0))
        field_label(frame, "Message déchiffré")
        self.result = tk.Text(frame, height=2, width=18, wrap="word", bg=PANEL, relief="flat",
                              highlightthickness=1, highlightbackground=BORDER, font=(FONT, 9),
                              padx=4, pady=4, state="disabled")
        self.result.pack(fill="x")

    def refresh_users(self):
        """Récepteurs : les autres comptes de la base ; « Entité B » si la base est injoignable."""
        try:
            users = [row["pseudo"] for row in database.list_users()
                     if row["pseudo"] != self.user.get("pseudo")]
        except database.DatabaseError:
            users = []
        self.receiver["values"] = users or ["Utilisateur"]
        self.receiver.current(0)

    def change_algorithm(self, event=None):
        name = self.algorithm.get()
        self.key.delete(0, "end")
        self.key.insert(0, integrite.CLES_PAR_DEFAUT[name])
        self.direction.config(state="readonly" if name == "Caesar" else "disabled")

    def set_channel_c(self, text):
        self.channel_c.delete("1.0", "end")
        self.channel_c.insert("1.0", text)

    def show_received(self, c, h):
        set_text(self.cipher_b, c)
        set_text(self.hash_b, h)
        set_text(self.hash_computed, "")
        set_text(self.result, "")
        self.status.config(text="")

    def send(self):
        message = get_text(self.message)
        if not message:
            messagebox.showerror("Erreur", "Le message est vide.")
            return
        try:
            c, h = integrite.envoyer(self.chiffrement, self.algorithm.get(), message,
                                     self.key.get().strip(), self.direction.get())
        except ValueError as error:
            messagebox.showerror("Erreur", str(error))
            return
        self.original = (c, h)
        set_text(self.cipher_a, c)
        set_text(self.hash_a, h)
        self.set_channel_c(c)
        set_text(self.channel_h, h)
        self.channel_status.config(fg=GREEN_TEXT, text="Message envoyé. Canal intact.")
        self.show_received(c, h)

    def tamper(self):
        if self.original is None:
            messagebox.showerror("Erreur", "Aucun message n'a été envoyé.")
            return
        try:
            c, index, old, new = integrite.falsifier(get_text(self.channel_c))
        except ValueError as error:
            messagebox.showerror("Erreur", str(error))
            return
        self.set_channel_c(c)
        self.channel_status.config(
            fg=RED,
            text="⚠  Modifié en transit : caractère n°%d du chiffré « %s » → « %s ». "
                 "Le hash transmis est resté celui d'origine." % (index, old, new),
        )
        self.show_received(c, get_text(self.channel_h))

    def reset(self):
        if self.original is None:
            return
        c, h = self.original
        self.set_channel_c(c)
        set_text(self.channel_h, h)
        self.channel_status.config(fg=GREEN_TEXT, text="Canal rétabli : message d'origine.")
        self.show_received(c, h)

    def verify(self):
        if self.original is None:
            messagebox.showerror("Erreur", "Aucun message n'a été envoyé.")
            return
        c, h = get_text(self.channel_c), get_text(self.channel_h)
        self.show_received(c, h)
        try:
            ok, h_computed, plain = integrite.recevoir(self.chiffrement, c, h, self.key.get().strip())
        except ValueError as error:
            messagebox.showerror("Erreur", str(error))
            return
        set_text(self.hash_computed, h_computed)
        if ok:
            self.status.config(fg=GREEN_TEXT, text="✔  Message intègre : H = H'.\nDéchiffrement autorisé.")
            set_text(self.result, plain)
        else:
            self.status.config(fg=RED, text="✖  Message modifié : H ≠ H'.\nDéchiffrement bloqué.")