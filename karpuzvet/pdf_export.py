from __future__ import annotations

from io import BytesIO
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import registerFontFamily
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as pdf_canvas
from reportlab.platypus import Frame, HRFlowable, Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

try:
    from pypdf import PdfReader, PdfWriter
except Exception:  # pragma: no cover - fallback remains available if dependency is missing
    PdfReader = None
    PdfWriter = None

from karpuzvet.database import CaseRecord, CaseTestRecord, DEFAULT_REPORT_ASSISTANT, DEFAULT_REPORT_SIGNER


FONT_NAME = "KarpuzTimes"
FONT_BOLD_NAME = "KarpuzTimesBold"
OVERLAY_FONT_NAME = "KarpuzArial"
OVERLAY_BOLD_FONT_NAME = "KarpuzArialBold"
FONT_PATHS = [
    (FONT_NAME, Path("/System/Library/Fonts/Supplemental/Times New Roman.ttf")),
    (FONT_BOLD_NAME, Path("/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf")),
    (FONT_NAME, Path("/System/Library/Fonts/Supplemental/Georgia.ttf")),
    (FONT_BOLD_NAME, Path("/System/Library/Fonts/Supplemental/Georgia Bold.ttf")),
    (FONT_NAME, Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf")),
    (FONT_BOLD_NAME, Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf")),
]
OVERLAY_FONT_PATHS = [
    (OVERLAY_FONT_NAME, Path("/System/Library/Fonts/Supplemental/Arial.ttf")),
    (OVERLAY_BOLD_FONT_NAME, Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf")),
    (OVERLAY_FONT_NAME, Path("/Library/Fonts/Arial Unicode.ttf")),
    (OVERLAY_BOLD_FONT_NAME, Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf")),
]

COMPANY_NAME = "KARPUZ PATOLOJI LABORATUVARI VETERINER HIZMETLERI TICARET LIMITED SIRKETI"
COMPANY_ADDRESS = "FATIH SULTAN MEHMET MAH. MERT SK. NO: 4 IC KAPI NO: 1 SARIYER / ISTANBUL"
LOGO_PATH = Path(__file__).resolve().parent.parent / "web" / "assets" / "logo.jpeg"
REPORT_TEMPLATE_PATH = Path(__file__).resolve().parent / "templates" / "pathology_report_template.pdf"
COMPANY_PHONE = "Tel: 0 (212) 000 00 00"
COMPANY_EMAIL = "E-posta: info@karpuzpatoloji.com"
BRAND_GREEN = colors.HexColor("#1f5a45")
LIGHT_BORDER = colors.HexColor("#d3d9e2")
LIGHT_FILL = colors.HexColor("#f6f8fb")


def _register_font() -> tuple[str, str]:
    found_regular = None
    found_bold = None
    for font_alias, path in FONT_PATHS:
        if path.exists() and ((font_alias == FONT_NAME and found_regular is None) or (font_alias == FONT_BOLD_NAME and found_bold is None)):
            try:
                pdfmetrics.registerFont(TTFont(font_alias, str(path)))
                if font_alias == FONT_NAME:
                    found_regular = FONT_NAME
                elif font_alias == FONT_BOLD_NAME:
                    found_bold = FONT_BOLD_NAME
            except Exception:
                continue
    if found_regular and found_bold:
        registerFontFamily("KarpuzSerifFamily", normal=found_regular, bold=found_bold)
        return found_regular, found_bold
    return "Helvetica", "Helvetica-Bold"


def _register_overlay_font() -> tuple[str, str]:
    found_regular = None
    found_bold = None
    for alias, path in OVERLAY_FONT_PATHS:
        if not path.exists():
            continue
        try:
            if alias not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont(alias, str(path)))
            if alias == OVERLAY_FONT_NAME:
                found_regular = OVERLAY_FONT_NAME
            elif alias == OVERLAY_BOLD_FONT_NAME:
                found_bold = OVERLAY_BOLD_FONT_NAME
        except Exception:
            continue
    if found_regular and found_bold:
        return found_regular, found_bold
    return "Helvetica", "Helvetica-Bold"


def _company_header(elements, normal, heading, subheading):
    title_block = [
        Paragraph(COMPANY_NAME, heading),
        Paragraph(COMPANY_ADDRESS, subheading),
    ]
    if LOGO_PATH.exists():
        logo = Image(str(LOGO_PATH), width=42 * mm, height=24 * mm)
        header_table = Table(
            [[logo, title_block]],
            colWidths=[48 * mm, 120 * mm],
        )
        header_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (0, 0), "LEFT"),
            ("ALIGN", (1, 0), (1, 0), "CENTER"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        elements.extend([header_table, Spacer(1, 4 * mm)])
        return
    elements.extend(title_block + [Spacer(1, 4 * mm)])


def _safe_text(value: str | None) -> str:
    return (value or "-").strip() or "-"


def _format_display_date(value: str | None) -> str:
    raw = _safe_text(value)
    if raw == "-":
        return raw
    for date_format in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(raw, date_format).strftime("%d.%m.%Y")
        except ValueError:
            continue
    return raw


def _calculate_age_display(case: CaseRecord) -> str:
    birth = _safe_text(case.birth_date)
    if birth == "-":
        return "-"
    accepted = _safe_text(case.acceptance_date)
    for birth_format in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
        try:
            birth_dt = datetime.strptime(birth, birth_format)
            break
        except ValueError:
            birth_dt = None
    else:
        birth_dt = None
    if birth_dt is None:
        return birth
    ref_dt = None
    for ref_format in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
        try:
            ref_dt = datetime.strptime(accepted, ref_format)
            break
        except ValueError:
            continue
    if ref_dt is None:
        return birth_dt.strftime("%d.%m.%Y")
    years = ref_dt.year - birth_dt.year - ((ref_dt.month, ref_dt.day) < (birth_dt.month, birth_dt.day))
    if years <= 0:
        return "1 Yaş Altı"
    return f"{years} Yaş"


def _line_value(label: str, value: str, label_style: ParagraphStyle, value_style: ParagraphStyle) -> list:
    return [
        Paragraph(f"{label}", label_style),
        Paragraph(value.replace("\n", "<br/>"), value_style),
    ]


def _draw_report_footer(canvas, doc):
    canvas.saveState()
    page_width, _ = A4
    footer_y = 12 * mm
    canvas.setStrokeColor(LIGHT_BORDER)
    canvas.setLineWidth(0.6)
    canvas.line(doc.leftMargin, footer_y + 4 * mm, page_width - doc.rightMargin, footer_y + 4 * mm)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#556070"))
    canvas.drawString(doc.leftMargin, footer_y, "Karpuz Patoloji Laboratuvarı Veteriner Hizmetleri")
    canvas.drawRightString(page_width - doc.rightMargin, footer_y, f"Sayfa {canvas.getPageNumber()}")
    canvas.restoreState()


def _build_shared_styles(font_name: str, bold_font_name: str) -> dict[str, ParagraphStyle]:
    styles = getSampleStyleSheet()
    normal = ParagraphStyle("SharedNormal", parent=styles["Normal"], fontName=font_name, fontSize=10.2, leading=14, alignment=TA_LEFT, spaceAfter=2, textColor=colors.black)
    label = ParagraphStyle("SharedLabel", parent=normal, fontName=bold_font_name, fontSize=9.6, leading=13)
    value = ParagraphStyle("SharedValue", parent=normal, fontSize=9.6, leading=13)
    company_name = ParagraphStyle("SharedCompanyName", parent=styles["Heading1"], fontName=bold_font_name, fontSize=12.5, leading=15, alignment=TA_CENTER, textColor=BRAND_GREEN, spaceAfter=2)
    company_meta = ParagraphStyle("SharedCompanyMeta", parent=normal, fontSize=8.3, leading=11, alignment=TA_CENTER, textColor=colors.HexColor("#364150"))
    title = ParagraphStyle("SharedTitle", parent=styles["Heading1"], fontName=bold_font_name, fontSize=16, leading=19, alignment=TA_CENTER, textColor=colors.black, spaceAfter=0)
    right_info = ParagraphStyle("SharedRightInfo", parent=normal, fontName=bold_font_name, fontSize=8.6, leading=11, alignment=TA_CENTER, textColor=colors.HexColor("#7b2020"))
    section_heading = ParagraphStyle("SharedSectionHeading", parent=styles["Heading2"], fontName=bold_font_name, fontSize=10.2, leading=13, textColor=colors.black, alignment=TA_LEFT, spaceAfter=2, spaceBefore=1)
    compact = ParagraphStyle("SharedCompact", parent=normal, fontSize=9, leading=11, spaceAfter=0)
    note = ParagraphStyle("SharedNote", parent=normal, fontSize=8.6, leading=11, textColor=colors.HexColor("#566173"))
    return {
        "normal": normal,
        "label": label,
        "value": value,
        "company_name": company_name,
        "company_meta": company_meta,
        "title": title,
        "right_info": right_info,
        "section_heading": section_heading,
        "compact": compact,
        "note": note,
    }


def _append_formal_header(elements: list, title_text: str, styles: dict[str, ParagraphStyle], protocol_no: str, date_text: str, stamp_text: str = "RAPOR\nONAYLI") -> None:
    center_lines = [
        Paragraph(COMPANY_NAME, styles["company_name"]),
        Paragraph("Veteriner Patoloji Laboratuvarı", styles["company_meta"]),
        Paragraph(COMPANY_ADDRESS, styles["company_meta"]),
        Paragraph(f"{COMPANY_PHONE}     {COMPANY_EMAIL}", styles["company_meta"]),
    ]
    left_logo = Image(str(LOGO_PATH), width=34 * mm, height=22 * mm) if LOGO_PATH.exists() else Paragraph("KARPUZ", styles["company_name"])
    right_box = Table(
        [[Paragraph(stamp_text.replace("\n", "<br/>"), styles["right_info"])]],
        colWidths=[26 * mm],
        rowHeights=[18 * mm],
    )
    right_box.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#b04a4a")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    top_table = Table([[left_logo, center_lines, right_box]], colWidths=[36 * mm, 107 * mm, 32 * mm])
    top_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (0, 0), "LEFT"),
        ("ALIGN", (1, 0), (1, 0), "CENTER"),
        ("ALIGN", (2, 0), (2, 0), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    header_info = Table(
        [[
            Paragraph(f"<b>PROTOKOL / BELGE NO:</b> {_safe_text(protocol_no)}", styles["compact"]),
            Paragraph(f"<b>TARİH:</b> {_format_display_date(date_text)}", styles["compact"]),
        ]],
        colWidths=[98 * mm, 77 * mm],
    )
    header_info.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("ALIGN", (0, 0), (0, 0), "LEFT"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
    ]))
    elements.extend([
        top_table,
        Spacer(1, 3 * mm),
        Paragraph(title_text, styles["title"]),
        Spacer(1, 2 * mm),
        header_info,
        Spacer(1, 2 * mm),
    ])


def _build_key_value_table(rows: list[list], col_widths: list[float]) -> Table:
    table = Table(rows, colWidths=col_widths)
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    return table


def _build_grid_table(rows: list[list], col_widths: list[float], font_name: str, highlight_last_row: bool = False) -> Table:
    table = Table(rows, colWidths=col_widths)
    styles = [
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("BACKGROUND", (0, 0), (-1, 0), LIGHT_FILL),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]
    if highlight_last_row:
        styles.append(("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#eef3ee")))
    table.setStyle(TableStyle(styles))
    return table


