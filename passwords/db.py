import os
import mysql.connector

def get_db_connection():
    return mysql.connector.connect(
        host="127.0.0.1",
        user="root",
        password="",
        database="crypto"
    )

def clear_all_users():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id NOT IN (4, 5)")
    conn.commit()
    cursor.close()
    conn.close()