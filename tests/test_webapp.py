import tempfile
import unittest
from io import BytesIO
from pathlib import Path

from karpuzvet.database import CaseRecord, Database
from karpuzvet.webapp import KarpuzWebApp, _build_case_from_payload, _case_to_dict, _file_response, _parse_decimal


class _FakeHandler:
    def __init__(self):
        self.headers = []
        self.wfile = BytesIO()
        self.close_connection = False
        self.status = None
        self.ended = False

    def send_response(self, status):
        self.status = status

    def send_header(self, key, value):
        self.headers.append((key, value))

    def end_headers(self):
        self.ended = True


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

    def test_file_response_uses_utf8_disposition_without_content_length(self):
        pdf_path = Path(self.temp_dir.name) / "örnek.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 test")
        handler = _FakeHandler()

        _file_response(handler, pdf_path, "rapor_çalışma.pdf")

        header_map = dict(handler.headers)
        self.assertEqual(handler.status, 200)
        self.assertEqual(header_map["Content-Type"], "application/pdf")
        self.assertIn("filename*=UTF-8''rapor_%C3%A7al%C4%B1%C5%9Fma.pdf", header_map["Content-Disposition"])
        self.assertEqual(header_map["Cache-Control"], "no-store")
        self.assertNotIn("Content-Length", header_map)
        self.assertTrue(handler.close_connection)
        self.assertEqual(handler.wfile.getvalue(), b"%PDF-1.4 test")


if __name__ == "__main__":
    unittest.main()
