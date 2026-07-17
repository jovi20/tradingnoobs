import type {
    JournalTimelineHomeResponse,
    JournalTimelineView,
    LifecycleDetailResponse,
} from './read-models'
import { buildBlobDownloadFromResponse, type BlobDownloadPayload } from './download.ts'

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
    ibkr_flex_query_id?: string
    ibkr_flex_token?: string
    ibkr_flex_start_date?: string
    binance_api_key?: string
    binance_api_secret?: string
    binance_api_secret_configured?: boolean
    binance_market_type?: 'SPOT' | 'USD_M_FUTURES'
    binance_symbols?: string[]
    finnhub_api_key?: string
    llm_api_url?: string
    llm_model?: string
}

export interface BrokerConnectionTestResponse {
    ok: boolean
    provider: string
    message: string
    reference_code?: string
}

export interface BrokerSyncRequest {
    start_date?: string
    end_date?: string
}

export interface BrokerSyncRun {
    public_id: string
    provider: string
    market_type?: string | null
    status: string
    requested_start_date?: string | null
    requested_end_date?: string | null
    records_fetched: number
    records_inserted: number
    records_skipped: number
    error_message?: string | null
    metadata_json?: Record<string, any> | null
    started_at?: string | null
    finished_at?: string | null
    created_at: string
}

export interface BrokerExecution {
    public_id: string
    provider: string
    market_type?: string | null
    account_ref?: string | null
    symbol: string
    side: string
    quantity: number
    price: number
    trade_time: string
    currency?: string | null
    commission?: number | null
    commission_currency?: string | null
    external_trade_id: string
    external_order_id?: string | null
    import_status: string
    created_at: string
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

export interface AnalysisHistoryDateRange {
    start_date: string
    end_date: string
    label: string
}

export interface AnalysisHistoryItem {
    run_public_id: string
    artifact_public_id: string
    analysis_type: AnalysisType | string
    title: string
    summary: string
    created_at: string
    date_range?: AnalysisHistoryDateRange | null
    href: string
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

export type RiskAlertSeverity = 'INFO' | 'NOTICE' | 'WARNING' | 'CRITICAL'
export type RiskAlertKind = 'DAILY_LOSS_LIMIT' | 'CONCENTRATION' | 'DRAWDOWN' | 'DATA_STALE' | string

export interface RiskRecommendedAction {
    kind: string
    label: string
    href: string
}

export interface RiskTrustMeta {
    freshness: string
    source: string
    value_status?: string
    source_refs?: string[]
    note?: string
}

export interface RiskAlert {
    public_id: string
    kind: RiskAlertKind
    severity: RiskAlertSeverity
    summary: string
    reason: string
    recommended_action: RiskRecommendedAction
    source_refs: string[]
    trust: RiskTrustMeta
}

export interface RiskPortfolioSummary {
    gross_exposure: number
    net_liquidation_value: number
    daily_pnl?: number | null
    daily_pnl_percent?: number | null
    max_drawdown?: number | null
}

export interface RiskSummaryResponse {
    as_of: string
    base_currency: string
    portfolio: RiskPortfolioSummary
    alerts: RiskAlert[]
    trust: RiskTrustMeta
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

export interface DashboardAccountBalance {
    name: string
    broker: string
    journal_balance: number
}

export interface DashboardStats {
    journal_balance: number
    realized_pnl: number
    win_rate: number
    avg_pnl_ratio: number
    total_trades: number
    open_positions: number
    closed_trades: number
    account_balances: DashboardAccountBalance[]
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
    public_id: string
    user_id: number
    name: string
    broker: string
    account_type?: string
    currency: string
    initial_balance: number
    journal_balance: number
    description?: string
    is_active: boolean
    created_at: string
}

export interface Transaction {
    id: number
    public_id: string
    account_id: number
    type: 'DEPOSIT' | 'WITHDRAWAL' | 'INTEREST' | 'FEE' | 'TRANSFER_IN' | 'TRANSFER_OUT'
    amount: number
    currency: string
    date: string
    description?: string
    created_at: string
}

export type JournalTransactionCreateType = 'DEPOSIT' | 'WITHDRAWAL' | 'INTEREST' | 'FEE'

export interface TransactionCreate {
    type: JournalTransactionCreateType
    amount: number
    currency?: string
    date: string
    description?: string
}

export interface User {
    id: number
    public_id: string
    email: string
    status: string
    is_active: boolean
    role: string
    last_login_at?: string
    locale?: string
    timezone?: string
    created_at: string
}

export interface UserProfileUpdate {
    locale?: string
    timezone?: string
}

export interface PasswordChangeRequest {
    current_password: string
    new_password: string
}

export interface PasswordChangeResponse {
    message: string
    active_sessions_revoked: boolean
}

export interface TradingAccountCreate {
    name: string
    broker: string
    account_type?: string
    currency: string
    initial_balance?: number
    description?: string
}

export interface TradingAccountUpdate {
    name?: string
    broker?: string
    account_type?: string
    currency?: string
    description?: string
}

// ============== Helper Functions ==============

export class ApiRequestError extends Error {
    readonly status: number

