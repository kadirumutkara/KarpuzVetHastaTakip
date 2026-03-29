from __future__ import annotations

import tempfile
from pathlib import Path

from karpuzvet.database import CaseRecord, Database
from karpuzvet.pdf_export import build_billing_pdf, build_case_pdf, build_request_form_pdf


def run_startup_checks() -> list[str]:
    messages: list[str] = []
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        db = Database(tmp_path / "startup-check.db")

        admin = db.authenticate_user("admin", "admin123")
        if not admin:
            raise RuntimeError("Startup check failed: admin girisi dogrulanamadi.")
        messages.append("Admin girisi dogrulandi.")

        test_type = db.save_test_type("CHK.001", "Startup Kontrol Tetkigi", 1250.50, 1)
        if not test_type.id:
            raise RuntimeError("Startup check failed: tetkik tanimi olusturulamadi.")
        messages.append("Tetkik tanimi olusturuldu.")

        case = db.save_case(
            CaseRecord(
                protocol_no="CHK-001",
                patient_name="Kontrol Hastasi",
                owner_name="Test Sahibi",
                sender_clinic="Test Klinigi",
                acceptance_date="2026-03-29",
            )
        )
        db.replace_case_tests(
            case.id,
            [
                {"test_type_id": test_type.id, "quantity": 2, "unit_price": test_type.unit_price},
            ],
        )
        checked_case = db.get_case(case.id)
        if checked_case.fee <= 0:
            raise RuntimeError("Startup check failed: vaka ucreti hesaplanamadi.")
        messages.append("Vaka ve tetkik hesaplamasi dogrulandi.")

        tests = db.list_case_tests(case.id)
        build_case_pdf(checked_case, tmp_path / "rapor.pdf")
        build_billing_pdf(checked_case, tests, tmp_path / "borc.pdf")
        build_request_form_pdf(checked_case, tests, tmp_path / "talep.pdf")
        for name in ("rapor.pdf", "borc.pdf", "talep.pdf"):
            if not (tmp_path / name).exists():
                raise RuntimeError(f"Startup check failed: {name} olusturulamadi.")
        messages.append("PDF olusturma akisi dogrulandi.")

    return messages
