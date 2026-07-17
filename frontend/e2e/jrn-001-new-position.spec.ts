import { expect, test, type Page, type Route } from '@playwright/test'

const user = {
    id: 1,
    public_id: 'user-public-id',
    email: 'journal@example.com',
    status: 'ACTIVE',
    is_active: true,
    role: 'user',
    timezone: 'Asia/Shanghai',
    created_at: '2026-07-17T00:00:00Z',
}

const account = {
    id: 7,
    public_id: 'account-public-id',
    user_id: 1,
    name: 'IBKR Journal',
    broker: 'IBKR',
    currency: 'USD',
    initial_balance: 0,
    journal_balance: 0,
    is_active: true,
    created_at: '2026-07-17T00:00:00Z',
}

const existingPosition = {
    id: 11,
    public_id: 'position-public-id',
    truth_position_public_id: 'truth-position-public-id',
    user_id: 1,
    account_id: account.id,
    symbol: 'BTC/USD',
    exchange: 'COINBASE',
    asset_type: 'CRYPTO',
    direction: 'LONG',
    status: 'OPEN',
    total_quantity: 2,
    average_entry_price: 65000,
    realized_pnl: 0,
    opened_at: '2026-07-17T00:00:00Z',
    created_at: '2026-07-17T00:00:00Z',
    screenshots: [],
    lessons: [],
    batches: [],
    asset_metadata: {
        symbol: 'BTC/USD',
        name: 'BTC/USD',
        core_type: 'CRYPTO',
        market: 'CRYPTO',
        currency: 'USD',
        sector: null,
        instrument: 'SPOT',
    },
}

type ApiHandler = (route: Route, url: URL) => Promise<boolean>

async function fulfillJson(route: Route, body: unknown, status = 200) {
    await route.fulfill({
        status,
        contentType: 'application/json',
        body: JSON.stringify(body),
    })
}

async function installApi(page: Page, handler: ApiHandler) {
    await page.addInitScript(() => {
        window.localStorage.setItem('tradingnoobs_token', 'browser-test-token')
    })
    await page.route('**/api/**', async route => {
        const url = new URL(route.request().url())
        if (await handler(route, url)) return
        if (url.pathname === '/api/auth/me') {
            await fulfillJson(route, user)
            return
        }
        if (url.pathname === '/api/settings') {
            await fulfillJson(route, { id: 1, user_id: 1, theme: 'system' })
            return
        }
        if (url.pathname === '/api/accounts') {
            await fulfillJson(route, [account])
            return
        }
        if (url.pathname === '/api/strategies') {
            await fulfillJson(route, [])
            return
        }
        await fulfillJson(route, { detail: 'Unexpected test API request' }, 500)
    })
}

async function choose(page: Page, label: string, option: RegExp) {
    await page.getByRole('button', { name: label, exact: true }).click()
    await page.getByRole('option', { name: option }).click()
}

async function fillTradeFields(page: Page, symbol: string) {
    await page.getByPlaceholder('AAPL, SPY, BTC/USD').fill(symbol)
    await page.getByPlaceholder('NASDAQ, NYSE, ARCA, COINBASE').fill(' coinbase ')
    await choose(page, '核心类型', /加密资产/)
    await choose(page, '市场', /加密市场/)
    await page.getByPlaceholder('0.00').fill('66000')
    await page.getByPlaceholder('0', { exact: true }).fill('0.5')
}

async function expectNoHorizontalOverflow(page: Page) {
    const dimensions = await page.evaluate(() => ({
        scrollWidth: document.documentElement.scrollWidth,
        clientWidth: document.documentElement.clientWidth,
    }))
    expect(dimensions.scrollWidth).toBeLessThanOrEqual(dimensions.clientWidth)
}

