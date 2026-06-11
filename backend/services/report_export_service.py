from __future__ import annotations

import textwrap
from datetime import datetime, timezone
from io import BytesIO
from typing import Any

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


PAGE_WIDTH, PAGE_HEIGHT = letter
LEFT_MARGIN = 56
RIGHT_MARGIN = 56
TOP_MARGIN = 56
BOTTOM_MARGIN = 56
LINE_HEIGHT = 14
BODY_FONT = "Helvetica"
BODY_BOLD_FONT = "Helvetica-Bold"


def build_report_filename(report) -> str:
    week_start = _format_date(getattr(report, "week_start", None))
    return f"tradingnoobs-weekly-report-{week_start}.pdf"


def build_weekly_report_pdf(report, portfolio_summary: dict[str, Any] | None = None, risk_summary: dict[str, Any] | None = None) -> bytes:
    if not getattr(report, "user_id", None):
        raise ValueError("Weekly report must have an owner before PDF export.")

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter, pageCompression=0)
    cursor_y = PAGE_HEIGHT - TOP_MARGIN

    cursor_y = _draw_heading(pdf, "Trading Noobs Weekly Report", cursor_y)
    cursor_y = _draw_line(
        pdf,
        f"Report period: {_format_date(report.week_start)} to {_format_date(report.week_end)}",
        cursor_y,
        font=BODY_BOLD_FONT,
    )
    cursor_y = _draw_line(pdf, f"Generated timestamp: {_format_datetime(_generated_at(report))}", cursor_y)
    cursor_y -= 10

    cursor_y = _draw_section(pdf, "Trades Summary", getattr(report, "trades_summary", None), cursor_y)
    cursor_y = _draw_section(pdf, "Munger Evaluation", getattr(report, "munger_evaluation", None), cursor_y)
    cursor_y = _draw_section(pdf, "Suggestions", getattr(report, "suggestions", None), cursor_y)

    if portfolio_summary:
        cursor_y = _draw_key_value_section(pdf, "Portfolio Summary", portfolio_summary, cursor_y)

    if risk_summary:
        cursor_y = _draw_key_value_section(pdf, "Risk Summary", risk_summary, cursor_y)

    evidence = [
        f"weekly_reports:{getattr(report, 'id', 'unknown')}",
        f"users:{getattr(report, 'user_id', 'unknown')}",
    ]
    if portfolio_summary:
        evidence.append("dashboard:portfolio_summary")
    if risk_summary:
        evidence.append("dashboard:risk_summary")

    _draw_footer(pdf, "Evidence sources: " + "; ".join(evidence))
    pdf.showPage()
    pdf.save()

    return buffer.getvalue()


def _draw_heading(pdf: canvas.Canvas, text: str, cursor_y: float) -> float:
    pdf.setFont(BODY_BOLD_FONT, 18)
    pdf.drawString(LEFT_MARGIN, cursor_y, _safe_text(text))
    return cursor_y - 28


def _draw_section(pdf: canvas.Canvas, title: str, content: Any, cursor_y: float) -> float:
    cursor_y = _ensure_space(pdf, cursor_y, 44)
    cursor_y = _draw_line(pdf, title, cursor_y, font=BODY_BOLD_FONT)
    body = str(content).strip() if content else "No content recorded."
    for paragraph in _split_markdownish_text(body):
        for line in _wrap_text(paragraph):
            cursor_y = _draw_line(pdf, line, cursor_y)
        cursor_y -= 4
    return cursor_y - 6


def _draw_key_value_section(pdf: canvas.Canvas, title: str, values: dict[str, Any], cursor_y: float) -> float:
    cursor_y = _ensure_space(pdf, cursor_y, 44)
    cursor_y = _draw_line(pdf, title, cursor_y, font=BODY_BOLD_FONT)
    for key in sorted(values.keys()):
        value = values[key]
        if value is None:
            continue
        for line in _wrap_text(f"{_humanize_key(key)}: {_format_value(value)}"):
            cursor_y = _draw_line(pdf, line, cursor_y)
    return cursor_y - 12


def _draw_line(pdf: canvas.Canvas, text: str, cursor_y: float, font: str = BODY_FONT, size: int = 10) -> float:
    cursor_y = _ensure_space(pdf, cursor_y, LINE_HEIGHT)
    pdf.setFont(font, size)
    pdf.drawString(LEFT_MARGIN, cursor_y, _safe_text(text))
    return cursor_y - LINE_HEIGHT


def _draw_footer(pdf: canvas.Canvas, text: str) -> None:
    pdf.setFont(BODY_FONT, 8)
    pdf.drawString(LEFT_MARGIN, BOTTOM_MARGIN - 18, _safe_text(text))


def _ensure_space(pdf: canvas.Canvas, cursor_y: float, required_height: float) -> float:
    if cursor_y - required_height >= BOTTOM_MARGIN:
        return cursor_y

    pdf.showPage()
    return PAGE_HEIGHT - TOP_MARGIN


def _split_markdownish_text(text: str) -> list[str]:
    paragraphs: list[str] = []
    for raw_line in text.replace("\r\n", "\n").split("\n"):
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith(("-", "*")):
            line = f"- {line.lstrip('-* ').strip()}"
        paragraphs.append(line)
    return paragraphs or ["No content recorded."]


def _wrap_text(text: str, width: int = 86) -> list[str]:
    return textwrap.wrap(text, width=width, break_long_words=False, replace_whitespace=True) or [""]


def _generated_at(report) -> datetime:
    created_at = getattr(report, "created_at", None)
    if isinstance(created_at, datetime):
        return created_at
    return datetime.now(timezone.utc)


def _format_date(value: Any) -> str:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value or "unknown")


def _format_datetime(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def _format_value(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.2f}"
    if isinstance(value, dict):
        return ", ".join(f"{_humanize_key(k)}={_format_value(v)}" for k, v in sorted(value.items()) if v is not None)
    if isinstance(value, list):
        return ", ".join(_format_value(item) for item in value)
    return str(value)


def _humanize_key(key: Any) -> str:
    return str(key).replace("_", " ").strip().title()


def _safe_text(text: Any) -> str:
    return str(text).encode("latin-1", errors="replace").decode("latin-1")
