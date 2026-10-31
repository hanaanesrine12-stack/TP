import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk

import passwords

COLORS = {
    "text": "#1D2A3A", "muted": "#637083", "danger": "#C0392B",
    "success": "#2DAA68", "warn": "#B8860B",
    "surface_dark": "#F4F8FD", "code": "#176B3A",
}

# --- Les 3 cas du sujet (indices 0, 1, 2) -----------------------------------
CASE_SPECS = [
    {"label": "Cas 1 — 3 caractères, uniquement 0 ou 1",
     "charset": passwords.BINARY, "length": 3},
    {"label": "Cas 2 — 4 caractères, uniquement 1, 2, 3 ou 4",
     "charset": passwords.DIGITS_1_4, "length": 4},
    {"label": "Cas 3 — libre (toute longueur, tout caractère)",
     "charset": None, "length": None},
]

# --- Politique de verrouillage à la connexion -------------------------------
MAX_FAILS = 3
LOCK_SECONDS = 20

# --- Limite de temps pour la force brute ------------------------------------
BRUTE_FORCE_SECONDS = 10

ATTACK_METHODS = ["Dictionnaire", "Force brute", "Dictionnaire puis force brute"]

STOP_REASONS = {
    "time_limit": "la force brute a été interrompue après la limite de %ds." % BRUTE_FORCE_SECONDS,
    "attempt_limit": "la limite de tentatives a été atteinte.",
    "exhausted": "tout l'espace de recherche a été parcouru sans succès.",
}


def _new_login_state():
    return {"phase": 1, "fails": 0, "locked_until": None, "blocked": False}


def _strict_problems(password, charset, length):
    """Liste précise des raisons de refus pour les cas 1 et 2."""
    problems = []
    if len(password) != length:
        problems.append(
            "la longueur doit être exactement %d caractère(s) (vous en avez saisi %d)."
            % (length, len(password)))
    invalid = sorted(set(character for character in password if character not in charset))
    if invalid:
        problems.append(
            "caractère(s) non autorisé(s) : %s (seuls %s sont permis)."
            % (", ".join(repr(character) for character in invalid), charset))
    return problems


