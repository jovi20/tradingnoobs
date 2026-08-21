
"""
Trading Noobs Backend - Metrics Service
Calculates risk-adjusted return metrics: Sharpe, Sortino, Calmar
"""
import statistics
import math
from typing import List, Optional

class MetricsService:
    @staticmethod
    def calculate_daily_returns(equity_curve: List[float]) -> List[float]:
        """
        Calculate daily percentage returns from an equity curve.
        equity_curve: List of total equity values (chronological)
        Returns: List of daily returns (e.g., 0.01 for 1%)
        """
        if len(equity_curve) < 2:
            return []
        
        returns = []
        for i in range(1, len(equity_curve)):
            prev = equity_curve[i-1]
            curr = equity_curve[i]
            if prev > 0:
                ret = (curr - prev) / prev
                returns.append(ret)
            else:
                returns.append(0.0)
        return returns

    @staticmethod
    def calculate_sharpe_ratio(returns: List[float], risk_free_rate: float = 0.02) -> Optional[float]:
        """
        Calculate Annualized Sharpe Ratio.
        Assumes daily returns.
        risk_free_rate: Annualized risk-free rate (default 2%)
        """
        if not returns or len(returns) < 2:
            return None
        
        # Annualized risk-free rate to daily
        daily_rf = (1 + risk_free_rate) ** (1/252) - 1
        
        excess_returns = [r - daily_rf for r in returns]
        avg_excess_return = statistics.mean(excess_returns)
        
        try:
            std_dev = statistics.stdev(returns)
        except:
            return None
            
        if std_dev == 0:
            return None
            
        daily_sharpe = avg_excess_return / std_dev
        annualized_sharpe = daily_sharpe * math.sqrt(252)
        
        return annualized_sharpe

    @staticmethod
    def calculate_sortino_ratio(returns: List[float], target_return: float = 0.0) -> Optional[float]:
        """
        Calculate Annualized Sortino Ratio.
        Only considers downside deviation.
        """
        if not returns or len(returns) < 2:
            return None
            
        # Downside returns (only negative returns relative to target)
        downside_returns = [min(0, r - target_return) for r in returns]
        
        avg_return = statistics.mean(returns)
        
        # Calculate downside deviation (RMS of downside returns)
        squared_downside = [r**2 for r in downside_returns]
        mean_squared_downside = statistics.mean(squared_downside)
        downside_dev = math.sqrt(mean_squared_downside)
        
        if downside_dev == 0:
            return None
            
        daily_sortino = (avg_return - target_return) / downside_dev
        annualized_sortino = daily_sortino * math.sqrt(252)
        
        return annualized_sortino

    @staticmethod
    def calculate_max_drawdown(equity_curve: List[float]) -> float:
        """
        Calculate Maximum Drawdown as a positive percentage (e.g. 0.15 for 15% drawdown)
        """
        if not equity_curve:
            return 0.0
            
        peak = equity_curve[0]
        max_dd = 0.0
        
        for val in equity_curve:
            if val > peak:
                peak = val
            elif peak > 0:
                dd = (peak - val) / peak
                if dd > max_dd:
                    max_dd = dd
                    
        return max_dd

    @staticmethod
    def calculate_calmar_ratio(annualized_return: float, max_drawdown: float) -> Optional[float]:
        """
        Calculate Calmar Ratio.
        """
        if max_drawdown == 0:
            return None
            
        # Calmar is usually calculated over 3 years, but here we use available period annualized
        return annualized_return / max_drawdown

    @staticmethod
    def calculate_cagr(start_equity: float, end_equity: float, days: int) -> float:
        """Calculate Compound Annual Growth Rate"""
        if start_equity <= 0 or days <= 0:
            return 0.0
            
        years = days / 365.25
        return (end_equity / start_equity) ** (1 / years) - 1
