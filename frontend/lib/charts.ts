import type { WorkbenchTone } from './adapters/timeline-workbench.ts'

export type SupportedChartType = 'bar' | 'line' | 'pie' | 'scatter' | 'sankey'
export type DashboardAllocationDimension = 'CORE_TYPE' | 'MARKET' | 'RISK'

export interface ChartSeriesRef {
  field: string
  label: string
  color?: string
}

export interface ChartDimensionRef {
  field: string
  label: string
}

export interface ChartSchema {
  schema_version: 'chart.v1'
  chart_type: SupportedChartType
  series: ChartSeriesRef[]
  dimensions?: ChartDimensionRef[]
  data_path?: string
  options?: Record<string, string | number | boolean | null>
}

export interface ChartTrustMeta {
  as_of?: string
  generated_at?: string
  freshness?: 'FRESH' | 'DELAYED' | 'STALE' | 'DEGRADED' | string
  source?: string
  source_refs?: string[]
  maturity?: string
  value_status?: string
  note?: string
}

export interface ChartEmptyState {
  is_empty: boolean
  reason: string | null
  message?: string
}

export interface ChartPayload<TData = Record<string, unknown>> {
  chart_schema: ChartSchema
  data: TData[]
  empty_state: ChartEmptyState
  trust_meta: ChartTrustMeta
}

export interface AllocationChartDataPoint {
  name: string
  value: number
  percent: number
}

export interface DashboardAllocationChartView {
  data: AllocationChartDataPoint[]
  emptyState: ChartEmptyState
  isEmpty: boolean
  schema: ChartSchema | null
  trustMeta: ChartTrustMeta
}

type AllocationPayloadInput = {
  name?: unknown
  value?: unknown
  percent?: unknown
}

const supportedChartTypes: ReadonlySet<string> = new Set(['bar', 'line', 'pie', 'scatter', 'sankey'])

export function assertSupportedChartSchema(schema: ChartSchema | null | undefined): boolean {
  if (!schema) return false
  if (schema.schema_version !== 'chart.v1') return false
  if (!supportedChartTypes.has(schema.chart_type)) return false
  if (!Array.isArray(schema.series) || schema.series.length === 0) return false
  if (schema.dimensions && !schema.dimensions.every((dimension) => Boolean(dimension.field && dimension.label))) return false
  return schema.series.every((series) => Boolean(series.field && series.label))
}

export function getChartSchemaBadge(schema: ChartSchema | null | undefined): string | null {
  if (!schema) return null
  if (!assertSupportedChartSchema(schema)) return null
  return `${schema.schema_version} · ${schema.chart_type}`
}

export function getChartFreshnessTone(trust: ChartTrustMeta | null | undefined): WorkbenchTone {
  if (trust?.freshness === 'FRESH') return 'positive'
  if (trust?.freshness === 'DEGRADED') return 'danger'
  if (trust?.freshness === 'DELAYED' || trust?.freshness === 'STALE') return 'warning'
  return 'neutral'
}

export function formatChartTrustLabel(trust: ChartTrustMeta | null | undefined): string {
  if (!trust || (!trust.freshness && !trust.source && !trust.as_of)) return 'local view'

  const pieces: string[] = []
  if (trust.freshness) pieces.push(trust.freshness.toLowerCase())
  if (trust.source) pieces.push(trust.source)
  if (trust.as_of) pieces.push(`as of ${new Date(trust.as_of).toLocaleString('zh-CN')}`)
  return pieces.length > 0 ? pieces.join(' · ') : 'local view'
}

export function buildChartEmptyState(
  payload: { empty_state?: ChartEmptyState } | undefined,
  fallbackReason: string
): ChartEmptyState {
  if (payload?.empty_state) return payload.empty_state
  return {
    is_empty: true,
    reason: fallbackReason,
    message: fallbackReason,
  }
}

export function hasChartData<TData>(data: TData[] | undefined, emptyState?: ChartEmptyState | null): boolean {
  if (emptyState?.is_empty) return false
  return Array.isArray(data) && data.length > 0
}

export function getDashboardChartPayloadKey(dimension: DashboardAllocationDimension) {
  if (dimension === 'MARKET') return 'market'
  if (dimension === 'RISK') return 'risk_level'
  return 'core_type'
}

export function adaptDashboardAllocationChartPayload(
  payload: ChartPayload<AllocationPayloadInput> | undefined
): DashboardAllocationChartView {
  if (!payload) {
    return {
      data: [],
      emptyState: buildChartEmptyState(undefined, 'MISSING_CHART_PAYLOAD'),
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
    message: payload.empty_state?.message,
  }

  return {
    data,
    emptyState,
    isEmpty: emptyState.is_empty,
    schema: payload.chart_schema ?? null,
    trustMeta: payload.trust_meta ?? {},
  }
}

export function buildDashboardAllocationFallbackChart(
  data: AllocationChartDataPoint[],
  dimension: DashboardAllocationDimension
): DashboardAllocationChartView {
  const isEmpty = data.length === 0

  return {
    data,
    emptyState: {
      is_empty: isEmpty,
      reason: isEmpty ? 'NO_ALLOCATION_DATA' : null,
      message: isEmpty ? 'NO_ALLOCATION_DATA' : undefined,
    },
    isEmpty,
    schema: {
      schema_version: 'chart.v1',
      chart_type: 'pie',
      data_path: getDashboardChartPayloadKey(dimension),
      dimensions: [{ field: 'name', label: 'Allocation bucket' }],
      series: [{ field: 'value', label: 'Value' }],
    },
    trustMeta: {
      freshness: 'DELAYED',
      source: 'LOCAL_FALLBACK_VIEW',
      source_refs: [`dashboard:allocation:${dimension}`],
    },
  }
}
