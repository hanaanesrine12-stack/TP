import random
import re
import tkinter as tk
from tkinter import ttk, messagebox

import database

COLORS = {
    "background": "#EAF3FF",
    "surface": "#FFFFFF",
    "surface_dark": "#F4F8FD",
    "text": "#1D2A3A",
    "muted": "#637083",
    "accent": "#2F75D6",
    "accent_hover": "#1F5FB8",
    "success": "#2DAA68",
    "danger": "#C0392B",
    "border": "#C5D6EA",
}

rng = random.SystemRandom()

USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,20}$")
MIN_PASSWORD = 6
MAX_PASSWORD = 64


def is_visible_ascii(text):
    """ASCII visible 33..126 : ni espace, ni accent, ni emoji (voir database.py)."""
    return all(33 <= ord(c) <= 126 for c in text)


def configure_style(window):
    c = COLORS
    style = ttk.Style(window)
    style.theme_use("clam")
    style.configure(".", background=c["background"], foreground=c["text"],
                    font=("Segoe UI", 10))
    style.configure("TFrame", background=c["background"])
    style.configure("Card.TFrame", background=c["surface"])
    style.configure("Card.TLabel", background=c["surface"], foreground=c["text"])
    style.configure("Heading.TLabel", background=c["surface"], foreground=c["text"],
                    font=("Segoe UI", 14, "bold"))
    style.configure("Muted.TLabel", background=c["surface"], foreground=c["muted"])
    style.configure("Error.TLabel", background=c["surface"], foreground=c["danger"])
    style.configure("Ok.TLabel", background=c["surface"], foreground=c["success"])
    style.configure("Title.TLabel", background=c["background"], foreground=c["accent"],
                    font=("Segoe UI", 22, "bold"))
    style.configure("Sub.TLabel", background=c["background"], foreground=c["muted"])
    style.configure("Card.TCheckbutton", background=c["surface"], foreground=c["muted"])
    style.map("Card.TCheckbutton", background=[("active", c["surface"])])
    style.configure("TEntry", fieldbackground=c["surface_dark"], foreground=c["text"],
                    bordercolor=c["border"], padding=6)
    style.configure("Primary.TButton", background=c["accent"], foreground="white",
                    padding=(14, 9), font=("Segoe UI", 10, "bold"), borderwidth=0)
    style.map("Primary.TButton", background=[("active", c["accent_hover"])])
    style.configure("Refresh.TButton", background=c["surface_dark"], foreground=c["accent"],
                    padding=(4, 4), font=("Segoe UI", 12, "bold"), borderwidth=1,
                    bordercolor=c["border"])
    style.map("Refresh.TButton", background=[("active", c["border"])])
    style.configure("Link.TButton", background=c["surface"], foreground=c["accent"],
                    borderwidth=0, padding=2, font=("Segoe UI", 10, "underline"))
    style.map("Link.TButton", background=[("active", c["surface"])],
              foreground=[("active", c["accent_hover"])])


class Captcha(tk.Canvas):
    """Code de 5 caractères déformé (position, taille, angle, bruit)."""

    ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    INKS = ["#1D2A3A", "#2F75D6", "#176B3A", "#8A3FB5", "#B3402A"]

    def __init__(self, parent, length=5, width=190, height=56):
        super().__init__(parent, width=width, height=height, bg=COLORS["surface_dark"],
                         highlightthickness=1, highlightbackground=COLORS["border"])
        self.length = length
        self.canvas_w = width
        self.canvas_h = height
        self.code = ""
        self.refresh()

    def _noise_line(self, color):
        self.create_line(
            rng.randint(0, self.canvas_w), rng.randint(0, self.canvas_h),
            rng.randint(0, self.canvas_w), rng.randint(0, self.canvas_h),
            fill=color, width=rng.randint(1, 2),
        )

    def refresh(self):
        self.code = "".join(rng.choice(self.ALPHABET) for _ in range(self.length))
        self.delete("all")
        for _ in range(70):
            x, y = rng.randint(0, self.canvas_w), rng.randint(0, self.canvas_h)
            self.create_oval(x, y, x + 2, y + 2, fill=COLORS["border"], outline="")
        for _ in range(4):
            self._noise_line(COLORS["border"])
        step = self.canvas_w / (self.length + 1)
        for i, char in enumerate(self.code):
            self.create_text(
                step * (i + 1) + rng.randint(-4, 4),
                self.canvas_h / 2 + rng.randint(-7, 7),
                text=char,
                angle=rng.randint(-25, 25),
                fill=rng.choice(self.INKS),
                font=("Segoe UI", rng.randint(20, 26), "bold"),
            )
        for _ in range(2):
            self._noise_line(rng.choice(self.INKS))

    def check(self, answer):
        return answer.strip().upper() == self.code


