"""
Trading Noobs Backend - Dashboard Router
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from datetime import date, timedelta

from database import get_db
from models import Trade, TradeStatus, User, Position, PositionStatus, TradingAccount, TradeBatch, BatchType, UserSettings
from schemas import DashboardStats, AssetAllocation, PositionMover, AccountAllocation, PortfolioFlow, SankeyNode, SankeyLink
from services.auth_service import get_current_user
from services.market_data_service import MarketDataService
from services.exchange_rate_service import get_exchange_rate, get_rates_batch
import asyncio
from models import DailySnapshot
from services.metrics_service import MetricsService

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get dashboard statistics"""
    # === 读取用户显示币种设置 ===
    user_settings = db.query(UserSettings).filter(UserSettings.user_id == current_user.id).first()
    display_currency = (user_settings.display_currency if user_settings and user_settings.display_currency else 'USD').upper()

    # Use Position table instead of Trade table (Legacy)
    query = db.query(Position).filter(Position.user_id == current_user.id)
    
    if start_date:
        query = query.filter(Position.opened_at >= start_date)
    if end_date:
        query = query.filter(Position.opened_at <= end_date)
    
    # Calculate stats using TradeBatch for more granular performance metrics
    # Win Rate and PnL Ratio should reflect every EXIT event (partial or full)
    batch_stats = db.query(
        func.count(TradeBatch.id).label("total_exits"),
        func.count(TradeBatch.id).filter(TradeBatch.pnl > 0).label("winning_exits"),
        func.sum(TradeBatch.pnl).filter(TradeBatch.pnl > 0).label("total_wins"),
        func.sum(func.abs(TradeBatch.pnl)).filter(TradeBatch.pnl < 0).label("total_losses")
    ).join(Position).filter(
        Position.user_id == current_user.id,
        TradeBatch.type == BatchType.EXIT
    )
    
    if start_date:
        batch_stats = batch_stats.filter(TradeBatch.time >= start_date)
    if end_date:
        batch_stats = batch_stats.filter(TradeBatch.time <= end_date)
        
    bs = batch_stats.one()
    
    total_exits = bs.total_exits or 0
    winning_exits = bs.winning_exits or 0
    total_wins = float(bs.total_wins or 0)
    total_losses = float(bs.total_losses or 0)
    
    # Position counts for context
    pos_stats = db.query(
        func.count(Position.id).label("total_trades"),
        func.sum(Position.realized_pnl).label("total_pnl"),
        func.count(Position.id).filter(Position.status == PositionStatus.CLOSED).label("closed_trades"),
        func.count(Position.id).filter(Position.status == PositionStatus.OPEN).label("open_positions")
    ).filter(Position.user_id == current_user.id)
    
    if start_date:
        pos_stats = pos_stats.filter(Position.opened_at >= start_date)
    if end_date:
        pos_stats = pos_stats.filter(Position.opened_at <= end_date)
        
    ps = pos_stats.one()
    
    total_trades = ps.total_trades or 0
    total_pnl = float(ps.total_pnl or 0)
    closed_trades_count = ps.closed_trades or 0
    open_positions_count = ps.open_positions or 0
    
    # Calculate performance metrics
    win_rate = (winning_exits / total_exits * 100) if total_exits > 0 else 0.0
    avg_pnl_ratio = (total_wins / total_losses) if total_losses > 0 else 0.0
    
    # --- New Logic: Asset & Account Allocation Corrected ---
    # 1. Get all OPEN positions for real-time valuation
    positions = db.query(Position).filter(
        Position.user_id == current_user.id,
        Position.status == PositionStatus.OPEN
    ).all()
    
    # 2. Get Trading Accounts
    accounts = db.query(TradingAccount).filter(
        TradingAccount.user_id == current_user.id,
        TradingAccount.is_active == True
    ).all()

    # === 预获取所有需要的汇率 ===
    all_currencies = set()
    for acc in accounts:
        all_currencies.add((acc.currency or 'USD').upper())
    # 汇率表: { "USD": 1.0, "HKD": 0.128, ... } 到 display_currency
    fx_rates = await get_rates_batch(list(all_currencies), display_currency)

    # 3. Calculate Total Realized PnL per Account (from ALL positions, open & closed)
    # We need this to adjust the "Cash" balance
    realized_pnl_query = db.query(
        Position.account_id,
        func.sum(Position.realized_pnl).label('total_realized')
    ).filter(
        Position.user_id == current_user.id,
        Position.account_id.isnot(None)
    ).group_by(Position.account_id).all()
    
    realized_pnl_map = {res.account_id: float(res.total_realized or 0) for res in realized_pnl_query}
    
    # 4. Fetch Market Data (Quotes & Asset Metadata)
    market_service = MarketDataService(db)
    
    # Parallelize metadata retrieval & quote fetching
    # Note: We only need this for OPEN positions to determine current market value
    metadata_tasks = [market_service.get_or_create_asset_metadata(p.symbol, exchange=p.exchange) for p in positions]
    quote_tasks = [market_service.get_quote(p.symbol, p.exchange) for p in positions]
    
    results = await asyncio.gather(*(metadata_tasks + quote_tasks), return_exceptions=True)
    num_pos = len(positions)
    metadata_results = results[:num_pos]
    quotes_results = results[num_pos:]
    
    # === 补充标的原生币种到汇率表 (metadata 获取后) ===
    asset_currencies_needed = set()
    for m in metadata_results:
        if not isinstance(m, Exception) and m and m.currency:
            c = m.currency.value.upper()
            if c not in fx_rates:
                asset_currencies_needed.add(c)
    if asset_currencies_needed:
        extra_rates = await get_rates_batch(list(asset_currencies_needed), display_currency)
        fx_rates.update(extra_rates)
    
    # Data Containers for multi-dimensional allocation
    core_type_map = {'CASH': 0.0}
    market_map = {'CASH': 0.0}
    risk_level_map = {'CASH': 0.0}
    
    movers_list = []
    
    # Account Stats: { acc_id: { initial, realized, unrealized, cost_basis, market_value, obj, fx_rate } }
    account_stats = {}
    for acc in accounts:
        # Use cash_balance if available, else fallback logic
        current_cash = float(acc.cash_balance or 0)
        acc_currency = (acc.currency or 'USD').upper()
        acc_fx_rate = fx_rates.get(acc_currency, 1.0)
        account_stats[acc.id] = {
            'initial': float(acc.initial_balance or 0),
            'cash_balance': current_cash,
            'realized': realized_pnl_map.get(acc.id, 0.0),
            'unrealized': 0.0,
            'cost_basis': 0.0,
            'market_value': 0.0,
            'obj': acc,
            'fx_rate': acc_fx_rate,  # 该账户币种到显示币种的汇率
            'currency': acc_currency
        }
    
    # Process Open Positions
    for i, pos in enumerate(positions):
        metadata = metadata_results[i]
        quote = quotes_results[i]
        
        # Handle exceptions in async results
        if isinstance(metadata, Exception): metadata = None
        
        core_type = metadata.core_type.value if (metadata and metadata.core_type) else "EQUITY"
        market = metadata.market.value if (metadata and metadata.market) else "UNKNOWN"
        risk_level = metadata.risk_level.value if (metadata and metadata.risk_level) else "MODERATE"
        
        # 获取该标的的原始币种（从 metadata 或所属账户）
        asset_currency = (metadata.currency.value if (metadata and metadata.currency) else None)
        if not asset_currency and pos.account_id in account_stats:
            asset_currency = account_stats[pos.account_id]['currency']
        asset_currency = (asset_currency or 'USD').upper()
        pos_fx_rate = fx_rates.get(asset_currency, 1.0)
        
        # determine price (原生币种价格)
        entry_price = float(pos.average_entry_price or 0)
        current_price = entry_price # fallback
        change_pct = 0.0
        
        if not isinstance(quote, Exception) and quote and quote.get('c'):
            current_price = float(quote['c'])
            if entry_price > 0:
                change_pct = ((current_price - entry_price) / entry_price) * 100
                if pos.direction == 'SHORT':
                    change_pct = -change_pct
        
        # Calculate Position Metrics (原生币种)
        qty = float(pos.total_quantity)
        market_value_native = qty * current_price
        cost_basis_native = qty * entry_price
        unrealized_pnl_native = market_value_native - cost_basis_native
        if pos.direction == 'SHORT':
             unrealized_pnl_native = (entry_price - current_price) * qty
             market_value_native = abs(market_value_native)

        # 换算到显示币种用于图表汇总
        market_value_display = market_value_native * pos_fx_rate
        unrealized_pnl_display = unrealized_pnl_native * pos_fx_rate

        # Update Allocations (使用换算后的值)
        core_type_map[core_type] = core_type_map.get(core_type, 0.0) + market_value_display
        market_map[market] = market_map.get(market, 0.0) + market_value_display
        risk_level_map[risk_level] = risk_level_map.get(risk_level, 0.0) + market_value_display
        
        # Update Movers (保持原生币种价格，不受显示币种影响)
        movers_list.append(PositionMover(
            id=pos.id,
            symbol=pos.symbol,
            asset_type=core_type,
            currency=asset_currency,  # 标的原生币种
            change_percent=round(change_pct, 2),
            current_price=current_price  # 原生价格
        ))
        
        # Accumulate to Account Stats (换算后)
        if pos.account_id in account_stats:
            stats = account_stats[pos.account_id]
            stats['unrealized'] += unrealized_pnl_display
            stats['unrealized_total'] = stats.get('unrealized_total', 0.0) + unrealized_pnl_display
            stats['market_value'] += market_value_display # Accumulate market value of holdings (换算后)

    # Final Aggregation & List Building
    total_portfolio_value = 0.0
    account_allocation = []
    
    for acc_id, stats in account_stats.items():
        acc_obj = stats['obj']
        acc_fx = stats['fx_rate']
        # Cash 也需要换算到显示币种
        cash_display = stats['cash_balance'] * acc_fx
        nav = stats['market_value'] + cash_display  # 换算后的 Market Value + Cash
        
        total_portfolio_value += nav
        account_allocation.append(AccountAllocation(
            name=stats['obj'].name,
            broker=stats['obj'].broker,
            value=nav,
            percent=0.0 
        ))

    # Calculate Cash component for Allocations (换算后)
    global_cash = sum(s['cash_balance'] * s['fx_rate'] for s in account_stats.values())
    
    core_type_map['CASH'] = global_cash
    market_map['CASH'] = global_cash
    risk_level_map['CASH'] = global_cash
    
    # Helper to build allocation list
    def build_allocation_list(m, total):
        res = []
        if total > 0:
            for k, v in m.items():
                if v > 0:
                    res.append(AssetAllocation(name=k, value=v, percent=round((v / total) * 100, 2)))
        return res

    core_allocation = build_allocation_list(core_type_map, total_portfolio_value)
    market_allocation = build_allocation_list(market_map, total_portfolio_value)
    risk_allocation = build_allocation_list(risk_level_map, total_portfolio_value)
    
    # Finalize Account Allocation List
    if total_portfolio_value > 0:
        account_allocation.sort(key=lambda x: x.value, reverse=True)
        for acc in account_allocation:
            acc.percent = round((acc.value / total_portfolio_value) * 100, 2)
            
    # Movers Sorting
    # Top Movers: Strict Positive (> 0), Sorted Descending
    top_movers = sorted(
        [m for m in movers_list if m.change_percent > 0], 
        key=lambda x: x.change_percent, 
        reverse=True
    )[:5]
    
    # Bottom Movers: Strict Negative (< 0), Sorted Ascending (Most negative first)
    bottom_movers = sorted(
        [m for m in movers_list if m.change_percent < 0], 
        key=lambda x: x.change_percent
    )[:5]

    # --- Sankey Chart Logic (Centered Total Assets Model) ---
    # Col 0: [Equity], [Liabilities]
    # Col 1: [Accounts]
    # Col 2: [Total Assets] (Center)
    # Col 3: [Categories]
    # Col 4: [Symbols]

    sankey_nodes = []
    sankey_links = []
    node_indices = {} # name -> index
    
    def get_node_index(name):
        if name not in node_indices:
            node_indices[name] = len(sankey_nodes)
            sankey_nodes.append({"name": name})
        return node_indices[name]

    # Names
    SRC_EQUITY = "Net Equity" # Unused now but kept for ref
    SRC_LIABS = "Liabilities"
    CENTER_NODE = "Total Assets" # Gross

    # Containers
    flows_l0 = {} # Sources -> Accounts
    flows_l1 = {} # Accounts -> Total Assets
    flows_l2 = {} # Total Assets -> Categories
    flows_l3 = {} # Categories -> Symbols
    
    # Global Aggregates
    cat_holdings = {} # { "Category": { "Symbol": Val } }
    total_gross = 0.0
    
    # Temp storage for Two-Pass Construction
    acc_calc_data = {} 

    # PASS 1: Calculate Metrics & Category Flows
    for acc_id, stats in account_stats.items():
        acc_obj = stats['obj']
        acc_name = acc_obj.name
        
        # 1. Calc Gross Assets & Liabilities per Account
        acc_longs = 0.0
        acc_shorts = 0.0
        
        for i, pos in enumerate(positions):
            if pos.account_id == acc_id:
                quote = quotes_results[i]
                price = (float(quote['c']) if (quote and not isinstance(quote, Exception) and quote.get('c')) 
                         else float(pos.average_entry_price or 0))
                mkt_val = float(pos.total_quantity) * price
                
                # 获取该标的币种的汇率用于 Sankey 换算
                metadata = metadata_results[i]
                if isinstance(metadata, Exception): metadata = None
                asset_type = metadata.core_type.value if (metadata and metadata.core_type) else "EQUITY"
                asset_cat_name = f"{asset_type}"
                asset_cur = (metadata.currency.value if (metadata and metadata.currency) else stats['currency'])
                pos_fx = fx_rates.get(asset_cur, 1.0)
                mkt_val_display = mkt_val * pos_fx  # 换算到显示币种
                
                if pos.direction == 'LONG':
                    val = mkt_val_display
                    acc_longs += val
                    if asset_cat_name not in cat_holdings: cat_holdings[asset_cat_name] = {}
                    sym_name = f"{pos.symbol} (Long)"
                    cat_holdings[asset_cat_name][sym_name] = cat_holdings[asset_cat_name].get(sym_name, 0.0) + val
                else:
                    val = abs(mkt_val_display)
                    acc_shorts += val
                    if asset_cat_name not in cat_holdings: cat_holdings[asset_cat_name] = {}
                    sym_name = f"{pos.symbol} (Short)"
                    cat_holdings[asset_cat_name][sym_name] = cat_holdings[asset_cat_name].get(sym_name, 0.0) + val

        # Cash & Margin (换算到显示币种)
        acc_fx = stats['fx_rate']
        derived_cash = stats['cash_balance'] * acc_fx
        
        acc_cash_asset = 0.0
        acc_margin_liab = 0.0
        
        if derived_cash >= 0:
            acc_cash_asset = derived_cash
            cash_cat = "Cash (Asset)"
            if cash_cat not in cat_holdings: cat_holdings[cash_cat] = {}
            cat_holdings[cash_cat]["Cash"] = cat_holdings[cash_cat].get("Cash", 0.0) + acc_cash_asset
        else:
            acc_margin_liab = abs(derived_cash)
            
        acc_gross_assets = acc_longs + acc_cash_asset + acc_shorts
        acc_total_liabs = acc_shorts + acc_margin_liab
        acc_equity_flow = acc_gross_assets - acc_total_liabs
        
        # Store for Pass 2
        acc_calc_data[acc_name] = {
            'liabs': acc_total_liabs,
            'equity': acc_equity_flow,
            'gross': acc_gross_assets
        }

        total_gross += acc_gross_assets
            
        # Persistence
        try:
            acc_obj.total_assets = acc_gross_assets
            acc_obj.total_liabilities = acc_total_liabs
            db.add(acc_obj)
        except:
            pass

    # PASS 2: Pre-register Nodes (Sorted & Filtered) & Build Links
    # This prevents zero-value nodes (e.g. "Liabilities $0") from appearing
    # while maintaining strict visual ordering.
    sorted_accounts = sorted(account_stats.values(), key=lambda x: x['obj'].name)
    
    for stat in sorted_accounts:
        acc_name = stat['obj'].name
        data = acc_calc_data.get(acc_name, {})
        
        liabs = data.get('liabs', 0)
        equity = data.get('equity', 0)
        gross = data.get('gross', 0)
        
        # Only register if > 1 to avoid "$0" nodes
        if liabs > 1: get_node_index(f"{acc_name} 负债")
        if equity > 1: get_node_index(f"{acc_name} 净值")
        if gross > 1:
             get_node_index(acc_name)
             
             # Build Links Here to maintain order in link array too
             if liabs > 1:
                 flows_l0[(f"{acc_name} 负债", acc_name)] = liabs
             if equity > 1:
                 flows_l0[(f"{acc_name} 净值", acc_name)] = equity
             
             flows_l1[(acc_name, CENTER_NODE)] = gross
             
    get_node_index(CENTER_NODE)

            
    try:
        db.commit()
    except:
        db.rollback()

    # L2: Total Assets -> Categories
    for cat, symbols in cat_holdings.items():
        cat_total = sum(symbols.values())
        if cat_total > 1:
            flows_l2[(CENTER_NODE, cat)] = cat_total
            
    # L3: Categories -> Symbols
    for cat, symbols in cat_holdings.items():
        cat_total = sum(symbols.values())
        if cat_total < 1: continue
        
        # Improve: Increase threshold to 2.5% to reduce noise
        threshold = cat_total * 0.025
        others = 0.0
        
        # Sort symbols by value descending for better visualization
        sorted_symbols = sorted(symbols.items(), key=lambda item: item[1], reverse=True)
        
        for sym, val in sorted_symbols:
            if val < 1: continue
            
            # Keep massive positions or Cash separate
            if (val >= threshold) or (sym == "Cash"):
                flows_l3[(cat, sym)] = val
            else:
                others += val
                
        if others > 0:
            flows_l3[(cat, "Others")] = others

    # Combine
    all_flows = {**flows_l0, **flows_l1, **flows_l2, **flows_l3}
    
    for (src, tgt), val in all_flows.items():
        if val > 0.1:
            sankey_links.append({
                "source": get_node_index(src),
                "target": get_node_index(tgt),
                "value": round(val, 2)
            })

    # Record Daily Snapshot (Async Background or Implicit)
    # Since this is a stats calculation, we can record a snapshot for today
    try:
        if current_user and total_portfolio_value > 0:
            today = date.today()
            existing = db.query(DailySnapshot).filter(
                DailySnapshot.user_id == current_user.id,
                DailySnapshot.date == today
            ).first()
            
            # Calculate metrics for snapshot
            # Total Assets = total_gross (calculated in PASS 1)
            # Total Liabilities = sum(liabs in acc_calc_data)
            # Total Equity = Total Assets - Total Liabilities (or total_portfolio_value)
            
            calc_equity = sum(d.get('equity', 0) for d in acc_calc_data.values())
            calc_liabs = sum(d.get('liabs', 0) for d in acc_calc_data.values())
            calc_assets = sum(d.get('gross', 0) for d in acc_calc_data.values())
            
            # Fallback if calc logic differs slightly from total_portfolio_value
            # Ideally total_portfolio_value (NAV) is the Equity
            
            if not existing:
                snapshot = DailySnapshot(
                    user_id=current_user.id,
                    date=today,
                    total_equity=total_portfolio_value,
                    total_assets=calc_assets,
                    total_liabilities=calc_liabs,
                    net_transfers=0 # TODO: Track transfers
                )
                db.add(snapshot)
            else:
                existing.total_equity = total_portfolio_value
                existing.total_assets = calc_assets
                existing.total_liabilities = calc_liabs
                existing.updated_at = func.now()
            
            db.commit()
    except Exception as e:
        print(f"Snapshot recording failed: {e}")
        # Don't block main response

    # Calculate Total Portfolio PnL (Realized + Unrealized) — 换算到显示币种
    total_unrealized = sum(s.get('unrealized_total', 0.0) for s in account_stats.values())
    # realized PnL 也需根据各账户币种换算
    total_realized_display = sum(
        realized_pnl_map.get(aid, 0.0) * stats['fx_rate']
        for aid, stats in account_stats.items()
    )
    combined_total_pnl = total_realized_display + total_unrealized

    # Calculate Risk Metrics (Sharpe, Sortino, Calmar, MaxDD)
    sharpe_ratio = None
    sortino_ratio = None
    calmar_ratio = None
    max_drawdown = None
    
    # Fetch full history of snapshots for metrics
    # We need a decent history to calculate these, e.g. all time or last year
    # Let's use all available history for "Account Stats"
    all_snapshots = db.query(DailySnapshot).filter(
        DailySnapshot.user_id == current_user.id
    ).order_by(DailySnapshot.date).all()
    
    if len(all_snapshots) >= 2: # Minimal data requirement (lowered for visibility)
        equity_curve = [float(s.total_equity) for s in all_snapshots]
        
        # Add current real-time equity as the latest data point
        if total_portfolio_value > 0:
             equity_curve.append(total_portfolio_value)
             
        daily_returns = MetricsService.calculate_daily_returns(equity_curve)
        
        # Sharpe (Annualized)
        sharpe_ratio = MetricsService.calculate_sharpe_ratio(daily_returns)
        
        # Sortino (Annualized)
        sortino_ratio = MetricsService.calculate_sortino_ratio(daily_returns)
        
        # Max Drawdown
        max_drawdown = MetricsService.calculate_max_drawdown(equity_curve)
        
        # Calmar Ratio (Annualized Return / Max DD)
        # Calculate simple annualized return first
        if max_drawdown > 0 and len(equity_curve) > 1:
            days = (date.today() - all_snapshots[0].date).days
            if days > 0:
                # CAGR
                start_eq = float(all_snapshots[0].total_equity)
                end_eq = total_portfolio_value
                cagr = MetricsService.calculate_cagr(start_eq, end_eq, days)
                calmar_ratio = cagr / max_drawdown

    return DashboardStats(
        total_assets=total_gross,
        total_pnl=combined_total_pnl,
        win_rate=win_rate,
        avg_pnl_ratio=avg_pnl_ratio,
        total_trades=total_trades,
        open_positions=open_positions_count,
        closed_trades=closed_trades_count,
        asset_allocation=core_allocation, # Default compatibility
        core_type_allocation=core_allocation,
        market_allocation=market_allocation,
        risk_level_allocation=risk_allocation,
        account_allocation=account_allocation[:5],
        top_movers=top_movers,
        bottom_movers=bottom_movers,
        portfolio_flow={"nodes": sankey_nodes, "links": sankey_links},
        sharpe_ratio=sharpe_ratio,
        sortino_ratio=sortino_ratio,
        calmar_ratio=calmar_ratio,
        max_drawdown=max_drawdown
    )