def build_case_pdf(case: CaseRecord, output_path: str | Path) -> Path:
    font_name, bold_font_name = _register_font()
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(target),
        pagesize=A4,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=12 * mm,
        bottomMargin=18 * mm,
        title=f"Karpuz Vet Rapor - {case.protocol_no}",
    )

    shared = _build_shared_styles(font_name, bold_font_name)
    normal = shared["normal"]
    label_style = shared["label"]
    value_style = shared["value"]
    section_heading = shared["section_heading"]
    compact_style = shared["compact"]

    elements = []
    _append_formal_header(elements, "Patoloji Raporu", shared, case.protocol_no, case.acceptance_date)

    meta_rows = [
        _line_value("GÖNDEREN HEKİM - KLİNİK", _safe_text(case.sender_clinic), label_style, value_style),
        _line_value("HASTA SAHİBİ", _safe_text(case.owner_name), label_style, value_style),
        _line_value("HASTANIN ADI", _safe_text(case.patient_name), label_style, value_style),
        _line_value("SAYFA SAYISI", "1", label_style, value_style),
        _line_value("KAYIT TARİHİ", _format_display_date(case.acceptance_date), label_style, value_style),
        _line_value("ANALİZ TARİHİ", _format_display_date(case.acceptance_date), label_style, value_style),
    ]
    meta_table = _build_key_value_table(meta_rows, [54 * mm, 121 * mm])
    elements.extend([meta_table, Spacer(1, 3 * mm), HRFlowable(width="100%", thickness=0.8, color=LIGHT_BORDER, spaceAfter=2.5 * mm, spaceBefore=0.5 * mm)])

    animal_info = Table(
        [[
            Paragraph(f"<b>Türü:</b> {_safe_text(case.species)}", compact_style),
            Paragraph(f"<b>Irkı:</b> {_safe_text(case.breed)}", compact_style),
            Paragraph(f"<b>Yaşı:</b> {_calculate_age_display(case)}", compact_style),
            Paragraph(f"<b>Cinsiyeti:</b> {_safe_text(case.gender)}", compact_style),
        ]],
        colWidths=[42 * mm, 54 * mm, 34 * mm, 45 * mm],
    )
    animal_info.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    elements.extend([animal_info, Spacer(1, 2.5 * mm), HRFlowable(width="100%", thickness=0.8, color=LIGHT_BORDER, spaceAfter=2.5 * mm, spaceBefore=0)])

    sections = [
        ("GÖNDERİLEN MATERYAL:", " / ".join(part for part in [_safe_text(case.material), _safe_text(case.sample_location)] if part != "-") or "-"),
        ("KLİNİK BİLGİ / ANAMNEZ:", _safe_text(case.pre_diagnosis)),
        ("MAKROSKOPİK BULGULAR:", _safe_text(case.gross_findings)),
        ("MİKROSKOPİK BULGULAR:", _safe_text(case.micro_findings)),
    ]
    diagnosis_text = _safe_text(case.diagnosis)
    if _safe_text(case.report_summary) != "-":
        diagnosis_text = f"{diagnosis_text}<br/><br/><b>Açıklayıcı Tanı:</b> {_safe_text(case.report_summary)}"
    sections.append(("HİSTOPATOLOJİK TANI:", diagnosis_text))
    if _safe_text(case.notes) != "-":
        sections.append(("NOTLAR:", _safe_text(case.notes)))

    for heading_text, body_text in sections:
        elements.append(Paragraph(heading_text, section_heading))
        elements.append(Paragraph(body_text.replace("\n", "<br/>"), normal))
        elements.append(Spacer(1, 1.5 * mm))

    assistant_name = DEFAULT_REPORT_ASSISTANT
    signer_name = DEFAULT_REPORT_SIGNER
    signature_table = Table(
        [[
            Paragraph(f"Raporu Hazırlayan<br/><br/><b>{assistant_name}</b><br/>____________________", compact_style),
            Paragraph(f"Onaylayan Sorumlu Uzman<br/><br/>{f'<b>{signer_name}</b><br/>' if signer_name else ''}____________________", compact_style),
        ]],
        colWidths=[82 * mm, 82 * mm],
    )
    signature_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    elements.extend([Spacer(1, 12 * mm), signature_table])

    doc.build(elements, onFirstPage=_draw_report_footer, onLaterPages=_draw_report_footer)
    return target


