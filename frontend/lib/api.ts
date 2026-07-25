import type {
    JournalTimelineHomeResponse,
    JournalTimelineView,
    LifecycleDetailResponse,
} from './read-models'
import { buildBlobDownloadFromResponse, type BlobDownloadPayload } from './download.ts'
import { JOURNAL_BETA_RELEASE_CONTRACT } from './generated/release-contract.ts'

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
    display_currency?: 'USD'
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
    accounting_health: 'ACCOUNTING_HEALTHY' | 'ACCOUNTING_RECONCILIATION_REQUIRED'
    journal_balance_trusted: boolean
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
    accounting_degraded: boolean
    accounting_warnings: string[]
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
    accounting_health: 'ACCOUNTING_HEALTHY' | 'ACCOUNTING_RECONCILIATION_REQUIRED'
    trade_source_state: 'CLEAN' | 'MANUAL' | 'SOURCE_BOUND'
    journal_balance_trusted: boolean
    description?: string
    is_active: boolean
    created_at: string
}

export interface Transaction {
    id: number
    public_id: string
    account_id: number
    type: 'DEPOSIT' | 'WITHDRAWAL' | 'INTEREST' | 'FEE'
    amount: number
    currency: string
    date: string
    description?: string
    created_at: string
    reverses_transaction_public_id?: string | null
    reversed_by_transaction_public_id?: string | null
    reversal_reason?: string | null
    request_id?: string | null
}

export type JournalTransactionCreateType = 'DEPOSIT' | 'WITHDRAWAL' | 'INTEREST' | 'FEE'

export interface TransactionCreate {
    type: JournalTransactionCreateType
    amount: number
    currency?: string
    date: string
    description?: string
}

export interface FinancialFactReverseCreate {
    occurred_at: string
    reason: string
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

export interface InviteRegistrationRequest {
    email: string
    password: string
    invite_code: string
    timezone: string
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
    readonly code?: string
    readonly positionPublicId?: string

