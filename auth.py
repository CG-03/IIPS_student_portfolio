"""Authentication: password hashing (PBKDF2-HMAC-SHA256), registration, login."""
import hashlib
import hmac
import re
import secrets
import sqlite3
from contextlib import closing

from database import get_conn, query, execute

ITERATIONS = 200_000
DEFAULT_ADMIN_USER = "admin"
DEFAULT_ADMIN_PASSWORD = "Admin@123"
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), ITERATIONS)
    return digest.hex(), salt


def verify_password(password, stored_hash, salt):
    candidate, _ = hash_password(password, salt)
    return hmac.compare_digest(candidate, stored_hash)


def validate_password(password):
    if len(password) < 8:
        return "Password must be at least 8 characters long."
    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        return "Password must contain at least one letter and one number."
    return ""


def ensure_default_admin():
    if query("SELECT 1 FROM users WHERE role = 'admin' LIMIT 1", one=True):
        return
    pw_hash, salt = hash_password(DEFAULT_ADMIN_PASSWORD)
    execute(
        "INSERT INTO users (username, email, full_name, password_hash, salt, role, must_change_password) "
        "VALUES (?, ?, ?, ?, ?, 'admin', 1)",
        (DEFAULT_ADMIN_USER, "", "System Administrator", pw_hash, salt),
    )


def get_user(user_id):
    return query(
        "SELECT id, username, email, full_name, role, must_change_password FROM users WHERE id = ?",
        (user_id,), one=True,
    )


def register_student(full_name, enrollment, email, password, confirm):
    full_name, enrollment, email = full_name.strip(), enrollment.strip().upper(), email.strip().lower()
    if not 3 <= len(full_name) <= 80:
        return False, "Full name must be between 3 and 80 characters."
    if not re.match(r"^[A-Z0-9/\-]{4,20}$", enrollment):
        return False, "Enrollment number must be 4-20 characters (letters, numbers, / or -)."
    if len(email) > 120 or not EMAIL_RE.match(email):
        return False, "Please enter a valid email address."
    err = validate_password(password)
    if err:
        return False, err
    if password != confirm:
        return False, "Passwords do not match."
    pw_hash, salt = hash_password(password)
    with closing(get_conn()) as conn:
        try:
            conn.execute("BEGIN IMMEDIATE")
            if conn.execute(
                "SELECT 1 FROM users WHERE email = ? COLLATE NOCASE "
                "OR username = ? COLLATE NOCASE LIMIT 1",
                (email, email),
            ).fetchone():
                conn.rollback()
                return False, "An account with this email already exists."
            if conn.execute(
                "SELECT 1 FROM student_profiles WHERE UPPER(enrollment_no) = ? LIMIT 1",
                (enrollment,),
            ).fetchone():
                conn.rollback()
                return False, "An account with this enrollment number already exists."
            cur = conn.execute(
                "INSERT INTO users (username, email, full_name, password_hash, salt, role) "
                "VALUES (?, ?, ?, ?, ?, 'student')",
                (email, email, full_name, pw_hash, salt),
            )
            conn.execute(
                "INSERT INTO student_profiles (user_id, enrollment_no) VALUES (?, ?)",
                (cur.lastrowid, enrollment),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            conn.rollback()
            if conn.execute(
                "SELECT 1 FROM users WHERE email = ? COLLATE NOCASE "
                "OR username = ? COLLATE NOCASE LIMIT 1",
                (email, email),
            ).fetchone():
                return False, "An account with this email already exists."
            if conn.execute(
                "SELECT 1 FROM student_profiles WHERE UPPER(enrollment_no) = ? LIMIT 1",
                (enrollment,),
            ).fetchone():
                return False, "An account with this enrollment number already exists."
            raise
    return True, "Registration successful. You can now log in."


def authenticate(identifier, password):
    identifier = identifier.strip()
    row = query(
        "SELECT id, username, email, full_name, password_hash, salt, role, must_change_password "
        "FROM users WHERE username = ? COLLATE NOCASE",
        (identifier,), one=True,
    )
    if not row:
        matches = query(
            "SELECT id, username, email, full_name, password_hash, salt, role, must_change_password "
            "FROM users WHERE email = ? COLLATE NOCASE ORDER BY id LIMIT 2",
            (identifier,),
        )
        row = matches[0] if len(matches) == 1 else None
    if not row:
        hash_password(password)  # keep timing similar for unknown users
        return None
    if verify_password(password, row["password_hash"], row["salt"]):
        return get_user(row["id"])
    return None


def change_password(user_id, old, new, confirm):
    row = query("SELECT password_hash, salt FROM users WHERE id = ?", (user_id,), one=True)
    if not row or not verify_password(old, row["password_hash"], row["salt"]):
        return False, "Current password is incorrect."
    err = validate_password(new)
    if err:
        return False, err
    if new != confirm:
        return False, "New passwords do not match."
    if new == old or new == DEFAULT_ADMIN_PASSWORD:
        return False, "Please choose a new password different from the current/default one."
    pw_hash, salt = hash_password(new)
    execute(
        "UPDATE users SET password_hash = ?, salt = ?, must_change_password = 0 WHERE id = ?",
        (pw_hash, salt, user_id),
    )
    return True, "Password updated successfully."