_build_case_pdf_programmatic = build_case_pdf


def _draw_boxed_paragraph(canvas_obj, text: str, x: float, y: float, width: float, height: float, style: ParagraphStyle, align_top: bool = True):
    story = [Paragraph((text or "-").replace("\n", "<br/>"), style)]
    frame = Frame(x, y, width, height, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0, showBoundary=0)
    frame.addFromList(story, canvas_obj)
    return story


def _cover(canvas_obj, x: float, y: float, width: float, height: float):
    canvas_obj.saveState()
    canvas_obj.setFillColor(colors.white)
    canvas_obj.setStrokeColor(colors.white)
    canvas_obj.rect(x, y, width, height, stroke=0, fill=1)
    canvas_obj.restoreState()


def _draw_template_page_header(canvas_obj, font_name: str, bold_font_name: str, page_width: float):
    _cover(canvas_obj, 20, 645, 455, 92)
    if LOGO_PATH.exists():
        canvas_obj.drawImage(str(LOGO_PATH), 28, 652, width=120, height=68, preserveAspectRatio=True, mask="auto")
    canvas_obj.setFillColor(BRAND_GREEN)
    canvas_obj.setFont(bold_font_name, 14)
    canvas_obj.drawCentredString(300, 709, "KARPUZ PATOLOJI LABORATUVARI")
    canvas_obj.setFont(font_name, 11)
    canvas_obj.drawCentredString(300, 694, "Veteriner Hizmetleri Ticaret Limited Şirketi")
    canvas_obj.drawCentredString(300, 679, COMPANY_ADDRESS)
    canvas_obj.drawCentredString(300, 664, f"{COMPANY_PHONE}     {COMPANY_EMAIL}")