class AuthForm(ttk.Frame):
    def __init__(self, parent, app, title):
        super().__init__(parent, style="Card.TFrame", padding=24)
        self.app = app
        ttk.Label(self, text=title, style="Heading.TLabel").pack(anchor="w")

    def add_field(self, label, secret=False):
        ttk.Label(self, text=label, style="Card.TLabel").pack(anchor="w", pady=(12, 2))
        entry = ttk.Entry(self, width=34, show="•" if secret else "")
        entry.pack(fill="x")
        entry.bind("<Return>", lambda event: self.submit())
        return entry

    def add_show_toggle(self, entries):
        shown = tk.BooleanVar(value=False)

        def toggle():
            for entry in entries:
                entry.config(show="" if shown.get() else "•")

        ttk.Checkbutton(self, text="Afficher le mot de passe", variable=shown,
                        command=toggle, style="Card.TCheckbutton").pack(anchor="w", pady=(8, 0))

    def add_captcha(self):
        ttk.Label(self, text="Recopie le code de l'image", style="Card.TLabel").pack(
            anchor="w", pady=(14, 2))
        row = ttk.Frame(self, style="Card.TFrame")
        row.pack(fill="x")
        self.captcha = Captcha(row)
        self.captcha.pack(side="left")
        ttk.Button(row, text="↻", width=3, style="Refresh.TButton",
                   command=self.new_captcha).pack(side="left", padx=8)
        self.captcha_entry = ttk.Entry(self, width=34)
        self.captcha_entry.pack(fill="x", pady=(6, 0))
        self.captcha_entry.bind("<Return>", lambda event: self.submit())

    def add_footer(self, button_text, link_text, link_command):
        self.message = ttk.Label(self, text="", style="Error.TLabel",
                                 wraplength=320, justify="left")
        self.message.pack(anchor="w", pady=(12, 0))
        ttk.Button(self, text=button_text, style="Primary.TButton",
                   command=self.submit).pack(fill="x", pady=(12, 6))
        ttk.Button(self, text=link_text, style="Link.TButton", cursor="hand2",
                   command=link_command).pack()

    def new_captcha(self):
        self.captcha.refresh()
        self.captcha_entry.delete(0, "end")

    def fail(self, text):
        self.message.config(text=text, style="Error.TLabel")
        self.new_captcha()

    def captcha_ok(self):
        if self.captcha.check(self.captcha_entry.get()):
            return True
        self.fail("Code incorrect. Un nouveau code a été généré.")
        return False

    def submit(self):
        raise NotImplementedError


class LoginForm(AuthForm):
    def __init__(self, parent, app, prefill="", notice=""):
        super().__init__(parent, app, "Connexion")
        self.username = self.add_field("Nom d'utilisateur")
        self.password = self.add_field("Mot de passe", secret=True)
        self.add_show_toggle([self.password])
        self.add_captcha()
        self.add_footer("Se connecter", "Pas de compte ? Créer un compte",
                        self.app.show_signup)
        if prefill:
            self.username.insert(0, prefill)
        if notice:
            self.message.config(text=notice, style="Ok.TLabel")

    def focus_first(self):
        (self.password if self.username.get() else self.username).focus_set()

    def submit(self):
        username = self.username.get().strip()
        password = self.password.get()
        if not username or not password:
            return self.fail("Saisis ton nom d'utilisateur et ton mot de passe.")
        if not self.captcha_ok():
            return
        try:
            user = database.authenticate(username, password)
        except database.LoginBlocked as error:
            self.password.delete(0, "end")
            return self.fail(str(error))
        except database.DatabaseError:
            return self.fail("Base de données indisponible. Vérifie que MySQL est démarré.")
        if user is None:
            self.password.delete(0, "end")
            return self.fail("Nom d'utilisateur ou mot de passe incorrect.")
        self.app.login_success(user)


