
from typing import List, Dict, Any, Optional
from datetime import date, timedelta
from sqlalchemy import func
from sqlalchemy.orm import Session
import pandas as pd
import numpy as np

from models import Position, PositionStatus, TradeBatch, BatchType
from schemas import AnalysisType
from services.truth_legacy_projection_service import exclude_void_truth_legacy_positions

class AnalyticsService:
    def __init__(self, db: Session):
        self.db = db

    def analyze(self, user_id: int, analysis_type: str, start_date: Optional[date] = None, end_date: Optional[date] = None) -> Dict[str, Any]:
        """
        Main entry point for analytics.
        """
        # Base query for closed positions (for performance analysis)
        query = self.db.query(Position).filter(
            Position.user_id == user_id,
            Position.status == PositionStatus.CLOSED
        )
        
        if start_date:
            query = query.filter(Position.closed_at >= start_date)
        if end_date:
            query = query.filter(Position.closed_at <= end_date)
            
        positions = exclude_void_truth_legacy_positions(
            self.db,
            user_id=user_id,
            positions=query.all(),
        )
        
        if analysis_type == "holding_period":
            return self._analyze_holding_period(positions)
        elif analysis_type == "losing_streak":
            return self._analyze_losing_streaks(positions)
        elif analysis_type == "emotion_pnl":
            # For emotion, we need Batches or Position initial emotion
            return self._analyze_emotion_pnl(user_id, start_date, end_date)
        elif analysis_type == "checklist_effect":
            return self._analyze_checklist_effect(positions)
        elif analysis_type == "strategy_health":
            return self._analyze_strategy_health(positions)
        else:
            return {"error": "Unknown analysis type"}

    def _analyze_holding_period(self, positions: List[Position]) -> Dict[str, Any]:
        """
        Analyze performance by holding duration buckets.
        buckets: <1 Day, 1-3 Days, 3-7 Days, 1-2 Weeks, 2 Weeks+
        """
        if not positions:
            return {"message": "No data found"}
            
        data = []
        for p in positions:
            if not p.opened_at or not p.closed_at: continue
            
            duration = (p.closed_at.date() - p.opened_at.date()).days
            # Intraday is 0 days, treat as 1 for bucket logic or separate "Intraday"
            if duration == 0: duration = 0.5 # Special flag
            
            bucket = ""
            if duration <= 0.5: bucket = "Intraday (<1d)"
            elif duration <= 3: bucket = "Short Term (1-3d)"
            elif duration <= 7: bucket = "Weekly (3-7d)"
            elif duration <= 14: bucket = "Bi-Weekly (1-2w)"
            else: bucket = "Long Term (2w+)"
            
            data.append({
                "bucket": bucket,
                "pnl": float(p.realized_pnl or 0),
                "win": 1 if (p.realized_pnl or 0) > 0 else 0
            })
            
        df = pd.DataFrame(data)
        if df.empty: return {"message": "Insufficient data"}
        
        # Group by bucket
        stats = df.groupby("bucket").agg(
            count=("pnl", "count"),
            avg_pnl=("pnl", "mean"),
            total_pnl=("pnl", "sum"),
            win_rate=("win", "mean")
        ).to_dict(orient="index")
        
        # Sort manually for display order?
        # For now return dict, frontend or LLM can sort
        return {"stats": stats}

    def _get_entry_emotion(self, position: Position) -> Optional[str]:
        """Helper to extract entry emotion from position batches"""
        if not position.batches:
            return None
        # Find first ENTRY batch with emotion
        for batch in position.batches:
            if batch.type == BatchType.ENTRY and batch.emotion:
                return batch.emotion
        # Fallback to first batch emotion if no explicit ENTRY with emotion
        if position.batches[0].emotion:
            return position.batches[0].emotion
        return None

    def _analyze_losing_streaks(self, positions: List[Position]) -> Dict[str, Any]:
        """
        Identify losing streaks and context.
        """
        if not positions: return {}
        
        # Sort by close time
        positions.sort(key=lambda x: x.closed_at)
        
        streaks = []
        current_streak = []
        
        for p in positions:
            pnl = float(p.realized_pnl or 0)
            if pnl < 0:
                current_streak.append(p)
            else:
                if len(current_streak) >= 2:
                    streaks.append(list(current_streak))
                current_streak = []
                
        if len(current_streak) >= 2:
            streaks.append(current_streak)
            
        # Analyze top 3 longest streaks
        streaks.sort(key=len, reverse=True)
        top_streaks = streaks[:3]
        
        report = []
        for streak in top_streaks:
            if not streak: continue
            start_date = streak[0].closed_at.date()
            end_date = streak[-1].closed_at.date()
            total_loss = sum(float(p.realized_pnl or 0) for p in streak)
            
            # Common factors?
            strategies = [p.strategy_id for p in streak if p.strategy_id]
            emotions = []
            for p in streak:
                emo = self._get_entry_emotion(p)
                if emo:
                    emotions.append(emo)
            
            report.append({
                "start": start_date,
                "end": end_date,
                "length": len(streak),
                "total_loss": total_loss,
                "strategies": list(set(strategies)), # IDs
                "emotions": list(set(emotions))
            })
            
        return {"streaks": report, "max_streak": len(streaks[0]) if streaks else 0}

    def _analyze_emotion_pnl(self, user_id: int, start_date, end_date) -> Dict[str, Any]:
        """
        Analyze PnL based on Entry Emotion.
        Note: Emotion is stored on TradeBatch. 
        """
        query = self.db.query(Position).filter(
            Position.user_id == user_id,
            Position.status == PositionStatus.CLOSED
        )
        if start_date: query = query.filter(Position.closed_at >= start_date)
        if end_date: query = query.filter(Position.closed_at <= end_date)
        
        positions = exclude_void_truth_legacy_positions(
            self.db,
            user_id=user_id,
            positions=query.all(),
        )
        data = []
        for p in positions:
            emotion = self._get_entry_emotion(p) or "Neutral/None"
            data.append({
                "emotion": emotion,
                "pnl": float(p.realized_pnl or 0),
                "win": 1 if (p.realized_pnl or 0) > 0 else 0
            })
            
        df = pd.DataFrame(data)
        if df.empty: return {}
        
        stats = df.groupby("emotion").agg(
            count=("pnl", "count"),
            avg_pnl=("pnl", "mean"),
            win_rate=("win", "mean")
        ).to_dict(orient="index")
        
        return {"stats": stats}

    def _analyze_checklist_effect(self, positions: List[Position]) -> Dict[str, Any]:
        """
        Compare trades depending on if checklist was fully completed.
        """
        # Need to know if checklist was 'full'. 
        # Currently we store 'checklist_responses' (JSON) and 'checklist_completed_at'.
        # We assume if 'checklist_completed_at' is present, it was completed. 
        # Or we can check if all items in response are True? 
        # For simplicity: Presence of checklist_completed_at
        
        completed = []
        ignored = []
        
        for p in positions:
            pnl = float(p.realized_pnl or 0)
            is_win = 1 if pnl > 0 else 0
            
            if p.checklist_completed_at:
                completed.append({"pnl": pnl, "win": is_win})
            else:
                ignored.append({"pnl": pnl, "win": is_win})
                
        def calc_stats(lst):
            if not lst: return None
            df = pd.DataFrame(lst)
            return {
                "count": len(df),
                "avg_pnl": float(df["pnl"].mean()),
                "win_rate": float(df["win"].mean())
            }
            
        return {
            "checklist_completed": calc_stats(completed),
            "checklist_ignored": calc_stats(ignored)
        }

    def _analyze_strategy_health(self, positions: List[Position]) -> Dict[str, Any]:
        """
        Analyze Strategy Performance.
        """
        data = []
        for p in positions:
            strat = str(p.strategy_id) if p.strategy_id else "No Strategy"
            data.append({
                "strategy": strat,
                "pnl": float(p.realized_pnl or 0),
                "win": 1 if (p.realized_pnl or 0) > 0 else 0
            })
            
        df = pd.DataFrame(data)
        if df.empty: return {}

        stats = df.groupby("strategy").agg(
            count=("pnl", "count"),
            avg_pnl=("pnl", "mean"),
            total_pnl=("pnl", "sum"),
            win_rate=("win", "mean")
        ).to_dict(orient="index")
        
        return {"stats": stats}
