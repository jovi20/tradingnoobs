import test from 'node:test'
import assert from 'node:assert/strict'

import {
    adaptDashboardAllocationChartPayload,
    getDashboardChartPayloadKey,
} from '../lib/chartSchemas.ts'

test('schema-first dashboard chart payload adapts into allocation chart data', () => {
    const result = adaptDashboardAllocationChartPayload({
        chart_schema: {
            schema_version: 'chart.v1',
            chart_type: 'bar',
            data_path: 'core_type_allocation',
            dimensions: [{ field: 'name', label: 'Asset type allocation' }],
            series: [{ field: 'value', label: 'Value' }],
        },
        data: [
            { name: 'EQUITY', value: 750, percent: 75 },
            { name: 'CASH', value: 250, percent: 25 },
        ],
        empty_state: { is_empty: false, reason: null },
        trust_meta: {
            freshness: 'FRESH',
            source: 'DASHBOARD_DERIVED_READ_MODEL',
            source_refs: ['dashboard:stats', 'dashboard:allocation:CORE_TYPE'],
        },
    })

    assert.equal(result.isEmpty, false)
    assert.deepEqual(result.data, [
        { name: 'EQUITY', value: 750, percent: 75 },
        { name: 'CASH', value: 250, percent: 25 },
    ])
    assert.equal(result.schema?.schema_version, 'chart.v1')
    assert.equal(result.trustMeta.source, 'DASHBOARD_DERIVED_READ_MODEL')
})

test('missing dashboard chart payload returns an explicit empty state', () => {
    const result = adaptDashboardAllocationChartPayload(undefined)

    assert.equal(result.isEmpty, true)
    assert.deepEqual(result.data, [])
    assert.equal(result.emptyState.reason, 'MISSING_CHART_PAYLOAD')
})

test('dashboard chart payload keys stay stable for allocation dimensions', () => {
    assert.equal(getDashboardChartPayloadKey('CORE_TYPE'), 'core_type')
    assert.equal(getDashboardChartPayloadKey('MARKET'), 'market')
    assert.equal(getDashboardChartPayloadKey('RISK'), 'risk_level')
})
