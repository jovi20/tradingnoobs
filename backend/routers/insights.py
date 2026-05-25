"""
Trading Noobs Backend - Weekly Report Router
"""
from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date, timedelta

from database import get_db
from models import User, WeeklyReport, AISummary, AIAnalysisResult
from schemas import WeeklyReportCreate, WeeklyReportResponse, AISummaryResponse, AnalysisRequest, AnalysisResponse
from services.auth_service import get_current_user
from services.llm_service import generate_weekly_report, generate_journal_summary, get_analysis_insight
from services.analytics_service import AnalyticsService
from services.idempotency_service import begin_idempotent_request, complete_idempotent_request
from services.platform_config_service import get_llm_runtime_config

router = APIRouter(prefix="/api/insights", tags=["Insights"])


def _begin_idempotent_insights_request(
    db: Session,
    *,
    scope: str,
    idempotency_key: str | None,
    current_user: User,
    request_payload,
    replay_status_code: int = 200,
) -> tuple[object | None, JSONResponse | None]:
    if not idempotency_key:
        return None, None

    try:
        idempotency_begin = begin_idempotent_request(
            db,
            scope=scope,
            key=f"{current_user.public_id}:{idempotency_key}",
            request_payload=jsonable_encoder(request_payload),
            user_id=current_user.id,
            ttl_seconds=24 * 60 * 60,
        )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    record = idempotency_begin.record
    if idempotency_begin.created:
        return record, None

    if record.status == "COMPLETED" and record.response_json is not None:
        return record, JSONResponse(status_code=replay_status_code, content=jsonable_encoder(record.response_json))

    raise HTTPException(status_code=409, detail="Idempotent request is already in progress.")


def _complete_idempotent_insights_request(db: Session, *, record, response_content: dict) -> None:
    if record is None:
        return
    complete_idempotent_request(
        db,
        record=record,
        response_json=jsonable_encoder(response_content),
    )


def _weekly_report_response_content(report: WeeklyReport) -> dict:
    return jsonable_encoder(WeeklyReportResponse(
        id=report.id,
        user_id=report.user_id,
        week_start=report.week_start,
        week_end=report.week_end,
        trades_summary=report.trades_summary,
        munger_evaluation=report.munger_evaluation,
        suggestions=report.suggestions,
        created_at=report.created_at,
    ))


