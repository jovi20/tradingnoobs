"""
Trading Noobs Backend - Weekly Report Router
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date, timedelta

from database import get_db
from models import User, WeeklyReport, UserSettings, SystemSetting, AISummary
from schemas import WeeklyReportCreate, WeeklyReportResponse, AISummaryResponse, AnalysisRequest, AnalysisResponse
from services.auth_service import get_current_user
from services.llm_service import generate_weekly_report, generate_journal_summary, get_analysis_insight
from services.analytics_service import AnalyticsService

router = APIRouter(prefix="/api/insights", tags=["Insights"])


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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate a new weekly report using LLM"""
    # Check if LLM is configured (System Settings)
    llm_api_url = db.query(SystemSetting).filter(SystemSetting.key == 'llm_api_url').first()
    llm_api_key = db.query(SystemSetting).filter(SystemSetting.key == 'llm_api_key').first()
    
    if not llm_api_url or not llm_api_url.value or not llm_api_key or not llm_api_key.value:
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
    
    return report


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
    
    # Check if LLM is configured (System Settings)
    llm_api_url = db.query(SystemSetting).filter(SystemSetting.key == 'llm_api_url').first()
    llm_api_key = db.query(SystemSetting).filter(SystemSetting.key == 'llm_api_key').first()
    
    if not llm_api_url or not llm_api_url.value or not llm_api_key or not llm_api_key.value:
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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """生成今日 AI 总结（每天限一次）"""
    today = date.today()
    
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
    
    # 检查 LLM 配置
    llm_api_url = db.query(SystemSetting).filter(SystemSetting.key == 'llm_api_url').first()
    llm_api_key = db.query(SystemSetting).filter(SystemSetting.key == 'llm_api_key').first()
    
    if not llm_api_url or not llm_api_url.value or not llm_api_key or not llm_api_key.value:
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
    db.commit()
    db.refresh(summary)
    
    return summary


# ============== Advanced Analytics Endpoints ==============

@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_trading_data(
    request: AnalysisRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Perform advanced AI analysis on trading data.
    """
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
    return AnalysisResponse(
        analysis_type=request.analysis_type,
        raw_data=raw_data,
        ai_insights=ai_insights,
        created_at=datetime.now()
    )
