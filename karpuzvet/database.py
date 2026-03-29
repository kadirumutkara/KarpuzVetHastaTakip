from __future__ import annotations

import hashlib
import hmac
import os
import shutil
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional


DEFAULT_APP_DIR = Path.home() / "KarpuzVetHastaTakip"
DEFAULT_DB_PATH = DEFAULT_APP_DIR / "karpuzvet.db"
DEFAULT_BACKUP_DIR = DEFAULT_APP_DIR / "backups"

STATUS_OPTIONS = [
    "Kabul Edildi",
    "Makroskopi Bekliyor",
    "Rapor Hazirlaniyor",
    "Tamamlandi",
]

USER_ROLES = ["admin", "user"]

DEFAULT_TEST_TYPES = [
    {"code": "10.00.00.008", "name": "Kucuk Irk Biyopsi / Histopatoloji", "category": "Biyopsi", "unit_price": 4500.0},
    {"code": "10.00.00.009", "name": "Nekropsi Ornegi", "category": "Nekropsi", "unit_price": 6500.0},
    {"code": "10.00.00.010", "name": "Sitoloji", "category": "Sitoloji", "unit_price": 2500.0},
    {"code": "10.00.00.011", "name": "Immunhistokimya", "category": "Immunhistokimya", "unit_price": 3500.0},
]


@dataclass
class CaseRecord:
    protocol_no: str
    acceptance_date: str = ""
    sender_clinic: str = ""
    owner_name: str = ""
    owner_phone: str = ""
    patient_name: str = ""
    species: str = ""
    breed: str = ""
    birth_date: str = ""
    gender: str = ""
    neutered: str = ""
    material: str = ""
    pre_diagnosis: str = ""
    sample_location: str = ""
    urgency: str = ""
    status: str = STATUS_OPTIONS[0]
    assigned_pathologist: str = ""
    gross_findings: str = ""
    micro_findings: str = ""
    diagnosis: str = ""
    report_summary: str = ""
    notes: str = ""
    fee: float = 0.0
    id: Optional[int] = None

    def as_db_dict(self) -> Dict[str, object]:
        data = self.__dict__.copy()
        if data.get("status") not in STATUS_OPTIONS:
            data["status"] = STATUS_OPTIONS[0]
        return data


@dataclass
class UserRecord:
    username: str
    full_name: str = ""
    role: str = "user"
    is_active: int = 1
    id: Optional[int] = None


@dataclass
class TestTypeRecord:
    code: str
    name: str
    unit_price: float
    category: str = "Genel"
    is_active: int = 1
    id: Optional[int] = None


@dataclass
class CaseTestRecord:
    case_id: int
    test_type_id: int
    quantity: int = 1
    unit_price: float = 0.0
    total_price: float = 0.0
    test_code: str = ""
    test_name: str = ""
    id: Optional[int] = None


def _row_to_case(row: sqlite3.Row) -> CaseRecord:
    data = dict(row)
    data.pop("created_at", None)
    data.pop("updated_at", None)
    return CaseRecord(**data)


def _row_to_user(row: sqlite3.Row) -> UserRecord:
    data = dict(row)
    data.pop("password_hash", None)
    data.pop("created_at", None)
    data.pop("updated_at", None)
    return UserRecord(**data)


def _row_to_test_type(row: sqlite3.Row) -> TestTypeRecord:
    return TestTypeRecord(**dict(row))


def _row_to_case_test(row: sqlite3.Row) -> CaseTestRecord:
    return CaseTestRecord(**dict(row))


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120000)
    return f"{salt.hex()}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt_hex, digest_hex = stored_hash.split("$", 1)
    except ValueError:
        return False
    recalculated = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt_hex),
        120000,
    ).hex()
    return hmac.compare_digest(recalculated, digest_hex)


