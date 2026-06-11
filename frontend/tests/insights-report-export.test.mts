import test from 'node:test'
import assert from 'node:assert/strict'

import { insightsAPI } from '../lib/api.ts'
import { buildBlobDownloadFromResponse, filenameFromContentDisposition } from '../lib/download.ts'

test('insightsAPI.exportWeeklyReportPdf fetches the weekly report PDF path', async () => {
  const originalFetch = globalThis.fetch
  let requestedUrl = ''
  let requestedInit: RequestInit | undefined

  globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
    requestedUrl = String(input)
    requestedInit = init
    return new Response(new Blob(['%PDF-1.4']), {
      status: 200,
      headers: {
        'Content-Disposition': 'attachment; filename=tradingnoobs-weekly-report-2026-06-01.pdf',
      },
    })
  }) as typeof fetch

  try {
    const result = await insightsAPI.exportWeeklyReportPdf('token-1', 42)
    const requestHeaders = requestedInit?.headers as Record<string, string>

    assert.equal(new URL(requestedUrl).pathname, '/api/insights/42/export/pdf')
    assert.equal(requestHeaders.Authorization, 'Bearer token-1')
    assert.equal(requestHeaders.Accept, 'application/pdf')
    assert.equal(result.filename, 'tradingnoobs-weekly-report-2026-06-01.pdf')
    assert.equal(await result.blob.text(), '%PDF-1.4')
  } finally {
    globalThis.fetch = originalFetch
  }
})

test('helper uses filename from Content-Disposition when present', async () => {
  const response = new Response(new Blob(['pdf']), {
    headers: {
      'Content-Disposition': 'attachment; filename="weekly report.pdf"',
    },
  })

  const result = await buildBlobDownloadFromResponse(response, 'fallback.pdf')

  assert.equal(result.filename, 'weekly report.pdf')
  assert.equal(await result.blob.text(), 'pdf')
})

test('fallback filename is stable when Content-Disposition is absent', () => {
  assert.equal(
    filenameFromContentDisposition(null, 'tradingnoobs-weekly-report-42.pdf'),
    'tradingnoobs-weekly-report-42.pdf',
  )
})
