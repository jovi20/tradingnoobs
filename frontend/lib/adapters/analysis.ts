export interface AnalysisDateRange {
    startDate: string
    endDate: string
}

const ONE_DAY_MS = 24 * 60 * 60 * 1000
const MAX_INCLUSIVE_RANGE_DAYS = 366

export function getDefaultAnalysisDateRange(now: Date = new Date()): AnalysisDateRange {
    const end = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()))
    const start = new Date(end.getTime() - 29 * ONE_DAY_MS)

    return {
        startDate: toDateInputValue(start),
        endDate: toDateInputValue(end),
    }
}

export function validateAnalysisDateRange(startDate: string, endDate: string): string | null {
    if (startDate && !endDate) return '请选择结束日期'
    if (!startDate && endDate) return '请选择开始日期'
    if (!startDate && !endDate) return '请选择开始日期和结束日期'

    const start = parseDateInput(startDate)
    const end = parseDateInput(endDate)
    if (!start || !end) return '日期格式无效'
    if (start.getTime() > end.getTime()) return '开始日期不能晚于结束日期'

    const inclusiveDays = Math.floor((end.getTime() - start.getTime()) / ONE_DAY_MS) + 1
    if (inclusiveDays > MAX_INCLUSIVE_RANGE_DAYS) {
        return '分析区间不能超过 366 天'
    }

    return null
}

export function formatAnalysisDateRangeLabel(startDate: string, endDate: string): string {
    return `${startDate} 至 ${endDate}`
}

function parseDateInput(value: string): Date | null {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return null

    const date = new Date(`${value}T00:00:00Z`)
    if (Number.isNaN(date.getTime())) return null

    return toDateInputValue(date) === value ? date : null
}

function toDateInputValue(date: Date): string {
    return date.toISOString().slice(0, 10)
}
