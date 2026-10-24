from __future__ import annotations

import argparse
import re
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


PAGE_WIDTH, PAGE_HEIGHT = A4
GREEN_PRIMARY = colors.HexColor("#9CCC10")
GREEN_SECONDARY = colors.HexColor("#5FAF38")
YELLOW_ACCENT = colors.HexColor("#F4D400")
TEXT_DARK = colors.HexColor("#111111")
TEXT_MUTED = colors.HexColor("#4A4A4A")
RULE = colors.HexColor("#D9E6CF")
SURFACE = colors.HexColor("#F7F9F4")


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Render README.md (the operator guide) to PDF.")
    parser.add_argument(
        "--input",
        type=Path,
        default=root / "README.md",
        help="Path to the source markdown file.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=root / "Guia-do-Usuario-BR-Crono-Desktop.pdf",
        help="Path to the generated PDF file.",
    )
    parser.add_argument(
        "--logo",
        type=Path,
        default=None,
        help="Optional path to Logo CB.png. If omitted or missing, a vector brand watermark is used.",
    )
    parser.add_argument(
        "--release-version",
        required=True,
        help="Release reference shown in the PDF chrome.",
    )
    return parser.parse_args()


def resolve_logo(root: Path, requested: Path | None) -> Path | None:
    candidates = []
    if requested is not None:
        candidates.append(requested)
    candidates.extend(
        [
            root / "Logo CB.png",
            root / "docs" / "Logo CB.png",
            root / "docs" / "assets" / "Logo CB.png",
            root / "assets" / "Logo CB.png",
        ]
    )

    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def build_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "cover_title": ParagraphStyle(
            "CoverTitle",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=29,
            leading=33,
            textColor=TEXT_DARK,
            alignment=TA_CENTER,
            spaceAfter=12,
        ),
        "subtitle": ParagraphStyle(
            "Subtitle",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=11.5,
            leading=16,
            textColor=TEXT_MUTED,
            spaceAfter=8,
        ),
        "h1": ParagraphStyle(
            "Heading1",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=TEXT_DARK,
            spaceBefore=12,
            spaceAfter=8,
        ),
        "h2": ParagraphStyle(
            "Heading2",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            textColor=TEXT_DARK,
            spaceBefore=10,
            spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=10.5,
            leading=15.5,
            textColor=TEXT_DARK,
            spaceAfter=8,
        ),
        "bullet": ParagraphStyle(
            "Bullet",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=10.5,
            leading=15.5,
            leftIndent=14,
            firstLineIndent=-10,
            bulletIndent=0,
            textColor=TEXT_DARK,
            spaceAfter=4.5,
        ),
        "number": ParagraphStyle(
            "Number",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=10.5,
            leading=15.5,
            leftIndent=16,
            firstLineIndent=-12,
            textColor=TEXT_DARK,
            spaceAfter=4.5,
        ),
        "code": ParagraphStyle(
            "Code",
            parent=base["Code"],
            fontName="Courier",
            fontSize=9,
            leading=11,
            leftIndent=10,
            rightIndent=10,
            borderPadding=10,
            borderWidth=0.5,
            borderColor=RULE,
            backColor=colors.HexColor("#F7F9F4"),
            spaceAfter=10,
        ),
        "table": ParagraphStyle(
            "Table",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=12,
            textColor=TEXT_DARK,
        ),
        "cover_meta": ParagraphStyle(
            "CoverMeta",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=12,
            textColor=GREEN_SECONDARY,
            alignment=TA_CENTER,
            spaceAfter=3,
        ),
        "cover_body": ParagraphStyle(
            "CoverBody",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=11,
            leading=16,
            textColor=TEXT_DARK,
            alignment=TA_CENTER,
            spaceAfter=6,
        ),
        "cover_note": ParagraphStyle(
            "CoverNote",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=9.5,
            leading=13,
            textColor=GREEN_SECONDARY,
            alignment=TA_CENTER,
            spaceAfter=0,
        ),
        "release_chip": ParagraphStyle(
            "ReleaseChip",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=11,
            textColor=colors.white,
            alignment=TA_CENTER,
            spaceAfter=0,
        ),
    }


