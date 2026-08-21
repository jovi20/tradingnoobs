"""
Trading Noobs Backend - LLM Service for Weekly Reports
"""
import httpx
import json
import os
from typing import Optional, List, Dict, Any
from datetime import date
from sqlalchemy.orm import Session

from models import WeeklyReport, SystemSetting, TradeBatch, Position, BatchType


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
    
    llm_api_url = llm_api_url_setting.value if llm_api_url_setting else os.getenv("LLM_API_URL")
    llm_api_key = llm_api_key_setting.value if llm_api_key_setting else os.getenv("LLM_API_KEY")
    llm_model = llm_model_setting.value if llm_model_setting else (os.getenv("LLM_MODEL") or "gpt-4")

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
    
    llm_api_url = llm_api_url_setting.value if llm_api_url_setting else os.getenv("LLM_API_URL")
    llm_api_key = llm_api_key_setting.value if llm_api_key_setting else os.getenv("LLM_API_KEY")
    llm_model = llm_model_setting.value if llm_model_setting else (os.getenv("LLM_MODEL") or "gpt-4")

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


def format_trades_for_llm(batches: List[TradeBatch]) -> str:
    """Format trade batches (transactions) for LLM prompt"""
    if not batches:
        return "本周无交易记录"
    
    lines = []
    for i, batch in enumerate(batches, 1):
        # Access relationship to get symbol/position info
        # Note: batch.position should be available if joined or lazy loaded
        position = batch.position
        symbol = position.symbol if position else "Unknown"
        exchange = position.exchange if position else "Unknown"
        
        type_str = "建仓/加仓" if batch.type == BatchType.ENTRY else "平仓/减仓"

        lines.append(f"""
交易 {i}:
- 时间: {batch.time.strftime('%Y-%m-%d %H:%M')}
- 标的: {symbol} ({exchange})
- 动作: {type_str}
- 价格: {batch.price}
- 数量: {batch.quantity}
{f'- 产生的盈亏: {batch.pnl}' if batch.pnl is not None else ''}
- 理由: {batch.reason or '未填写'}
- 情绪: {batch.emotion or '未填写'}
- 信心: {batch.confidence or '未填写'}/5
""")
        
        # If this is an exit and position is closed, maybe add position review?
        # For now, keep it simple to individual actions.

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
    
    llm_api_url = llm_api_url_setting.value if llm_api_url_setting else os.getenv("LLM_API_URL")
    llm_api_key = llm_api_key_setting.value if llm_api_key_setting else os.getenv("LLM_API_KEY")
    llm_model = llm_model_setting.value if llm_model_setting else (os.getenv("LLM_MODEL") or "gpt-4")

    if not llm_api_url or not llm_api_key:
        return None
    
    # Get trade batches for the week
    batches = db.query(TradeBatch).join(Position).filter(
        Position.user_id == user_id,
        TradeBatch.time >= week_start,
        TradeBatch.time <= week_end
    ).order_by(TradeBatch.time).all()
    
    # Format trades for LLM
    trades_data = format_trades_for_llm(batches)
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


JOURNAL_SUMMARY_PROMPT = """你是一位专业的交易心理与仓位管理顾问。请根据用户本周的随笔记录和持仓变动情况，生成一份简洁的周度总结。

## 本周随笔
{journal_entries}

## 本周持仓变动
{position_changes}

## 请从以下两个维度进行分析总结：

### 📊 仓位管理
分析用户的加仓、减仓、建仓、平仓决策是否合理，是否有过度交易、追涨杀跌等问题。

### 🧠 交易心态
从随笔中分析用户的情绪状态、决策心理，是否有恐惧、贪婪、焦虑等影响交易的情绪。

### 💡 本周建议
给出 2-3 条具体可执行的改进建议。

请用中文回答，保持简洁专业。
"""


