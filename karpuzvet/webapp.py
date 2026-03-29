from __future__ import annotations

import json
import logging
import mimetypes
import secrets
import socket
import re
import sys
import threading
import urllib.parse
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from karpuzvet.database import DEFAULT_APP_DIR, DEFAULT_DB_PATH, CaseRecord, Database
from karpuzvet.pdf_export import build_billing_pdf, build_case_pdf, build_proforma_pdf, build_request_form_pdf
from karpuzvet.xlsx_importer import load_cases_from_xlsx


if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    STATIC_DIR = Path(sys._MEIPASS) / "web"
else:
    STATIC_DIR = Path(__file__).resolve().parent.parent / "web"


LOGGER = logging.getLogger("karpuzvet.webapp")


class KarpuzWebApp:
    def __init__(self, db: Database):
        self.db = db
        self.sessions: dict[str, dict[str, object]] = {}

    def create_session(self, user):
        token = secrets.token_urlsafe(24)
        self.sessions[token] = {
            "id": user.id,
            "username": user.username,
            "full_name": user.full_name,
            "role": user.role,
            "is_active": user.is_active,
        }
        return token

    def get_session(self, token: str | None):
        if not token:
            return None
        return self.sessions.get(token)


def _case_to_dict(case: CaseRecord, db: Database | None = None) -> dict[str, object]:
    data = case.__dict__.copy()
    if case.id and db is not None:
        tests = db.list_case_tests(case.id)
        data["tests"] = [test.__dict__.copy() for test in tests]
        data["fee"] = case.fee or sum(test.total_price for test in tests)
    else:
        data["tests"] = []
    return data


def _json_response(handler: BaseHTTPRequestHandler, status: int, payload: dict[str, object]) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _file_response(handler: BaseHTTPRequestHandler, file_path: Path, download_name: str) -> None:
    body = file_path.read_bytes()
    handler.send_response(HTTPStatus.OK)
    handler.send_header("Content-Type", "application/pdf")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Content-Disposition", f'attachment; filename="{download_name}"')
    handler.end_headers()
    handler.wfile.write(body)


def _read_json(handler: BaseHTTPRequestHandler) -> dict[str, object]:
    length = int(handler.headers.get("Content-Length", "0"))
    raw = handler.rfile.read(length) if length else b"{}"
    return json.loads(raw.decode("utf-8"))


def _parse_decimal(value: object) -> float:
    normalized = str(value or "").replace(",", ".").strip()
    try:
        return float(normalized) if normalized else 0.0
    except ValueError as exc:
        raise ValueError("Sayisal alan gecersiz.") from exc


def _build_case_from_payload(payload: dict[str, object], case_id=None) -> CaseRecord:
    try:
        fee = _parse_decimal(payload.get("fee", ""))
    except ValueError:
        fee = 0.0
    return CaseRecord(
        id=case_id,
        protocol_no=str(payload.get("protocol_no", "")).strip(),
        acceptance_date=str(payload.get("acceptance_date", "")).strip(),
        sender_clinic=str(payload.get("sender_clinic", "")).strip(),
        owner_name=str(payload.get("owner_name", "")).strip(),
        owner_phone=str(payload.get("owner_phone", "")).strip(),
        patient_name=str(payload.get("patient_name", "")).strip(),
        species=str(payload.get("species", "")).strip(),
        breed=str(payload.get("breed", "")).strip(),
        birth_date=str(payload.get("birth_date", "")).strip(),
        gender=str(payload.get("gender", "")).strip(),
        neutered=str(payload.get("neutered", "")).strip(),
        material=str(payload.get("material", "")).strip(),
        pre_diagnosis=str(payload.get("pre_diagnosis", "")).strip(),
        sample_location=str(payload.get("sample_location", "")).strip(),
        urgency=str(payload.get("urgency", "")).strip(),
        status=str(payload.get("status", "")).strip(),
        assigned_pathologist=str(payload.get("assigned_pathologist", "")).strip(),
        gross_findings=str(payload.get("gross_findings", "")).strip(),
        micro_findings=str(payload.get("micro_findings", "")).strip(),
        diagnosis=str(payload.get("diagnosis", "")).strip(),
        report_summary=str(payload.get("report_summary", "")).strip(),
        notes=str(payload.get("notes", "")).strip(),
        fee=fee,
    )