def format_inline(text: str) -> str:
    text = text.replace("BR|Crono", "BR Crono")
    placeholders: dict[str, str] = {}

    def protect(prefix: str, value: str) -> str:
        key = f"@@{prefix}{len(placeholders)}@@"
        placeholders[key] = value
        return key

    working = text
    working = re.sub(
        r"`([^`]+)`",
        lambda match: protect("CODE", f"<font name='Courier'>{escape(match.group(1))}</font>"),
        working,
    )
    working = re.sub(
        r"\*\*([^*]+)\*\*",
        lambda match: protect("BOLD", f"<b>{escape(match.group(1))}</b>"),
        working,
    )
    working = re.sub(
        r"<(https?://[^>]+)>",
        lambda match: protect("LINK", f"<link href='{escape(match.group(1))}' color='#5FAF38'>{escape(match.group(1))}</link>"),
        working,
    )
    working = re.sub(
        r"\[([^\]]+)\]\((https?://[^)]+)\)",
        lambda match: protect("LINK", f"<link href='{escape(match.group(2))}' color='#5FAF38'>{escape(match.group(1))}</link>"),
        working,
    )
    working = escape(working)
    for key, value in placeholders.items():
        working = working.replace(escape(key), value)
    return working


def draw_brand_mark(canvas, x: float, y: float, size: float, alpha: float) -> None:
    canvas.saveState()
    if hasattr(canvas, "setFillAlpha"):
        canvas.setFillAlpha(alpha)
        canvas.setStrokeAlpha(alpha)

    pad = size * 0.18
    arm = size * 0.34
    gap = size * 0.12
    cx = x + size / 2
    cy = y + size / 2

    canvas.setStrokeColor(colors.white)
    canvas.setLineWidth(size * 0.02)

    canvas.setFillColor(GREEN_PRIMARY)
    canvas.roundRect(x + pad, cy + gap, arm, size - (pad * 2) - gap * 2, arm * 0.35, stroke=0, fill=1)
    canvas.roundRect(cx + gap, y + pad, size - (pad * 2) - gap * 2, arm, arm * 0.35, stroke=0, fill=1)
    canvas.roundRect(x + pad, y + pad, arm, size - (pad * 2) - gap * 2, arm * 0.35, stroke=0, fill=1)
    canvas.roundRect(x + gap, y + pad, size - (pad * 2) - gap * 2, arm, arm * 0.35, stroke=0, fill=1)

    canvas.setFillColor(GREEN_SECONDARY)
    path = canvas.beginPath()
    path.moveTo(cx, y + size * 0.1)
    path.lineTo(x + size * 0.9, cy)
    path.lineTo(cx, y + size * 0.9)
    path.lineTo(x + size * 0.1, cy)
    path.close()
    canvas.drawPath(path, stroke=0, fill=1)

    canvas.setFillColor(colors.white)
    inner = canvas.beginPath()
    inner.moveTo(cx, y + size * 0.26)
    inner.lineTo(x + size * 0.74, cy)
    inner.lineTo(cx, y + size * 0.74)
    inner.lineTo(x + size * 0.26, cy)
    inner.close()
    canvas.drawPath(inner, stroke=0, fill=1)
    canvas.restoreState()


def draw_wordmark(canvas, x: float, y: float, scale: float, alpha: float) -> None:
    canvas.saveState()
    if hasattr(canvas, "setFillAlpha"):
        canvas.setFillAlpha(alpha)
        canvas.setStrokeAlpha(alpha)

    chip_size = 34 * scale
    brasil_size = 31 * scale
    divider_h = 40 * scale
    divider_w = 3 * scale

    canvas.setFillColor(TEXT_DARK)
    canvas.setFont("Helvetica-Bold", chip_size)
    canvas.drawString(x, y, "Chip")

    chip_w = stringWidth("Chip", "Helvetica-Bold", chip_size)
    divider_x = x + chip_w + 8 * scale
    canvas.setFillColor(YELLOW_ACCENT)
    canvas.rect(divider_x, y - 3 * scale, divider_w, divider_h, stroke=0, fill=1)

    canvas.setFillColor(TEXT_MUTED)
    canvas.setFont("Helvetica", brasil_size)
    canvas.drawString(divider_x + 10 * scale, y, "Brasil")
    canvas.restoreState()