    constructor(status: number, message: string, code?: string, positionPublicId?: string) {
        super(message)
        this.name = 'ApiRequestError'
        this.status = status
        this.code = code
        this.positionPublicId = positionPublicId
    }
}

export function isAuthenticationApiError(error: unknown): boolean {
    return error instanceof ApiRequestError && (error.status === 401 || error.status === 403)
}

const LOCALIZED_API_ERROR_MESSAGES: Readonly<Record<string, string>> = {
    [JOURNAL_BETA_RELEASE_CONTRACT.lifecycle.same_side_open_conflict.code]: '同一账户中已存在相同标的和方向的未平仓仓位，请加仓到已有仓位。',
    ACCOUNT_ARCHIVED: '该账户已归档，不能继续导入。',
    ACCOUNTING_RECONCILIATION_REQUIRED: '该账户需要先完成账务对账。',
    DUPLICATE_IMPORT_ROW_SELECTION: '同一行不能重复选择。',
    GENERIC_BOOTSTRAP_NOT_ELIGIBLE: '该账户已有交易或非期初资金记录，不能执行首次通用导入。',
    IDEMPOTENCY_KEY_REUSED: '本次重试内容与原确认请求不一致。',
    IDEMPOTENCY_REQUEST_IN_PROGRESS: '导入确认正在处理，请稍后重试。',
    IMPORT_LIFECYCLE_CLOSE_QUANTITY_MISMATCH: '平仓数量必须等于该生命周期的剩余数量。',
    IMPORT_LIFECYCLE_OPEN_CONFLICT: '选中行在尚未平仓时再次开仓。',
    IMPORT_LIFECYCLE_ORPHAN_EVENT: '选中行缺少前置开仓记录。',
    IMPORT_LIFECYCLE_OVER_REDUCE: '减仓数量必须小于剩余持仓数量。',
    IMPORT_ROW_ALREADY_APPLIED: '选中行已经写入，不能重复导入。',
    IMPORT_ROW_INVALID: '选中行包含校验错误。',
    IMPORT_ROW_NOT_FOUND: '选中行不属于当前导入会话。',
    IMPORT_SESSION_ALREADY_CONSUMED: '该导入会话已经确认，不能再次消费。',
    IMPORT_SESSION_EXPIRED: '导入预览已过期，请重新上传文件。',
    IMPORT_SESSION_STATE_CONFLICT: '导入会话状态已变化，请刷新后重试。',
    STALE_IMPORT_PREVIEW: '预览内容已变化，请重新上传文件。',
}

function resolveApiError(payload: unknown, status: number): {
    message: string
    code?: string
    positionPublicId?: string
} {
    if (!payload || typeof payload !== 'object') {
        return { message: `HTTP ${status}` }
    }

    const detail = (payload as { detail?: unknown }).detail
    if (typeof detail === 'string' && detail.trim()) {
        return { message: detail }
    }
    if (detail && typeof detail === 'object' && !Array.isArray(detail)) {
        const structuredDetail = detail as Record<string, unknown>
        const code = typeof structuredDetail.code === 'string' && structuredDetail.code.trim()
            ? structuredDetail.code.trim()
            : undefined
        const positionReferenceField = (
            JOURNAL_BETA_RELEASE_CONTRACT.lifecycle.same_side_open_conflict.position_reference_field
        )
        const rawPositionPublicId = structuredDetail[positionReferenceField]
        const positionPublicId = (
            typeof rawPositionPublicId === 'string'
            && rawPositionPublicId.trim()
        ) ? rawPositionPublicId.trim() : undefined
        const localizedMessage = code ? LOCALIZED_API_ERROR_MESSAGES[code] : undefined
        if (localizedMessage) return { message: localizedMessage, code, positionPublicId }

        const message = typeof structuredDetail.message === 'string' && structuredDetail.message.trim()
            ? structuredDetail.message.trim()
            : undefined
        if (message) return { message, code, positionPublicId }
        if (code) return { message: code, code, positionPublicId }
    }
    if (Array.isArray(detail)) {
        const validationMessage = detail.find(item => (
            item && typeof item === 'object' && typeof (item as { msg?: unknown }).msg === 'string'
        )) as { msg?: string } | undefined
        if (validationMessage?.msg) return { message: validationMessage.msg }
    }

    return { message: `HTTP ${status}` }
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
        const errorPayload = await response.json().catch(() => null)
        const error = resolveApiError(errorPayload, response.status)
        throw new ApiRequestError(
            response.status,
            error.message,
            error.code,
            error.positionPublicId,
        )
    }

    // Handle 204 No Content
    if (response.status === 204) {
        return null
    }

    return response.json()
}

// ============== Auth API ==============

