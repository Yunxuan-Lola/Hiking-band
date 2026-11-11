"""Build the design report and user manual PDFs from their Markdown sources.

Requires reportlab. This intentionally supports the small Markdown subset used
in the two source documents, so the PDF remains reproducible without a browser.
"""
from html import escape
from pathlib import Path
import re

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable, PageBreak, Paragraph, Preformatted, SimpleDocTemplate,
    Spacer, Table, TableStyle,
)


ROOT = Path(__file__).resolve().parent
FONT_PAIRS = [
    (Path('/System/Library/Fonts/Supplemental/Arial.ttf'),
     Path('/System/Library/Fonts/Supplemental/Arial Bold.ttf')),
    (Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),
     Path('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf')),
]
REGULAR, BOLD = 'Helvetica', 'Helvetica-Bold'
for regular_file, bold_file in FONT_PAIRS:
    if regular_file.exists() and bold_file.exists():
        REGULAR, BOLD = 'DocumentRegular', 'DocumentBold'
        pdfmetrics.registerFont(TTFont(REGULAR, regular_file))
        pdfmetrics.registerFont(TTFont(BOLD, bold_file))
        pdfmetrics.registerFontFamily(REGULAR, normal=REGULAR, bold=BOLD)
        break

PAGE_W, PAGE_H = A4
INK = colors.HexColor('#183047')
ACCENT = colors.HexColor('#12617e')
PALE = colors.HexColor('#eaf2f6')

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name='DocTitle', fontName=BOLD, fontSize=19, leading=24,
                          textColor=INK, spaceAfter=10))
styles.add(ParagraphStyle(name='DocH2', fontName=BOLD, fontSize=12.3, leading=16,
                          textColor=ACCENT, spaceBefore=13, spaceAfter=6, keepWithNext=True))
styles.add(ParagraphStyle(name='DocBody', fontName=REGULAR, fontSize=8.8, leading=12.8,
                          textColor=INK, spaceAfter=6))
styles.add(ParagraphStyle(name='DocBullet', parent=styles['DocBody'], leftIndent=14,
                          firstLineIndent=-8, spaceAfter=4))
styles.add(ParagraphStyle(name='DocCell', fontName=REGULAR, fontSize=8, leading=11,
                          textColor=INK))
styles.add(ParagraphStyle(name='DocCellHead', parent=styles['DocCell'], fontName=BOLD,
                          textColor=colors.white))


def inline(text):
    text = escape(text)
    text = re.sub(r'`([^`]+)`', r'<font name="Courier" color="#0b5d77">\1</font>', text)
    text = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'\[([^\]]+)\]\((https?://[^)]+)\)', r'<link href="\2" color="#0b5d77">\1</link>', text)
    return text


def flush_paragraph(lines, story):
    if lines:
        story.append(Paragraph(inline(' '.join(lines)), styles['DocBody']))
        lines.clear()


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor('#c9dce5'))
    canvas.line(19 * mm, 18 * mm, PAGE_W - 19 * mm, 18 * mm)
    canvas.setFont(REGULAR, 8)
    canvas.setFillColor(colors.HexColor('#557185'))
    canvas.drawString(19 * mm, 12 * mm, 'Hiking Assistant')
    canvas.drawRightString(PAGE_W - 19 * mm, 12 * mm, str(doc.page))
    canvas.restoreState()


def build(source):
    output = source.with_suffix('.pdf')
    doc = SimpleDocTemplate(str(output), pagesize=A4, leftMargin=19 * mm,
                            rightMargin=19 * mm, topMargin=16 * mm,
                            bottomMargin=20 * mm, title=source.stem.replace('_', ' ').title(),
                            author='Hiking Assistant project')
    story, paragraph = [], []
    lines = source.read_text(encoding='utf-8').splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.strip():
            flush_paragraph(paragraph, story)
            index += 1
            continue
        if line.startswith('```'):
            flush_paragraph(paragraph, story)
            code = []
            index += 1
            while index < len(lines) and not lines[index].startswith('```'):
                code.append(lines[index])
                index += 1
            story.append(Preformatted('\n'.join(code), ParagraphStyle(
                name=f'Code{index}', fontName='Courier', fontSize=7.2, leading=9.4,
                leftIndent=7, rightIndent=5, textColor=INK,
                backColor=PALE, borderPadding=7, spaceBefore=4, spaceAfter=9)))
            index += 1
            continue
        if line.startswith('|'):
            flush_paragraph(paragraph, story)
            rows = []
            while index < len(lines) and lines[index].startswith('|'):
                cells = [cell.strip() for cell in lines[index].strip('|').split('|')]
                if not all(re.fullmatch(r':?-{3,}:?', cell) for cell in cells):
                    rows.append(cells)
                index += 1
            width = (PAGE_W - 38 * mm) / len(rows[0])
            data = [[Paragraph(inline(cell), styles['DocCellHead' if r == 0 else 'DocCell'])
                     for cell in row] for r, row in enumerate(rows)]
            table = Table(data, colWidths=[width] * len(rows[0]), repeatRows=1, hAlign='LEFT')
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), ACCENT),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, PALE]),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 7),
                ('RIGHTPADDING', (0, 0), (-1, -1), 7),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('LINEBELOW', (0, 0), (-1, 0), 0.5, ACCENT),
            ]))
            story.append(table)
            story.append(Spacer(1, 8))
            continue
        if line.startswith('# '):
            flush_paragraph(paragraph, story)
            story.append(Paragraph(inline(line[2:]), styles['DocTitle']))
            story.append(HRFlowable(width='100%', thickness=1.2, color=ACCENT, spaceAfter=9))
        elif line.startswith('## '):
            flush_paragraph(paragraph, story)
            if source.stem == 'user_manual' and line.startswith('## 7. '):
                story.append(PageBreak())
            story.append(Paragraph(inline(line[3:]), styles['DocH2']))
        elif line.startswith('- '):
            flush_paragraph(paragraph, story)
            story.append(Paragraph('&#8226; ' + inline(line[2:]), styles['DocBullet']))
        elif re.match(r'^\d+\. ', line):
            flush_paragraph(paragraph, story)
            story.append(Paragraph(inline(line), styles['DocBullet']))
        else:
            paragraph.append(line.strip())
        index += 1
    flush_paragraph(paragraph, story)
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print(output)


if __name__ == '__main__':
    for name in ('design_report.md', 'user_manual.md'):
        build(ROOT / name)
