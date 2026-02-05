"""
Trading Noobs Backend - LLM Service for Weekly Reports
"""
import httpx
import json
from typing import Optional, List, Dict, Any
from datetime import date, timedelta
from sqlalchemy.orm import Session

from models import Trade, TradeStatus, UserSettings, WeeklyReport, SystemSetting


MUNGER_PROMPT = """你是一位投资分析师，精通查理·芒格的投资哲学。请根据以下一周的交易记录，生成交易洞察报告。

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

ASSET_CLASSIFICATION_PROMPT = """Role: Financial Asset Classifier
Task: Classify the given financial symbol into exactly one of the following categories.

Categories:
- EQUITY: Individual stocks (e.g., AAPL, TSLA) or indices.
- ETF_EQUITY: Equity-based ETFs (e.g., SPY, QQQ, XLF).
- ETF_BOND: Fixed income/Bond ETFs (e.g., TLT, AGG, HYG).
- ETF_COMMODITY: Commodity-based ETFs or trusts (e.g., GLD, SLV, USO).
- CRYPTO: Cryptocurrencies (e.g., BTC, ETH, SOL).
- FOREX: Currency pairs (e.g., EURUSD).

Input Symbol: {symbol}
Exchange: {exchange}

Output Format: JSON only, strictly complying with the schema: {"type": "CATEGORY_CODE", "name": "Short Descriptive Name"}

Rules:
1. Do not explain. Return ONLY JSON.
2. If unsure or symbol implies mixed assets, choose the dominant asset class.
"""

RICH_ASSET_CLASSIFICATION_PROMPT = """Role: Multi-dimensional Financial Asset Classifier
Task: Extract rich metadata for the given financial ticker/symbol.

Input:
Symbol: {symbol}
Name: {name}
Exchange: {exchange}

Output Format: JSON only.
Schema:
{{
  "core_type": "STOCK|BOND|FUND|COMMODITY|FX|DERIVATIVE|CRYPTO",
  "market": "US|HK|A_SHARE|CN_OTC|FOREX|COMMODITY_FUT|UK|CRYPTO",
  "currency": "USD|HKD|CNY|EUR|GBP",
  "risk_level": "CONSERVATIVE|MODERATE|GROWTH|AGGRESSIVE|HEDGE",
  "sector": "Sector or Theme (e.g., Technology, AI, Finance)",
  "instrument": "Spot|ETF|Future|Option|Bond|Index"
}}

Mappings for Reference:
- core_type: STOCK(股票), BOND(债券), FUND(基金), COMMODITY(大宗商品), FX(外汇), DERIVATIVE(衍生品), CRYPTO(加密货币)
- market: US(美股), HK(港股), A_SHARE(A股), CN_OTC(中国场外), FOREX(外汇市场), COMMODITY_FUT(商品期货), UK(英股), CRYPTO(加密货币市场)
- risk_level: CONSERVATIVE(保守), MODERATE(稳健), GROWTH(成长), AGGRESSIVE(激进), HEDGE(避险)

Rules:
1. Be financially accurate.
2. Return ONLY clean JSON. No markdown blocks.
3. If unsure about sector, use "General".
"""


async def classify_asset_rich(db: Session, symbol: str, name: Optional[str] = None, exchange: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Classify asset with rich multi-dimensional metadata using LLM"""
    # Get system settings for LLM 
    llm_api_url_setting = db.query(SystemSetting).filter(SystemSetting.key == 'llm_api_url').first()
    llm_api_key_setting = db.query(SystemSetting).filter(SystemSetting.key == 'llm_api_key').first()
    llm_model_setting = db.query(SystemSetting).filter(SystemSetting.key == 'llm_model').first()
    
    llm_api_url = llm_api_url_setting.value if llm_api_url_setting else None
    llm_api_key = llm_api_key_setting.value if llm_api_key_setting else None
    llm_model = llm_model_setting.value if llm_model_setting else "gpt-4"

    if not llm_api_url or not llm_api_key:
        return None
    
    prompt = RICH_ASSET_CLASSIFICATION_PROMPT.format(
        symbol=symbol, 
        name=name or "Unknown", 
        exchange=exchange or "Unknown"
    )
    
    api_endpoint = llm_api_url.strip().rstrip('/')
    if not api_endpoint.endswith('/chat/completions'):
        api_endpoint = f"{api_endpoint}/chat/completions"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                api_endpoint,
                headers={
                    "Authorization": f"Bearer {llm_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": llm_model,
                    "messages": [
                        {"role": "system", "content": "You are a professional financial data expert. Return ONLY JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.0,
                    "max_tokens": 300
                }
            )
            response.raise_for_status()
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            
            # Clean markdown code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            return json.loads(content.strip())
            
    except Exception as e:
        print(f"Rich LLM Classification failed for {symbol}: {str(e)}")
        return None



async def classify_asset(db: Session, symbol: str, exchange: Optional[str] = None) -> Optional[Dict[str, str]]:
    """Classify asset type using LLM"""
    # Get system settings for LLM
    llm_api_url_setting = db.query(SystemSetting).filter(SystemSetting.key == 'llm_api_url').first()
    llm_api_key_setting = db.query(SystemSetting).filter(SystemSetting.key == 'llm_api_key').first()
    llm_model_setting = db.query(SystemSetting).filter(SystemSetting.key == 'llm_model').first()
    
    llm_api_url = llm_api_url_setting.value if llm_api_url_setting else None
    llm_api_key = llm_api_key_setting.value if llm_api_key_setting else None
    llm_model = llm_model_setting.value if llm_model_setting else "gpt-4"

    if not llm_api_url or not llm_api_key:
        return None
    
    prompt = ASSET_CLASSIFICATION_PROMPT.format(symbol=symbol, exchange=exchange or "Unknown")
    
    # Construct API endpoint
    api_endpoint = llm_api_url.strip().rstrip('/')
    if not api_endpoint.endswith('/chat/completions'):
        api_endpoint = f"{api_endpoint}/chat/completions"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                api_endpoint,
                headers={
                    "Authorization": f"Bearer {llm_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": llm_model,
                    "messages": [
                        {"role": "system", "content": "You are a financial data expert."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.1,
                    "max_tokens": 100
                }
            )
            response.raise_for_status()
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            
            # Clean markdown code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            return json.loads(content.strip())
            
    except Exception as e:
        print(f"LLM Classification failed: {str(e)}")
        return None


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
    # Get system settings for LLM
    llm_api_url_setting = db.query(SystemSetting).filter(SystemSetting.key == 'llm_api_url').first()
    llm_api_key_setting = db.query(SystemSetting).filter(SystemSetting.key == 'llm_api_key').first()
    llm_model_setting = db.query(SystemSetting).filter(SystemSetting.key == 'llm_model').first()
    
    llm_api_url = llm_api_url_setting.value if llm_api_url_setting else None
    llm_api_key = llm_api_key_setting.value if llm_api_key_setting else None
    llm_model = llm_model_setting.value if llm_model_setting else "gpt-4"

    if not llm_api_url or not llm_api_key:
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
    
    # Construct API endpoint
    api_endpoint = llm_api_url.strip().rstrip('/')
    if not api_endpoint.endswith('/chat/completions'):
        api_endpoint = f"{api_endpoint}/chat/completions"

    # Call LLM API (OpenAI format)
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                api_endpoint,
                headers={
                    "Authorization": f"Bearer {llm_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": llm_model,
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
