import tkinter as tk
from tkinter import ttk, messagebox

from partie2 import ciphers


def read_hill_key(text):
    if "," in text:
        numbers = [int(x) for x in text.split(",")]
        size = int(len(numbers) ** 0.5)
        if size * size != len(numbers):
            raise ValueError("la matrice doit être carrée")
        return [numbers[i * size:(i + 1) * size] for i in range(size)]
    return ciphers.key_from_text(text)


def make_text_box(parent, height):
    box = tk.Text(parent, height=height, wrap="word")
    box.pack(fill="both", expand=True)
    return box


def set_text(box, text):
    box.config(state="normal")
    box.delete("1.0", "end")
    box.insert("1.0", text)
    box.config(state="disabled")


def get_text(box):
    return box.get("1.0", "end").strip()


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
        self.hint = ttk.Label(self, foreground="#555")
        self.hint.pack(anchor="w", pady=6)

    def build_entity_a(self):
        frame = ttk.LabelFrame(self, text="Entité A", padding=6)
        frame.pack(fill="both", expand=True, pady=6)
        self.message = make_text_box(frame, 4)
        self.message.insert("1.0", "Retrouve-moi a la bibliotheque a midi")
        ttk.Button(frame, text="Chiffrer et envoyer", command=self.send).pack(
            anchor="e", pady=4
        )

    def build_channel(self):
        channel = ttk.LabelFrame(self, text="Canal", padding=6)
        channel.pack(fill="both", expand=True, pady=6)
        self.channel_info = ttk.Label(channel, text="Aucun message envoyé.", foreground="#555")
        self.channel_info.pack(anchor="w", pady=(0, 4))
        self.cipher_box = make_text_box(channel, 3)
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
        ttk.Label(key_frame, text="Clé secrète de B (partagée séparément) :").pack(side="left")
        self.key_b = ttk.Entry(key_frame, width=22, show="*")
        self.key_b.pack(side="left", padx=6)
        self.result_box = make_text_box(frame, 4)
        self.result_box.config(state="disabled")
        bottom = ttk.Frame(frame)
        bottom.pack(fill="x", pady=4)
        self.status = ttk.Label(bottom)
        self.status.pack(side="left")
        ttk.Button(bottom, text="Déchiffrer", command=self.receive).pack(side="right")

        self.sent_ciphertext = ""
        self.sent_algorithm = ""
        self.sent_direction = ""
        self.hill_format_positions = []
        self.hill_padding = 0
        self.playfair_format_positions = []
        self.playfair_padding_positions = []
        self.playfair_j_positions = []

    def change_algorithm(self, event=None):
        name = self.algorithm.get()
        settings = {
            "Caesar": ("3", "Clé : décalage n (entier). Le sens s'applique au chiffrement.", "readonly"),
            "Hill": ("3,3,2,5", "Clé : 4 ou 9 nombres séparés par des virgules, ou un mot de 4 ou 9 lettres.", "disabled"),
            "Playfair": ("monarchy", "Clé : un mot quelconque (J est confondu avec I).", "disabled"),
        }
        key, hint, direction_state = settings[name]
        self.key_a.delete(0, "end")
        self.key_a.insert(0, key)
        self.hint.config(text=hint)
        self.direction.config(state=direction_state)
        set_text(self.result_box, "")

    def encrypt(self, text, key_text):
        name = self.algorithm.get()
        key = key_text
        if name == "Caesar":
            return ciphers.caesar(text, int(key), self.direction.get())
        if name == "Hill":
            hill_key = read_hill_key(key)
            letters = ciphers.clean(text)
            self.hill_format_positions = ciphers.format_positions(text.upper())
            self.hill_padding = (-len(letters)) % len(hill_key)
            return ciphers.hill_encrypt(text, hill_key)
        self.playfair_format_positions = ciphers.format_positions(text.upper())
        self.playfair_padding_positions = ciphers.playfair_prepare(text)[1]
        self.playfair_j_positions = ciphers.playfair_j_positions(text)
        return ciphers.playfair_encrypt(text, key)

    def decrypt(self, text, key_text):
        name, direction, _ = ciphers.decode_channel_message(text)
        self.sent_algorithm = name
        self.sent_direction = {"r": "droite", "l": "gauche"}.get(direction, "")
        if name == "Caesar":
            decrypted = ciphers.dechiffrement_automatique(text, key_text)
            return decrypted
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

    def send(self):
        try:
            encrypted = self.encrypt(get_text(self.message), self.key_a.get().strip())
        except ValueError as error:
            messagebox.showerror("Erreur", str(error))
            return
        self.sent_algorithm = self.algorithm.get()
        self.sent_direction = self.direction.get()
        channel_message = ciphers.build_channel_message(
            self.sent_algorithm,
            self.sent_direction,
            encrypted,
        )
        set_text(self.cipher_box, channel_message)
        self.sent_ciphertext = channel_message
        self.algorithm_b.config(text=self.sent_algorithm)
        self.direction_b.config(
            text=self.sent_direction if self.sent_algorithm == "Caesar" else "non applicable"
        )
        direction = self.sent_direction if self.sent_algorithm == "Caesar" else "non applicable"
        self.channel_info.config(
            text="Message chiffré | algorithme : %s | sens : %s | clé secrète non transmise"
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
            decrypted = self.decrypt(encrypted, self.key_b.get().strip())
        except ValueError as error:
            messagebox.showerror("Erreur", str(error))
            return
        self.status.config(text="message déchiffré", foreground="green")
        set_text(self.result_box, decrypted)


def main():
    window = tk.Tk()
    window.title("Framework de chiffrement - SSAD TP1")
    window.geometry("820x720")
    tabs = ttk.Notebook(window)
    tabs.pack(fill="both", expand=True, padx=6, pady=6)
    tabs.add(MessagingTab(tabs), text="Messagerie")
    window.mainloop()


if __name__ == "__main__":
    main()