export const authAPI = {
    register: async (data: InviteRegistrationRequest): Promise<User> => {
        return fetchAPI('/auth/register', {
            method: 'POST',
            body: JSON.stringify(data),
        })
    },

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

    createTransaction: async (
        token: string,
        accountId: number | string,
        data: TransactionCreate,
        idempotencyKey: string,
    ): Promise<Transaction> => {
        return fetchAPI(`/api/accounts/${accountId}/transactions`, {
            method: 'POST',
            headers: { 'Idempotency-Key': idempotencyKey },
            body: JSON.stringify(data),
        }, token)
    },

    reverseTransaction: async (
        token: string,
        id: number | string,
        data: FinancialFactReverseCreate,
        idempotencyKey: string,
    ): Promise<Transaction> => {
        return fetchAPI(`/api/transactions/${id}/reverse`, {
            method: 'POST',
            headers: { 'Idempotency-Key': idempotencyKey },
            body: JSON.stringify(data),
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
    asset_type: string | null
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

export type ReleaseAssetType = 'STOCK' | 'FUND' | 'CRYPTO'
export type ReleaseMarket = 'US' | 'CRYPTO'
export type ReleaseInstrumentType = 'SPOT'
export type ReleaseCurrency = 'USD'

export interface PositionCreate {
    account_id: number
    symbol: string
    exchange_code: string
    asset_type: ReleaseAssetType
    direction: 'LONG' | 'SHORT'
    strategy_id?: number
    entry_price: number
    quantity: number
    entry_time: string
    entry_reason?: string
    entry_emotion?: string
    entry_confidence?: number
    fee_amount?: number
    fee_currency?: ReleaseCurrency
    // Phase 1: Plan Drift Detection
    planned_entry_price?: number
    planned_stop_loss?: number
    planned_take_profit?: { price: number; percent?: number }[]
    // Phase 1: Checklist Responses
    checklist_responses?: Record<string, boolean>
    asset_metadata: {
        core_type: ReleaseAssetType
        market: ReleaseMarket
        currency: ReleaseCurrency
        instrument: ReleaseInstrumentType
    }
}

export interface PositionUpdatePayload {
    strategy_id?: number
    trade_review?: string
    screenshots?: string[]
    lessons?: string[]
    rating?: number
    planned_entry_price?: number
    planned_stop_loss?: number
    planned_take_profit?: { price: number; percent?: number }[]
    checklist_responses?: Record<string, boolean>
}

export interface PositionOpenIdentity {
    account_id: number | string
    symbol: string
    exchange_code: string
    direction: 'LONG' | 'SHORT'
    asset_type: ReleaseAssetType
    market: ReleaseMarket
    instrument_type: ReleaseInstrumentType
    quote_currency: ReleaseCurrency
}

export interface ImportIssue {
    code: string
    field?: string | null
    message: string
}

export interface ImportPreviewRow {
    public_id: string
    row_number: number
    raw_values: Record<string, unknown>
    normalized_values: Record<string, unknown>
    is_valid: boolean
    errors: ImportIssue[]
    warnings: ImportIssue[]
}

export interface ImportSession {
    schema_version: 1
    session_public_id: string
    account_public_id: string
    adapter_kind: 'GENERIC_BOOTSTRAP'
    file_format: 'CSV_UTF8' | 'XLSX'
    status:
        | 'UPLOADING'
        | 'PREVIEW_READY'
        | 'CONFIRMING'
        | 'COMPLETED'
        | 'COMPLETED_NOOP'
        | 'CONFLICTED'
        | 'FAILED'
        | 'EXPIRED'
    expires_at: string
    total_rows: number
    valid_rows: number
    error_rows: number
    warning_rows: number
    error?: ImportIssue | null
    rows: ImportPreviewRow[]
    confirm_available: boolean
}

export interface ImportConfirmResponse {
    schema_version: 1
    session_public_id: string
    account_public_id: string
    status: 'COMPLETED' | 'COMPLETED_NOOP'
    selected_row_count: number
    position_count: number
    event_count: number
    posting_count: number
    source_ids: {
        position_public_ids: string[]
        event_public_ids: string[]
        posting_public_ids: string[]
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
    reason: string
    note?: string
}

export interface TradingPositionVoidCreate {
    occurred_at: string
    reason: string
}

// ============== Positions API ==============

export const positionsAPI = {
    uploadImportPreview: async (
        token: string,
        accountPublicId: string,
        file: File,
        idempotencyKey: string,
    ): Promise<ImportSession> => {
        const form = new FormData()
        form.append('account_id', accountPublicId)
        form.append('adapter_kind', 'GENERIC_BOOTSTRAP')
        form.append('file', file)
        const response = await fetch(`${API_BASE}/api/positions/import/upload`, {
            method: 'POST',
            headers: {
                Authorization: `Bearer ${token}`,
                'Idempotency-Key': idempotencyKey,
            },
            body: form,
        })
        const payload = await response.json().catch(() => null)
        if (
            (response.ok || response.status === 422)
            && payload
            && typeof payload.session_public_id === 'string'
        ) {
            return payload as ImportSession
        }
        const error = resolveApiError(payload, response.status)
        throw new ApiRequestError(
            response.status,
            error.message,
            error.code,
            error.positionPublicId,
        )
    },

    getImportSession: async (
        token: string,
        sessionPublicId: string,
    ): Promise<ImportSession> => {
        return fetchAPI(
            `/api/positions/import/sessions/${encodeURIComponent(sessionPublicId)}`,
            {},
            token,
        )
    },

    confirmImport: async (
        token: string,
        sessionPublicId: string,
        selectedRowPublicIds: string[],
        idempotencyKey: string,
    ): Promise<ImportConfirmResponse> => {
        const response = await fetch(`${API_BASE}/api/positions/import/confirm`, {
            method: 'POST',
            headers: {
                Authorization: `Bearer ${token}`,
                'Content-Type': 'application/json',
                'Idempotency-Key': idempotencyKey,
            },
            body: JSON.stringify({
                session_public_id: sessionPublicId,
                selected_row_public_ids: selectedRowPublicIds,
            }),
        })
        const payload = await response.json().catch(() => null)
        if (response.ok) return payload as ImportConfirmResponse
        const error = resolveApiError(payload, response.status)
        throw new ApiRequestError(
            response.status,
            error.message,
            error.code,
            error.positionPublicId,
        )
    },

    downloadImportTemplate: async (token: string): Promise<Blob> => {
        const response = await fetch(`${API_BASE}/api/positions/import/template`, {
            headers: { Authorization: `Bearer ${token}` },
        })
        if (!response.ok) {
            const payload = await response.json().catch(() => null)
            const error = resolveApiError(payload, response.status)
            throw new ApiRequestError(response.status, error.message, error.code)
        }
        return response.blob()
    },

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
        data: TradingPositionTradeEventCreate,
        idempotencyKey: string,
    ): Promise<LifecycleDetailResponse> => {
        return fetchAPI(`/api/trading-positions/${positionPublicId}/events`, {
            method: 'POST',
            headers: { 'Idempotency-Key': idempotencyKey },
            body: JSON.stringify(data),
        }, token)
    },

    reverseTradingPositionTradeEvent: async (
        token: string,
        positionPublicId: string,
        eventPublicId: string,
        data: TradingPositionTradeEventReverseCreate,
        idempotencyKey: string,
        requestId?: string,
    ): Promise<LifecycleDetailResponse> => {
        return fetchAPI(`/api/trading-positions/${positionPublicId}/events/${eventPublicId}/reverse`, {
            method: 'POST',
            headers: {
                'Idempotency-Key': idempotencyKey,
                'X-Request-ID': requestId || idempotencyKey,
            },
            body: JSON.stringify(data),
        }, token)
    },

    voidTradingPosition: async (
        token: string,
        positionPublicId: string,
        data: TradingPositionVoidCreate,
        idempotencyKey: string,
        requestId?: string,
    ): Promise<LifecycleDetailResponse> => {
        return fetchAPI(`/api/trading-positions/${positionPublicId}/void`, {
            method: 'POST',
            headers: {
                'Idempotency-Key': idempotencyKey,
                'X-Request-ID': requestId || idempotencyKey,
            },
            body: JSON.stringify(data),
        }, token)
    },

    create: async (token: string, data: PositionCreate, idempotencyKey: string): Promise<Position> => {
        return fetchAPI('/api/positions', {
            method: 'POST',
            headers: { 'Idempotency-Key': idempotencyKey },
            body: JSON.stringify(data),
        }, token)
    },

    update: async (token: string, id: number | string, data: PositionUpdatePayload): Promise<Position> => {
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

    checkOpen: async (token: string, identity: PositionOpenIdentity): Promise<Position | null> => {
        const query = new URLSearchParams(
            Object.entries(identity).map(([key, value]) => [key, String(value)])
        )
        return fetchAPI(`/api/positions/check/open?${query.toString()}`, {}, token)
    },

    analyze: async (token: string, id: number | string): Promise<PositionMarketAnalysis> => {
        return fetchAPI(`/api/positions/${id}/analyze`, {
            method: 'POST',
        }, token)
    },

    // Legacy batch mutations remain read-only on public product routes.
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