async def generate_journal_summary(
    db: Session,
    user_id: int,
    week_start: date,
    week_end: date
) -> Optional[str]:
    """Generate weekly journal summary using LLM"""
    from models import JournalEntry, Position, TradeBatch
    
    # Get system settings for LLM
    llm_api_url_setting = db.query(SystemSetting).filter(SystemSetting.key == 'llm_api_url').first()
    llm_api_key_setting = db.query(SystemSetting).filter(SystemSetting.key == 'llm_api_key').first()
    llm_model_setting = db.query(SystemSetting).filter(SystemSetting.key == 'llm_model').first()
    
    llm_api_url = llm_api_url_setting.value if llm_api_url_setting else os.getenv("LLM_API_URL")
    llm_api_key = llm_api_key_setting.value if llm_api_key_setting else os.getenv("LLM_API_KEY")
    llm_model = llm_model_setting.value if llm_model_setting else (os.getenv("LLM_MODEL") or "gpt-4")

    if not llm_api_url or not llm_api_key:
        raise Exception("LLM API 未配置，请联系管理员")
    
    # Get journal entries for the week
    journal_entries = db.query(JournalEntry).filter(
        JournalEntry.user_id == user_id,
        JournalEntry.date >= week_start,
        JournalEntry.date <= week_end
    ).order_by(JournalEntry.date, JournalEntry.created_at).all()
    
    # Format journal entries
    if journal_entries:
        journal_text = "\n".join([
            f"[{entry.date}] {entry.content}"
            for entry in journal_entries
        ])
    else:
        journal_text = "本周无随笔记录"
    
    # Get position changes (batches) for the week
    batches = db.query(TradeBatch).join(Position).filter(
        Position.user_id == user_id,
        TradeBatch.time >= week_start,
        TradeBatch.time <= week_end
    ).all()
    
    # Format position changes
    if batches:
        position_lines = []
        for batch in batches:
            position = db.query(Position).filter(Position.id == batch.position_id).first()
            action = "建仓/加仓" if batch.type.value == "ENTRY" else "平仓/减仓"
            pnl_str = f"，盈亏: {batch.pnl}" if batch.pnl else ""
            position_lines.append(
                f"[{batch.time.strftime('%Y-%m-%d')}] {position.symbol} {action} {batch.quantity}股 @ ${batch.price}{pnl_str}"
            )
        position_text = "\n".join(position_lines)
    else:
        position_text = "本周无持仓变动"
    
    prompt = JOURNAL_SUMMARY_PROMPT.format(
        journal_entries=journal_text,
        position_changes=position_text
    )
    
    # Construct API endpoint
    api_endpoint = llm_api_url.strip().rstrip('/')
    if not api_endpoint.endswith('/chat/completions'):
        api_endpoint = f"{api_endpoint}/chat/completions"

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
                        {"role": "system", "content": "你是一位专业的交易心理与仓位管理顾问。"},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 1500
                }
            )
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]
    except Exception as e:
        raise Exception(f"LLM API 调用失败: {str(e)}")


ANALYSIS_PROMPT_TEMPLATE = """你是一位资深的交易绩效教练。请分析以下交易统计数据并提供可操作的建议。

分析类型: {analysis_type}
数据:
{data}

请使用 **中文** 回答，输出格式为 Markdown，包含以下部分：
1. **🔍 深度诊断**: 数据反映了交易者的什么行为模式？
2. **💡 核心洞察**: 一个最重要的发现。
3. **🚀 改进建议**: 2-3 条具体的改进措施。

保持专业、鼓励性，并基于数据说话。
"""

async def get_analysis_insight(
    db: Session,
    analysis_type: str,
    data: Dict[str, Any]
) -> Optional[str]:
    """Generate insight for advanced analytics using LLM"""
    
    # Get system settings for LLM
    llm_api_url_setting = db.query(SystemSetting).filter(SystemSetting.key == 'llm_api_url').first()
    llm_api_key_setting = db.query(SystemSetting).filter(SystemSetting.key == 'llm_api_key').first()
    llm_model_setting = db.query(SystemSetting).filter(SystemSetting.key == 'llm_model').first()
    
    llm_api_url = llm_api_url_setting.value if llm_api_url_setting else os.getenv("LLM_API_URL")
    llm_api_key = llm_api_key_setting.value if llm_api_key_setting else os.getenv("LLM_API_KEY")
    llm_model = llm_model_setting.value if llm_model_setting else (os.getenv("LLM_MODEL") or "gpt-4")

    if not llm_api_url or not llm_api_key:
        return "LLM not configured."
    
    # Format data for prompt
    data_str = json.dumps(data, indent=2, ensure_ascii=False, default=str)
    
    prompt = ANALYSIS_PROMPT_TEMPLATE.format(
        analysis_type=analysis_type,
        data=data_str
    )
    
    # Construct API endpoint
    api_endpoint = llm_api_url.strip().rstrip('/')
    if not api_endpoint.endswith('/chat/completions'):
        api_endpoint = f"{api_endpoint}/chat/completions"

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
                        {"role": "system", "content": "You are a professional trading coach."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 1000
                }
            )
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Failed to generate insight: {str(e)}"
