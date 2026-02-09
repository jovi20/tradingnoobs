"""
Trading Noobs Backend - Dashboard Router
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from datetime import date, timedelta

from database import get_db
from models import Trade, TradeStatus, User, Position, PositionStatus, TradingAccount, TradeBatch, BatchType
from schemas import DashboardStats, AssetAllocation, PositionMover, AccountAllocation, PortfolioFlow, SankeyNode, SankeyLink
from services.auth_service import get_current_user
from services.market_data_service import MarketDataService
import asyncio
from models import DailySnapshot

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get dashboard statistics"""
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
    
    # Data Containers for multi-dimensional allocation
    core_type_map = {'CASH': 0.0}
    market_map = {'CASH': 0.0}
    risk_level_map = {'CASH': 0.0}
    
    movers_list = []
    
    # Account Stats: { acc_id: { initial, realized, unrealized, cost_basis, market_value, obj } }
    account_stats = {}
    for acc in accounts:
        # Use cash_balance if available, else fallback logic
        current_cash = float(acc.cash_balance or 0)
        account_stats[acc.id] = {
            'initial': float(acc.initial_balance or 0),
            'cash_balance': current_cash,
            'realized': realized_pnl_map.get(acc.id, 0.0),
            'unrealized': 0.0,
            'cost_basis': 0.0,
            'market_value': 0.0,
            'obj': acc
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
        
        # determine price
        entry_price = float(pos.average_entry_price or 0)
        current_price = entry_price # fallback
        change_pct = 0.0
        
        if not isinstance(quote, Exception) and quote and quote.get('c'):
            current_price = float(quote['c'])
            if entry_price > 0:
                change_pct = ((current_price - entry_price) / entry_price) * 100
                if pos.direction == 'SHORT':
                    change_pct = -change_pct
        
        # Calculate Position Metrics
        qty = float(pos.total_quantity)
        market_value = qty * current_price
        cost_basis = qty * entry_price
        unrealized_pnl = market_value - cost_basis
        if pos.direction == 'SHORT':
             unrealized_pnl = (entry_price - current_price) * qty
             market_value = abs(market_value)

        # Update Allocations
        core_type_map[core_type] = core_type_map.get(core_type, 0.0) + market_value
        market_map[market] = market_map.get(market, 0.0) + market_value
        risk_level_map[risk_level] = risk_level_map.get(risk_level, 0.0) + market_value
        
        # Update Movers
        movers_list.append(PositionMover(
            id=pos.id,
            symbol=pos.symbol,
            asset_type=core_type,
            change_percent=round(change_pct, 2),
            current_price=current_price
        ))
        
        # Accumulate to Account Stats
        if pos.account_id in account_stats:
            stats = account_stats[pos.account_id]
            stats['unrealized'] += unrealized_pnl
            stats['unrealized_total'] = stats.get('unrealized_total', 0.0) + unrealized_pnl
            stats['market_value'] += market_value # Accumulate market value of holdings

    # Final Aggregation & List Building
    total_portfolio_value = 0.0
    account_allocation = []
    
    for acc_id, stats in account_stats.items():
        acc_obj = stats['obj']
        nav = stats['market_value'] + stats['cash_balance'] # Market Value of Positions + Cash
        
        total_portfolio_value += nav
        account_allocation.append(AccountAllocation(
            name=stats['obj'].name,
            broker=stats['obj'].broker,
            value=nav,
            percent=0.0 
        ))

    # Calculate Cash component for Allocations
    # Now we sum up explicit cash balances from accounts
    global_cash = sum(s['cash_balance'] for s in account_stats.values())
    
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
                
                metadata = metadata_results[i]
                if isinstance(metadata, Exception): metadata = None
                asset_type = metadata.core_type.value if (metadata and metadata.core_type) else "EQUITY"
                asset_cat_name = f"{asset_type}" 
                
                if pos.direction == 'LONG':
                    val = mkt_val
                    acc_longs += val
                    if asset_cat_name not in cat_holdings: cat_holdings[asset_cat_name] = {}
                    sym_name = f"{pos.symbol} (Long)"
                    cat_holdings[asset_cat_name][sym_name] = cat_holdings[asset_cat_name].get(sym_name, 0.0) + val
                else:
                    val = abs(mkt_val)
                    acc_shorts += val
                    if asset_cat_name not in cat_holdings: cat_holdings[asset_cat_name] = {}
                    sym_name = f"{pos.symbol} (Short)"
                    cat_holdings[asset_cat_name][sym_name] = cat_holdings[asset_cat_name].get(sym_name, 0.0) + val

        # Cash & Margin
        # Now using explicit cash_balance
        derived_cash = stats['cash_balance']
        
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
        
        threshold = cat_total * 0.01
        others = 0.0
        
        for sym, val in symbols.items():
            if val < 1: continue
            if val < threshold and sym != "Cash":
                others += val
            else:
                flows_l3[(cat, sym)] = val
                
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

    # Calculate Total Portfolio PnL (Realized + Unrealized)
    total_unrealized = sum(s.get('unrealized_total', 0.0) for s in account_stats.values())
    combined_total_pnl = total_pnl + total_unrealized

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
        portfolio_flow={"nodes": sankey_nodes, "links": sankey_links}
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
    # Note: If user deposits more, we should optimally use Time-Weighted Return
    # But for now, Simple Return on Current Principal is acceptable or Net Transfers adjusted
    accounts = db.query(TradingAccount).filter(
        TradingAccount.user_id == current_user.id,
        TradingAccount.is_active == True
    ).all()
    current_principal = sum(float(acc.initial_balance or 0) for acc in accounts)
    
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