def _build_case_pdf_from_template(case: CaseRecord, output_path: str | Path) -> Path:
    if PdfReader is None or PdfWriter is None:
        return _build_case_pdf_programmatic(case, output_path)

    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)

    reader = PdfReader(str(REPORT_TEMPLATE_PATH))
    writer = PdfWriter(clone_from=str(REPORT_TEMPLATE_PATH))
    overlay_buffer = BytesIO()
    canvas_obj = pdf_canvas.Canvas(overlay_buffer, pagesize=A4)
    font_name, bold_font_name = _register_overlay_font()

    body_style = ParagraphStyle(
        "TemplateBody",
        fontName=font_name,
        fontSize=11.2,
        leading=13.8,
        textColor=colors.black,
    )
    label_style = ParagraphStyle("TemplateLabel", fontName=bold_font_name, fontSize=12, leading=12, textColor=colors.black)
    value_style = ParagraphStyle("TemplateValue", fontName=font_name, fontSize=12, leading=12.5, textColor=colors.black)
    diag_style = ParagraphStyle("TemplateDiagnosis", fontName=font_name, fontSize=11.7, leading=14, textColor=colors.black)
    signer_style = ParagraphStyle("TemplateSigner", fontName=bold_font_name, fontSize=12, leading=12, textColor=colors.black)

    page1_histology = _safe_text(case.micro_findings)
    if page1_histology == "-":
        page1_histology = _safe_text(case.gross_findings)
    if _safe_text(case.report_summary) != "-":
        page1_histology = f"{page1_histology}<br/><br/><b>Not:</b> {_safe_text(case.report_summary)}"
    page2_continuation = _safe_text(case.notes)
    if page2_continuation == "-":
        page2_continuation = _safe_text(case.report_summary)
    diagnosis_text = _safe_text(case.diagnosis)

    for page_index in range(len(reader.pages)):
        _draw_template_page_header(canvas_obj, font_name, bold_font_name, 595.2)
        if page_index == 0:
            for rect in [
                (226, 540, 300, 14),
                (196, 526, 160, 14),
                (196, 512, 220, 14),
                (196, 498, 120, 14),
                (196, 484, 120, 14),
                (196, 470, 180, 14),
                (103, 431, 420, 14),
                (103, 335, 420, 78),
                (103, 184, 430, 130),
            ]:
                _cover(canvas_obj, *rect)

            canvas_obj.setFillColor(colors.black)
            canvas_obj.setFont(font_name, 12)
            canvas_obj.drawString(233.6, 547.1, _safe_text(case.sender_clinic))
            canvas_obj.drawString(197.8, 533.2, _safe_text(case.protocol_no))
            canvas_obj.drawString(197.8, 519.5, _safe_text(case.owner_name))
            canvas_obj.drawString(197.8, 505.6, _safe_text(case.patient_name))
            canvas_obj.drawString(197.8, 491.9, "2")
            canvas_obj.drawString(197.8, 478.0, _format_display_date(case.acceptance_date))
            canvas_obj.drawString(197.8, 464.3, _format_display_date(case.acceptance_date))
            canvas_obj.drawString(485.9, 574.7, _format_display_date(case.acceptance_date))
            canvas_obj.drawString(108.3, 436.7, _safe_text(case.species).upper())
            canvas_obj.drawString(215.9, 436.7, _safe_text(case.breed).upper())
            canvas_obj.drawString(349.1, 436.7, _calculate_age_display(case))
            canvas_obj.drawString(476.6, 436.7, _safe_text(case.gender).upper())

            material_text = _safe_text(case.material)
            if _safe_text(case.sample_location) != "-":
                material_text = f"{material_text}<br/>Numune bölgesi: {_safe_text(case.sample_location)}"
            _draw_boxed_paragraph(canvas_obj, material_text, 106.1, 338, 420, 74, body_style)
            _draw_boxed_paragraph(canvas_obj, page1_histology, 106.1, 186, 430, 124, body_style)
        else:
            for rect in [
                (103, 446, 430, 147),
                (392, 416, 150, 18),
            ]:
                _cover(canvas_obj, *rect)
            _draw_boxed_paragraph(canvas_obj, page2_continuation, 106.1, 520, 430, 70, body_style)
            _draw_boxed_paragraph(canvas_obj, diagnosis_text, 106.1, 448, 430, 34, diag_style)
            signer_name = _safe_text(case.assigned_pathologist) if _safe_text(case.assigned_pathologist) != "-" else DEFAULT_REPORT_SIGNER
            canvas_obj.setFont(bold_font_name, 12)
            canvas_obj.drawString(399.5, 422.8, signer_name)

        canvas_obj.showPage()

    canvas_obj.save()
    overlay_buffer.seek(0)
    overlay_reader = PdfReader(overlay_buffer)

    for page_index, overlay_page in enumerate(overlay_reader.pages):
        writer.pages[page_index].merge_page(overlay_page)

    with target.open("wb") as handle:
        writer.write(handle)
    return target


