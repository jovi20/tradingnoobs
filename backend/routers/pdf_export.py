"""PDF export routes isolated from the AI Insights capability."""
from __future__ import annotations

from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from models import Position, PositionStatus, User, WeeklyReport
from services.auth_service import get_current_user
from services.report_export_service import build_report_filename, build_weekly_report_pdf


router = APIRouter(prefix="/api/insights", tags=["PDF Export"])


def _get_owned_weekly_report(
    db: Session,
    *,
    report_id: int,
    user_id: int,
) -> WeeklyReport:
    report = db.query(WeeklyReport).filter(
        WeeklyReport.id == report_id,
        WeeklyReport.user_id == user_id,
    ).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


def _build_report_portfolio_summary(db: Session, user_id: int) -> dict:
    stats = db.query(
        func.count(Position.id).label("total_positions"),
        func.count(Position.id).filter(Position.status == PositionStatus.OPEN).label("open_positions"),
        func.count(Position.id).filter(Position.status == PositionStatus.CLOSED).label("closed_positions"),
        func.sum(Position.realized_pnl).label("realized_pnl"),
    ).filter(Position.user_id == user_id).one()

    return {
        "total_positions": int(stats.total_positions or 0),
        "open_positions": int(stats.open_positions or 0),
        "closed_positions": int(stats.closed_positions or 0),
        "realized_pnl": float(stats.realized_pnl or 0),
    }


@router.get("/{report_id}/export/pdf")
async def export_weekly_report_pdf(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    report = _get_owned_weekly_report(
        db,
        report_id=report_id,
        user_id=current_user.id,
    )
    pdf_bytes = build_weekly_report_pdf(
        report,
        portfolio_summary=_build_report_portfolio_summary(db, current_user.id),
    )
    filename = build_report_filename(report)

    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )
