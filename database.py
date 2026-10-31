"""MySQL adapter matching the CryptoLink SQL schema."""

import json
import os
from contextlib import contextmanager

import mysql.connector

from passwords.crypto import encrypt_password, verify_password

CONFIG = {
    "host": os.getenv("CRYPTO_DB_HOST", "127.0.0.1"),
    "port": int(os.getenv("CRYPTO_DB_PORT", "3306")),
    "user": os.getenv("CRYPTO_DB_USER", "root"),
    "password": os.getenv("CRYPTO_DB_PASSWORD", ""),
    "database": os.getenv("CRYPTO_DB_NAME", "crypto"),
}


class DatabaseError(Exception):
    """MySQL injoignable ou requete refusee."""


class LoginBlocked(Exception):
    """Compatibility exception kept for the login screen."""

    def __init__(self, seconds):
        super().__init__("Trop de tentatives. Reessaie dans %d s." % seconds)
        self.seconds = seconds


SCHEMA = (
    """CREATE TABLE IF NOT EXISTS users (
        id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(50) NOT NULL UNIQUE,
        salt BLOB NOT NULL,
        ciphertext BLOB NOT NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        pseudo VARCHAR(50) NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci""",
    """CREATE TABLE IF NOT EXISTS messages (
        id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        sender_id INT NOT NULL,
        receiver_id INT NOT NULL,
        channel_message TEXT NOT NULL,
        algorithm VARCHAR(20) NOT NULL,
        metadata LONGTEXT NOT NULL CHECK (JSON_VALID(metadata)),
        sent_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        KEY sender_id (sender_id),
        KEY receiver_id (receiver_id),
        CONSTRAINT messages_sender_fk FOREIGN KEY (sender_id) REFERENCES users(id),
        CONSTRAINT messages_receiver_fk FOREIGN KEY (receiver_id) REFERENCES users(id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci""",
    """CREATE TABLE IF NOT EXISTS notifications (
        id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        content VARCHAR(255) NOT NULL,
        is_read TINYINT(1) NOT NULL DEFAULT 0,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        KEY user_id (user_id),
        CONSTRAINT notifications_user_fk FOREIGN KEY (user_id) REFERENCES users(id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci""",
)


@contextmanager
def _cursor(commit=False):
    try:
        connection = mysql.connector.connect(**CONFIG)
    except mysql.connector.Error as error:
        raise DatabaseError(str(error)) from error
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True, buffered=True)
        yield cursor
        if commit:
            connection.commit()
    except mysql.connector.IntegrityError:
        connection.rollback()
        raise
    except mysql.connector.Error as error:
        connection.rollback()
        raise DatabaseError(str(error)) from error
    finally:
        if cursor is not None:
            cursor.close()
        connection.close()


def init_db():
    config = dict(CONFIG)
    database_name = config.pop("database")
    try:
        connection = mysql.connector.connect(**config)
        cursor = connection.cursor()
        cursor.execute(
            "CREATE DATABASE IF NOT EXISTS `%s` CHARACTER SET utf8mb4 "
            "COLLATE=utf8mb4_general_ci" % database_name
        )
        connection.commit()
        cursor.close()
        connection.close()
    except mysql.connector.Error as error:
        raise DatabaseError(str(error)) from error
    with _cursor(commit=True) as cursor:
        for statement in SCHEMA:
            cursor.execute(statement)
        cursor.execute("SHOW COLUMNS FROM users LIKE 'pseudo'")
        if cursor.fetchone() is None:
            cursor.execute("ALTER TABLE users ADD COLUMN pseudo VARCHAR(50) NULL")


DISPLAY_NAME = "COALESCE(NULLIF(pseudo, ''), username)"


def _user_id(cursor, display_name):
    """Trouve un utilisateur par son nom affiché (pseudo, ou username si pas de pseudo)."""
    cursor.execute("SELECT id FROM users WHERE %s = %%s" % DISPLAY_NAME, (display_name,))
    row = cursor.fetchone()
    return row["id"] if row else None


def create_user(username, password, pseudo=None):
    """Create a user using the schema's salt, ciphertext and pseudo columns."""
    pseudo = (pseudo or username).strip()
    salt = os.urandom(16)
    ciphertext = encrypt_password(password, salt)
    try:
        with _cursor(commit=True) as cursor:
            cursor.execute(
                "SELECT id FROM users WHERE username IN (%%s, %%s) OR %s IN (%%s, %%s)" % DISPLAY_NAME,
                (username, pseudo, username, pseudo),
            )
            if cursor.fetchone() is not None:
                raise ValueError("Ce nom d'utilisateur ou ce nom affiche est deja pris.")
            cursor.execute(
                "INSERT INTO users (username, salt, ciphertext, pseudo) VALUES (%s, %s, %s, %s)",
                (username, salt, ciphertext, pseudo),
            )
            return cursor.lastrowid
    except mysql.connector.IntegrityError as error:
        raise ValueError("Ce nom d'utilisateur est deja pris.") from error


