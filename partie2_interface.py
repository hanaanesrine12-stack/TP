import tkinter as tk
from tkinter import messagebox, ttk

import database
from partie2 import ciphers


COLORS = {
    "surface": "#FFFFFF", "surface_dark": "#F4F8FD", "text": "#1D2A3A",
    "muted": "#637083", "accent": "#2F75D6", "success": "#2DAA68",
    "border": "#C5D6EA", "code": "#176B3A",
}


def _text_box(parent, height, code=False):
    box = tk.Text(parent, height=height, wrap="word", relief="flat",
                  bg=COLORS["surface_dark"] if code else COLORS["surface"],
                  fg=COLORS["code"] if code else COLORS["text"],
                  insertbackground=COLORS["text"], highlightthickness=1,
                  highlightbackground=COLORS["border"],
                  font=("Consolas", 10) if code else ("Segoe UI", 10))
    box.pack(fill="both", expand=True)
    return box


def _set_text(box, value):
    box.config(state="normal")
    box.delete("1.0", "end")
    box.insert("1.0", value)
    box.config(state="disabled")


def _get_text(box):
    return box.get("1.0", "end").strip()


def _auto_decrypt(channel_message, metadata=None):
    """Déchiffre un message du canal avec les fonctions déjà existantes dans
    ciphers.py (decode_channel_message / dechiffrement_automatique), sans rien
    demander au destinataire : la clé est déjà intégrée dans le message."""
    algorithm, _direction, key, _ciphertext = ciphers.decode_channel_message(channel_message)
    hill_key = None
    if algorithm == "Hill":
        numbers = [int(value.strip()) for value in key.split(",")]
        size = int(len(numbers) ** 0.5)
        if size * size != len(numbers):
            raise ValueError("la clé Hill intégrée au message est invalide")
        hill_key = [numbers[index:index + size] for index in range(0, len(numbers), size)]
    plaintext = ciphers.dechiffrement_automatique(channel_message, key, hill_key=hill_key)
    metadata = metadata or {}
    if algorithm == "Caesar" and metadata.get("caesar_mask"):
        plaintext = ciphers.caesar_restore(plaintext, metadata["caesar_mask"])
    elif algorithm == "Hill":
        padding = metadata.get("hill_padding", 0)
        if padding:
            plaintext = plaintext[:-int(padding)]
        plaintext = ciphers.restore_format(plaintext, metadata.get("format_positions", []))
    elif algorithm == "Playfair":
        plaintext = ciphers.playfair_strip_padding(
            plaintext, metadata.get("playfair_padding_positions")
        )
        plaintext = ciphers.playfair_restore_j(
            plaintext, metadata.get("playfair_j_positions", [])
        )
        plaintext = ciphers.restore_format(plaintext, metadata.get("format_positions", []))
    return algorithm, plaintext


