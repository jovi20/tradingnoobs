import type { ChartSchema, InsightArtifactTrustMeta } from './insightArtifacts.ts'

export type DashboardAllocationDimension = 'CORE_TYPE' | 'MARKET' | 'RISK'

export interface DashboardChartEmptyState {
    is_empty: boolean
    reason: string | null
}

export interface DashboardChartPayload<TData = Record<string, unknown>> {
    chart_schema: ChartSchema
    data: TData[]
    empty_state: DashboardChartEmptyState
    trust_meta: InsightArtifactTrustMeta
}

export interface AllocationChartDataPoint {
    name: string
    value: number
    percent: number
}

export interface DashboardAllocationChartView {
    data: AllocationChartDataPoint[]
    emptyState: DashboardChartEmptyState
    isEmpty: boolean
    schema: ChartSchema | null
    trustMeta: InsightArtifactTrustMeta
}

type AllocationPayloadInput = {
    name?: unknown
    value?: unknown
    percent?: unknown
}

export function getDashboardChartPayloadKey(dimension: DashboardAllocationDimension) {
    if (dimension === 'MARKET') return 'market'
    if (dimension === 'RISK') return 'risk_level'
    return 'core_type'
}

export function adaptDashboardAllocationChartPayload(
    payload: DashboardChartPayload<AllocationPayloadInput> | undefined
): DashboardAllocationChartView {
    if (!payload) {
        return {
            data: [],
            emptyState: { is_empty: true, reason: 'MISSING_CHART_PAYLOAD' },
            isEmpty: true,
            schema: null,
            trustMeta: {},
        }
    }

    const data = Array.isArray(payload.data)
        ? payload.data.map((item) => ({
            name: String(item.name ?? ''),
            value: Number(item.value ?? 0),
            percent: Number(item.percent ?? 0),
        })).filter((item) => item.name.length > 0)
        : []

    const emptyState = {
        is_empty: payload.empty_state?.is_empty ?? data.length === 0,
        reason: payload.empty_state?.reason ?? (data.length === 0 ? 'NO_ALLOCATION_DATA' : null),
    }

    return {
        data,
        emptyState,
        isEmpty: emptyState.is_empty,
        schema: payload.chart_schema ?? null,
        trustMeta: payload.trust_meta ?? {},
    }
}