class SignupForm(AuthForm):
    def __init__(self, parent, app):
        super().__init__(parent, app, "Créer un compte")
        self.username = self.add_field("Nom d'utilisateur (3 à 20 : lettres, chiffres, _ . -)")
        self.pseudo = self.add_field("Nom affiché (3 à 20 : lettres, chiffres, _ . -)")
        self.password = self.add_field("Mot de passe (6 caractères minimum)", secret=True)
        self.confirm = self.add_field("Confirmer le mot de passe", secret=True)
        self.add_show_toggle([self.password, self.confirm])
        self.add_captcha()
        self.add_footer("Créer mon compte", "J'ai déjà un compte", self.app.show_login)

    def focus_first(self):
        self.username.focus_set()

    def submit(self):
        username = self.username.get().strip()
        pseudo = self.pseudo.get().strip()
        password = self.password.get()
        confirm = self.confirm.get()

        if not USERNAME_RE.match(username):
            return self.fail("Nom d'utilisateur invalide : 3 à 20 caractères parmi "
                             "lettres, chiffres, _ . -")
        if not USERNAME_RE.match(pseudo):
            return self.fail("Nom affiché invalide : 3 à 20 caractères parmi "
                             "lettres, chiffres, _ . -")
        if not (MIN_PASSWORD <= len(password) <= MAX_PASSWORD):
            return self.fail("Le mot de passe doit faire %d à %d caractères."
                             % (MIN_PASSWORD, MAX_PASSWORD))
        if not is_visible_ascii(password):
            return self.fail("Le mot de passe ne peut pas contenir d'espace, d'accent ni d'emoji.")
        if password != confirm:
            return self.fail("Les deux mots de passe sont différents.")
        if not self.captcha_ok():
            return
        try:
            database.create_user(username, password, pseudo)
        except ValueError as error:
            return self.fail(str(error))
        except database.DatabaseError:
            return self.fail("Base de données indisponible. Vérifie que MySQL est démarré.")
        self.app.show_login(prefill=username, notice="Compte créé. Tu peux te connecter.")


class AuthApp(tk.Tk):
    def __init__(self):
        super().__init__()
        configure_style(self)
        self.configure(bg=COLORS["background"])
        self.resizable(False, False)
        self.user = None

        header = ttk.Frame(self)
        header.pack(pady=(24, 12))
        ttk.Label(header, text="🔐 CryptoLink", style="Title.TLabel").pack()
        ttk.Label(header, text="Messagerie chiffrée", style="Sub.TLabel").pack()

        self.holder = tk.Frame(self, bg=COLORS["surface"], highlightthickness=1,
                               highlightbackground=COLORS["border"])
        self.holder.pack(padx=30, pady=(0, 30), fill="x")
        self.form = None
        self.show_login()

    def _show(self, form, title):
        if self.form is not None:
            self.form.destroy()
        self.form = form
        self.form.pack(fill="x")
        self.title(title)
        self.center()
        self.form.focus_first()

    def show_login(self, prefill="", notice=""):
        self._show(LoginForm(self.holder, self, prefill, notice), "CryptoLink — Connexion")

    def show_signup(self):
        self._show(SignupForm(self.holder, self), "CryptoLink — Créer un compte")

    def login_success(self, user):
        self.user = user
        self.destroy()

    def center(self):
        self.update_idletasks()
        x = (self.winfo_screenwidth() - self.winfo_reqwidth()) // 2
        y = (self.winfo_screenheight() - self.winfo_reqheight()) // 3
        self.geometry("+%d+%d" % (x, max(y, 0)))


def run_auth():
    """Affiche les pages de connexion / création de compte.
    Retourne le dict utilisateur après connexion, ou None si la fenêtre est fermée."""
    try:
        database.init_db()
    except database.DatabaseError as error:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "CryptoLink",
            "Connexion à MySQL impossible.\n\n%s\n\n"
            "Vérifie que MySQL (XAMPP / WAMP) est démarré et que les variables "
            "CRYPTO_DB_* (hôte, utilisateur, mot de passe) sont correctes." % error,
        )
        root.destroy()
        return None
    app = AuthApp()
    app.mainloop()
    return app.user


def launch_main_app(user):
    """Ouvre la fenêtre principale (app.py) pour l'utilisateur connecté."""
    import inspect
    import app
    if "user" in inspect.signature(app.main).parameters:
        app.main(user)
    else:
        app.main()


if __name__ == "__main__":
    current_user = run_auth()
    if current_user is not None:
        launch_main_app(current_user)