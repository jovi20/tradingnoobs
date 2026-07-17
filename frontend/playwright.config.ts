import { defineConfig } from '@playwright/test'

const port = 3100
const baseURL = `http://127.0.0.1:${port}`

export default defineConfig({
    testDir: './e2e',
    fullyParallel: false,
    workers: 1,
    timeout: 30_000,
    expect: { timeout: 8_000 },
    reporter: [['list']],
    outputDir: 'test-results',
    use: {
        baseURL,
        trace: 'retain-on-failure',
        screenshot: 'only-on-failure',
    },
    webServer: {
        command: `npm run dev -- --hostname 127.0.0.1 --port ${port}`,
        url: baseURL,
        reuseExistingServer: false,
        timeout: 120_000,
        env: {
            NEXT_PUBLIC_API_URL: baseURL,
            NEXT_TELEMETRY_DISABLED: '1',
        },
    },
    projects: [
        {
            name: 'desktop-1440x900',
            use: { viewport: { width: 1440, height: 900 } },
        },
        {
            name: 'mobile-390x844',
            use: { viewport: { width: 390, height: 844 } },
        },
    ],
})
