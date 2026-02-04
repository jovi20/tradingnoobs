
export interface Holiday {
    date: string // YYYY-MM-DD
    name: string
    market: 'CN' | 'HK' | 'US'
}

export const HOLIDAYS: Holiday[] = [
    // === 2025 CN (A-Share) ===
    { date: '2025-01-01', name: '元旦', market: 'CN' },
    { date: '2025-01-28', name: '春节', market: 'CN' },
    { date: '2025-01-29', name: '春节', market: 'CN' },
    { date: '2025-01-30', name: '春节', market: 'CN' },
    { date: '2025-01-31', name: '春节', market: 'CN' },
    { date: '2025-02-03', name: '春节', market: 'CN' },
    { date: '2025-02-04', name: '春节', market: 'CN' },
    { date: '2025-04-04', name: '清明节', market: 'CN' },
    { date: '2025-05-01', name: '劳动节', market: 'CN' },
    { date: '2025-05-02', name: '劳动节', market: 'CN' },
    { date: '2025-05-05', name: '劳动节', market: 'CN' }, // Adjust if substitution
    { date: '2025-06-02', name: '端午节', market: 'CN' }, // June 2 (Mon) for May 31
    { date: '2025-10-01', name: '国庆节', market: 'CN' },
    { date: '2025-10-02', name: '国庆节', market: 'CN' },
    { date: '2025-10-03', name: '国庆节', market: 'CN' },
    { date: '2025-10-06', name: '国庆节', market: 'CN' },
    { date: '2025-10-07', name: '国庆节', market: 'CN' },
    { date: '2025-10-08', name: '国庆节', market: 'CN' },

    // === 2025 HK ===
    { date: '2025-01-01', name: '元旦', market: 'HK' },
    { date: '2025-01-29', name: '农历年初一', market: 'HK' },
    { date: '2025-01-30', name: '农历年初二', market: 'HK' },
    { date: '2025-01-31', name: '农历年初三', market: 'HK' },
    { date: '2025-04-04', name: '清明节', market: 'HK' },
    { date: '2025-04-18', name: '耶稣受难节', market: 'HK' },
    { date: '2025-04-19', name: '耶稣受难节翌日', market: 'HK' },
    { date: '2025-04-21', name: '复活节星期一', market: 'HK' },
    { date: '2025-05-01', name: '劳动节', market: 'HK' },
    { date: '2025-05-05', name: '佛诞', market: 'HK' },
    { date: '2025-05-31', name: '端午节', market: 'HK' },
    { date: '2025-07-01', name: '特区成立纪念日', market: 'HK' },
    { date: '2025-10-01', name: '国庆日', market: 'HK' },
    { date: '2025-10-07', name: '中秋节翌日', market: 'HK' }, // Check actual date
    { date: '2025-10-29', name: '重阳节', market: 'HK' },
    { date: '2025-12-25', name: '圣诞节', market: 'HK' },
    { date: '2025-12-26', name: '圣诞节后第一个周日', market: 'HK' },

    // === 2025 US ===
    { date: '2025-01-01', name: 'New Year\'s Day', market: 'US' },
    { date: '2025-01-20', name: 'Martin Luther King, Jr. Day', market: 'US' },
    { date: '2025-02-17', name: 'Washington\'s Birthday', market: 'US' },
    { date: '2025-04-18', name: 'Good Friday', market: 'US' },
    { date: '2025-05-26', name: 'Memorial Day', market: 'US' },
    { date: '2025-06-19', name: 'Juneteenth National Independence Day', market: 'US' },
    { date: '2025-07-04', name: 'Independence Day', market: 'US' },
    { date: '2025-09-01', name: 'Labor Day', market: 'US' },
    { date: '2025-11-27', name: 'Thanksgiving Day', market: 'US' },
    { date: '2025-12-25', name: 'Christmas Day', market: 'US' },

    // === 2026 CN (A-Share) - Estimates ===
    { date: '2026-01-01', name: '元旦', market: 'CN' },
    { date: '2026-02-17', name: '春节', market: 'CN' }, // Estimate
    { date: '2026-02-18', name: '春节', market: 'CN' },
    { date: '2026-02-19', name: '春节', market: 'CN' },
    { date: '2026-02-20', name: '春节', market: 'CN' },
    { date: '2026-02-23', name: '春节', market: 'CN' },

    // Add more as needed or fetch from API
]

export const getHolidays = (market: string, year: number, month: number) => {
    return HOLIDAYS.filter(h => {
        if (h.market !== market) return false
        const date = new Date(h.date)
        return date.getFullYear() === year && date.getMonth() === month
    })
}
