import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

import auth
import database


class AuthenticationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "student_portfolio.db"
        self.db_path_patch = patch.object(database, "DB_PATH", self.db_path)
        self.db_path_patch.start()
        database.init_db()

    def tearDown(self):
        self.db_path_patch.stop()
        self.temp_dir.cleanup()

    def test_registration_persists_student_profile_and_password_hash(self):
        ok, message = auth.register_student(
            "Test Student", "ENR-1001", "student@example.edu", "Student123", "Student123"
        )

        self.assertTrue(ok, message)
        student = auth.authenticate("STUDENT@example.edu", "Student123")
        self.assertIsNotNone(student)
        self.assertEqual(student["role"], "student")
        profile = database.query(
            "SELECT enrollment_no FROM student_profiles WHERE user_id = ?",
            (student["id"],), one=True,
        )
        self.assertEqual(profile["enrollment_no"], "ENR-1001")
        stored = database.query(
            "SELECT password_hash FROM users WHERE id = ?", (student["id"],), one=True
        )
        self.assertNotEqual(stored["password_hash"], "Student123")
        self.assertIsNone(auth.authenticate("student@example.edu", "Incorrect123"))

    def test_duplicate_email_is_detected_even_when_username_differs(self):
        password_hash, salt = auth.hash_password("Legacy123")
        database.execute(
            "INSERT INTO users (username, email, full_name, password_hash, salt, role) "
            "VALUES (?, ?, ?, ?, ?, 'student')",
            ("legacy-login", "taken@example.edu", "Legacy Student", password_hash, salt),
        )

        ok, message = auth.register_student(
            "Another Student", "ENR-1002", "TAKEN@example.edu", "Student123", "Student123"
        )

        self.assertFalse(ok)
        self.assertIn("email", message.lower())

    def test_existing_account_can_log_in_using_email(self):
        password_hash, salt = auth.hash_password("Legacy123")
        user_id = database.execute(
            "INSERT INTO users (username, email, full_name, password_hash, salt, role) "
            "VALUES (?, ?, ?, ?, ?, 'student')",
            ("legacy-login", "legacy@example.edu", "Legacy Student", password_hash, salt),
        )

        user = auth.authenticate("LEGACY@example.edu", "Legacy123")

        self.assertEqual(user["id"], user_id)
        self.assertEqual(user["role"], "student")

    def test_duplicate_enrollment_is_rejected(self):
        auth.register_student(
            "First Student", "ENR-1001", "first@example.edu", "Student123", "Student123"
        )

        ok, message = auth.register_student(
            "Second Student", "enr-1001", "second@example.edu", "Student123", "Student123"
        )

        self.assertFalse(ok)
        self.assertIn("enrollment", message.lower())
        self.assertIsNone(auth.authenticate("second@example.edu", "Student123"))

    def test_registration_rejects_invalid_fields(self):
        invalid_cases = [
            ("  ", "ENR-1001", "valid@example.edu", "Student123", "Student123", "full name"),
            ("Valid Name", "ENR-1002", "not-an-email", "Student123", "Student123", "email"),
            ("Valid Name", "ENR-1003", "weak@example.edu", "weak", "weak", "password"),
            ("Valid Name", "ENR-1004", "mismatch@example.edu", "Student123", "Student456", "match"),
        ]
        for name, enrollment, email, password, confirm, expected in invalid_cases:
            with self.subTest(expected=expected):
                ok, message = auth.register_student(name, enrollment, email, password, confirm)
                self.assertFalse(ok)
                self.assertIn(expected, message.lower())
        self.assertEqual(database.query("SELECT COUNT(*) AS n FROM users", one=True)["n"], 0)

    def test_failed_profile_insert_rolls_back_user_insert(self):
        with closing(database.get_conn()) as conn:
            conn.execute(
                "CREATE TRIGGER reject_test_profile BEFORE INSERT ON student_profiles "
                "WHEN NEW.enrollment_no = 'FAIL-0001' "
                "BEGIN SELECT RAISE(ABORT, 'test failure'); END"
            )
            conn.commit()

        with self.assertRaises(sqlite3.IntegrityError):
            auth.register_student(
                "Test Student", "FAIL-0001", "rollback@example.edu", "Student123", "Student123"
            )

        self.assertEqual(database.query(
            "SELECT COUNT(*) AS n FROM users WHERE email = 'rollback@example.edu'", one=True
        )["n"], 0)

    def test_default_admin_is_not_duplicated_and_password_change_works(self):
        auth.ensure_default_admin()
        auth.ensure_default_admin()

        self.assertEqual(
            database.query("SELECT COUNT(*) AS n FROM users WHERE role = 'admin'", one=True)["n"],
            1,
        )
        admin_user = auth.authenticate("admin", "Admin@123")
        self.assertIsNotNone(admin_user)
        self.assertEqual(admin_user["role"], "admin")
        ok, message = auth.change_password(
            admin_user["id"], "Admin@123", "NewAdmin123", "NewAdmin123"
        )
        self.assertTrue(ok, message)
        self.assertEqual(auth.authenticate("admin", "NewAdmin123")["must_change_password"], 0)


if __name__ == "__main__":
    unittest.main()