class Partie3Page(ttk.Frame):
    """Partie 3 : création de compte (par essai), connexion protégée et attaques."""

    def __init__(self, parent):
        super().__init__(parent, padding=18)
        self.accounts = {}          # username -> {record, case_index, password_used, login}
        self._attack_generation = 0
        self._attack_running = False
        self._attack_start = 0.0
        self._build()
        self._refresh_account_lists()

    # ------------------------------------------------------------------ UI
    def _build(self):
        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0, 10))
        ttk.Label(header, text="Sécurité des mots de passe",
                  font=("Segoe UI", 18, "bold")).pack(anchor="w")
        ttk.Label(header, text="Démonstration par essai : créez des comptes, connectez-vous, "
                               "puis attaquez-les.",
                  foreground=COLORS["muted"]).pack(anchor="w", pady=(3, 8))

        toolbar = ttk.Frame(header)
        toolbar.pack(fill="x")
        self.accounts_count_label = ttk.Label(toolbar, text="", foreground=COLORS["muted"])
        self.accounts_count_label.pack(side="left")
        ttk.Button(toolbar, text="Réinitialiser l'essai",
                   command=self.reinitialize_trial).pack(side="right")

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True)

        create_tab = ttk.Frame(notebook, padding=14)
        login_tab = ttk.Frame(notebook, padding=14)
        attack_tab = ttk.Frame(notebook, padding=14)
        notebook.add(create_tab, text="Créer un compte")
        notebook.add(login_tab, text="Connexion")
        notebook.add(attack_tab, text="Attaque (pirate)")

        self._build_create_tab(create_tab)
        self._build_login_tab(login_tab)
        self._build_attack_tab(attack_tab)

    # ---------------------------------------------------------- Création
    def _build_create_tab(self, parent):
        form = ttk.LabelFrame(parent, text="Nouveau compte (essai)", padding=12)
        form.pack(fill="x")
        form.columnconfigure(1, weight=1)

        ttk.Label(form, text="Nom d'utilisateur").grid(row=0, column=0, sticky="w", pady=4)
        self.create_username = ttk.Entry(form)
        self.create_username.grid(row=0, column=1, sticky="ew", padx=8, pady=4)

        ttk.Label(form, text="Cas").grid(row=1, column=0, sticky="w", pady=4)
        self.create_case = ttk.Combobox(form, state="readonly",
                                        values=[spec["label"] for spec in CASE_SPECS])
        self.create_case.current(0)
        self.create_case.grid(row=1, column=1, sticky="ew", padx=8, pady=4)
        self.create_case.bind("<<ComboboxSelected>>", lambda event: self._live_preview())

        ttk.Label(form, text="Mot de passe").grid(row=2, column=0, sticky="w", pady=4)
        self.create_password = ttk.Entry(form, show="•")
        self.create_password.grid(row=2, column=1, sticky="ew", padx=8, pady=4)
        self.create_password.bind("<KeyRelease>", lambda event: self._live_preview())

        self.create_show = tk.BooleanVar(value=False)
        ttk.Checkbutton(form, text="Afficher", variable=self.create_show,
                        command=self._toggle_create_show).grid(row=2, column=2, padx=(6, 0))

        ttk.Button(form, text="Créer le compte", command=self.create_account,
                   style="Primary.TButton").grid(row=3, column=1, sticky="e", pady=(10, 0))

        self.create_feedback = ttk.Label(parent, text="", wraplength=560, justify="left")
        self.create_feedback.pack(fill="x", pady=(12, 0), anchor="w")

    def _toggle_create_show(self):
        self.create_password.config(show="" if self.create_show.get() else "•")

    def _evaluate_create(self):
        """Évalue le mot de passe saisi par rapport au cas sélectionné.
        Retourne (accepté, message, type) ; accepté est None si le champ est vide."""
        index = self.create_case.current()
        if index < 0:
            index = 0
        spec = CASE_SPECS[index]
        password = self.create_password.get()
        if not password:
            return None, "", "muted"
        if spec["charset"] is not None:
            problems = _strict_problems(password, spec["charset"], spec["length"])
            if problems:
                return False, "Mot de passe refusé :\n- " + "\n- ".join(problems), "error"
            return True, "Mot de passe conforme au %s." % spec["label"], "ok"
        problems = passwords.strength_problems(password)
        if problems:
            return True, ("Mot de passe accepté. Suggestions pour le renforcer :\n- " +
                          "\n- ".join(problems)), "warn"
        return True, "Mot de passe robuste.", "ok"

    def _live_preview(self):
        accepted, message, kind = self._evaluate_create()
        if accepted is None:
            self._set_create_feedback("", "muted")
        else:
            self._set_create_feedback(message, kind)

    def create_account(self):
        username = self.create_username.get().strip()
        if not username:
            return self._set_create_feedback("Veuillez saisir un nom d'utilisateur.", "error")
        if username in self.accounts:
            return self._set_create_feedback(
                "Ce nom d'utilisateur existe déjà dans cet essai.\n"
                "Choisissez-en un autre, ou cliquez sur « Réinitialiser l'essai ».", "error")
        if not self.create_password.get():
            return self._set_create_feedback("Veuillez saisir un mot de passe.", "error")

        accepted, message, kind = self._evaluate_create()
        if not accepted:
            return self._set_create_feedback(message, kind)

        case_index = self.create_case.current()
        password = self.create_password.get()
        record = passwords.make_record(password)
        self.accounts[username] = {
            "record": record,
            "case_index": case_index,
            "password_used": password,   # conservé pour alimenter l'attaque (démo uniquement)
            "login": _new_login_state(),
        }
        self._set_create_feedback("Compte « %s » créé.\n%s" % (username, message), "ok")
        self.create_username.delete(0, "end")
        self.create_password.delete(0, "end")
        self._refresh_account_lists()

    # ----------------------------------------------------------- Connexion
    def _build_login_tab(self, parent):
        form = ttk.LabelFrame(parent, text="Connexion", padding=12)
        form.pack(fill="x")
        form.columnconfigure(1, weight=1)

        ttk.Label(form, text="Nom d'utilisateur").grid(row=0, column=0, sticky="w", pady=4)
        self.login_username = ttk.Entry(form)
        self.login_username.grid(row=0, column=1, sticky="ew", padx=8, pady=4)

        ttk.Label(form, text="Mot de passe").grid(row=1, column=0, sticky="w", pady=4)
        self.login_password = ttk.Entry(form, show="•")
        self.login_password.grid(row=1, column=1, sticky="ew", padx=8, pady=4)

        ttk.Button(form, text="Se connecter", command=self.attempt_login,
                   style="Primary.TButton").grid(row=2, column=1, sticky="e", pady=(10, 0))

        ttk.Label(parent, text="Politique : 3 essais, puis verrouillage de %ds, puis 3 essais "
                               "supplémentaires, puis blocage définitif du compte."
                               % LOCK_SECONDS,
                  foreground=COLORS["muted"], wraplength=560, justify="left").pack(
            anchor="w", pady=(10, 4))

        self.login_status = ttk.Label(parent, text="", wraplength=560, justify="left")
        self.login_status.pack(anchor="w", pady=(4, 0))

    def attempt_login(self):
        username = self.login_username.get().strip()
        password = self.login_password.get()
        account = self.accounts.get(username)
        if not username:
            return self._set_login_status("Veuillez saisir un nom d'utilisateur.", "error")
        if account is None:
            return self._set_login_status(
                "Aucun compte « %s » dans cet essai." % username, "error")

        state = account["login"]
        now = time.time()

        if state["blocked"]:
            return self._set_login_status(
                "Compte bloqué définitivement. Réinitialisez l'essai ou créez un nouveau "
                "compte pour réessayer.", "error")

        if state["locked_until"] is not None:
            if now < state["locked_until"]:
                remaining = int(state["locked_until"] - now) + 1
                return self._set_login_status(
                    "Compte verrouillé. Réessayez dans %ds." % remaining, "error")
            state["locked_until"] = None   # le verrou vient d'expirer

        if passwords.check_record(account["record"], password):
            state["phase"], state["fails"], state["locked_until"] = 1, 0, None
            self.login_password.delete(0, "end")
            return self._set_login_status(
                "Connexion réussie. Bienvenue %s !" % username, "ok")

        state["fails"] += 1
        if state["fails"] >= MAX_FAILS:
            if state["phase"] == 1:
                state["phase"] = 2
                state["fails"] = 0
                state["locked_until"] = time.time() + LOCK_SECONDS
                self._start_lock_countdown(username)
                return self._set_login_status(
                    "%d/%d essais incorrects. Compte verrouillé pendant %ds."
                    % (MAX_FAILS, MAX_FAILS, LOCK_SECONDS), "error")
            state["blocked"] = True
            return self._set_login_status(
                "%d/%d essais supplémentaires incorrects. Compte bloqué définitivement."
                % (MAX_FAILS, MAX_FAILS), "error")
        return self._set_login_status(
            "Mot de passe incorrect. %d/%d essais utilisés."
            % (state["fails"], MAX_FAILS), "error")

    def _start_lock_countdown(self, username):
        def tick():
            if not self.winfo_exists():
                return
            account = self.accounts.get(username)
            if account is None:
                return
            state = account["login"]
            if state["locked_until"] is None:
                return
            remaining = int(state["locked_until"] - time.time()) + 1
            if remaining <= 0:
                if self.login_username.get().strip() == username:
                    self._set_login_status(
                        "Vous pouvez réessayer (%s)." % username, "muted")
                return
            if self.login_username.get().strip() == username:
                self._set_login_status(
                    "Compte verrouillé. Réessayez dans %ds." % remaining, "error")
            self.after(1000, tick)
        self.after(1000, tick)

    # ------------------------------------------------------------- Attaque
    def _build_attack_tab(self, parent):
        form = ttk.LabelFrame(parent, text="Paramètres de l'attaque", padding=12)
        form.pack(fill="x")
        form.columnconfigure(1, weight=1)

        ttk.Label(form, text="Compte cible").grid(row=0, column=0, sticky="w", pady=4)
        self.attack_target = ttk.Combobox(form, state="readonly")
        self.attack_target.grid(row=0, column=1, sticky="ew", padx=8, pady=4)
        self.attack_target.bind("<<ComboboxSelected>>", lambda event: self._update_target_info())
        ttk.Button(form, text="Actualiser", command=self._refresh_account_lists).grid(
            row=0, column=2, padx=(8, 0))

        ttk.Label(form, text="Méthode").grid(row=1, column=0, sticky="w", pady=4)
        self.attack_method = ttk.Combobox(form, state="readonly", values=ATTACK_METHODS)
        self.attack_method.current(0)
        self.attack_method.grid(row=1, column=1, sticky="ew", padx=8, pady=4)

        self.attack_target_info = ttk.Label(parent, text="", foreground=COLORS["muted"],
                                            wraplength=560, justify="left")
        self.attack_target_info.pack(anchor="w", pady=(8, 0))

        self.attack_button = ttk.Button(parent, text="Lancer l'attaque",
                                        command=self.start_attack, style="Primary.TButton")
        self.attack_button.pack(anchor="e", pady=(8, 8))

        self.attack_timer_label = ttk.Label(parent, text="", foreground=COLORS["muted"])
        self.attack_timer_label.pack(anchor="w")

        self.attack_log = tk.Text(parent, height=14, state="disabled", wrap="word",
                                  relief="flat", bg=COLORS["surface_dark"], fg=COLORS["code"],
                                  font=("Consolas", 10))
        self.attack_log.pack(fill="both", expand=True, pady=(6, 0))

    def _update_target_info(self):
        username = self.attack_target.get()
        account = self.accounts.get(username)
        if account is None:
            self.attack_target_info.config(text="")
            return
        spec = CASE_SPECS[account["case_index"]]
        note = ""
        if spec["charset"] is None:
            note = (" — la force brute suppose la longueur connue (%d caractères) ; "
                    "en situation réelle, l'attaquant ne la connaît pas."
                    % len(account["password_used"]))
        self.attack_target_info.config(text="Cible : %s — %s%s" % (username, spec["label"], note))

    def start_attack(self):
        if self._attack_running:
            return
        username = self.attack_target.get()
        account = self.accounts.get(username)
        if account is None:
            messagebox.showinfo("Attaque", "Choisissez un compte cible (actualisez si besoin).")
            return

        spec = CASE_SPECS[account["case_index"]]
        target_hash = passwords.fingerprint(account["password_used"])
        if spec["charset"] is not None:
            charset, length = spec["charset"], spec["length"]
        else:
            charset, length = passwords.FULL, len(account["password_used"])
        method = self.attack_method.get()

        self._attack_generation += 1
        generation = self._attack_generation
        self._attack_running = True
        self._attack_start = time.perf_counter()
        self.attack_button.config(state="disabled")
        self._append_log("Cible : %s (%s)\nMéthode : %s\n" % (username, spec["label"], method),
                         clear=True)
        self._tick_attack(generation)

        def work():
            if method == "Dictionnaire":
                found, attempts, duration = passwords.dictionary_attack(target_hash)
                self._finish_dictionary(generation, found, attempts, duration)
            elif method == "Force brute":
                found, attempts, duration, reason = passwords.brute_force(
                    target_hash, charset, length, max_seconds=BRUTE_FORCE_SECONDS)
                self._finish_brute(generation, found, attempts, duration, reason)
            else:
                found, attempts, duration = passwords.dictionary_attack(target_hash)
                self._log_phase(generation, found, attempts, duration)
                if found is not None:
                    self._finish_dictionary(generation, found, attempts, duration, combined=True)
                    return
                found2, attempts2, duration2, reason = passwords.brute_force(
                    target_hash, charset, length, max_seconds=BRUTE_FORCE_SECONDS)
                self._finish_brute(generation, found2, attempts2, duration2, reason,
                                   combined=True, extra_attempts=attempts, extra_duration=duration)

        threading.Thread(target=work, daemon=True).start()

    def _tick_attack(self, generation):
        if generation != self._attack_generation or not self.winfo_exists():
            return
        if not self._attack_running:
            self.attack_timer_label.config(text="")
            return
        elapsed = time.perf_counter() - self._attack_start
        self.attack_timer_label.config(
            text="Statut : recherche en cours… Temps écoulé : %s" % passwords.human_time(elapsed))
        self.after(150, lambda: self._tick_attack(generation))

    def _log_phase(self, generation, found, attempts, duration):
        def apply():
            if generation != self._attack_generation or not self.winfo_exists():
                return
            if found is None:
                self._append_log(
                    "Phase dictionnaire : non trouvé (%d tentatives, %s).\n"
                    "Passage à la force brute (limite %ds)…\n"
                    % (attempts, passwords.human_time(duration), BRUTE_FORCE_SECONDS))
        self.after(0, apply)

    def _finish_dictionary(self, generation, found, attempts, duration, combined=False):
        if found is not None:
            text = ("Statut : TROUVÉ (dictionnaire)\nMot de passe : %s\n"
                    "Tentatives : %d\nTemps : %s\n"
                    % (found, attempts, passwords.human_time(duration)))
        else:
            text = ("Statut : NON TROUVÉ (dictionnaire)\n"
                    "Raison : mot de passe absent du dictionnaire.\n"
                    "Tentatives : %d\nTemps : %s\n"
                    % (attempts, passwords.human_time(duration)))
        self._finish(generation, text)

    def _finish_brute(self, generation, found, attempts, duration, reason,
                      combined=False, extra_attempts=0, extra_duration=0.0):
        if found is not None:
            text = ("Statut : TROUVÉ (force brute)\nMot de passe : %s\n"
                    "Tentatives (force brute) : %d\nTemps (force brute) : %s\n"
                    % (found, attempts, passwords.human_time(duration)))
        else:
            reason_text = STOP_REASONS.get(reason, "raison inconnue.")
            text = ("Statut : NON TROUVÉ (force brute)\nRaison : %s\n"
                    "Tentatives (force brute) : %d\nTemps (force brute) : %s\n"
                    % (reason_text, attempts, passwords.human_time(duration)))
        if combined:
            total_attempts = extra_attempts + attempts
            total_duration = extra_duration + duration
            text += ("Total (dictionnaire + force brute) : %d tentatives, %s\n"
                    % (total_attempts, passwords.human_time(total_duration)))
        self._finish(generation, text)

    def _finish(self, generation, text):
        def apply():
            if generation != self._attack_generation or not self.winfo_exists():
                return
            self._attack_running = False
            self._append_log(text)
            self.attack_timer_label.config(text="")
            self.attack_button.config(state="normal")
        self.after(0, apply)

    def _append_log(self, text, clear=False):
        self.attack_log.config(state="normal")
        if clear:
            self.attack_log.delete("1.0", "end")
        self.attack_log.insert("end", text)
        self.attack_log.see("end")
        self.attack_log.config(state="disabled")

    # -------------------------------------------------------------- Divers
    def _refresh_account_lists(self):
        usernames = sorted(self.accounts)
        current = self.attack_target.get()
        self.attack_target["values"] = usernames
        if usernames:
            self.attack_target.current(usernames.index(current) if current in usernames else 0)
        else:
            self.attack_target.set("")
        self._update_target_info()
        self.accounts_count_label.config(
            text="Comptes créés dans cet essai : %d" % len(usernames))

    def reinitialize_trial(self):
        if self.accounts and not messagebox.askyesno(
                "Réinitialiser l'essai",
                "Cela supprime tous les comptes créés dans cet essai (création, connexion, "
                "attaques). Les noms d'utilisateur redeviendront disponibles. Continuer ?"):
            return
        self.accounts.clear()
        self._attack_generation += 1
        self._attack_running = False
        self.attack_button.config(state="normal")
        self.attack_timer_label.config(text="")
        self._append_log("", clear=True)
        self._set_create_feedback("Essai réinitialisé. Tous les noms d'utilisateur sont de "
                                  "nouveau disponibles.", "ok")
        self._set_login_status("", "muted")
        self.login_username.delete(0, "end")
        self.login_password.delete(0, "end")
        self._refresh_account_lists()

    def _set_feedback(self, label, text, kind):
        color = {"error": COLORS["danger"], "ok": COLORS["success"],
                 "warn": COLORS["warn"], "muted": COLORS["muted"]}.get(kind, COLORS["text"])
        label.config(text=text, foreground=color)

    def _set_create_feedback(self, text, kind):
        self._set_feedback(self.create_feedback, text, kind)

    def _set_login_status(self, text, kind):
        self._set_feedback(self.login_status, text, kind)