def build_case_pdf(case: CaseRecord, output_path: str | Path) -> Path:
    return _build_case_pdf_programmatic(case, output_path)


def build_billing_pdf(case: CaseRecord, tests: list[CaseTestRecord], output_path: str | Path) -> Path:
    font_name, bold_font_name = _register_font()
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(target), pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm, topMargin=12 * mm, bottomMargin=18 * mm)
    shared = _build_shared_styles(font_name, bold_font_name)
    normal = shared["normal"]
    label_style = shared["label"]
    elements = []
    _append_formal_header(elements, "Numune Borç Detayı Bilgisi", shared, case.protocol_no, case.acceptance_date, "BORÇ\nDETAY")
    detail_rows = [
        _line_value("BORÇLU ADI", _safe_text(case.owner_name), label_style, normal),
        _line_value("NUMUNE", _safe_text(case.material), label_style, normal),
        _line_value("KLİNİK", _safe_text(case.sender_clinic), label_style, normal),
    ]
    elements.extend([
        _build_key_value_table(detail_rows, [42 * mm, 133 * mm]),
        Spacer(1, 2.5 * mm),
        HRFlowable(width="100%", thickness=0.8, color=LIGHT_BORDER, spaceAfter=3 * mm, spaceBefore=0),
    ])
    rows = [["Tarih", "Tetkik Kodu", "Tetkik", "Adet", "Fiyat", "Toplam"]]
    for item in tests:
        rows.append([
            _format_display_date(case.acceptance_date),
            item.test_code,
            item.test_name,
            str(item.quantity),
            f"{item.unit_price:.2f} TL",
            f"{item.total_price:.2f} TL",
        ])
    total = sum(item.total_price for item in tests)
    rows.append(["", "", "", "", "GENEL TOPLAM", f"{total:.2f} TL"])
    table = _build_grid_table(rows, [24 * mm, 30 * mm, 62 * mm, 16 * mm, 22 * mm, 24 * mm], font_name, highlight_last_row=True)
    elements.extend([
        table,
        Spacer(1, 5 * mm),
        Paragraph("Bu belge laboratuvar içi ücret dökümüdür.", shared["note"]),
    ])
    doc.build(elements, onFirstPage=_draw_report_footer, onLaterPages=_draw_report_footer)
    return target