def _slugify_filename_part(value: str | None, fallback: str) -> str:
    raw = (value or "").strip()
    if not raw:
        return fallback
    normalized = raw.replace("/", "-").replace("\\", "-").replace(" ", "_")
    normalized = re.sub(r"[^0-9A-Za-zÇĞİÖŞÜçğıöşü_-]+", "", normalized)
    return normalized[:80] or fallback


def _build_export_filename(case: CaseRecord, suffix: str) -> str:
    date_part = _slugify_filename_part(case.acceptance_date, "tarih-yok")
    patient_part = _slugify_filename_part(case.patient_name, "hasta-yok")
    protocol_part = _slugify_filename_part(case.protocol_no, "protokol-yok")
    return f"{suffix}_{date_part}_{patient_part}_{protocol_part}.pdf"


def make_handler(app: KarpuzWebApp):
    class Handler(BaseHTTPRequestHandler):
        def _safe_handle(self, fn):
            try:
                fn()
            except Exception as exc:  # pragma: no cover - exercised through runtime
                LOGGER.exception("Istek islenirken hata olustu. path=%s", self.path)
                _json_response(self, HTTPStatus.INTERNAL_SERVER_ERROR, {"ok": False, "error": "Beklenmeyen bir hata olustu."})

        def do_GET(self):
            def _impl():
                parsed = urllib.parse.urlparse(self.path)
                LOGGER.info("GET %s", parsed.path)
                if parsed.path == "/api/bootstrap":
                    token = urllib.parse.parse_qs(parsed.query).get("token", [None])[0]
                    session = app.get_session(token)
                    if not session:
                        return _json_response(self, HTTPStatus.UNAUTHORIZED, {"ok": False, "error": "Unauthorized"})
                    cases = [_case_to_dict(case, app.db) for case in app.db.list_cases()]
                    users = [user.__dict__.copy() for user in app.db.list_users()] if session["role"] == "admin" else []
                    tests = [item.__dict__.copy() for item in app.db.list_test_types()]
                    return _json_response(self, HTTPStatus.OK, {"ok": True, "session": session, "counts": app.db.case_counts(), "cases": cases, "users": users, "test_types": tests})

                if parsed.path == "/api/cases":
                    params = urllib.parse.parse_qs(parsed.query)
                    token = params.get("token", [None])[0]
                    session = app.get_session(token)
                    if not session:
                        return _json_response(self, HTTPStatus.UNAUTHORIZED, {"ok": False, "error": "Unauthorized"})
                    query = params.get("q", [""])[0]
                    status = params.get("status", [""])[0]
                    cases = [_case_to_dict(case, app.db) for case in app.db.list_cases(query, status)]
                    return _json_response(self, HTTPStatus.OK, {"ok": True, "cases": cases, "counts": app.db.case_counts()})

                if parsed.path == "/api/export/pdf":
                    params = urllib.parse.parse_qs(parsed.query)
                    token = params.get("token", [None])[0]
                    case_id_raw = params.get("id", [None])[0]
                    session = app.get_session(token)
                    if not session or not case_id_raw:
                        return _json_response(self, HTTPStatus.UNAUTHORIZED, {"ok": False, "error": "Unauthorized"})
                    case = app.db.get_case(int(case_id_raw))
                    export_dir = DEFAULT_APP_DIR / "exports"
                    export_dir.mkdir(parents=True, exist_ok=True)
                    target = export_dir / _build_export_filename(case, "rapor")
                    build_case_pdf(case, target)
                    LOGGER.info("Rapor PDF olusturuldu: %s", target)
                    if params.get("download", ["0"])[0] == "1":
                        return _file_response(self, target, target.name)
                    return _json_response(self, HTTPStatus.OK, {"ok": True, "path": str(target)})

                if parsed.path == "/api/export/billing":
                    params = urllib.parse.parse_qs(parsed.query)
                    token = params.get("token", [None])[0]
                    case_id_raw = params.get("id", [None])[0]
                    session = app.get_session(token)
                    if not session or not case_id_raw:
                        return _json_response(self, HTTPStatus.UNAUTHORIZED, {"ok": False, "error": "Unauthorized"})
                    case = app.db.get_case(int(case_id_raw))
                    tests = app.db.list_case_tests(int(case_id_raw))
                    export_dir = DEFAULT_APP_DIR / "exports"
                    export_dir.mkdir(parents=True, exist_ok=True)
                    target = export_dir / _build_export_filename(case, "borc-detayi")
                    build_billing_pdf(case, tests, target)
                    LOGGER.info("Borc detayi PDF olusturuldu: %s", target)
                    if params.get("download", ["0"])[0] == "1":
                        return _file_response(self, target, target.name)
                    return _json_response(self, HTTPStatus.OK, {"ok": True, "path": str(target)})

                if parsed.path == "/api/export/request-form":
                    params = urllib.parse.parse_qs(parsed.query)
                    token = params.get("token", [None])[0]
                    case_id_raw = params.get("id", [None])[0]
                    session = app.get_session(token)
                    if not session or not case_id_raw:
                        return _json_response(self, HTTPStatus.UNAUTHORIZED, {"ok": False, "error": "Unauthorized"})
                    case = app.db.get_case(int(case_id_raw))
                    tests = app.db.list_case_tests(int(case_id_raw))
                    export_dir = DEFAULT_APP_DIR / "exports"
                    export_dir.mkdir(parents=True, exist_ok=True)
                    target = export_dir / _build_export_filename(case, "analiz-talep")
                    build_request_form_pdf(case, tests, target)
                    LOGGER.info("Analiz talep PDF olusturuldu: %s", target)
                    if params.get("download", ["0"])[0] == "1":
                        return _file_response(self, target, target.name)
                    return _json_response(self, HTTPStatus.OK, {"ok": True, "path": str(target)})

                if parsed.path == "/api/export/proforma":
                    params = urllib.parse.parse_qs(parsed.query)
                    token = params.get("token", [None])[0]
                    case_id_raw = params.get("id", [None])[0]
                    session = app.get_session(token)
                    if not session or not case_id_raw:
                        return _json_response(self, HTTPStatus.UNAUTHORIZED, {"ok": False, "error": "Unauthorized"})
                    case = app.db.get_case(int(case_id_raw))
                    tests = app.db.list_case_tests(int(case_id_raw))
                    export_dir = DEFAULT_APP_DIR / "exports"
                    export_dir.mkdir(parents=True, exist_ok=True)
                    target = export_dir / _build_export_filename(case, "proforma")
                    build_proforma_pdf(case, tests, target)
                    LOGGER.info("Proforma PDF olusturuldu: %s", target)
                    if params.get("download", ["0"])[0] == "1":
                        return _file_response(self, target, target.name)
                    return _json_response(self, HTTPStatus.OK, {"ok": True, "path": str(target)})

                return self._serve_static(parsed.path)

            self._safe_handle(_impl)

        def do_POST(self):
            def _impl():
                parsed = urllib.parse.urlparse(self.path)
                LOGGER.info("POST %s", parsed.path)
                payload = _read_json(self)
                if parsed.path == "/api/login":
                    user = app.db.authenticate_user(str(payload.get("username", "")), str(payload.get("password", "")))
                    if not user:
                        LOGGER.warning("Basarisiz login denemesi. username=%s", str(payload.get("username", "")))
                        return _json_response(self, HTTPStatus.UNAUTHORIZED, {"ok": False, "error": "Kullanici adi veya sifre hatali."})
                    token = app.create_session(user)
                    LOGGER.info("Basarili login. username=%s", user.username)
                    return _json_response(self, HTTPStatus.OK, {"ok": True, "token": token, "user": user.__dict__})

                if parsed.path == "/api/cases":
                    token = str(payload.get("token", ""))
                    session = app.get_session(token)
                    if not session:
                        return _json_response(self, HTTPStatus.UNAUTHORIZED, {"ok": False, "error": "Unauthorized"})
                    case_id = payload.get("id")
                    case = _build_case_from_payload(payload, int(case_id) if case_id else None)
                    saved = app.db.save_case(case)
                    selected_tests = payload.get("selected_tests") or []
                    if saved.id is not None and isinstance(selected_tests, list):
                        app.db.replace_case_tests(saved.id, selected_tests)
                        saved = app.db.get_case(saved.id)
                    LOGGER.info("Vaka kaydedildi. protocol_no=%s id=%s", saved.protocol_no, saved.id)
                    return _json_response(self, HTTPStatus.OK, {"ok": True, "case": _case_to_dict(saved, app.db), "counts": app.db.case_counts()})

                if parsed.path == "/api/users":
                    token = str(payload.get("token", ""))
                    session = app.get_session(token)
                    if not session or session["role"] != "admin":
                        return _json_response(self, HTTPStatus.UNAUTHORIZED, {"ok": False, "error": "Unauthorized"})
                    try:
                        if payload.get("id"):
                            user = app.db.update_user(
                                int(payload["id"]),
                                str(payload.get("full_name", "")),
                                str(payload.get("role", "user")),
                                int(payload.get("is_active", 1)),
                                str(payload.get("password", "")),
                            )
                        else:
                            user = app.db.create_user(
                                str(payload.get("username", "")),
                                str(payload.get("password", "")),
                                str(payload.get("full_name", "")),
                                str(payload.get("role", "user")),
                                int(payload.get("is_active", 1)),
                            )
                    except Exception as exc:
                        LOGGER.warning("Kullanici kaydetme hatasi: %s", exc)
                        return _json_response(self, HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(exc)})
                    users = [entry.__dict__.copy() for entry in app.db.list_users()]
                    LOGGER.info("Kullanici kaydedildi. username=%s", user.username)
                    return _json_response(self, HTTPStatus.OK, {"ok": True, "user": user.__dict__, "users": users})

                if parsed.path == "/api/test-types":
                    token = str(payload.get("token", ""))
                    session = app.get_session(token)
                    if not session or session["role"] != "admin":
                        return _json_response(self, HTTPStatus.UNAUTHORIZED, {"ok": False, "error": "Unauthorized"})
                    try:
                        test_type = app.db.save_test_type(
                            code=str(payload.get("code", "")),
                            name=str(payload.get("name", "")),
                            unit_price=_parse_decimal(payload.get("unit_price", 0)),
                            is_active=int(payload.get("is_active", 1)),
                            category=str(payload.get("category", "Genel")),
                            test_type_id=int(payload["id"]) if payload.get("id") else None,
                        )
                    except Exception as exc:
                        LOGGER.warning("Tetkik kaydetme hatasi: %s", exc)
                        return _json_response(self, HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(exc)})
                    tests = [entry.__dict__.copy() for entry in app.db.list_test_types()]
                    LOGGER.info("Tetkik kaydedildi. code=%s", test_type.code)
                    return _json_response(self, HTTPStatus.OK, {"ok": True, "test_type": test_type.__dict__, "test_types": tests})

                if parsed.path == "/api/import":
                    token = str(payload.get("token", ""))
                    session = app.get_session(token)
                    if not session:
                        return _json_response(self, HTTPStatus.UNAUTHORIZED, {"ok": False, "error": "Unauthorized"})
                    try:
                        imported = app.db.import_cases(load_cases_from_xlsx(str(payload.get("path", ""))))
                    except Exception as exc:
                        LOGGER.warning("Excel ice aktarim hatasi: %s", exc)
                        return _json_response(self, HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(exc)})
                    LOGGER.info("Excel ice aktarim tamamlandi. adet=%s", imported)
                    return _json_response(self, HTTPStatus.OK, {"ok": True, "imported": imported, "counts": app.db.case_counts(), "cases": [_case_to_dict(case, app.db) for case in app.db.list_cases()]})

                return _json_response(self, HTTPStatus.NOT_FOUND, {"ok": False, "error": "Not found"})

            self._safe_handle(_impl)

        def log_message(self, format, *args):
            return

        def _serve_static(self, path: str):
            file_path = STATIC_DIR / ("index.html" if path in ("/", "") else path.lstrip("/"))
            if not file_path.exists() or not file_path.is_file():
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            content_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
            if content_type.startswith("text/") or content_type in ("application/javascript", "application/json"):
                content_type = f"{content_type}; charset=utf-8"
            body = file_path.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return Handler


def launch_web_app(port: int = 8765, open_browser: bool = True) -> ThreadingHTTPServer:
    DEFAULT_APP_DIR.mkdir(parents=True, exist_ok=True)
    app = KarpuzWebApp(Database(DEFAULT_DB_PATH))
    server = None
    last_error = None
    for candidate_port in range(port, port + 10):
        try:
            server = ThreadingHTTPServer(("127.0.0.1", candidate_port), make_handler(app))
            break
        except OSError as exc:
            last_error = exc
            continue
    if server is None:
        raise OSError(f"Uygulama portu acilamadi: {last_error}") from last_error
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    if open_browser:
        webbrowser.open(f"http://127.0.0.1:{server.server_address[1]}")
    return server
