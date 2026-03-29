from __future__ import annotations

import datetime as dt
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Dict, List

from karpuzvet.database import CaseRecord


MAIN_NS = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
REL_NS = {"pr": "http://schemas.openxmlformats.org/package/2006/relationships"}


def _shared_strings(archive: zipfile.ZipFile) -> List[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    return [
        "".join(node.text or "" for node in item.findall(".//a:t", MAIN_NS))
        for item in root.findall("a:si", MAIN_NS)
    ]


def _sheet_targets(archive: zipfile.ZipFile) -> Dict[str, str]:
    workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    rel_map = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rels.findall("pr:Relationship", REL_NS)}
    targets = {}
    for sheet in workbook.find("a:sheets", MAIN_NS):
        relation_id = sheet.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]
        targets[sheet.attrib["name"]] = f"xl/{rel_map[relation_id]}"
    return targets


def _cell_value(cell: ET.Element, shared: List[str]) -> str:
    inline = cell.find("a:is", MAIN_NS)
    if inline is not None:
        return "".join(node.text or "" for node in inline.findall(".//a:t", MAIN_NS))
    value = cell.find("a:v", MAIN_NS)
    if value is None or value.text is None:
        return ""
    if cell.attrib.get("t") == "s" and value.text.isdigit():
        return shared[int(value.text)]
    return value.text


def _excel_date_to_iso(raw: str) -> str:
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return raw.strip()
    base = dt.datetime(1899, 12, 30)
    return (base + dt.timedelta(days=value)).date().isoformat()


def load_cases_from_xlsx(path: str | Path) -> List[CaseRecord]:
    archive_path = Path(path)
    with zipfile.ZipFile(archive_path) as archive:
        shared = _shared_strings(archive)
        targets = _sheet_targets(archive)
        source_sheet = next((targets[name] for name in targets if "Sayfa2" in name or "KAYIT" in name.upper()), next(iter(targets.values())))
        root = ET.fromstring(archive.read(source_sheet))
        rows = root.findall(".//a:sheetData/a:row", MAIN_NS)
        records: List[CaseRecord] = []
        for index, row in enumerate(rows):
            values = {}
            for cell in row.findall("a:c", MAIN_NS):
                ref = cell.attrib.get("r", "")
                column = "".join(ch for ch in ref if ch.isalpha())
                values[column] = _cell_value(cell, shared)
            if index == 0 or not values.get("B", "").strip():
                continue
            material = values.get("M", "").strip()
            records.append(
                CaseRecord(
                    protocol_no=values.get("B", "").strip(),
                    acceptance_date=_excel_date_to_iso(values.get("C", "")),
                    sender_clinic=values.get("E", "").strip(),
                    owner_name=values.get("F", "").strip(),
                    patient_name=values.get("G", "").strip(),
                    species=values.get("H", "").strip(),
                    breed=values.get("I", "").strip(),
                    birth_date=_excel_date_to_iso(values.get("J", "")),
                    gender=values.get("K", "").strip(),
                    neutered=values.get("L", "").strip(),
                    material=material,
                    gross_findings=values.get("N", "").strip(),
                    notes=values.get("O", "").strip(),
                    status="Makroskopi Bekliyor" if material else "Kabul Edildi",
                )
            )
    return records
