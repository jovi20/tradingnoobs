/**
 * Trading Noobs Frontend - API Client
 */

// Strips trailing /api if present to avoid double prefixing when concatenated with /api/ endpoints
const rawBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
export const API_BASE = rawBase.replace(/\/api$/, '')

// ============== Types ==============


export interface Strategy {
    id: number
    user_id: number
    name: string
    description?: string
    entry_rules?: string
    exit_rules?: string
    risk_rules?: string
    symbols: string[]
    status: 'ACTIVE' | 'PAUSED' | 'ARCHIVED'
    checklist_items?: ChecklistItem[]  // Phase 1: Pre-Trade Checklist
    created_at: string
    updated_at?: string
}

// Phase 1: Checklist item structure
export interface ChecklistItem {
    id: number
    label: string
    category?: 'entry' | 'risk' | 'exit' | 'other'
    required?: boolean
}

export interface StrategyCreate {
    name: string
    description?: string
    entry_rules?: string
    exit_rules?: string
    risk_rules?: string
    symbols?: string[]
    checklist_items?: ChecklistItem[]  // Phase 1: Pre-Trade Checklist
}

export interface UserSettings {
    id: number
    user_id: number
    theme: string
    up_color?: 'GREEN' | 'RED'
    display_currency?: 'USD' | 'HKD' | 'CNY' | 'EUR' | 'GBP'
    ibkr_host?: string
    ibkr_port?: number
    ibkr_client_id?: number
    binance_api_key?: string
    finnhub_api_key?: string
    llm_api_url?: string
    llm_model?: string
}

export interface WeeklyReport {
    id: number
    user_id: number
    week_start: string
    week_end: string
    trades_summary?: string
    munger_evaluation?: string
    suggestions?: string
    created_at: string
}

export type AnalysisType = 'holding_period' | 'losing_streak' | 'emotion_pnl' | 'checklist_effect' | 'strategy_health'

export interface AnalysisRequest {
    analysis_type: AnalysisType
    start_date?: string
    end_date?: string
}

export interface AnalysisResponse {
    analysis_type: AnalysisType
    raw_data: any
    ai_insights?: string
    created_at: string
}

export interface AssetAllocation {
    name: string
    value: number
    percent: number
}

export interface PositionMover {
    id: number
    symbol: string
    asset_type?: string
    currency?: string
    change_percent: number
    current_price: number
}

export interface SankeyNode {
    name: string
}

export interface SankeyLink {
    source: number
    target: number
    value: number
}

export interface PortfolioFlow {
    nodes: SankeyNode[]
    links: SankeyLink[]
}

export interface AccountAllocation {
    name: string
    broker: string
    value: number
    percent: number
}

export interface DashboardStats {
    total_assets: number;
    total_pnl: number
    win_rate: number
    avg_pnl_ratio: number
    total_trades: number
    open_positions: number
    closed_trades: number
    asset_allocation: AssetAllocation[]
    core_type_allocation: AssetAllocation[];
    market_allocation: AssetAllocation[];
    risk_level_allocation: AssetAllocation[];
    account_allocation: AccountAllocation[]
    top_movers: PositionMover[]
    bottom_movers: PositionMover[]
    portfolio_flow?: PortfolioFlow
    // Risk Metrics
    sharpe_ratio?: number
    sortino_ratio?: number
    calmar_ratio?: number
    max_drawdown?: number
}

export interface DailySummary {
    id: number
    user_id: number
    date: string
    market_mood?: string
    personal_mood?: string
    summary?: string
    created_at: string
}

export interface TradingAccount {
    id: number
    user_id: number
    name: string
    broker: string
    account_type?: string
    currency: string
    initial_balance: number
    cash_balance?: number
    current_balance?: number
    market_value?: number // Real-time calculated
    total_equity?: number // Real-time calculated (NAV)
    total_assets?: number
    total_liabilities?: number
    description?: string
    is_active: boolean
    created_at: string
}

export interface Transaction {
    id: number
    account_id: number
    type: 'DEPOSIT' | 'WITHDRAWAL' | 'INTEREST' | 'FEE' | 'TRANSFER_IN' | 'TRANSFER_OUT'
    amount: number
    currency: string
    date: string
    description?: string
    created_at: string
}

export interface TransactionCreate {
    type: string
    amount: number
    currency?: string
    date: string
    description?: string
}

export interface User {
    id: number
    email: string
    is_active: boolean
    role: string
    created_at: string
}