def authenticate(username, password):
    with _cursor() as cursor:
        cursor.execute(
            "SELECT id, username, pseudo, salt, ciphertext FROM users WHERE username = %s",
            (username,),
        )
        row = cursor.fetchone()
    if row is None:
        return None
    if not verify_password(password, bytes(row["salt"]), bytes(row["ciphertext"])):
        return None
    return {
        "id": row["id"],
        "username": row["username"],
        "pseudo": row["pseudo"] or row["username"],
    }


def list_users():
    with _cursor() as cursor:
        cursor.execute("SELECT id, username, pseudo FROM users ORDER BY id")
        return [
            {"id": row["id"], "username": row["username"],
             "pseudo": row["pseudo"] or row["username"]}
            for row in cursor.fetchall()
        ]


def pseudo_exists(pseudo):
    with _cursor() as cursor:
        return _user_id(cursor, pseudo) is not None


def send_message(sender_pseudo, receiver_pseudo, text, algorithm=None, metadata=None):
    from partie2 import ciphers

    try:
        detected_algorithm, _, _, _ = ciphers.decode_channel_message(text)
    except ValueError:
        detected_algorithm = algorithm or "Unknown"
    metadata_json = json.dumps(metadata or {}, ensure_ascii=True)
    with _cursor(commit=True) as cursor:
        sender_id = _user_id(cursor, sender_pseudo)
        receiver_id = _user_id(cursor, receiver_pseudo)
        if sender_id is None or receiver_id is None:
            raise ValueError("Destinataire introuvable.")
        cursor.execute(
            "INSERT INTO messages "
            "(sender_id, receiver_id, channel_message, algorithm, metadata) "
            "VALUES (%s, %s, %s, %s, %s)",
            (sender_id, receiver_id, text, detected_algorithm, metadata_json),
        )
        cursor.execute(
            "INSERT INTO notifications (user_id, content) VALUES (%s, %s)",
            (receiver_id, "Nouveau message recu de %s." % sender_pseudo),
        )


def get_messages(pseudo, other=None):
    with _cursor() as cursor:
        current_id = _user_id(cursor, pseudo)
        if current_id is None:
            return []
        if other is None:
            cursor.execute(
                "SELECT * FROM messages WHERE sender_id = %s OR receiver_id = %s ORDER BY id",
                (current_id, current_id),
            )
        else:
            other_id = _user_id(cursor, other)
            cursor.execute(
                "SELECT * FROM messages WHERE (sender_id = %s AND receiver_id = %s) "
                "OR (sender_id = %s AND receiver_id = %s) ORDER BY id",
                (current_id, other_id, other_id, current_id),
            )
        return cursor.fetchall()


def get_inbox(pseudo):
    """Boite de reception : messages recus par l'utilisateur, avec l'expediteur resolu."""
    with _cursor() as cursor:
        user_id = _user_id(cursor, pseudo)
        if user_id is None:
            return []
        cursor.execute(
            "SELECT m.id, m.channel_message, m.algorithm, m.sent_at, "
            "COALESCE(NULLIF(u.pseudo, ''), u.username) AS sender "
            "FROM messages m JOIN users u ON u.id = m.sender_id "
            "WHERE m.receiver_id = %s ORDER BY m.id DESC",
            (user_id,),
        )
        return cursor.fetchall()


def get_notifications(pseudo, unread_only=False):
    with _cursor() as cursor:
        user_id = _user_id(cursor, pseudo)
        if user_id is None:
            return []
        query = "SELECT id, content, is_read, created_at FROM notifications WHERE user_id = %s"
        if unread_only:
            query += " AND is_read = 0"
        query += " ORDER BY id DESC"
        cursor.execute(query, (user_id,))
        return [
            {"id": row["id"], "content": row["content"],
             "is_read": bool(row["is_read"]), "date": row["created_at"]}
            for row in cursor.fetchall()
        ]


def mark_notification_read(notification_id):
    with _cursor(commit=True) as cursor:
        cursor.execute("UPDATE notifications SET is_read = 1 WHERE id = %s", (notification_id,))


def unread_count(pseudo):
    return len(get_notifications(pseudo, unread_only=True))


def dump_raw():
    result = {}
    with _cursor() as cursor:
        for table in ("users", "messages", "notifications"):
            cursor.execute("SELECT * FROM %s" % table)
            result[table] = cursor.fetchall()
    return result