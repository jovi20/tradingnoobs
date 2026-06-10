import test from 'node:test'
import assert from 'node:assert/strict'

import {
  assertSupportedChartSchema,
  buildChartEmptyState,
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
  }), 'chart.v1 · scatter')

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

test('chart trust label keeps missing trust visible instead of hiding it', () => {
  assert.equal(formatChartTrustLabel({}), 'local view')
  assert.equal(formatChartTrustLabel({
    freshness: 'FRESH',
    source: 'DASHBOARD_DERIVED_READ_MODEL',
    as_of: '2026-06-10T08:00:00Z',
  }), 'fresh · DASHBOARD_DERIVED_READ_MODEL · as of 2026/6/10 16:00:00')
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