export interface TradingAccountCreate {
    name: string
    broker: string
    account_type?: string
    currency: string
    initial_balance?: number
    cash_balance?: number
    current_balance?: number
    total_assets?: number
    total_liabilities?: number
    description?: string
}

// ============== Helper Functions ==============

async function fetchAPI(
    endpoint: string,
    options: RequestInit = {},
    token?: string
): Promise<any> {
    const headers: HeadersInit = {
        'Content-Type': 'application/json',
        ...options.headers,
    }

    if (token) {
        (headers as Record<string, string>)['Authorization'] = `Bearer ${token}`
    }

    // Always ensure there's exactly one /api prefix
    const path = endpoint.startsWith('/api') ? endpoint : `/api${endpoint}`

    const response = await fetch(`${API_BASE}${path}`, {
        ...options,
        headers,
    })

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Request failed' }))
        throw new Error(error.detail || `HTTP ${response.status}`)
    }

    // Handle 204 No Content
    if (response.status === 204) {
        return null
    }

    return response.json()
}

// ============== Auth API ==============

export const authAPI = {
    login: async (email: string, password: string) => {
        const formData = new URLSearchParams()
        formData.append('username', email)
        formData.append('password', password)

        // Standardized to use the /api prefix correctly with the raw fetch
        const response = await fetch(`${API_BASE}/api/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: formData,
        })

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Login failed' }))
            throw new Error(error.detail || 'Login failed')
        }

        return response.json()
    },

    register: async (email: string, password: string, invite_code: string) => {
        return fetchAPI('/auth/register', {
            method: 'POST',
            body: JSON.stringify({ email, password, invite_code }),
        })
    },

    me: async (token: string) => {
        return fetchAPI('/auth/me', {}, token)
    },
}


// ============== Strategies API ==============

export const strategiesAPI = {
    list: async (token: string) => {
        return fetchAPI('/api/strategies', {}, token)
    },

    get: async (token: string, id: number) => {
        return fetchAPI(`/api/strategies/${id}`, {}, token)
    },

    create: async (token: string, data: StrategyCreate) => {
        return fetchAPI('/api/strategies', {
            method: 'POST',
            body: JSON.stringify(data),
        }, token)
    },

    update: async (token: string, id: number, data: Partial<StrategyCreate>) => {
        return fetchAPI(`/api/strategies/${id}`, {
            method: 'PATCH',
            body: JSON.stringify(data),
        }, token)
    },

    delete: async (token: string, id: number) => {
        return fetchAPI(`/api/strategies/${id}`, {
            method: 'DELETE',
        }, token)
    },
}

// ============== Settings API ==============

export const settingsAPI = {
    get: async (token: string): Promise<UserSettings> => {
        return fetchAPI('/api/settings', {}, token)
    },

    update: async (token: string, data: Partial<UserSettings>) => {
        return fetchAPI('/api/settings', {
            method: 'PATCH',
            body: JSON.stringify(data),
        }, token)
    },
}

// ============== Reports API ==============

export interface AISummary {
    id: number
    user_id: number
    date: string
    content: string
    created_at: string
}

export const insightsAPI = {
    list: async (token: string): Promise<WeeklyReport[]> => {
        return fetchAPI('/api/insights', {}, token)
    },

    generateCurrentWeek: async (token: string): Promise<WeeklyReport> => {
        // 计算本周的开始和结束日期
        const now = new Date()
        const dayOfWeek = now.getDay()
        const weekStart = new Date(now)
        weekStart.setDate(now.getDate() - dayOfWeek)
        const weekEnd = new Date(weekStart)
        weekEnd.setDate(weekStart.getDate() + 6)

        return fetchAPI('/api/insights/generate-current-week', {
            method: 'POST',
        }, token)
    },

    // AI Summary methods
    getTodaySummary: async (token: string): Promise<AISummary | null> => {
        return fetchAPI('/api/insights/summary/today', {}, token)
    },

    generateSummary: async (token: string): Promise<AISummary> => {
        return fetchAPI('/api/insights/summary/generate', {
            method: 'POST',
        }, token)
    },

    analyze: async (token: string, data: AnalysisRequest): Promise<AnalysisResponse> => {
        return fetchAPI('/api/insights/analyze', {
            method: 'POST',
            body: JSON.stringify(data)
        }, token)
    },

    getLatestAnalysis: async (token: string, type: string): Promise<AnalysisResponse | null> => {
        return fetchAPI(`/api/insights/analyze/latest/${type}`, {}, token)
    }
}

// ============== Dashboard API ==============

export const dashboardAPI = {
    stats: async (token: string): Promise<DashboardStats> => {
        return fetchAPI('/api/dashboard/stats', {}, token)
    },

    pnlHistory: async (token: string, days: number = 30) => {
        return fetchAPI(`/api/dashboard/pnl-history?days=${days}`, {}, token)
    },
}

// ============== Daily API ==============

export const dailyAPI = {
    list: async (token: string): Promise<DailySummary[]> => {
        return fetchAPI('/api/daily', {}, token)
    },

    get: async (token: string, date: string): Promise<DailySummary> => {
        return fetchAPI(`/api/daily/${date}`, {}, token)
    },

    create: async (token: string, data: any): Promise<DailySummary> => {
        return fetchAPI('/api/daily', {
            method: 'POST',
            body: JSON.stringify(data),
        }, token)
    },

    update: async (token: string, date: string, data: any): Promise<DailySummary> => {
        return fetchAPI(`/api/daily/${date}`, {
            method: 'PATCH',
            body: JSON.stringify(data),
        }, token)
    },
}

// ============== Journal API ==============

export interface JournalEntry {
    id: number
    user_id: number
    date: string
    content: string
    created_at: string
    updated_at?: string
}

export const journalAPI = {
    list: async (token: string): Promise<JournalEntry[]> => {
        return fetchAPI('/api/journal', {}, token)
    },

    getByDate: async (token: string, date: string): Promise<JournalEntry[]> => {
        return fetchAPI(`/api/journal/${date}`, {}, token)
    },

    create: async (token: string, data: { date: string; content: string }): Promise<JournalEntry> => {
        return fetchAPI('/api/journal', {
            method: 'POST',
            body: JSON.stringify(data),
        }, token)
    },

    update: async (token: string, id: number, data: { content: string }): Promise<JournalEntry> => {
        return fetchAPI(`/api/journal/${id}`, {
            method: 'PATCH',
            body: JSON.stringify(data),
        }, token)
    },

    delete: async (token: string, id: number): Promise<void> => {
        return fetchAPI(`/api/journal/${id}`, {
            method: 'DELETE',
        }, token)
    },
}

// ============== Accounts API ==============

export const accountsAPI = {
    list: async (token: string): Promise<TradingAccount[]> => {
        return fetchAPI('/api/accounts', {}, token)
    },

    get: async (token: string, id: number): Promise<TradingAccount> => {
        return fetchAPI(`/api/accounts/${id}`, {}, token)
    },

    create: async (token: string, data: TradingAccountCreate): Promise<TradingAccount> => {
        return fetchAPI('/api/accounts', {
            method: 'POST',
            body: JSON.stringify(data),
        }, token)
    },

    update: async (token: string, id: number, data: Partial<TradingAccountCreate> & { is_active?: boolean }): Promise<TradingAccount> => {
        return fetchAPI(`/api/accounts/${id}`, {
            method: 'PATCH',
            body: JSON.stringify(data),
        }, token)
    },

    delete: async (token: string, id: number): Promise<void> => {
        return fetchAPI(`/api/accounts/${id}`, {
            method: 'DELETE',
        }, token)
    },

    // Transactions
    getTransactions: async (token: string, accountId: number): Promise<Transaction[]> => {
        return fetchAPI(`/api/accounts/${accountId}/transactions`, {}, token)
    },

    createTransaction: async (token: string, accountId: number, data: TransactionCreate): Promise<Transaction> => {
        return fetchAPI(`/api/accounts/${accountId}/transactions`, {
            method: 'POST',
            body: JSON.stringify(data),
        }, token)
    },

    deleteTransaction: async (token: string, id: number): Promise<void> => {
        return fetchAPI(`/api/transactions/${id}`, {
            method: 'DELETE',
        }, token)
    }
}

export interface SystemSetting {
    key: string
    value: string | null
    description: string | null
    updated_at: string | null
}

export const adminAPI = {
    listSettings: async (token: string): Promise<SystemSetting[]> => {
        return fetchAPI('/api/admin/settings', {}, token)
    },

    updateSetting: async (token: string, key: string, data: { value?: string, description?: string }): Promise<SystemSetting> => {
        return fetchAPI(`/api/admin/settings/${key}`, {
            method: 'PUT',
            body: JSON.stringify(data),
        }, token)
    },

    testLLM: async (token: string): Promise<{ status: string; message: string }> => {
        return fetchAPI('/api/admin/test-llm', {
            method: 'POST'
        }, token)
    }
}

// ============== Position & Batch Types ==============

export interface TradeBatch {
    id: number
    position_id: number
    type: 'ENTRY' | 'EXIT'
    price: number
    quantity: number
    time: string
    reason?: string
    emotion?: string
    confidence?: number
    pnl?: number
    created_at: string
}

export interface Position {
    id: number
    user_id: number
    account_id?: number
    strategy_id?: number
    symbol: string
    exchange: string
    asset_type?: string
    direction: 'LONG' | 'SHORT'
    status: 'OPEN' | 'CLOSED'
    total_quantity: number
    average_entry_price?: number
    realized_pnl: number
    current_price?: number  // Live price for open positions
    unrealized_pnl?: number  // Calculated unrealized P&L
    opened_at: string
    closed_at?: string
    trade_review?: string
    screenshots: string[]
    lessons: string[]
    rating?: number
    created_at: string
    updated_at?: string
    asset_metadata?: any // Detailed AssetMetadataResponse
    batches?: TradeBatch[]
    // Phase 1: Plan Drift Detection
    planned_entry_price?: number
    planned_stop_loss?: number
    planned_take_profit?: { price: number; percent?: number }[]
    // Phase 1: Checklist Responses
    checklist_responses?: Record<string, boolean>
    checklist_completed_at?: string
    // Phase 1: Drift Analysis (computed by backend)
    drift_analysis?: {
        has_planned_data: boolean
        has_drift: boolean
        entry_drift_pct?: number
        entry_drift_direction?: 'above' | 'below' | 'on_target'
        stop_loss_risk_pct?: number
        execution_quality?: 'excellent' | 'good' | 'fair' | 'poor'
    }
    // Phase 2: MAE/MFE
    max_price_during_hold?: number
    min_price_during_hold?: number
}

export interface PositionCreate {
    account_id: number
    symbol: string
    asset_type?: string
    direction: 'LONG' | 'SHORT'
    strategy_id?: number
    entry_price: number
    quantity: number
    entry_time: string
    entry_reason?: string
    entry_emotion?: string
    entry_confidence?: number
    // Phase 1: Plan Drift Detection
    planned_entry_price?: number
    planned_stop_loss?: number
    planned_take_profit?: { price: number; percent?: number }[]
    // Phase 1: Checklist Responses
    checklist_responses?: Record<string, boolean>
    asset_metadata?: {
        name?: string
        core_type?: string
        market?: string
        currency?: string
        sector?: string
        risk_level?: string
        instrument?: string
    }
}

export interface BatchCreate {
    type: 'ENTRY' | 'EXIT'
    price: number
    quantity: number
    time: string
    reason?: string
    emotion?: string
    confidence?: number
}

// ============== Positions API ==============

export const positionsAPI = {
    list: async (token: string, params?: {
        status?: string;
        symbol?: string;
        account_id?: number | string;
        core_type?: string;
        market?: string;
        risk_level?: string;
        asset_type?: string;
    }): Promise<Position[]> => {
        const searchParams = new URLSearchParams()
        if (params?.status) searchParams.append('status', params.status)
        if (params?.symbol) searchParams.append('symbol', params.symbol)
        if (params?.account_id) searchParams.append('account_id', params.account_id.toString())
        if (params?.core_type) searchParams.append('core_type', params.core_type)
        if (params?.market) searchParams.append('market', params.market)
        if (params?.risk_level) searchParams.append('risk_level', params.risk_level)
        if (params?.asset_type) searchParams.append('asset_type', params.asset_type)
        const query = searchParams.toString()
        return fetchAPI(`/api/positions${query ? `?${query}` : ''}`, {}, token)
    },

    get: async (token: string, id: number): Promise<Position> => {
        return fetchAPI(`/api/positions/${id}`, {}, token)
    },

    create: async (token: string, data: PositionCreate): Promise<Position> => {
        return fetchAPI('/api/positions', {
            method: 'POST',
            body: JSON.stringify(data),
        }, token)
    },

    update: async (token: string, id: number, data: Partial<Position>): Promise<Position> => {
        return fetchAPI(`/api/positions/${id}`, {
            method: 'PATCH',
            body: JSON.stringify(data),
        }, token)
    },

    delete: async (token: string, id: number): Promise<void> => {
        return fetchAPI(`/api/positions/${id}`, {
            method: 'DELETE',
        }, token)
    },

    checkOpen: async (token: string, symbol: string, accountId: number): Promise<Position | null> => {
        return fetchAPI(`/api/positions/check/${symbol}?account_id=${accountId}`, {}, token)
    },

    analyze: async (token: string, id: number): Promise<Position> => {
        return fetchAPI(`/api/positions/${id}/analyze`, {
            method: 'POST',
        }, token)
    },

    // Batch operations
    addBatch: (token: string, positionId: number, data: BatchCreate): Promise<TradeBatch> =>
        fetchAPI(`/api/positions/${positionId}/batches`, {
            method: 'POST',
            body: JSON.stringify(data)
        }, token),

    updateBatch: (token: string, batchId: number, data: Partial<BatchCreate>): Promise<TradeBatch> =>
        fetchAPI(`/api/positions/batches/${batchId}`, {
            method: 'PATCH',
            body: JSON.stringify(data)
        }, token),

    deleteBatch: (token: string, batchId: number): Promise<void> => {
        return fetchAPI(`/api/positions/batches/${batchId}`, {
            method: 'DELETE',
        }, token)
    },

    // Import operations
    importUpload: async (token: string, file: File): Promise<any> => {
        const formData = new FormData()
        formData.append('file', file)

        // Use raw fetch for FormData to avoid Content-Type json override
        const response = await fetch(`${API_BASE}/api/positions/import/upload`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            },
            body: formData
        })

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Upload failed' }))
            throw new Error(error.detail || 'Upload failed')
        }
        return response.json()
    },

    importConfirm: async (token: string, data: { file_token: string, account_id: number, selected_indices?: number[] }): Promise<any> => {
        return fetchAPI('/api/positions/import/confirm', {
            method: 'POST',
            body: JSON.stringify(data)
        }, token)
    },

    getImportTemplate: async (token: string): Promise<Blob> => {
        const response = await fetch(`${API_BASE}/api/positions/import/template`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        })
        if (!response.ok) throw new Error("Failed to download template")
        return response.blob()
    }
}

// ============== Market Data API ==============

export interface SymbolValidation {
    valid: boolean
    symbol: string
    asset_type?: string // 'A_STOCK' | 'HK_STOCK' | 'CRYPTO' | 'US_STOCK' | 'EQUITY' | 'ETF_...'
    price?: number
    name?: string
    provider?: string
    error?: string
    metadata?: any // Rich metadata
    candidates?: { symbol: string; reason: string }[]
}


import { getHolidays } from './holidays'

export interface MarketHoliday {
    date: string
    name: string
    is_trading?: boolean
}

export interface MarketCalendar {
    market: string
    year: number
    month: number
    holidays: MarketHoliday[]
    trading_days: string[]
    non_trading_days: string[]
}

export const marketAPI = {
    validateSymbol: async (token: string, symbol: string, exchange?: string): Promise<SymbolValidation> => {
        const params = new URLSearchParams()
        if (exchange) params.append('exchange', exchange)
        const query = params.toString()
        return fetchAPI(`/api/market/validate/${symbol}${query ? `?${query}` : ''}`, {}, token)
    },

    getQuote: async (token: string, symbol: string, exchange?: string): Promise<any> => {
        const params = new URLSearchParams()
        if (exchange) params.append('exchange', exchange)
        const query = params.toString()
        return fetchAPI(`/api/market/quote/${symbol}${query ? `?${query}` : ''}`, {}, token)
    },

    calendar: async (token: string, market: string, year: number, month: number): Promise<MarketCalendar> => {
        try {
            // Try fetching from backend first
            return await fetchAPI(`/api/market/calendar?market=${market}&year=${year}&month=${month}`, {}, token)
        } catch (err) {
            console.warn(`Failed to fetch calendar for ${market}, using local fallback`, err)
            // Fallback to local data
            const holidays = getHolidays(market, year, month - 1).map(h => ({
                date: h.date,
                name: h.name,
                is_trading: false
            }))

            // Simple generation of trading days (Mon-Fri minus holidays) for fallback
            // This is an approximation
            const trading_days: string[] = []
            const date = new Date(year, month - 1, 1)
            const endDate = new Date(year, month, 0)

            while (date <= endDate) {
                const dateStr = date.toISOString().split('T')[0]
                const day = date.getDay()
                const isWeekend = day === 0 || day === 6
                const isHoliday = holidays.some(h => h.date === dateStr)

                if (!isWeekend && !isHoliday) {
                    trading_days.push(dateStr)
                }
                date.setDate(date.getDate() + 1)
            }

            return {
                market,
                year,
                month,
                holidays,
                trading_days,
                non_trading_days: []
            }
        }
    }
}