    constructor(status: number, message: string) {
        super(message)
        this.name = 'ApiRequestError'
        this.status = status
    }
}

export function isAuthenticationApiError(error: unknown): boolean {
    return error instanceof ApiRequestError && (error.status === 401 || error.status === 403)
}

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
        throw new ApiRequestError(response.status, error.detail || `HTTP ${response.status}`)
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

    me: async (token: string) => {
        return fetchAPI('/auth/me', {}, token)
    },

    updateMe: async (token: string, data: UserProfileUpdate): Promise<User> => {
        return fetchAPI('/auth/me', {
            method: 'PATCH',
            body: JSON.stringify(data),
        }, token)
    },

    changePassword: async (token: string, data: PasswordChangeRequest): Promise<PasswordChangeResponse> => {
        return fetchAPI('/auth/change-password', {
            method: 'POST',
            body: JSON.stringify(data),
        }, token)
    },

    logout: async (token: string): Promise<void> => {
        await fetchAPI('/auth/logout', {
            method: 'POST',
        }, token)
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

// ============== Broker Sync API ==============

export const brokerSyncAPI = {
    testIBKR: async (token: string): Promise<BrokerConnectionTestResponse> => {
        return fetchAPI('/api/broker-sync/ibkr/test', { method: 'POST' }, token)
    },

    testBinance: async (token: string): Promise<BrokerConnectionTestResponse> => {
        return fetchAPI('/api/broker-sync/binance/test', { method: 'POST' }, token)
    },

    syncIBKR: async (token: string, data: BrokerSyncRequest = {}): Promise<BrokerSyncRun> => {
        return fetchAPI('/api/broker-sync/ibkr/sync', {
            method: 'POST',
            body: JSON.stringify(data),
        }, token)
    },

    syncBinance: async (token: string, data: BrokerSyncRequest = {}): Promise<BrokerSyncRun> => {
        return fetchAPI('/api/broker-sync/binance/sync', {
            method: 'POST',
            body: JSON.stringify(data),
        }, token)
    },

    listRuns: async (token: string, limit = 5): Promise<BrokerSyncRun[]> => {
        return fetchAPI(`/api/broker-sync/runs?limit=${limit}`, {}, token)
    },

    listExecutions: async (token: string, limit = 20): Promise<BrokerExecution[]> => {
        return fetchAPI(`/api/broker-sync/executions?limit=${limit}`, {}, token)
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

    exportWeeklyReportPdf: async (token: string, reportId: number): Promise<BlobDownloadPayload> => {
        const response = await fetch(`${API_BASE}/api/insights/${reportId}/export/pdf`, {
            headers: {
                Accept: 'application/pdf',
                Authorization: `Bearer ${token}`,
            },
        })

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'PDF export failed' }))
            const detail = typeof error.detail === 'string' ? error.detail : error.error?.message
            throw new Error(detail || `HTTP ${response.status}`)
        }