def draw_watermark(canvas, logo_path: Path | None) -> None:
    if logo_path is not None:
        canvas.saveState()
        if hasattr(canvas, "setFillAlpha"):
            canvas.setFillAlpha(0.075)
            canvas.setStrokeAlpha(0.075)
        size = 9.2 * cm
        x = (PAGE_WIDTH - size) / 2
        y = (PAGE_HEIGHT - size) / 2 + 1.6 * cm
        canvas.drawImage(str(logo_path), x, y, width=size, height=size, preserveAspectRatio=True, mask="auto")
        canvas.restoreState()
        return

    mark_size = 6.8 * cm
    mark_x = (PAGE_WIDTH - mark_size) / 2
    mark_y = (PAGE_HEIGHT - mark_size) / 2 + 2.2 * cm
    draw_brand_mark(canvas, mark_x, mark_y, mark_size, alpha=0.12)
    draw_wordmark(canvas, PAGE_WIDTH / 2 - 4.8 * cm, mark_y - 2.2 * cm, scale=0.38, alpha=0.08)


def decorate_cover_page(canvas, doc, logo_path: Path | None, release_version: str) -> None:
    canvas.saveState()

    canvas.setFillColor(colors.white)
    canvas.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, stroke=0, fill=1)

    canvas.setFillColor(GREEN_PRIMARY)
    canvas.rect(0, PAGE_HEIGHT - 4.1 * cm, PAGE_WIDTH, 1.1 * cm, stroke=0, fill=1)
    canvas.setFillColor(GREEN_SECONDARY)
    canvas.rect(0, PAGE_HEIGHT - 4.8 * cm, PAGE_WIDTH * 0.62, 0.55 * cm, stroke=0, fill=1)
    canvas.setFillColor(YELLOW_ACCENT)
    canvas.rect(PAGE_WIDTH * 0.62, PAGE_HEIGHT - 4.8 * cm, PAGE_WIDTH * 0.12, 0.55 * cm, stroke=0, fill=1)

    canvas.setFillColor(SURFACE)
    canvas.roundRect(doc.leftMargin, 5.2 * cm, PAGE_WIDTH - doc.leftMargin - doc.rightMargin, 4.1 * cm, 14, stroke=0, fill=1)

    if logo_path is not None:
        canvas.saveState()
        if hasattr(canvas, "setFillAlpha"):
            canvas.setFillAlpha(0.13)
            canvas.setStrokeAlpha(0.13)
        size = 7.8 * cm
        canvas.drawImage(str(logo_path), PAGE_WIDTH - doc.rightMargin - size, PAGE_HEIGHT - 10.2 * cm, width=size, height=size, preserveAspectRatio=True, mask="auto")
        canvas.restoreState()
    else:
        draw_brand_mark(canvas, PAGE_WIDTH - doc.rightMargin - 7.2 * cm, PAGE_HEIGHT - 10.0 * cm, 6.8 * cm, alpha=0.12)

    canvas.setStrokeColor(RULE)
    canvas.setLineWidth(0.5)
    canvas.line(doc.leftMargin, 1.35 * cm, PAGE_WIDTH - doc.rightMargin, 1.35 * cm)

    canvas.setFont("Helvetica", 8.5)
    canvas.setFillColor(TEXT_MUTED)
    canvas.drawString(doc.leftMargin, 0.92 * cm, "BR Crono Desktop • Publicação de Operação")
    canvas.drawRightString(PAGE_WIDTH - doc.rightMargin, 0.92 * cm, f"Chip Brasil • {release_version}")
    canvas.restoreState()


def decorate_content_page(canvas, doc, logo_path: Path | None, release_version: str) -> None:
    canvas.saveState()
    draw_watermark(canvas, logo_path)

    if logo_path is not None:
        logo_width = 1.45 * cm
        logo_height = 1.26 * cm
        canvas.drawImage(
            str(logo_path),
            PAGE_WIDTH - doc.rightMargin - logo_width,
            PAGE_HEIGHT - 1.95 * cm,
            width=logo_width,
            height=logo_height,
            preserveAspectRatio=True,
            mask="auto",
        )

    canvas.setFillColor(GREEN_PRIMARY)
    canvas.rect(doc.leftMargin, PAGE_HEIGHT - 1.55 * cm, 3.1 * cm, 0.18 * cm, stroke=0, fill=1)
    canvas.setFillColor(GREEN_SECONDARY)
    canvas.rect(doc.leftMargin + 3.3 * cm, PAGE_HEIGHT - 1.55 * cm, 1.3 * cm, 0.18 * cm, stroke=0, fill=1)

    canvas.setStrokeColor(RULE)
    canvas.setLineWidth(0.5)
    canvas.line(doc.leftMargin, 1.3 * cm, PAGE_WIDTH - doc.rightMargin, 1.3 * cm)

    canvas.setFont("Helvetica", 8.5)
    canvas.setFillColor(TEXT_MUTED)
    canvas.drawString(doc.leftMargin, 0.9 * cm, f"BR Crono Desktop • Guia do Usuário • {release_version}")
    canvas.drawRightString(PAGE_WIDTH - doc.rightMargin, 0.9 * cm, f"Página {canvas.getPageNumber()}")
    canvas.restoreState()