class Database:
    def __init__(self, db_path: Path | str = DEFAULT_DB_PATH, enable_backups: bool | None = None, backup_dir: Path | str = DEFAULT_BACKUP_DIR):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.backup_dir = Path(backup_dir)
        self.enable_backups = (self.db_path == DEFAULT_DB_PATH) if enable_backups is None else enable_backups
        self._initialize()

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = NORMAL")
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    protocol_no TEXT NOT NULL UNIQUE,
                    acceptance_date TEXT NOT NULL DEFAULT '',
                    sender_clinic TEXT NOT NULL DEFAULT '',
                    owner_name TEXT NOT NULL DEFAULT '',
                    owner_phone TEXT NOT NULL DEFAULT '',
                    patient_name TEXT NOT NULL DEFAULT '',
                    species TEXT NOT NULL DEFAULT '',
                    breed TEXT NOT NULL DEFAULT '',
                    birth_date TEXT NOT NULL DEFAULT '',
                    gender TEXT NOT NULL DEFAULT '',
                    neutered TEXT NOT NULL DEFAULT '',
                    material TEXT NOT NULL DEFAULT '',
                    pre_diagnosis TEXT NOT NULL DEFAULT '',
                    sample_location TEXT NOT NULL DEFAULT '',
                    urgency TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'Kabul Edildi',
                    assigned_pathologist TEXT NOT NULL DEFAULT '',
                    gross_findings TEXT NOT NULL DEFAULT '',
                    micro_findings TEXT NOT NULL DEFAULT '',
                    diagnosis TEXT NOT NULL DEFAULT '',
                    report_summary TEXT NOT NULL DEFAULT '',
                    notes TEXT NOT NULL DEFAULT '',
                    fee REAL NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    full_name TEXT NOT NULL DEFAULT '',
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'user',
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS test_types (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    category TEXT NOT NULL DEFAULT 'Genel',
                    unit_price REAL NOT NULL DEFAULT 0,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS case_tests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    case_id INTEGER NOT NULL,
                    test_type_id INTEGER NOT NULL,
                    quantity INTEGER NOT NULL DEFAULT 1,
                    unit_price REAL NOT NULL DEFAULT 0,
                    total_price REAL NOT NULL DEFAULT 0,
                    FOREIGN KEY(case_id) REFERENCES cases(id) ON DELETE CASCADE,
                    FOREIGN KEY(test_type_id) REFERENCES test_types(id) ON DELETE CASCADE
                )
                """
            )
            columns = {row["name"] for row in conn.execute("PRAGMA table_info(test_types)").fetchall()}
            if "category" not in columns:
                conn.execute("ALTER TABLE test_types ADD COLUMN category TEXT NOT NULL DEFAULT 'Genel'")
        self._ensure_default_admin()
        self._ensure_default_tests()

    def _create_backup_snapshot(self) -> None:
        if self.enable_backups:
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            latest = self.backup_dir / "karpuzvet-latest.db"
            timestamped = self.backup_dir / f"karpuzvet-{datetime.now().strftime('%Y%m%d-%H%M%S')}.db"
            if self.db_path.exists():
                shutil.copy2(self.db_path, latest)
                shutil.copy2(self.db_path, timestamped)
            backups = sorted(self.backup_dir.glob("karpuzvet-*.db"))
            for old_file in backups[:-20]:
                old_file.unlink(missing_ok=True)

    def _ensure_default_admin(self) -> None:
        with self.connect() as conn:
            existing = conn.execute("SELECT id FROM users WHERE username = 'admin'").fetchone()
            if existing:
                return
            now = datetime.now().isoformat(timespec="seconds")
            conn.execute(
                """
                INSERT INTO users (username, full_name, password_hash, role, is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                ("admin", "Sistem Yonetici", hash_password("admin123"), "admin", 1, now, now),
            )

    def _ensure_default_tests(self) -> None:
        now = datetime.now().isoformat(timespec="seconds")
        with self.connect() as conn:
            for item in DEFAULT_TEST_TYPES:
                existing = conn.execute("SELECT id FROM test_types WHERE code = ?", (item["code"],)).fetchone()
                if existing:
                    continue
                conn.execute(
                    """
                    INSERT INTO test_types (code, name, category, unit_price, is_active, created_at, updated_at)
                    VALUES (?, ?, ?, ?, 1, ?, ?)
                    """,
                    (item["code"], item["name"], item["category"], item["unit_price"], now, now),
                )

    def save_case(self, record: CaseRecord) -> CaseRecord:
        payload = record.as_db_dict()
        now = datetime.now().isoformat(timespec="seconds")
        with self.connect() as conn:
            if record.id:
                conn.execute(
                    """
                    UPDATE cases
                    SET protocol_no=:protocol_no,
                        acceptance_date=:acceptance_date,
                        sender_clinic=:sender_clinic,
                        owner_name=:owner_name,
                        owner_phone=:owner_phone,
                        patient_name=:patient_name,
                        species=:species,
                        breed=:breed,
                        birth_date=:birth_date,
                        gender=:gender,
                        neutered=:neutered,
                        material=:material,
                        pre_diagnosis=:pre_diagnosis,
                        sample_location=:sample_location,
                        urgency=:urgency,
                        status=:status,
                        assigned_pathologist=:assigned_pathologist,
                        gross_findings=:gross_findings,
                        micro_findings=:micro_findings,
                        diagnosis=:diagnosis,
                        report_summary=:report_summary,
                        notes=:notes,
                        fee=:fee,
                        updated_at=:updated_at
                    WHERE id=:id
                    """,
                    {**payload, "updated_at": now},
                )
                row = conn.execute("SELECT * FROM cases WHERE id = ?", (record.id,)).fetchone()
                saved = _row_to_case(row)
            else:
                existing = conn.execute("SELECT id FROM cases WHERE protocol_no = ?", (record.protocol_no,)).fetchone()
                if existing:
                    payload["id"] = existing["id"]
                    payload["updated_at"] = now
                    conn.execute(
                        """
                        UPDATE cases
                        SET acceptance_date=:acceptance_date,
                            sender_clinic=:sender_clinic,
                            owner_name=:owner_name,
                            owner_phone=:owner_phone,
                            patient_name=:patient_name,
                            species=:species,
                            breed=:breed,
                            birth_date=:birth_date,
                            gender=:gender,
                            neutered=:neutered,
                            material=:material,
                            pre_diagnosis=:pre_diagnosis,
                            sample_location=:sample_location,
                            urgency=:urgency,
                            status=:status,
                            assigned_pathologist=:assigned_pathologist,
                            gross_findings=:gross_findings,
                            micro_findings=:micro_findings,
                            diagnosis=:diagnosis,
                            report_summary=:report_summary,
                            notes=:notes,
                            fee=:fee,
                            updated_at=:updated_at
                        WHERE id=:id
                        """,
                        payload,
                    )
                    row = conn.execute("SELECT * FROM cases WHERE id = ?", (existing["id"],)).fetchone()
                    saved = _row_to_case(row)
                else:
                    cursor = conn.execute(
                        """
                        INSERT INTO cases (
                            protocol_no, acceptance_date, sender_clinic, owner_name,
                            owner_phone, patient_name, species, breed, birth_date,
                            gender, neutered, material, pre_diagnosis, sample_location,
                            urgency, status, assigned_pathologist, gross_findings,
                            micro_findings, diagnosis, report_summary, notes, fee,
                            created_at, updated_at
                        ) VALUES (
                            :protocol_no, :acceptance_date, :sender_clinic, :owner_name,
                            :owner_phone, :patient_name, :species, :breed, :birth_date,
                            :gender, :neutered, :material, :pre_diagnosis, :sample_location,
                            :urgency, :status, :assigned_pathologist, :gross_findings,
                            :micro_findings, :diagnosis, :report_summary, :notes, :fee,
                            :created_at, :updated_at
                        )
                        """,
                        {**payload, "created_at": now, "updated_at": now},
                    )
                    row = conn.execute("SELECT * FROM cases WHERE id = ?", (cursor.lastrowid,)).fetchone()
                    saved = _row_to_case(row)
        self._create_backup_snapshot()
        return saved

    def get_case(self, case_id: int) -> CaseRecord:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()
        if not row:
            raise KeyError(f"Case {case_id} bulunamadi")
        return _row_to_case(row)

    def get_case_total(self, case_id: int) -> float:
        with self.connect() as conn:
            value = conn.execute("SELECT COALESCE(SUM(total_price), 0) FROM case_tests WHERE case_id = ?", (case_id,)).fetchone()[0]
        return float(value or 0.0)

    def list_cases(self, query: str = "", status: str = "") -> List[CaseRecord]:
        sql = "SELECT * FROM cases WHERE 1=1"
        params: List[object] = []
        if query.strip():
            sql += """
                AND (
                    protocol_no LIKE ?
                    OR patient_name LIKE ?
                    OR owner_name LIKE ?
                    OR sender_clinic LIKE ?
                    OR diagnosis LIKE ?
                )
            """
            wildcard = f"%{query.strip()}%"
            params.extend([wildcard] * 5)
        if status.strip():
            sql += " AND status = ?"
            params.append(status.strip())
        sql += " ORDER BY acceptance_date DESC, updated_at DESC, protocol_no DESC"
        with self.connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [_row_to_case(row) for row in rows]

    def case_counts(self) -> Dict[str, int]:
        with self.connect() as conn:
            total = conn.execute("SELECT COUNT(*) FROM cases").fetchone()[0]
            total_revenue = conn.execute("SELECT COALESCE(SUM(fee), 0) FROM cases").fetchone()[0]
            counts = {
                row["status"]: row["count"]
                for row in conn.execute("SELECT status, COUNT(*) AS count FROM cases GROUP BY status").fetchall()
            }
        return {
            "total": total,
            "kabul": counts.get("Kabul Edildi", 0),
            "makro": counts.get("Makroskopi Bekliyor", 0),
            "rapor": counts.get("Rapor Hazirlaniyor", 0),
            "tamamlandi": counts.get("Tamamlandi", 0),
            "total_revenue": float(total_revenue or 0.0),
            "average_revenue": float(total_revenue or 0.0) / total if total else 0.0,
        }

    def import_cases(self, cases: Iterable[CaseRecord]) -> int:
        imported = 0
        for case in cases:
            self.save_case(case)
            imported += 1
        return imported

    def list_test_types(self, active_only: bool = False) -> List[TestTypeRecord]:
        sql = "SELECT id, code, name, category, unit_price, is_active FROM test_types"
        params: List[object] = []
        if active_only:
            sql += " WHERE is_active = 1"
        sql += " ORDER BY code ASC"
        with self.connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [_row_to_test_type(row) for row in rows]

    def save_test_type(self, code: str, name: str, unit_price: float, is_active: int = 1, test_type_id: Optional[int] = None, category: str = "Genel") -> TestTypeRecord:
        now = datetime.now().isoformat(timespec="seconds")
        with self.connect() as conn:
            if test_type_id:
                conn.execute(
                    "UPDATE test_types SET code=?, name=?, category=?, unit_price=?, is_active=?, updated_at=? WHERE id=?",
                    (code.strip(), name.strip(), category.strip() or "Genel", float(unit_price), int(bool(is_active)), now, test_type_id),
                )
                row = conn.execute("SELECT id, code, name, category, unit_price, is_active FROM test_types WHERE id=?", (test_type_id,)).fetchone()
            else:
                cursor = conn.execute(
                    "INSERT INTO test_types (code, name, category, unit_price, is_active, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (code.strip(), name.strip(), category.strip() or "Genel", float(unit_price), int(bool(is_active)), now, now),
                )
                row = conn.execute("SELECT id, code, name, category, unit_price, is_active FROM test_types WHERE id=?", (cursor.lastrowid,)).fetchone()
        self._create_backup_snapshot()
        return _row_to_test_type(row)

    def list_case_tests(self, case_id: int) -> List[CaseTestRecord]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT ct.id, ct.case_id, ct.test_type_id, ct.quantity, ct.unit_price, ct.total_price,
                       tt.code AS test_code, tt.name AS test_name
                FROM case_tests ct
                JOIN test_types tt ON tt.id = ct.test_type_id
                WHERE ct.case_id = ?
                ORDER BY ct.id ASC
                """,
                (case_id,),
            ).fetchall()
        return [_row_to_case_test(row) for row in rows]

    def replace_case_tests(self, case_id: int, tests: List[dict]) -> List[CaseTestRecord]:
        with self.connect() as conn:
            conn.execute("DELETE FROM case_tests WHERE case_id = ?", (case_id,))
            for item in tests:
                test_type_id = int(item["test_type_id"])
                quantity = max(1, int(item.get("quantity", 1)))
                catalog = conn.execute(
                    "SELECT id, code, name, category, unit_price, is_active FROM test_types WHERE id = ?",
                    (test_type_id,),
                ).fetchone()
                if not catalog:
                    continue
                unit_price = float(item.get("unit_price") or catalog["unit_price"])
                total_price = quantity * unit_price
                conn.execute(
                    "INSERT INTO case_tests (case_id, test_type_id, quantity, unit_price, total_price) VALUES (?, ?, ?, ?, ?)",
                    (case_id, test_type_id, quantity, unit_price, total_price),
                )
            fee = conn.execute("SELECT COALESCE(SUM(total_price), 0) FROM case_tests WHERE case_id = ?", (case_id,)).fetchone()[0]
            conn.execute("UPDATE cases SET fee = ?, updated_at = ? WHERE id = ?", (float(fee or 0.0), datetime.now().isoformat(timespec='seconds'), case_id))
        self._create_backup_snapshot()
        return self.list_case_tests(case_id)

    def authenticate_user(self, username: str, password: str) -> Optional[UserRecord]:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE username = ? AND is_active = 1",
                (username.strip(),),
            ).fetchone()
        if not row:
            return None
        if not verify_password(password, row["password_hash"]):
            return None
        self._create_backup_snapshot()
        return _row_to_user(row)

    def list_users(self) -> List[UserRecord]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT id, username, full_name, role, is_active FROM users ORDER BY role DESC, username ASC"
            ).fetchall()
        return [_row_to_user(row) for row in rows]

    def get_user(self, user_id: int) -> UserRecord:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT id, username, full_name, role, is_active FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
        if not row:
            raise KeyError(f"User {user_id} bulunamadi")
        self._create_backup_snapshot()
        return _row_to_user(row)

    def create_user(self, username: str, password: str, full_name: str, role: str = "user", is_active: int = 1) -> UserRecord:
        username = username.strip()
        if not username:
            raise ValueError("Kullanici adi zorunlu.")
        if len(password.strip()) < 4:
            raise ValueError("Sifre en az 4 karakter olmali.")
        role = role if role in USER_ROLES else "user"
        now = datetime.now().isoformat(timespec="seconds")
        with self.connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO users (username, full_name, password_hash, role, is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (username, full_name.strip(), hash_password(password.strip()), role, int(bool(is_active)), now, now),
            )
            row = conn.execute(
                "SELECT id, username, full_name, role, is_active FROM users WHERE id = ?",
                (cursor.lastrowid,),
            ).fetchone()
        return _row_to_user(row)

    def update_user(self, user_id: int, full_name: str, role: str, is_active: int, password: str = "") -> UserRecord:
        role = role if role in USER_ROLES else "user"
        now = datetime.now().isoformat(timespec="seconds")
        with self.connect() as conn:
            existing = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
            if not existing:
                raise KeyError(f"User {user_id} bulunamadi")
            if existing["username"] == "admin" and not int(bool(is_active)):
                raise ValueError("Varsayilan admin pasif yapilamaz.")
            if existing["username"] == "admin" and role != "admin":
                raise ValueError("Varsayilan admin rolu degistirilemez.")
            if password.strip():
                if len(password.strip()) < 4:
                    raise ValueError("Sifre en az 4 karakter olmali.")
                conn.execute(
                    """
                    UPDATE users
                    SET full_name = ?, role = ?, is_active = ?, password_hash = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (full_name.strip(), role, int(bool(is_active)), hash_password(password.strip()), now, user_id),
                )
            else:
                conn.execute(
                    """
                    UPDATE users
                    SET full_name = ?, role = ?, is_active = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (full_name.strip(), role, int(bool(is_active)), now, user_id),
                )
            row = conn.execute(
                "SELECT id, username, full_name, role, is_active FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
        return _row_to_user(row)