class Partie2Page(ttk.Frame):
    """Interface de messagerie chiffrée pour l'utilisateur authentifié."""

    def __init__(self, parent, user, on_notifications_changed=None):
        super().__init__(parent, padding=18)
        self.user = user
        self.on_notifications_changed = on_notifications_changed
        self.sent = None
        self._build()
        self.refresh_users()

    def _build(self):
        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0, 14))
        ttk.Label(header, text="Envoyer un message", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        ttk.Label(header, text="Chiffrez votre message avant de le transmettre au canal.",
                  foreground=COLORS["muted"]).pack(anchor="w", pady=(3, 0))

        form = ttk.LabelFrame(self, text="Paramètres du message", padding=12)
        form.pack(fill="x", pady=(0, 12))
        form.columnconfigure(1, weight=1)
        ttk.Label(form, text="Récepteur").grid(row=0, column=0, sticky="w", padx=(0, 10), pady=4)
        self.receiver = ttk.Combobox(form, state="readonly")
        self.receiver.grid(row=0, column=1, sticky="ew", pady=4)
        ttk.Button(form, text="Actualiser", command=self.refresh_users).grid(row=0, column=2, padx=(8, 0))
        ttk.Label(form, text="Algorithme").grid(row=1, column=0, sticky="w", padx=(0, 10), pady=4)
        self.algorithm = ttk.Combobox(form, state="readonly", values=("Caesar", "Hill", "Playfair"))
        self.algorithm.current(0)
        self.algorithm.grid(row=1, column=1, sticky="ew", pady=4)
        self.algorithm.bind("<<ComboboxSelected>>", self.change_algorithm)
        ttk.Label(form, text="Clé").grid(row=2, column=0, sticky="w", padx=(0, 10), pady=4)
        self.key = ttk.Entry(form)
        self.key.grid(row=2, column=1, sticky="ew", pady=4)
        ttk.Label(form, text="Sens").grid(row=3, column=0, sticky="w", padx=(0, 10), pady=4)
        self.direction = ttk.Combobox(form, state="readonly", values=("droite", "gauche"))
        self.direction.current(0)
        self.direction.grid(row=3, column=1, sticky="w", pady=4)
        self.change_algorithm()

        compose = ttk.LabelFrame(self, text="Message", padding=12)
        compose.pack(fill="both", expand=True, pady=(0, 12))
        self.message = _text_box(compose, 6)
        ttk.Button(compose, text="Chiffrer et envoyer", command=self.send,
                   style="Primary.TButton").pack(anchor="e", pady=(8, 0))

        channel = ttk.LabelFrame(self, text="Canal", padding=12)
        channel.pack(fill="both", expand=True)
        self.channel = _text_box(channel, 4, code=True)
        self.channel.config(state="disabled")
        self.status = ttk.Label(channel, text="Aucun message envoyé.", foreground=COLORS["muted"])
        self.status.pack(anchor="w", pady=(8, 0))

    def change_algorithm(self, event=None):
        values = {"Caesar": ("3", "normal"), "Hill": ("3,3,2,5", "disabled"),
                  "Playfair": ("monarchy", "disabled")}
        key, direction_state = values[self.algorithm.get()]
        self.key.delete(0, "end")
        self.key.insert(0, key)
        self.direction.config(state=direction_state)

    def refresh_users(self):
        try:
            users = [user["pseudo"] for user in database.list_users()
                     if user["pseudo"] != self.user.get("pseudo")]
        except database.DatabaseError as error:
            messagebox.showerror("Destinataires", str(error))
            users = []
        self.receiver["values"] = users
        if users:
            self.receiver.current(0)

    def _encrypt(self, text):
        name = self.algorithm.get()
        key = self.key.get().strip()
        metadata = {}
        if name == "Caesar":
            try:
                shift = ciphers.validate_key(int(key))
            except ValueError as error:
                raise ValueError(str(error)) from error
            letters, mask = ciphers.caesar_prepare(text)
            encrypted = ciphers.caesar(letters, shift, self.direction.get())
            metadata["caesar_mask"] = mask
        elif name == "Hill":
            numbers = [int(value.strip()) for value in key.split(",")]
            size = int(len(numbers) ** 0.5)
            if size * size != len(numbers):
                raise ValueError("La matrice Hill doit être carrée.")
            hill_key = [numbers[index:index + size] for index in range(0, len(numbers), size)]
            metadata["format_positions"] = ciphers.format_positions(text.upper())
            metadata["hill_padding"] = (-len(ciphers.clean(text))) % len(hill_key)
            encrypted = ciphers.hill_encrypt(text, hill_key)
        else:
            metadata["format_positions"] = ciphers.format_positions(text.upper())
            metadata["playfair_padding_positions"] = ciphers.playfair_prepare(text)[1]
            metadata["playfair_j_positions"] = ciphers.playfair_j_positions(text)
            encrypted = ciphers.playfair_encrypt(text, key)
        direction = self.direction.get() if name == "Caesar" else ""
        return ciphers.build_channel_message(name, direction, encrypted, key), metadata

    def send(self):
        text = _get_text(self.message)
        recipient = self.receiver.get()
        if not text or not recipient:
            messagebox.showwarning("Message", "Choisissez un récepteur et saisissez un message.")
            return
        try:
            channel_message, metadata = self._encrypt(text)
            database.send_message(self.user["pseudo"], recipient, channel_message, metadata=metadata)
        except (ValueError, database.DatabaseError) as error:
            messagebox.showerror("Envoi impossible", str(error))
            return
        self.sent = channel_message
        _set_text(self.channel, channel_message)
        self.status.config(text="Message chiffré et envoyé.", foreground=COLORS["success"])
        if self.on_notifications_changed:
            self.on_notifications_changed()


class InboxPage(ttk.Frame):
    """Boîte de réception : messages reçus, déchiffrables en un clic."""

    def __init__(self, parent, user, on_notifications_changed=None):
        super().__init__(parent, padding=18)
        self.user = user
        self.on_notifications_changed = on_notifications_changed
        self._build()
        self.refresh()

    def _build(self):
        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0, 14))
        title_row = ttk.Frame(header)
        title_row.pack(fill="x")
        ttk.Label(title_row, text="Boîte de réception", font=("Segoe UI", 18, "bold")).pack(side="left")
        ttk.Button(title_row, text="Actualiser", command=self.refresh).pack(side="right")
        ttk.Label(header, text="Messages chiffrés reçus. Cliquez sur « Déchiffrer » pour lire un message.",
                  foreground=COLORS["muted"]).pack(anchor="w", pady=(3, 0))

        table = ttk.LabelFrame(self, text="Messages reçus", padding=10)
        table.pack(fill="both", expand=True)

        head = ttk.Frame(table)
        head.pack(fill="x")
        bold = {"font": ("Segoe UI", 10, "bold"), "foreground": COLORS["muted"]}
        ttk.Label(head, text="#", width=3, **bold).pack(side="left")
        ttk.Label(head, text="Expéditeur", width=16, **bold).pack(side="left", padx=(0, 10))
        ttk.Label(head, text="Message", **bold).pack(side="left", fill="x", expand=True)
        ttk.Label(head, text="", width=12, **bold).pack(side="right")
        ttk.Separator(table).pack(fill="x", pady=(4, 6))

        canvas_holder = ttk.Frame(table)
        canvas_holder.pack(fill="both", expand=True)
        canvas = tk.Canvas(canvas_holder, bg=COLORS["surface"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_holder, orient="vertical", command=canvas.yview)
        self.rows_frame = ttk.Frame(canvas)
        self.rows_frame.bind(
            "<Configure>", lambda event: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.rows_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.status = ttk.Label(self, text="", foreground=COLORS["muted"])
        self.status.pack(anchor="w", pady=(10, 0))

    def refresh(self):
        for child in self.rows_frame.winfo_children():
            child.destroy()
        try:
            messages = database.get_inbox(self.user.get("pseudo", ""))
        except database.DatabaseError as error:
            messagebox.showerror("Boîte de réception", str(error))
            messages = []
        if not messages:
            ttk.Label(self.rows_frame, text="Aucun message reçu pour le moment.",
                     foreground=COLORS["muted"]).pack(anchor="w", pady=10)
            self.status.config(text="")
            return
        for position, message in enumerate(messages, start=1):
            self._build_row(position, message)
        self.status.config(text="%d message(s) reçu(s)." % len(messages))

    def _build_row(self, position, message):
        row = ttk.Frame(self.rows_frame)
        row.pack(fill="x", pady=3)
        ttk.Label(row, text=str(position), width=3).pack(side="left")
        ttk.Label(row, text=message["sender"], width=16).pack(side="left", padx=(0, 10))
        text_var = tk.StringVar(value=message["channel_message"])
        text_label = ttk.Label(row, textvariable=text_var, foreground=COLORS["code"],
                               font=("Consolas", 10), wraplength=360, justify="left")
        text_label.pack(side="left", fill="x", expand=True, padx=(0, 10))

        channel_message = message["channel_message"]
        metadata = message.get("metadata") or {}

        def toggle():
            if action["text"] == "Déchiffrer":
                try:
                    algorithm, plaintext = _auto_decrypt(channel_message, metadata)
                except ValueError as error:
                    messagebox.showerror("Déchiffrement", str(error))
                    return
                text_var.set("[%s] %s" % (algorithm, plaintext))
                text_label.config(foreground=COLORS["success"])
                action.config(text="Masquer")
            else:
                text_var.set(channel_message)
                text_label.config(foreground=COLORS["code"])
                action.config(text="Déchiffrer")

        action = ttk.Button(row, text="Déchiffrer", style="Primary.TButton", command=toggle)
        action.pack(side="right")


class NotificationsPage(ttk.Frame):
    """Centre de notifications : messages de succès, alertes et notifications de sécurité."""

    def __init__(self, parent, user, on_notifications_changed=None):
        super().__init__(parent, padding=18)
        self.user = user
        self.on_notifications_changed = on_notifications_changed
        self._build()
        self.refresh()

    def _build(self):
        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0, 14))
        ttk.Label(header, text="Notifications", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        ttk.Label(header, text="Messages de succès, alertes et notifications de sécurité.",
                  foreground=COLORS["muted"]).pack(anchor="w", pady=(3, 0))

        table_frame = ttk.LabelFrame(self, text="Centre de notifications", padding=10)
        table_frame.pack(fill="both", expand=True)

        columns = ("state", "content", "date")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings",
                                 selectmode="extended", height=12)
        self.tree.heading("state", text="État")
        self.tree.heading("content", text="Notification")
        self.tree.heading("date", text="Date")
        self.tree.column("state", width=80, anchor="w")
        self.tree.column("content", width=420, anchor="w")
        self.tree.column("date", width=150, anchor="w")
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.tag_configure("unread", foreground=COLORS["accent"])
        self.tree.tag_configure("read", foreground=COLORS["muted"])

        footer = ttk.Frame(self)
        footer.pack(fill="x", pady=(10, 0))
        self.count_label = ttk.Label(footer, text="", foreground=COLORS["muted"])
        self.count_label.pack(side="left")
        ttk.Button(footer, text="Marquer comme lu", style="Primary.TButton",
                   command=self.mark_read).pack(side="right")
        ttk.Button(footer, text="Actualiser", command=self.refresh).pack(side="right", padx=(0, 8))

    def refresh(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        try:
            notifications = database.get_notifications(self.user.get("pseudo", ""))
        except database.DatabaseError as error:
            messagebox.showerror("Notifications", str(error))
            notifications = []
        for notification in notifications:
            is_read = notification["is_read"]
            self.tree.insert(
                "", "end", iid=str(notification["id"]),
                values=("Lu" if is_read else "Nouveau", notification["content"], notification["date"]),
                tags=("read" if is_read else "unread",))
        self.count_label.config(text="%d notification(s)" % len(notifications))

    def mark_read(self):
        ids = self.tree.selection() or self.tree.get_children()
        if not ids:
            return
        for item_id in ids:
            database.mark_notification_read(int(item_id))
        self.refresh()
        if self.on_notifications_changed:
            self.on_notifications_changed()