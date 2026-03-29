from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from karpuzvet.database import CaseRecord, CaseTestRecord


FONT_NAME = "ArialUnicodeKarpuz"
FONT_PATHS = [
    Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
    Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
]


def _register_font() -> str:
    for path in FONT_PATHS:
        if path.exists():
            try:
                pdfmetrics.registerFont(TTFont(FONT_NAME, str(path)))
                return FONT_NAME
            except Exception:
                continue
    return "Helvetica"


def build_case_pdf(case: CaseRecord, output_path: str | Path) -> Path:
    font_name = _register_font()
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(target),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=f"Karpuz Vet Rapor - {case.protocol_no}",
    )

    styles = getSampleStyleSheet()
    normal = ParagraphStyle("KarpuzNormal", parent=styles["Normal"], fontName=font_name, fontSize=10.5, leading=15, alignment=TA_LEFT, spaceAfter=4)
    heading = ParagraphStyle("KarpuzHeading", parent=styles["Heading1"], fontName=font_name, fontSize=16, leading=20, textColor=colors.HexColor("#174836"), spaceAfter=2, alignment=TA_CENTER)
    subheading = ParagraphStyle("KarpuzSubheading", parent=styles["Heading2"], fontName=font_name, fontSize=11.5, leading=16, textColor=colors.HexColor("#1f6b52"), spaceAfter=4, alignment=TA_CENTER)
    section_heading = ParagraphStyle("KarpuzSectionHeading", parent=styles["Heading2"], fontName=font_name, fontSize=11, leading=15, textColor=colors.black, alignment=TA_CENTER, spaceAfter=5)

    elements = [
        Paragraph("T.C.", normal),
        Paragraph("KARPUZ VETERINER PATOLOJI LABORATUVARI", heading),
        Paragraph("PATOLOJI BOLUMU", subheading),
        Paragraph("HISTOPATOLOJI RAPORU", subheading),
        Spacer(1, 5 * mm),
    ]

    meta_rows = [
        ["Sayi", case.protocol_no or "-"],
        ["Protokol", case.protocol_no or "-"],
        ["Tarih", case.acceptance_date or "-"],
        ["Durum", case.status or "-"],
        ["Nobetci Ogretim Uyesi", case.assigned_pathologist or "-"],
        ["Ucret", f"{case.fee:.2f} TL" if case.fee else "-"],
    ]
    meta_table = Table(meta_rows, colWidths=[52 * mm, 110 * mm])
    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    elements.extend([meta_table, Spacer(1, 6 * mm)])

    intro_rows = [
        ("Gonderen Klinik", case.sender_clinic),
        ("Hasta Sahibinin Adi Soyadi", case.owner_name),
        ("Hasta Sahibinin Telefonu", case.owner_phone),
        ("Hayvanin Turu / Irki", f"{case.species or '-'} / {case.breed or '-'}"),
        ("Hayvanin Adi", case.patient_name),
        ("Dogum Tarihi", case.birth_date),
        ("Cinsiyet / Kisirlik", f"{case.gender or '-'} / {case.neutered or '-'}"),
        ("Gonderilen Materyal", case.material),
        ("Numune Bolgesi", case.sample_location),
        ("Anamnez", case.pre_diagnosis),
    ]
    for label, value in intro_rows:
        elements.append(Paragraph(f"<b>{label} :</b> {(value or '-').replace(chr(10), '<br/>')}", normal))

    elements.extend([
        Spacer(1, 4 * mm),
        Paragraph("MAKROSKOPIK BULGULAR", section_heading),
        Paragraph((case.gross_findings or "-").replace("\n", "<br/>"), normal),
        Spacer(1, 4 * mm),
        Paragraph("HISTOPATOLOJIK TANI", section_heading),
    ])
    tani_text = case.diagnosis or "-"
    if case.report_summary:
        tani_text = f"{tani_text}<br/><br/><b>Aciklayici Tani:</b> {case.report_summary}"
    elements.append(Paragraph(tani_text.replace("\n", "<br/>"), normal))

    if case.notes:
        elements.extend([
            Spacer(1, 4 * mm),
            Paragraph("NOTLAR", section_heading),
            Paragraph(case.notes.replace("\n", "<br/>"), normal),
        ])

    signature_table = Table(
        [[
            Paragraph("Nobetci Ogretim Elemani<br/><br/>____________________", normal),
            Paragraph("Nobetci Ogretim Uyesi<br/><br/>____________________", normal),
        ]],
        colWidths=[80 * mm, 80 * mm],
    )
    signature_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, -1), font_name),
    ]))
    elements.extend([Spacer(1, 12 * mm), signature_table])

    doc.build(elements)
    return target


def build_billing_pdf(case: CaseRecord, tests: list[CaseTestRecord], output_path: str | Path) -> Path:
    font_name = _register_font()
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(target), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm)
    styles = getSampleStyleSheet()
    normal = ParagraphStyle("BillNormal", parent=styles["Normal"], fontName=font_name, fontSize=10.5, leading=14, alignment=TA_LEFT, spaceAfter=4)
    heading = ParagraphStyle("BillHeading", parent=styles["Heading1"], fontName=font_name, fontSize=15, leading=18, alignment=TA_CENTER, textColor=colors.black)
    elements = [
        Paragraph("T.C.", normal),
        Paragraph("KARPUZ VETERINER PATOLOJI LABORATUVARI", heading),
        Paragraph("NUMUNE BORC DETAYI BILGISI", heading),
        Spacer(1, 6 * mm),
        Paragraph(f"<b>Protokol:</b> {case.protocol_no or '-'}", normal),
        Paragraph(f"<b>Borclu Adi:</b> {case.owner_name or '-'}", normal),
        Paragraph(f"<b>Tarih:</b> {case.acceptance_date or '-'}", normal),
        Paragraph(f"<b>Numune:</b> {case.material or '-'}", normal),
        Spacer(1, 4 * mm),
    ]
    rows = [["Tarih", "Tetkik Kodu", "Tetkik", "Adet", "Fiyat", "Toplam"]]
    for item in tests:
        rows.append([
            case.acceptance_date or "-",
            item.test_code,
            item.test_name,
            str(item.quantity),
            f"{item.unit_price:.2f}",
            f"{item.total_price:.2f}",
        ])
    total = sum(item.total_price for item in tests)
    table = Table(rows, colWidths=[24 * mm, 30 * mm, 62 * mm, 16 * mm, 22 * mm, 24 * mm])
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#efefef")),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]))
    elements.extend([table, Spacer(1, 5 * mm), Paragraph(f"<b>Toplam Tutar:</b> {total:.2f} TL", normal)])
    doc.build(elements)
    return target


def build_request_form_pdf(case: CaseRecord, tests: list[CaseTestRecord], output_path: str | Path) -> Path:
    font_name = _register_font()
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(target), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm)
    styles = getSampleStyleSheet()
    normal = ParagraphStyle("ReqNormal", parent=styles["Normal"], fontName=font_name, fontSize=10.5, leading=14, alignment=TA_LEFT, spaceAfter=4)
    heading = ParagraphStyle("ReqHeading", parent=styles["Heading1"], fontName=font_name, fontSize=14, leading=18, alignment=TA_CENTER, textColor=colors.black)
    elements = [
        Paragraph("I.U. BUTUNLESIK KALITE YONETIM SISTEMI", heading),
        Paragraph("ANALIZ TALEP DILEKCE FORMU", heading),
        Spacer(1, 6 * mm),
        Paragraph(f"<b>Protokol No:</b> {case.protocol_no or '-'}", normal),
        Paragraph(f"<b>Tarih:</b> {case.acceptance_date or '-'}", normal),
        Paragraph(f"<b>Hasta Sahibi:</b> {case.owner_name or '-'}", normal),
        Paragraph(f"<b>Telefon:</b> {case.owner_phone or '-'}", normal),
        Paragraph(f"<b>Adres / Klinik:</b> {case.sender_clinic or '-'}", normal),
        Paragraph(f"<b>Aciklama:</b> {case.notes or case.pre_diagnosis or '-'}", normal),
        Paragraph(f"<b>Numunenin Gonderilis Sekli:</b> Elden Teslim", normal),
        Spacer(1, 4 * mm),
    ]
    rows = [["Tarih", "Tetkik Kodu", "Tetkik Adi", "Adet"]]
    for item in tests:
        rows.append([case.acceptance_date or "-", item.test_code, item.test_name, str(item.quantity)])
    table = Table(rows, colWidths=[28 * mm, 34 * mm, 90 * mm, 18 * mm])
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#efefef")),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]))
    elements.append(table)
    doc.build(elements)
    return target


def build_proforma_pdf(case: CaseRecord, tests: list[CaseTestRecord], output_path: str | Path) -> Path:
    font_name = _register_font()
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(target), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm)
    styles = getSampleStyleSheet()
    normal = ParagraphStyle("ProformaNormal", parent=styles["Normal"], fontName=font_name, fontSize=10.5, leading=14, alignment=TA_LEFT, spaceAfter=4)
    heading = ParagraphStyle("ProformaHeading", parent=styles["Heading1"], fontName=font_name, fontSize=15, leading=18, alignment=TA_CENTER, textColor=colors.black)
    elements = [
        Paragraph("KARPUZ VETERINER PATOLOJI LABORATUVARI", heading),
        Paragraph("PROFORMA / UCRET BILGILENDIRME", heading),
        Spacer(1, 6 * mm),
        Paragraph(f"<b>Protokol No:</b> {case.protocol_no or '-'}", normal),
        Paragraph(f"<b>Hasta Sahibi:</b> {case.owner_name or '-'}", normal),
        Paragraph(f"<b>Hasta Adi:</b> {case.patient_name or '-'}", normal),
        Paragraph(f"<b>Klinik:</b> {case.sender_clinic or '-'}", normal),
        Paragraph(f"<b>Tarih:</b> {case.acceptance_date or '-'}", normal),
        Spacer(1, 4 * mm),
    ]
    rows = [["Kategori", "Tetkik", "Adet", "Birim Fiyat", "Toplam"]]
    for item in tests:
        rows.append([
            "-",
            item.test_name,
            str(item.quantity),
            f"{item.unit_price:.2f} TL",
            f"{item.total_price:.2f} TL",
        ])
    total = sum(item.total_price for item in tests)
    rows.append(["", "", "", "Genel Toplam", f"{total:.2f} TL"])
    table = Table(rows, colWidths=[28 * mm, 76 * mm, 18 * mm, 30 * mm, 30 * mm])
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#efefef")),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#f7f7f7")),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]))
    elements.extend([
        table,
        Spacer(1, 6 * mm),
        Paragraph("Bu belge resmi e-Fatura yerine gecmez; on bilgilendirme ve ucret ozetidir.", normal),
    ])
    doc.build(elements)
    return target
