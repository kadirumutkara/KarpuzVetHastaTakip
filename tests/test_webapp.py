import tempfile
import unittest
from pathlib import Path

from karpuzvet.database import CaseRecord, Database
from karpuzvet.webapp import KarpuzWebApp, _build_case_from_payload, _case_to_dict, _parse_decimal


class WebAppTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.temp_dir.name) / "test-web.db")
        self.app = KarpuzWebApp(self.db)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_login_session_flow(self):
        user = self.db.authenticate_user("admin", "admin123")
        token = self.app.create_session(user)
        session = self.app.get_session(token)
        self.assertEqual(session["username"], "admin")
        self.assertEqual(session["role"], "admin")

    def test_parse_decimal_accepts_comma_value(self):
        self.assertAlmostEqual(_parse_decimal("10000,03"), 10000.03)

    def test_build_case_from_payload_parses_fee(self):
        case = _build_case_from_payload(
            {
                "protocol_no": "26-WEB-01",
                "patient_name": "Pati",
                "owner_name": "Ali",
                "fee": "1500,75",
            }
        )
        self.assertEqual(case.protocol_no, "26-WEB-01")
        self.assertAlmostEqual(case.fee, 1500.75)

    def test_case_to_dict_includes_multiple_tests(self):
        saved = self.db.save_case(CaseRecord(protocol_no="26-WEB-02", patient_name="Pati"))
        test_types = self.db.list_test_types(active_only=True)[:2]
        self.db.replace_case_tests(
            saved.id,
            [
                {"test_type_id": test_types[0].id, "quantity": 1, "unit_price": test_types[0].unit_price},
                {"test_type_id": test_types[1].id, "quantity": 2, "unit_price": test_types[1].unit_price},
            ],
        )
        case_data = _case_to_dict(self.db.get_case(saved.id), self.db)
        self.assertEqual(len(case_data["tests"]), 2)
        expected_fee = test_types[0].unit_price + (test_types[1].unit_price * 2)
        self.assertAlmostEqual(case_data["fee"], expected_fee)


if __name__ == "__main__":
    unittest.main()