def parse_markdown(markdown_text: str, styles: dict[str, ParagraphStyle], base_dir: Path) -> list:
    story: list = []
    lines = markdown_text.splitlines()
    paragraph: list[str] = []
    index = 0
    sections_seen = 0

    def flush_paragraph() -> None:
        nonlocal paragraph
        if not paragraph:
            return
        text = " ".join(part.strip() for part in paragraph if part.strip())
        story.append(Paragraph(format_inline(text), styles["body"]))
        paragraph = []

    while index < len(lines):
        line = lines[index]
        stripped = line.strip()

        if not stripped:
            flush_paragraph()
            story.append(Spacer(1, 0.08 * cm))
            index += 1
            continue

        # The README's link to download this PDF has no use inside the PDF.
        if re.fullmatch(r"\**\[[^\]]+\]\([^)]+\.pdf\)\**", stripped):
            index += 1
            continue

        if stripped.startswith("```"):
            flush_paragraph()
            block: list[str] = []
            index += 1
            while index < len(lines) and not lines[index].strip().startswith("```"):
                block.append(lines[index])
                index += 1
            story.append(Preformatted("\n".join(block), styles["code"]))
            index += 1
            continue

        image_match = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)$", stripped)
        if image_match:
            flush_paragraph()
            image_path = base_dir / image_match.group(2)
            frame_width = PAGE_WIDTH - 4.0 * cm
            reader = ImageReader(str(image_path))
            width, height = reader.getSize()
            picture = Image(str(image_path), width=frame_width, height=frame_width * height / width)
            picture.hAlign = "CENTER"
            framed = Table([[picture]], colWidths=[frame_width])
            framed.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.6, RULE), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
            story.append(Spacer(1, 0.15 * cm))
            story.append(framed)
            story.append(Spacer(1, 0.25 * cm))
            index += 1
            continue

        if stripped.startswith("### "):
            flush_paragraph()
            story.append(Paragraph(format_inline(stripped[4:]), styles["h2"]))
            index += 1
            continue

        if stripped.startswith("## "):
            flush_paragraph()
            # Every section after the first starts on a new page; the first
            # already follows the cover's page break.
            if sections_seen:
                story.append(PageBreak())
            sections_seen += 1
            story.append(Paragraph(format_inline(stripped[3:]), styles["h1"]))
            index += 1
            continue

        if stripped.startswith("# "):
            flush_paragraph()
            index += 1
            continue

        if stripped.startswith("|"):
            flush_paragraph()
            raw_rows: list[list[str]] = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                row = [cell.strip() for cell in lines[index].strip().strip("|").split("|")]
                raw_rows.append(row)
                index += 1
            if len(raw_rows) >= 2:
                data = [[Paragraph(format_inline(cell), styles["table"]) for cell in row] for row in raw_rows if not all(set(cell) <= {"-", ":"} for cell in row)]
                table = Table(data, colWidths=[1.0 * cm, 4.4 * cm, 9.5 * cm], repeatRows=1)
                table.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEF5E3")),
                            ("TEXTCOLOR", (0, 0), (-1, 0), TEXT_DARK),
                            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                            ("LINEBELOW", (0, 0), (-1, 0), 0.75, GREEN_SECONDARY),
                            ("GRID", (0, 0), (-1, -1), 0.35, RULE),
                            ("VALIGN", (0, 0), (-1, -1), "TOP"),
                            ("LEFTPADDING", (0, 0), (-1, -1), 6),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                            ("TOPPADDING", (0, 0), (-1, -1), 6),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                        ]
                    )
                )
                story.append(table)
                story.append(Spacer(1, 0.2 * cm))
            continue

        bullet_match = re.match(r"^[-*]\s+(.*)$", stripped)
        if bullet_match:
            flush_paragraph()
            story.append(Paragraph(f"• {format_inline(bullet_match.group(1))}", styles["bullet"]))
            index += 1
            continue

        number_match = re.match(r"^(\d+)\.\s+(.*)$", stripped)
        if number_match:
            flush_paragraph()
            story.append(Paragraph(f"{number_match.group(1)}. {format_inline(number_match.group(2))}", styles["number"]))
            index += 1
            continue

        paragraph.append(stripped)
        index += 1

    flush_paragraph()
    return story