@router.get("/pnl-history")
async def get_pnl_history(
    days: int = Query(30, ge=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get P&L history from Daily Snapshots"""
    # 1. Determine Date Range
    if days > 1000 and current_user.created_at:
        start_date = current_user.created_at.date()
    else:
        start_date = date.today() - timedelta(days=days)
        
    # 2. Fetch Snapshots
    snapshots = db.query(DailySnapshot).filter(
        DailySnapshot.user_id == current_user.id,
        DailySnapshot.date >= start_date
    ).order_by(DailySnapshot.date).all()
    
    # 3. Fetch Total Principal (Initial Balance) to calc PnL %
    # 注意: initial_balance 需要按账户币种换算到 display_currency
    user_settings = db.query(UserSettings).filter(UserSettings.user_id == current_user.id).first()
    display_currency = (user_settings.display_currency if user_settings and user_settings.display_currency else 'USD').upper()
    
    accounts = db.query(TradingAccount).filter(
        TradingAccount.user_id == current_user.id,
        TradingAccount.is_active == True
    ).all()
    
    # 各账户初始资金按各自币种换算到 display_currency 后求和
    acc_currencies = list(set((acc.currency or 'USD').upper() for acc in accounts))
    fx_rates = await get_rates_batch(acc_currencies, display_currency)
    current_principal = sum(
        float(acc.initial_balance or 0) * fx_rates.get((acc.currency or 'USD').upper(), 1.0)
        for acc in accounts
    )
    
    # 4. Build Series
    result = []
    
    # Map snapshots by date string
    snapshot_map = {s.date.isoformat(): float(s.total_equity) for s in snapshots}
    
    # Fill gaps (forward fill)
    current_date = start_date
    last_equity = current_principal # Default to principal if no snapshots yet
    today = date.today()
    
    while current_date <= today:
        date_str = current_date.isoformat()
        equity = snapshot_map.get(date_str)
        
        if equity is not None:
            last_equity = equity
        
        # Calculate PnL relative to principal
        # If no snapshots, equity will be 'current_principal', resulting in 0 PnL
        pnl_val = last_equity - current_principal
        pnl_pct = (pnl_val / current_principal * 100) if current_principal > 0 else 0
        
        result.append({
            "date": date_str,
            "pnl": round(pnl_val, 2),
            "pnl_percent": round(pnl_pct, 2),
            "total_equity": round(last_equity, 2)
        })
        
        current_date += timedelta(days=1)
        
    return result