test('complete identity preserves hedge-by-direction and ADD writes truth only', async ({ page }) => {
    const checkRequests: URL[] = []
    const truthWrites: unknown[] = []
    const legacyBatchWrites: string[] = []

    await installApi(page, async (route, url) => {
        if (url.pathname === '/api/positions/check/open') {
            checkRequests.push(url)
            await fulfillJson(
                route,
                url.searchParams.get('direction') === 'LONG' ? existingPosition : null,
            )
            return true
        }
        if (url.pathname === `/api/positions/${existingPosition.public_id}/truth-lifecycle`) {
            await fulfillJson(route, {
                data: { position_summary: { public_id: existingPosition.truth_position_public_id } },
                meta: {},
            })
            return true
        }
        if (url.pathname === `/api/trading-positions/${existingPosition.truth_position_public_id}/events`) {
            truthWrites.push(route.request().postDataJSON())
            await fulfillJson(route, { data: {}, meta: {} })
            return true
        }
        if (url.pathname.includes('/batches')) {
            legacyBatchWrites.push(url.pathname)
            await fulfillJson(route, {}, 500)
            return true
        }
        return false
    })

    await page.goto('/positions/import')
    await expect(page.getByRole('heading', { name: '404' })).toBeVisible()
    await expect(page.getByRole('heading', { name: '批量导入交易' })).toHaveCount(0)

    await page.goto('/positions/new')
    await expect(page.getByRole('heading', { name: '新增交易' })).toBeVisible()
    await fillTradeFields(page, ' btc/usd ')

    await expect.poll(() => checkRequests.length).toBeGreaterThan(0)
    const firstCheck = checkRequests.at(-1)!
    expect(firstCheck.pathname).toBe('/api/positions/check/open')
    expect(firstCheck.searchParams.get('account_id')).toBe(String(account.id))
    expect(firstCheck.searchParams.get('symbol')).toBe('BTC/USD')
    expect(firstCheck.searchParams.get('exchange_code')).toBe('COINBASE')
    expect(firstCheck.searchParams.get('asset_type')).toBe('CRYPTO')
    expect(firstCheck.searchParams.get('market')).toBe('CRYPTO')
    expect(firstCheck.searchParams.get('instrument_type')).toBe('SPOT')
    expect(firstCheck.searchParams.get('quote_currency')).toBe('USD')
    await expect(page.getByText('检测到已有 BTC/USD 持仓')).toBeVisible()
    await expect(page.getByRole('button', { name: '创建交易' })).toBeDisabled()

    const beforeShort = checkRequests.length
    await page.getByRole('button', { name: '做空' }).click()
    await expect.poll(() => checkRequests.length).toBeGreaterThan(beforeShort)
    await expect(page.getByText('检测到已有 BTC/USD 持仓')).toBeHidden()
    await expect(page.getByRole('button', { name: '创建交易' })).toBeEnabled()

    const beforeLong = checkRequests.length
    await page.getByRole('button', { name: '做多' }).click()
    await expect.poll(() => checkRequests.length).toBeGreaterThan(beforeLong)
    await expect(page.getByText('检测到已有 BTC/USD 持仓')).toBeVisible()

    const beforeAdd = checkRequests.length
    await page.getByRole('button', { name: '加仓到此仓位' }).click()
    await expect.poll(() => checkRequests.length).toBeGreaterThan(beforeAdd)
    await expect.poll(() => truthWrites.length).toBe(1)
    expect(truthWrites[0]).toMatchObject({
        event_type: 'ADD',
        quantity: 0.5,
        price: 66000,
        currency: 'USD',
    })
    expect(legacyBatchWrites).toEqual([])
    await expectNoHorizontalOverflow(page)
})

test('non-ASCII is rejected and a duplicate-OPEN race recovers into ADD', async ({ page }) => {
    const checkRequests: URL[] = []
    const createBodies: unknown[] = []
    let duplicateWon = false

    await installApi(page, async (route, url) => {
        if (url.pathname === '/api/positions/check/open') {
            checkRequests.push(url)
            await fulfillJson(route, duplicateWon ? existingPosition : null)
            return true
        }
        if (url.pathname === '/api/positions' && route.request().method() === 'POST') {
            createBodies.push(route.request().postDataJSON())
            duplicateWon = true
            await fulfillJson(route, {
                detail: {
                    code: 'OPEN_POSITION_EXISTS',
                    message: 'Use ADD for an existing same-side lifecycle',
                    position_public_id: existingPosition.public_id,
                },
            }, 409)
            return true
        }
        return false
    })

    await page.goto('/positions/new')
    await expect(page.getByRole('heading', { name: '新增交易' })).toBeVisible()
    await fillTradeFields(page, '\u00a0btc/usd')
    await page.getByRole('button', { name: '创建交易' }).click()
    await expect(page.getByText('标的代码仅支持 ASCII 字符')).toBeVisible()
    expect(createBodies).toEqual([])
    expect(checkRequests).toEqual([])

    await page.getByPlaceholder('AAPL, SPY, BTC/USD').fill(' btc/usd ')
    await expect.poll(() => checkRequests.length).toBeGreaterThan(0)
    await page.getByRole('button', { name: '创建交易' }).click()

    await expect.poll(() => createBodies.length).toBe(1)
    expect(createBodies[0]).toMatchObject({
        account_id: account.id,
        symbol: 'BTC/USD',
        exchange_code: 'COINBASE',
        asset_type: 'CRYPTO',
        direction: 'LONG',
        asset_metadata: {
            core_type: 'CRYPTO',
            market: 'CRYPTO',
            currency: 'USD',
            instrument: 'SPOT',
        },
    })
    await expect(page.getByText('检测到已有 BTC/USD 持仓')).toBeVisible()
    await expect(page.getByRole('button', { name: '加仓到此仓位' })).toBeVisible()
    await expect(page.getByText('[object Object]')).toHaveCount(0)
    await expectNoHorizontalOverflow(page)
})
