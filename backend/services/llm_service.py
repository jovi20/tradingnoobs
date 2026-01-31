"""
Trading Noobs Backend - LLM Service for Weekly Reports
"""
import httpx
from typing import Optional, List
from datetime import date, timedelta
from sqlalchemy.orm import Session

from models import Trade, TradeStatus, UserSettings, WeeklyReport


MUNGER_PROMPT = """你是一位投资分析师，精通查理·芒格的投资哲学。请根据以下一周的交易记录，生成周报总结。

## 交易记录
{trades_data}

## 请按以下格式输出：

### 📊 本周交易摘要
- 总交易次数、盈亏情况、胜率等

### 🎯 芒格理论评价
请从以下五个维度评价本周交易决策质量（每项 1-5 分）：

1. **能力圈**：是否在熟悉的领域交易？
2. **安全边际**：买入价格是否具备安全边际？
3. **逆向思维**：是否考虑过反面观点？
4. **耐心等待**：是否避免了冲动交易？
5. **独立思考**：是否受情绪/市场噪音影响？

### 💡 改进建议
基于芒格投资哲学，给出具体的改进建议。
"""


def format_trades_for_llm(trades: List[Trade]) -> str:
    """Format trades data for LLM prompt"""
    if not trades:
        return "本周无交易记录"
    
    lines = []
    for i, trade in enumerate(trades, 1):
        status = "已平仓" if trade.status == TradeStatus.CLOSED else "持仓中"
        pnl = trade.pnl or 0
        pnl_str = f"+{pnl:.2f}" if pnl >= 0 else f"{pnl:.2f}"
        
        lines.append(f"""
交易 {i}:
- 标的: {trade.symbol} ({trade.exchange})
- 状态: {status}
- 成本价: {trade.entry_price}
- 数量: {trade.quantity}
- 盈亏: {pnl_str}
- 买入理由: {trade.entry_reason or '未填写'}
- 买入情绪: {trade.entry_emotion or '未填写'}
- 信心程度: {trade.entry_confidence or '未填写'}/5
""")
        
        if trade.status == TradeStatus.CLOSED:
            lines.append(f"""- 卖出价: {trade.exit_price}
- 卖出理由: {trade.exit_reason or '未填写'}
- 卖出情绪: {trade.exit_emotion or '未填写'}
- 复盘笔记: {trade.trade_review or '未填写'}
- 自评分: {trade.rating or '未填写'}/5
""")
    
    return "\n".join(lines)


async def generate_weekly_report(
    db: Session,
    user_id: int,
    week_start: date,
    week_end: date
) -> Optional[WeeklyReport]:
    """Generate weekly report using LLM"""
    # Get user settings
    settings = db.query(UserSettings).filter(
        UserSettings.user_id == user_id
    ).first()
    
    if not settings or not settings.llm_api_url or not settings.llm_api_key:
        return None
    
    # Get trades for the week
    trades = db.query(Trade).filter(
        Trade.user_id == user_id,
        Trade.entry_time >= week_start,
        Trade.entry_time <= week_end
    ).all()
    
    # Format trades for LLM
    trades_data = format_trades_for_llm(trades)
    prompt = MUNGER_PROMPT.format(trades_data=trades_data)
    
    # Call LLM API (OpenAI format)
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{settings.llm_api_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.llm_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": settings.llm_model or "gpt-4",
                    "messages": [
                        {"role": "system", "content": "你是一位专业的投资分析师。"},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 2000
                }
            )
            response.raise_for_status()
            result = response.json()
            content = result["choices"][0]["message"]["content"]
    except Exception as e:
        raise Exception(f"LLM API call failed: {str(e)}")
    
    # Parse response (simple split for now)
    trades_summary = ""
    munger_evaluation = ""
    suggestions = ""
    
    sections = content.split("###")
    for section in sections:
        if "交易摘要" in section:
            trades_summary = section.strip()
        elif "芒格理论评价" in section:
            munger_evaluation = section.strip()
        elif "改进建议" in section:
            suggestions = section.strip()
    
    # Create report
    report = WeeklyReport(
        user_id=user_id,
        week_start=week_start,
        week_end=week_end,
        trades_summary=trades_summary or content,
        munger_evaluation=munger_evaluation,
        suggestions=suggestions
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    
    return report
