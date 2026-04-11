import tempfile
import unittest
from pathlib import Path

from karpuzvet.database import CaseRecord, CaseTestRecord
from karpuzvet.pdf_export import FONT_PATHS, OVERLAY_FONT_PATHS, build_billing_pdf, build_case_pdf, build_proforma_pdf, build_request_form_pdf


class PdfExportTests(unittest.TestCase):
    def test_build_case_pdf_creates_file(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            target = Path(tmp_dir) / "rapor.pdf"
            build_case_pdf(
                CaseRecord(
                    protocol_no="26-301",
                    patient_name="Kıtır",
                    owner_name="Ayşe",
                    sender_clinic="Karpuz Vet",
                    diagnosis="Mast hucreli tumor",
                    report_summary="Cerrahi sınırlar temiz görünmektedir.",
                ),
                target,
            )
            self.assertTrue(target.exists())
            self.assertGreater(target.stat().st_size, 500)

    def test_build_billing_pdf_creates_file(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            target = Path(tmp_dir) / "borc.pdf"
            build_billing_pdf(
                CaseRecord(
                    protocol_no="26-302",
                    acceptance_date="2026-03-29",
                    owner_name="Ayse Yilmaz",
                    material="Nekropsi Ornegi",
                ),
                [
                    CaseTestRecord(
                        case_id=1,
                        test_type_id=1,
                        quantity=1,
                        unit_price=6500.0,
                        total_price=6500.0,
                        test_code="10.00.00.009",
                        test_name="Nekropsi Ornegi",
                    )
                ],
                target,
            )
            self.assertTrue(target.exists())
            self.assertGreater(target.stat().st_size, 500)

    def test_build_request_form_pdf_creates_file(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            target = Path(tmp_dir) / "talep.pdf"
            build_request_form_pdf(
                CaseRecord(
                    protocol_no="26-303",
                    acceptance_date="2026-03-29",
                    owner_name="Ayse Yilmaz",
                    owner_phone="0555 111 22 33",
                    sender_clinic="Karpuz Vet",
                    pre_diagnosis="Kontrol amacli",
                ),
                [
                    CaseTestRecord(
                        case_id=1,
                        test_type_id=1,
                        quantity=2,
                        unit_price=2500.0,
                        total_price=5000.0,
                        test_code="10.00.00.010",
                        test_name="Sitoloji",
                    )
                ],
                target,
            )
            self.assertTrue(target.exists())
            self.assertGreater(target.stat().st_size, 500)

    def test_build_proforma_pdf_creates_file(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            target = Path(tmp_dir) / "proforma.pdf"
            build_proforma_pdf(
                CaseRecord(
                    protocol_no="26-304",
                    acceptance_date="2026-03-29",
                    owner_name="Ayse Yilmaz",
                    patient_name="Mavi",
                    sender_clinic="Karpuz Vet",
                ),
                [
                    CaseTestRecord(
                        case_id=1,
                        test_type_id=1,
                        quantity=1,
                        unit_price=4500.0,
                        total_price=4500.0,
                        test_code="10.00.00.008",
                        test_name="Kucuk Irk Biyopsi / Histopatoloji",
                    )
                ],
                target,
            )
            self.assertTrue(target.exists())
            self.assertGreater(target.stat().st_size, 500)

    def test_windows_font_candidates_exist_in_configuration(self):
        font_paths = {str(path).lower() for _, path in FONT_PATHS}
        overlay_paths = {str(path).lower() for _, path in OVERLAY_FONT_PATHS}
        self.assertIn("c:/windows/fonts/arial.ttf", font_paths)
        self.assertIn("c:/windows/fonts/arialbd.ttf", font_paths)
        self.assertIn("c:/windows/fonts/arial.ttf", overlay_paths)
        self.assertIn("c:/windows/fonts/arialbd.ttf", overlay_paths)


if __name__ == "__main__":
    unittest.main()