        return buildBlobDownloadFromResponse(response, `tradingnoobs-weekly-report-${reportId}.pdf`)
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

    listAnalysisHistory: async (
        token: string,
        params?: {
            analysis_type?: AnalysisType
            limit?: number
        }
    ): Promise<AnalysisHistoryItem[]> => {
        const searchParams = new URLSearchParams()
        if (params?.analysis_type) searchParams.set('analysis_type', params.analysis_type)
        if (params?.limit) searchParams.set('limit', String(params.limit))
        const query = searchParams.toString()

        return fetchAPI(`/api/insights/analyze/history${query ? `?${query}` : ''}`, {}, token)
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

export const timelineAPI = {
    home: async (
        token: string,
        params?: {
            view?: JournalTimelineView
        }
    ): Promise<JournalTimelineHomeResponse> => {
        const searchParams = new URLSearchParams()
        if (params?.view) searchParams.append('view', params.view)
        const query = searchParams.toString()
        return fetchAPI(`/api/timeline/home${query ? `?${query}` : ''}`, {}, token)
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

    get: async (token: string, id: number | string): Promise<TradingAccount> => {
        return fetchAPI(`/api/accounts/${id}`, {}, token)
    },

    create: async (token: string, data: TradingAccountCreate): Promise<TradingAccount> => {
        return fetchAPI('/api/accounts', {
            method: 'POST',
            body: JSON.stringify(data),
        }, token)
    },

    update: async (token: string, id: number | string, data: TradingAccountUpdate): Promise<TradingAccount> => {
        return fetchAPI(`/api/accounts/${id}`, {
            method: 'PATCH',
            body: JSON.stringify(data),
        }, token)
    },

    delete: async (token: string, id: number | string): Promise<void> => {
        return fetchAPI(`/api/accounts/${id}`, {
            method: 'DELETE',
        }, token)
    },

    // Transactions
    getTransactions: async (token: string, accountId: number | string): Promise<Transaction[]> => {
        return fetchAPI(`/api/accounts/${accountId}/transactions`, {}, token)
    },

    createTransaction: async (token: string, accountId: number | string, data: TransactionCreate): Promise<Transaction> => {
        return fetchAPI(`/api/accounts/${accountId}/transactions`, {
            method: 'POST',
            body: JSON.stringify(data),
        }, token)
    },

    deleteTransaction: async (token: string, id: number | string): Promise<void> => {
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

export interface PlatformSetting {
    id: number
    key: string
    value: string | null
    description: string | null
    created_at: string | null
    updated_at: string | null
}

export interface IntegrationCredential {
    id: number
    provider_key: string
    credential_key: string
    masked_value: string | null
    description: string | null
    is_active: boolean
    is_configured: boolean
    created_at: string | null
    updated_at: string | null
}

export interface FeatureFlag {
    id: number
    key: string
    enabled: boolean
    actor_targets: string[]
    rollout_percentage: number | null
    expires_at: string | null
    description: string | null
    created_at: string | null
    updated_at: string | null
}

export type AdminJobStatus = 'QUEUED' | 'RUNNING' | 'SUCCEEDED' | 'FAILED' | 'RETRYING' | 'CANCELLED'
export type AdminJobRecommendedAction = 'REQUEUE' | 'CANCEL' | 'FORCE_CANCEL' | 'WAIT'
export type AdminOperationStatus = 'SUCCESS' | 'FAILED'

export interface AdminBackupResponse {
    status: AdminOperationStatus
    backup_id: string
    path: string
    database_backend: string
    created_at: string
    message: string
}

export interface AdminBackupSummary {
    backup_id: string
    path: string
    database_backend: string
    created_at: string
    size_bytes: number
}

export interface AdminOpsSummary {
    database_backend: string
    backup_provider_configured: boolean
    backup_count: number
    latest_backup_at: string | null
    user_count: number
    active_user_count: number
    admin_count: number
    job_counts: Record<string, number>
    stale_running_job_count: number
    platform_setting_count: number
    configured_integration_count: number
    active_integration_count: number
    enabled_feature_flag_count: number
    expired_feature_flag_count: number
    active_business_lock_count: number
    expired_business_lock_count: number
}

export interface AdminUserOperationResponse {
    status: AdminOperationStatus
    user_public_id: string
    role: string
    message: string
}

export interface AdminUserSummary {
    public_id: string
    email: string
    status: string
    is_active: boolean
    role: string
    last_login_at: string | null
    created_at: string
}

export interface AdminPasswordResetResponse {
    status: AdminOperationStatus
    user_public_id: string
    temporary_password: string
    active_sessions_revoked: boolean
    revoked_session_count: number
    revoked_token_count: number
    message: string
}

export interface AdminJobDefinitionRef {
    public_id: string
    key: string
    display_name: string
    queue_name?: string
}

export interface AdminJobRunSummary {
    public_id: string
    definition: AdminJobDefinitionRef
    status: AdminJobStatus
    queue_name: string
    priority: number
    attempt_count: number
    max_attempts: number
    next_run_at: string | null
    started_at: string | null
    finished_at: string | null
    created_at: string
    error_message: string | null
    stale_reason?: string | null
    recommended_action?: AdminJobRecommendedAction | null
    force_cancel_warning?: string | null
}

export interface AdminJobRunEvent {
    public_id: string
    event_type: string
    from_status: AdminJobStatus | null
    to_status: AdminJobStatus | null
    message: string | null
    metadata: Record<string, unknown>
    created_at: string
}

export interface AdminJobBusinessLock {
    public_id: string
    scope: string
    resource_key: string
    owner_id: string
    owner_type: string
    status: 'ACTIVE' | 'RELEASED' | 'EXPIRED'
    metadata: Record<string, unknown>
    acquired_at: string | null
    expires_at: string
    released_at: string | null
}

export interface AdminJobRunDetail extends AdminJobRunSummary {
    user_public_id: string | null
    idempotency_key: string | null
    payload: Record<string, unknown>
    result: Record<string, unknown>
    locked_by: string | null
    locked_at: string | null
    updated_at: string | null
    business_locks: AdminJobBusinessLock[]
    events: AdminJobRunEvent[]
}

export interface AdminJobListResponse {
    items: AdminJobRunSummary[]
    total: number
    limit: number
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
    },

    listPlatformSettings: async (token: string): Promise<PlatformSetting[]> => {
        return fetchAPI('/api/admin/platform/settings', {}, token)
    },

    upsertPlatformSetting: async (
        token: string,
        key: string,
        data: { value?: string; description?: string }
    ): Promise<PlatformSetting> => {
        return fetchAPI(`/api/admin/platform/settings/${key}`, {
            method: 'PUT',
            body: JSON.stringify(data),
        }, token)
    },

    listIntegrationCredentials: async (token: string): Promise<IntegrationCredential[]> => {
        return fetchAPI('/api/admin/platform/integrations', {}, token)
    },

    upsertIntegrationCredential: async (
        token: string,
        providerKey: string,
        credentialKey: string,
        data: { secret_value: string; description?: string; is_active?: boolean }
    ): Promise<IntegrationCredential> => {
        return fetchAPI(`/api/admin/platform/integrations/${providerKey}/${credentialKey}`, {
            method: 'PUT',
            body: JSON.stringify(data),
        }, token)
    },

    updateIntegrationCredentialActive: async (
        token: string,
        providerKey: string,
        credentialKey: string,
        isActive: boolean
    ): Promise<IntegrationCredential> => {
        return fetchAPI(`/api/admin/platform/integrations/${providerKey}/${credentialKey}/active`, {
            method: 'PATCH',
            body: JSON.stringify({ is_active: isActive }),
        }, token)
    },

    listFeatureFlags: async (token: string): Promise<FeatureFlag[]> => {
        return fetchAPI('/api/admin/platform/feature-flags', {}, token)
    },

    upsertFeatureFlag: async (
        token: string,
        key: string,
        data: {
            enabled: boolean
            actor_targets?: string[]
            rollout_percentage?: number | null
            expires_at?: string | null
            description?: string
        }
    ): Promise<FeatureFlag> => {
        return fetchAPI(`/api/admin/platform/feature-flags/${key}`, {
            method: 'PUT',
            body: JSON.stringify(data),
        }, token)
    },

    listJobs: async (
        token: string,
        params: { status?: AdminJobStatus; queue_name?: string; limit?: number } = {}
    ): Promise<AdminJobListResponse> => {
        const search = new URLSearchParams()
        if (params.status) search.set('status', params.status)
        if (params.queue_name) search.set('queue_name', params.queue_name)
        if (params.limit) search.set('limit', String(params.limit))
        const suffix = search.toString() ? `?${search.toString()}` : ''
        return fetchAPI(`/api/admin/jobs${suffix}`, {}, token)
    },

    getJob: async (token: string, jobPublicId: string): Promise<AdminJobRunDetail> => {
        return fetchAPI(`/api/admin/jobs/${jobPublicId}`, {}, token)
    },

    requeueJob: async (token: string, jobPublicId: string): Promise<AdminJobRunDetail> => {
        return fetchAPI(`/api/admin/jobs/${jobPublicId}/requeue`, {
            method: 'POST',
        }, token)
    },

    cancelJob: async (token: string, jobPublicId: string): Promise<AdminJobRunDetail> => {
        return fetchAPI(`/api/admin/jobs/${jobPublicId}/cancel`, {
            method: 'POST',
        }, token)
    },

    forceCancelJob: async (token: string, jobPublicId: string): Promise<AdminJobRunDetail> => {
        return fetchAPI(`/api/admin/jobs/${jobPublicId}/force-cancel`, {
            method: 'POST',
        }, token)
    },

    triggerBackup: async (token: string): Promise<AdminBackupResponse> => {
        return fetchAPI('/api/admin/ops/backups', {
            method: 'POST',
        }, token)
    },

    listUsers: async (token: string, limit = 100): Promise<AdminUserSummary[]> => {
        return fetchAPI(`/api/admin/users?limit=${limit}`, {}, token)
    },

    promoteUser: async (token: string, userPublicId: string): Promise<AdminUserOperationResponse> => {
        return fetchAPI(`/api/admin/users/${encodeURIComponent(userPublicId)}/promote`, {
            method: 'POST',
        }, token)
    },

    resetUserPassword: async (token: string, userPublicId: string): Promise<AdminPasswordResetResponse> => {
        return fetchAPI(`/api/admin/users/${encodeURIComponent(userPublicId)}/reset-password`, {
            method: 'POST',
        }, token)
    },

    getOpsSummary: async (token: string): Promise<AdminOpsSummary> => {
        return fetchAPI('/api/admin/ops/summary', {}, token)
    },

    listBackups: async (token: string, limit = 20): Promise<AdminBackupSummary[]> => {
        return fetchAPI(`/api/admin/ops/backups?limit=${limit}`, {}, token)
    },

    updateUserRole: async (token: string, userPublicId: string, role: 'user' | 'admin'): Promise<AdminUserOperationResponse> => {
        return fetchAPI(`/api/admin/users/${encodeURIComponent(userPublicId)}/role`, {
            method: 'PATCH',
            body: JSON.stringify({ role }),
        }, token)
    },

    updateUserActive: async (token: string, userPublicId: string, isActive: boolean): Promise<AdminUserOperationResponse> => {
        return fetchAPI(`/api/admin/users/${encodeURIComponent(userPublicId)}/active`, {
            method: 'PATCH',
            body: JSON.stringify({ is_active: isActive }),
        }, token)
    },
}

// ============== Position & Batch Types ==============

export interface TradeBatch {
    id: number
    public_id: string
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
    public_id: string
    truth_position_public_id?: string
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
}

export interface PositionMarketAnalysis extends Position {
    current_price?: number
    unrealized_pnl?: number
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

export interface TradingPositionEventNarrativeUpdate {
    reason?: string
    emotion?: string
    confidence?: number
    thesis?: string
    edge_source?: string
    disconfirming_evidence?: string
    invalidation_rule?: string
    expected_holding_period?: string
    planned_exit_rule?: string
    sizing_rationale?: string
    checklist_snapshot?: Record<string, boolean>
    note?: string
}

export interface TradingPositionTradeEventCreate {
    event_type: 'ADD' | 'REDUCE' | 'CLOSE'
    quantity: number
    price: number
    currency?: string
    occurred_at: string
    fee_amount?: number
    fee_currency?: string
    fx_rate_to_account_ccy?: number
    reason?: string
    emotion?: string
    confidence?: number
    note?: string
}

export interface TradingPositionTradeEventReverseCreate {
    occurred_at: string
    note?: string
}

// ============== Positions API ==============

export const positionsAPI = {
    list: async (token: string, params?: {
        status?: string;
        symbol?: string;
        account_id?: number | string;
        core_type?: string;
        market?: string;
        asset_type?: string;
    }): Promise<Position[]> => {
        const searchParams = new URLSearchParams()
        if (params?.status) searchParams.append('status', params.status)
        if (params?.symbol) searchParams.append('symbol', params.symbol)
        if (params?.account_id) searchParams.append('account_id', params.account_id.toString())
        if (params?.core_type) searchParams.append('core_type', params.core_type)
        if (params?.market) searchParams.append('market', params.market)
        if (params?.asset_type) searchParams.append('asset_type', params.asset_type)
        const query = searchParams.toString()
        return fetchAPI(`/api/positions${query ? `?${query}` : ''}`, {}, token)
    },

    get: async (token: string, id: number | string): Promise<Position> => {
        return fetchAPI(`/api/positions/${id}`, {}, token)
    },

    getTruthLifecycle: async (token: string, id: number | string): Promise<LifecycleDetailResponse> => {
        return fetchAPI(`/api/positions/${id}/truth-lifecycle`, {}, token)
    },

    getTradingPositionLifecycle: async (token: string, positionPublicId: string): Promise<LifecycleDetailResponse> => {
        return fetchAPI(`/api/trading-positions/${positionPublicId}/lifecycle`, {}, token)
    },

    updateTradingPositionEventNarrative: async (
        token: string,
        positionPublicId: string,
        eventPublicId: string,
        data: TradingPositionEventNarrativeUpdate
    ): Promise<LifecycleDetailResponse> => {
        return fetchAPI(`/api/trading-positions/${positionPublicId}/events/${eventPublicId}`, {
            method: 'PATCH',
            body: JSON.stringify(data),
        }, token)
    },

    createTradingPositionTradeEvent: async (
        token: string,
        positionPublicId: string,
        data: TradingPositionTradeEventCreate
    ): Promise<LifecycleDetailResponse> => {
        return fetchAPI(`/api/trading-positions/${positionPublicId}/events`, {
            method: 'POST',
            body: JSON.stringify(data),
        }, token)
    },

    reverseTradingPositionTradeEvent: async (
        token: string,
        positionPublicId: string,
        eventPublicId: string,
        data: TradingPositionTradeEventReverseCreate
    ): Promise<LifecycleDetailResponse> => {
        return fetchAPI(`/api/trading-positions/${positionPublicId}/events/${eventPublicId}/reverse`, {
            method: 'POST',
            body: JSON.stringify(data),
        }, token)
    },

    create: async (token: string, data: PositionCreate): Promise<Position> => {
        return fetchAPI('/api/positions', {
            method: 'POST',
            body: JSON.stringify(data),
        }, token)
    },

    update: async (token: string, id: number | string, data: Partial<Position>): Promise<Position> => {
        return fetchAPI(`/api/positions/${id}`, {
            method: 'PATCH',
            body: JSON.stringify(data),
        }, token)
    },

    delete: async (token: string, id: number | string): Promise<void> => {
        return fetchAPI(`/api/positions/${id}`, {
            method: 'DELETE',
        }, token)
    },

    checkOpen: async (token: string, symbol: string, accountId: number | string): Promise<Position | null> => {
        return fetchAPI(`/api/positions/check/${symbol}?account_id=${accountId}`, {}, token)
    },

    analyze: async (token: string, id: number | string): Promise<PositionMarketAnalysis> => {
        return fetchAPI(`/api/positions/${id}/analyze`, {
            method: 'POST',
        }, token)
    },

    // Batch operations
    addBatch: (
        token: string,
        positionId: number | string,
        data: BatchCreate,
        options?: { migrationFallback?: boolean }
    ): Promise<TradeBatch> =>
        fetchAPI(`/api/positions/${positionId}/batches`, {
            method: 'POST',
            headers: options?.migrationFallback ? { 'X-Migration-Fallback': 'legacy-batch-write' } : undefined,
            body: JSON.stringify(data)
        }, token),

    updateBatch: (token: string, batchId: number | string, data: Partial<BatchCreate>): Promise<TradeBatch> =>
        fetchAPI(`/api/positions/batches/${batchId}`, {
            method: 'PATCH',
            body: JSON.stringify(data)
        }, token),

    deleteBatch: (token: string, batchId: number | string): Promise<void> => {
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
    freshness?: string
    degraded?: boolean
    degraded_reason?: string
    source_refs?: string[]
    as_of?: string
    error?: string
    metadata?: any // Rich metadata
    candidates?: { symbol: string; reason: string }[]
}

export interface MarketQuoteTrustMeta {
    freshness: string
    degraded: boolean
    degraded_reason?: string
    source_refs: string[]
    as_of?: string
}

export interface MarketQuoteResponse {
    symbol: string
    asset_type?: string
    quote?: Record<string, any>
    provider?: string
    freshness: string
    degraded: boolean
    degraded_reason?: string
    source_refs: string[]
    as_of?: string
    error?: string
    trust: MarketQuoteTrustMeta
}


import { getHolidays } from './holidays.ts'

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

export function buildLocalMarketCalendar(
    market: string,
    year: number,
    month: number,
): MarketCalendar {
    const holidays = getHolidays(market, year, month - 1).map(holiday => ({
        date: holiday.date,
        name: holiday.name,
        is_trading: false,
    }))
    const trading_days: string[] = []
    const date = new Date(year, month - 1, 1)
    const endDate = new Date(year, month, 0)

    while (date <= endDate) {
        const dateStr = [
            date.getFullYear(),
            String(date.getMonth() + 1).padStart(2, '0'),
            String(date.getDate()).padStart(2, '0'),
        ].join('-')
        const day = date.getDay()
        const isWeekend = day === 0 || day === 6
        const isHoliday = holidays.some(holiday => holiday.date === dateStr)

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
        non_trading_days: [],
    }
}

export const marketAPI = {
    validateSymbol: async (token: string, symbol: string, exchange?: string): Promise<SymbolValidation> => {
        const params = new URLSearchParams()
        if (exchange) params.append('exchange', exchange)
        const query = params.toString()
        return fetchAPI(`/api/market/validate/${symbol}${query ? `?${query}` : ''}`, {}, token)
    },

    getQuote: async (token: string, symbol: string, exchange?: string): Promise<MarketQuoteResponse> => {
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
            return buildLocalMarketCalendar(market, year, month)
        }
    }
}
