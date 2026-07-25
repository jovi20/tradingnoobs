import test from 'node:test'
import assert from 'node:assert/strict'

import {
  assertSupportedChartSchema,
  buildChartEmptyState,
  formatChartEmptyStateCopy,
  formatChartTrustLabel,
  getChartFreshnessTone,
  getChartSchemaBadge,
  hasChartData,
} from '../lib/charts.ts'

test('chart schema validation supports every current Recharts surface', () => {
  const types = ['bar', 'line', 'pie', 'scatter', 'sankey'] as const

  for (const chartType of types) {
    assert.equal(assertSupportedChartSchema({
      schema_version: 'chart.v1',
      chart_type: chartType,
      dimensions: [{ field: 'name', label: 'Name' }],
      series: [{ field: 'value', label: 'Value' }],
    }), true)
  }
})

test('chart schema validation rejects unversioned or fieldless charts', () => {
  assert.equal(assertSupportedChartSchema(null), false)
  assert.equal(assertSupportedChartSchema({
    schema_version: 'chart.v1',
    chart_type: 'bar',
    series: [],
  }), false)
  assert.equal(assertSupportedChartSchema({
    schema_version: 'chart.v1',
    chart_type: 'bar',
    dimensions: [{ field: '', label: 'Missing field' }],
    series: [{ field: 'value', label: 'Value' }],
  }), false)
})

test('chart schema badge is shared by dashboard and insight artifacts', () => {
  assert.equal(getChartSchemaBadge({
    schema_version: 'chart.v1',
    chart_type: 'scatter',
    series: [{ field: 'mfe', label: 'MFE' }],
  }), 'chart.v1 · 散点图')

  assert.equal(getChartSchemaBadge(null), null)
})

test('chart freshness maps to stable UI tones', () => {
  assert.equal(getChartFreshnessTone({ freshness: 'FRESH' }), 'positive')
  assert.equal(getChartFreshnessTone({ freshness: 'DELAYED' }), 'warning')
  assert.equal(getChartFreshnessTone({ freshness: 'STALE' }), 'warning')
  assert.equal(getChartFreshnessTone({ freshness: 'DEGRADED' }), 'danger')
  assert.equal(getChartFreshnessTone({ freshness: 'UNKNOWN_VENDOR_STATE' }), 'neutral')
  assert.equal(getChartFreshnessTone({}), 'neutral')
})

test('chart trust label keeps missing trust visible with localized copy', () => {
  const asOf = '2026-06-10T08:00:00Z'

  assert.equal(formatChartTrustLabel({}), '本地视图')
  assert.equal(formatChartTrustLabel({
    freshness: 'FRESH',
    source: 'DASHBOARD_DERIVED_READ_MODEL',
    as_of: asOf,
  }), `实时 · 组合汇总 · 数据时间 ${new Date(asOf).toLocaleString('zh-CN')}`)
  assert.equal(formatChartTrustLabel({
    freshness: 'UNKNOWN_VENDOR_STATE',
    source: 'UNKNOWN_TECHNICAL_SOURCE',
  }), '状态未知 · 系统数据')
})

test('chart empty state copy never exposes diagnostic codes or raw English messages', () => {
  assert.deepEqual(formatChartEmptyStateCopy({
    is_empty: true,
    reason: 'NO_ALLOCATION_DATA',
    message: 'NO_ALLOCATION_DATA',
  }), {
    title: '暂无图表数据',
    detail: '当前图表没有可展示的数据。',
  })
  assert.deepEqual(formatChartEmptyStateCopy({
    is_empty: true,
    reason: 'NO_SANKEY_LINKS',
    message: '暂无资金流向数据',
  }), {
    title: '暂无图表数据',
    detail: '暂无资金流向数据',
  })
})

test('chart empty state and data presence use payload flags plus actual data', () => {
  const emptyState = buildChartEmptyState(undefined, 'MISSING_CHART_PAYLOAD')
  assert.deepEqual(emptyState, {
    is_empty: true,
    reason: 'MISSING_CHART_PAYLOAD',
    message: 'MISSING_CHART_PAYLOAD',
  })

  assert.equal(hasChartData([{ name: 'A', value: 1 }], { is_empty: false, reason: null }), true)
  assert.equal(hasChartData([], { is_empty: false, reason: null }), false)
  assert.equal(hasChartData([{ name: 'A', value: 1 }], { is_empty: true, reason: 'NO_DATA' }), false)
})