def build_request_form_pdf(case: CaseRecord, tests: list[CaseTestRecord], output_path: str | Path) -> Path:
    font_name, bold_font_name = _register_font()
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(target), pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm, topMargin=12 * mm, bottomMargin=18 * mm)
    shared = _build_shared_styles(font_name, bold_font_name)
    normal = shared["normal"]
    label_style = shared["label"]
    elements = []
    _append_formal_header(elements, "Analiz Talep Dilekçe Formu", shared, case.protocol_no, case.acceptance_date, "TALEP\nFORMU")
    info_rows = [
        _line_value("HASTA SAHİBİ", _safe_text(case.owner_name), label_style, normal),
        _line_value("TELEFON", _safe_text(case.owner_phone), label_style, normal),
        _line_value("KLİNİK / ADRES", _safe_text(case.sender_clinic), label_style, normal),
        _line_value("AÇIKLAMA", _safe_text(case.notes or case.pre_diagnosis), label_style, normal),
        _line_value("NUMUNENİN GÖNDERİLİŞ ŞEKLİ", "Elden Teslim", label_style, normal),
    ]
    elements.extend([
        _build_key_value_table(info_rows, [52 * mm, 123 * mm]),
        Spacer(1, 2.5 * mm),
        HRFlowable(width="100%", thickness=0.8, color=LIGHT_BORDER, spaceAfter=3 * mm, spaceBefore=0),
    ])
    rows = [["Tarih", "Tetkik Kodu", "Tetkik Adi", "Adet"]]
    for item in tests:
        rows.append([_format_display_date(case.acceptance_date), item.test_code, item.test_name, str(item.quantity)])
    elements.extend([
        _build_grid_table(rows, [28 * mm, 34 * mm, 90 * mm, 18 * mm], font_name),
        Spacer(1, 5 * mm),
        Paragraph("* Laboratuvar yetkilisi ile teslimat doğrulanacaktır.", shared["note"]),
    ])
    doc.build(elements, onFirstPage=_draw_report_footer, onLaterPages=_draw_report_footer)
    return target