def build_story(markdown_text: str, styles: dict[str, ParagraphStyle], logo_path: Path | None, release_version: str, base_dir: Path) -> list:
    story = [Spacer(1, 2.15 * cm)]

    if logo_path is not None:
        logo = Image(str(logo_path), width=4.9 * cm, height=4.26 * cm)
        logo.hAlign = "CENTER"
        story.append(logo)
        story.append(Spacer(1, 0.25 * cm))

    story.append(Paragraph("Guia do Usuário", styles["cover_meta"]))
    story.append(Paragraph("BR Crono Desktop", styles["cover_title"]))
    release_chip = Table(
        [[Paragraph(f"Release de Referência {format_inline(release_version)}", styles["release_chip"])]],
        colWidths=[5.0 * cm],
    )
    release_chip.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), GREEN_SECONDARY),
                ("BOX", (0, 0), (-1, -1), 0, GREEN_SECONDARY),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    release_chip.hAlign = "CENTER"
    story.append(release_chip)
    story.append(Spacer(1, 0.22 * cm))
    story.append(
        Paragraph(
            "Documento de publicação para operadores do equipamento de cronometragem eletrônica BR Crono.",
            styles["cover_body"],
        )
    )
    story.append(Spacer(1, 0.45 * cm))

    summary = Table(
        [
            [Paragraph("Conteúdo", styles["cover_note"])],
            [
                Paragraph(
                    "Instalação, escolha do leitor, telas de operação, Teste de Campo, solução de problemas, atualizações e suporte.",
                    styles["cover_body"],
                )
            ],
        ],
        colWidths=[PAGE_WIDTH - 7.0 * cm],
    )
    summary.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                ("BOX", (0, 0), (-1, -1), 0.6, RULE),
                ("LINEBELOW", (0, 0), (-1, 0), 0.6, RULE),
                ("LEFTPADDING", (0, 0), (-1, -1), 16),
                ("RIGHTPADDING", (0, 0), (-1, -1), 16),
                ("TOPPADDING", (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
            ]
        )
    )
    summary.hAlign = "CENTER"
    story.append(summary)
    story.append(Spacer(1, 0.35 * cm))
    story.append(Paragraph("Uso operacional com foco em campo e suporte rápido.", styles["cover_note"]))
    story.append(Spacer(1, 0.15 * cm))
    story.append(Paragraph(f"Baseado na release estável {format_inline(release_version)}.", styles["cover_meta"]))
    story.append(PageBreak())
    story.extend(parse_markdown(markdown_text, styles, base_dir))
    return story


def render_pdf(input_path: Path, output_path: Path, logo_path: Path | None, release_version: str) -> None:
    styles = build_styles()
    markdown_text = input_path.read_text(encoding="utf-8")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=2.0 * cm,
        rightMargin=2.0 * cm,
        topMargin=2.2 * cm,
        bottomMargin=1.8 * cm,
        title="BR Crono Desktop - Guia do Usuário",
        author="Chip Brasil",
    )
    story = build_story(markdown_text, styles, logo_path, release_version, input_path.parent)
    doc.build(
        story,
        onFirstPage=lambda canvas, current_doc: decorate_cover_page(canvas, current_doc, logo_path, release_version),
        onLaterPages=lambda canvas, current_doc: decorate_content_page(canvas, current_doc, logo_path, release_version),
    )


def main() -> None:
    args = parse_args()
    root = Path(__file__).resolve().parents[1]
    logo_path = resolve_logo(root, args.logo)
    render_pdf(args.input.resolve(), args.output.resolve(), logo_path, args.release_version)
    if logo_path is None:
        print(
            f"Rendered {args.output} with vector brand watermark fallback (Logo CB.png not found) for {args.release_version}."
        )
    else:
        print(f"Rendered {args.output} using logo asset {logo_path} for {args.release_version}.")


if __name__ == "__main__":
    main()
