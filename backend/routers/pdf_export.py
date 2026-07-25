"""PDF export routes isolated from the AI Insights capability."""
from __future__ import annotations

from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from database import get_db
from models import Position, PositionStatus, User, WeeklyReport
from services.auth_service import get_current_user
from services.report_export_service import build_report_filename, build_weekly_report_pdf
from services.truth_legacy_projection_service import exclude_void_truth_legacy_positions


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
    positions = exclude_void_truth_legacy_positions(
        db,
        user_id=user_id,
        positions=db.query(Position).filter(Position.user_id == user_id).all(),
    )

    return {
        "total_positions": len(positions),
        "open_positions": sum(
            1 for position in positions if position.status == PositionStatus.OPEN
        ),
        "closed_positions": sum(
            1 for position in positions if position.status == PositionStatus.CLOSED
        ),
        "realized_pnl": float(
            sum((position.realized_pnl or 0 for position in positions), 0)
        ),
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