def build_proforma_pdf(case: CaseRecord, tests: list[CaseTestRecord], output_path: str | Path) -> Path:
    font_name, bold_font_name = _register_font()
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(target), pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm, topMargin=12 * mm, bottomMargin=18 * mm)
    shared = _build_shared_styles(font_name, bold_font_name)
    normal = shared["normal"]
    label_style = shared["label"]
    elements = []
    _append_formal_header(elements, "Proforma / Ücret Bilgilendirme", shared, case.protocol_no, case.acceptance_date, "PROFORMA")
    info_rows = [
        _line_value("HASTA SAHİBİ", _safe_text(case.owner_name), label_style, normal),
        _line_value("HASTA ADI", _safe_text(case.patient_name), label_style, normal),
        _line_value("KLİNİK", _safe_text(case.sender_clinic), label_style, normal),
    ]
    elements.extend([
        _build_key_value_table(info_rows, [42 * mm, 133 * mm]),
        Spacer(1, 2.5 * mm),
        HRFlowable(width="100%", thickness=0.8, color=LIGHT_BORDER, spaceAfter=3 * mm, spaceBefore=0),
    ])
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
    table = _build_grid_table(rows, [28 * mm, 76 * mm, 18 * mm, 30 * mm, 30 * mm], font_name, highlight_last_row=True)
    elements.extend([
        table,
        Spacer(1, 6 * mm),
        Paragraph("Bu belge resmi e-Fatura yerine geçmez; ön bilgilendirme ve ücret özetidir.", shared["note"]),
    ])
    doc.build(elements, onFirstPage=_draw_report_footer, onLaterPages=_draw_report_footer)
    return target
