import tempfile
import unittest
from pathlib import Path

from karpuzvet.database import CaseRecord, Database


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.temp_dir.name) / "test.db")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_insert_and_fetch_case(self):
        saved = self.db.save_case(CaseRecord(protocol_no="26-101", patient_name="Mina", owner_name="Ayse", sender_clinic="Karpuz Klinik", status="Kabul Edildi"))
        fetched = self.db.get_case(saved.id)
        self.assertEqual(fetched.protocol_no, "26-101")
        self.assertEqual(fetched.patient_name, "Mina")

    def test_protocol_no_auto_generated_when_blank(self):
        saved = self.db.save_case(CaseRecord(protocol_no="", patient_name="Mina"))
        self.assertRegex(saved.protocol_no, r"^\d{2}-\d{2,}$")

    def test_protocol_no_auto_generation_increments(self):
        first = self.db.save_case(CaseRecord(protocol_no="", patient_name="Bir"))
        second = self.db.save_case(CaseRecord(protocol_no="", patient_name="Iki"))
        self.assertNotEqual(first.protocol_no, second.protocol_no)

    def test_upsert_by_protocol_number(self):
        self.db.save_case(CaseRecord(protocol_no="26-102", patient_name="Ilk"))
        saved = self.db.save_case(CaseRecord(protocol_no="26-102", patient_name="Guncel"))
        cases = self.db.list_cases("26-102")
        self.assertEqual(len(cases), 1)
        self.assertEqual(saved.patient_name, "Guncel")

    def test_default_admin_authentication(self):
        user = self.db.authenticate_user("admin", "admin123")
        self.assertIsNotNone(user)
        self.assertEqual(user.role, "admin")

    def test_create_and_update_user(self):
        created = self.db.create_user("testuser", "1234", "Test Kullanici", "user", 1)
        self.assertIsNotNone(self.db.authenticate_user("testuser", "1234"))
        updated = self.db.update_user(created.id, "Yeni Ad", "admin", 1, "4321")
        self.assertEqual(updated.role, "admin")
        self.assertIsNone(self.db.authenticate_user("testuser", "1234"))
        self.assertIsNotNone(self.db.authenticate_user("testuser", "4321"))

    def test_default_test_types_exist(self):
        test_types = self.db.list_test_types()
        self.assertGreaterEqual(len(test_types), 4)
        self.assertTrue(any(item.code == "10.00.00.009" for item in test_types))
        self.assertTrue(any(item.category == "Biyopsi" for item in test_types))

    def test_case_tests_update_total_fee(self):
        saved = self.db.save_case(CaseRecord(protocol_no="26-103", patient_name="Boncuk"))
        test_type = self.db.list_test_types(active_only=True)[0]
        self.db.replace_case_tests(
            saved.id,
            [{"test_type_id": test_type.id, "quantity": 2, "unit_price": test_type.unit_price}],
        )
        tests = self.db.list_case_tests(saved.id)
        refreshed = self.db.get_case(saved.id)
        self.assertEqual(len(tests), 1)
        self.assertEqual(tests[0].quantity, 2)
        self.assertAlmostEqual(refreshed.fee, test_type.unit_price * 2)

    def test_multiple_case_tests_accumulate_total_fee(self):
        saved = self.db.save_case(CaseRecord(protocol_no="26-104", patient_name="Pati"))
        test_types = self.db.list_test_types(active_only=True)[:2]
        self.db.replace_case_tests(
            saved.id,
            [
                {"test_type_id": test_types[0].id, "quantity": 1, "unit_price": test_types[0].unit_price},
                {"test_type_id": test_types[1].id, "quantity": 3, "unit_price": test_types[1].unit_price},
            ],
        )
        refreshed = self.db.get_case(saved.id)
        expected = test_types[0].unit_price + (test_types[1].unit_price * 3)
        self.assertAlmostEqual(refreshed.fee, expected)
        self.assertEqual(len(self.db.list_case_tests(saved.id)), 2)

    def test_save_test_type_updates_existing_definition(self):
        original = self.db.list_test_types(active_only=True)[0]
        updated = self.db.save_test_type(
            code=original.code,
            name="Guncel Tetkik",
            category="Kontrol",
            unit_price=9999.0,
            is_active=1,
            test_type_id=original.id,
        )
        self.assertEqual(updated.name, "Guncel Tetkik")
        self.assertEqual(updated.category, "Kontrol")
        self.assertAlmostEqual(updated.unit_price, 9999.0)

    def test_backup_snapshot_created_when_enabled(self):
        backup_dir = Path(self.temp_dir.name) / "backups"
        db = Database(Path(self.temp_dir.name) / "backup-test.db", enable_backups=True, backup_dir=backup_dir)
        db.save_case(CaseRecord(protocol_no="26-105", patient_name="Yedek"))
        self.assertTrue((backup_dir / "karpuzvet-latest.db").exists())


if __name__ == "__main__":
    unittest.main()