@router.get("", response_model=List[WeeklyReportResponse])
async def get_weekly_reports(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all weekly reports for current user"""
    return db.query(WeeklyReport).filter(
        WeeklyReport.user_id == current_user.id
    ).order_by(WeeklyReport.week_start.desc()).all()


@router.get("/{report_id}", response_model=WeeklyReportResponse)
async def get_weekly_report(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific weekly report"""
    report = db.query(WeeklyReport).filter(
        WeeklyReport.id == report_id,
        WeeklyReport.user_id == current_user.id
    ).first()
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    return report


@router.post("/generate", response_model=WeeklyReportResponse, status_code=status.HTTP_201_CREATED)
async def generate_report(
    report_data: WeeklyReportCreate,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate a new weekly report using LLM"""
    idempotency_record, replay_response = _begin_idempotent_insights_request(
        db,
        scope="insights.weekly_report.generate",
        idempotency_key=idempotency_key,
        current_user=current_user,
        request_payload=jsonable_encoder(report_data),
        replay_status_code=201,
    )
    if replay_response is not None:
        return replay_response

    llm_config = get_llm_runtime_config(db)
    if not llm_config["api_url"] or not llm_config["api_key"]:
        raise HTTPException(
            status_code=400,
            detail="System LLM API not configured. Please contact admin."
        )
    
    # Check if report exists for this week
    existing = db.query(WeeklyReport).filter(
        WeeklyReport.user_id == current_user.id,
        WeeklyReport.week_start == report_data.week_start,
        WeeklyReport.week_end == report_data.week_end
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Weekly report already exists for this period"
        )
    
    try:
        report = await generate_weekly_report(
            db=db,
            user_id=current_user.id,
            week_start=report_data.week_start,
            week_end=report_data.week_end
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate report: {str(e)}"
        )
    
    if not report:
        raise HTTPException(
            status_code=500,
            detail="Failed to generate report"
        )
    
    response_content = _weekly_report_response_content(report)
    _complete_idempotent_insights_request(db, record=idempotency_record, response_content=response_content)
    db.commit()

    return JSONResponse(status_code=201, content=response_content)


@router.post("/generate-current-week", response_model=WeeklyReportResponse, status_code=status.HTTP_201_CREATED)
async def generate_current_week_report(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate report for current week"""
    today = date.today()
    # Week starts on Monday
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    
    llm_config = get_llm_runtime_config(db)
    if not llm_config["api_url"] or not llm_config["api_key"]:
        raise HTTPException(
            status_code=400,
            detail="System LLM API not configured. Please contact admin."
        )
    
    try:
        report = await generate_weekly_report(
            db=db,
            user_id=current_user.id,
            week_start=week_start,
            week_end=week_end
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate report: {str(e)}"
        )
    
    if not report:
        raise HTTPException(
            status_code=500,
            detail="Failed to generate report"
        )
    
    return report


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_weekly_report(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a weekly report"""
    report = db.query(WeeklyReport).filter(
        WeeklyReport.id == report_id,
        WeeklyReport.user_id == current_user.id
    ).first()
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    db.delete(report)
    db.commit()


# ============== AI Summary Endpoints ==============

@router.get("/summary/today", response_model=Optional[AISummaryResponse])
async def get_today_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取今日 AI 总结（如已生成）"""
    today = date.today()
    summary = db.query(AISummary).filter(
        AISummary.user_id == current_user.id,
        AISummary.date == today
    ).first()
    return summary


@router.post("/summary/generate", response_model=AISummaryResponse, status_code=status.HTTP_201_CREATED)
async def generate_summary(
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """生成今日 AI 总结（每天限一次）"""
    today = date.today()
    idempotency_record, replay_response = _begin_idempotent_insights_request(
        db,
        scope="insights.summary.generate",
        idempotency_key=idempotency_key,
        current_user=current_user,
        request_payload={"date": today.isoformat()},
        replay_status_code=201,
    )
    if replay_response is not None:
        return replay_response
    
    # 检查今天是否已生成
    existing = db.query(AISummary).filter(
        AISummary.user_id == current_user.id,
        AISummary.date == today
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail="今日已生成总结，每天只能生成一次"
        )
    
    llm_config = get_llm_runtime_config(db)
    if not llm_config["api_url"] or not llm_config["api_key"]:
        raise HTTPException(
            status_code=400,
            detail="System LLM API not configured. Please contact admin."
        )
    
    # 计算本周日期范围（周一到周日）
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    
    try:
        content = await generate_journal_summary(
            db=db,
            user_id=current_user.id,
            week_start=week_start,
            week_end=week_end
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
    
    # 保存总结
    summary = AISummary(
        user_id=current_user.id,
        date=today,
        content=content
    )
    db.add(summary)
    db.flush()
    db.refresh(summary)

    response_content = jsonable_encoder(AISummaryResponse(
        id=summary.id,
        user_id=summary.user_id,
        date=summary.date,
        content=summary.content,
        created_at=summary.created_at,
    ))
    _complete_idempotent_insights_request(db, record=idempotency_record, response_content=response_content)
    db.commit()
    
    return JSONResponse(status_code=201, content=response_content)


# ============== Advanced Analytics Endpoints ==============

@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_trading_data(
    request: AnalysisRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Perform advanced AI analysis on trading data.
    """
    idempotency_record, replay_response = _begin_idempotent_insights_request(
        db,
        scope="insights.analysis.create",
        idempotency_key=idempotency_key,
        current_user=current_user,
        request_payload=request,
    )
    if replay_response is not None:
        return replay_response

    # 1. Calculate Statistics
    analytics_service = AnalyticsService(db)
    raw_data = analytics_service.analyze(
        user_id=current_user.id,
        analysis_type=request.analysis_type.value,
        start_date=request.start_date,
        end_date=request.end_date
    )
    
    # 2. Generate AI Insights
    ai_insights = await get_analysis_insight(
        db=db,
        analysis_type=request.analysis_type.value,
        data=raw_data
    )
    
    from datetime import datetime
    
    # 3. Persist Analysis Result
    ai_result = AIAnalysisResult(
        user_id=current_user.id,
        analysis_type=request.analysis_type.value,
        raw_data=raw_data,
        ai_insights=ai_insights
    )
    db.add(ai_result)
    db.flush()
    db.refresh(ai_result)

    response_content = jsonable_encoder(AnalysisResponse(
        analysis_type=request.analysis_type,
        raw_data=raw_data,
        ai_insights=ai_insights,
        created_at=ai_result.created_at
    ))
    _complete_idempotent_insights_request(db, record=idempotency_record, response_content=response_content)
    db.commit()

    return JSONResponse(status_code=200, content=response_content)


@router.get("/analyze/latest/{analysis_type}", response_model=Optional[AnalysisResponse])
async def get_latest_analysis(
    analysis_type: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the latest analysis result for a specific type"""
    result = db.query(AIAnalysisResult).filter(
        AIAnalysisResult.user_id == current_user.id,
        AIAnalysisResult.analysis_type == analysis_type
    ).order_by(AIAnalysisResult.created_at.desc()).first()
    
    if not result:
        return None
        
    return AnalysisResponse(
        analysis_type=result.analysis_type,
        raw_data=result.raw_data,
        ai_insights=result.ai_insights,
        created_at=result.created_at
    )
