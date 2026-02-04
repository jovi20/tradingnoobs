/**
 * 标的代码格式检测工具
 * 根据输入格式判断标的类型，在调用API前进行前端预判断
 */

export type AssetType = 'A_STOCK' | 'HK_STOCK' | 'CRYPTO' | 'US_STOCK' | 'UNKNOWN' | 'EQUITY' | 'ETF_EQUITY' | 'ETF_BOND' | 'ETF_COMMODITY' | 'FOREX' | 'CASH'

export interface SymbolDetection {
    type: AssetType
    normalized: string
    label: string
    provider: string
    format: string
}

/**
 * 标的格式规则:
 * 
 * A股:
 *   - 上海: 6开头6位 (600xxx, 601xxx, 603xxx, 688xxx)
 *   - 深圳: 0开头6位 (000xxx, 001xxx, 002xxx, 003xxx)
 *   - 创业板: 300xxx
 *   - 北交所: 8开头 (8xxxxx)
 * 
 * 港股:
 *   - 5位数字 或 带.HK后缀 (00700, 09988.HK)
 * 
 * 加密货币:
 *   - 以USDT/BUSD结尾 (BTCUSDT, ETHUSDT)
 *   - 或 带-斜杠分隔 (BTC/USDT, BTC-USDT)
 * 
 * 美股:
 *   - 1-5位英文字母 (AAPL, TSLA, NVDA)
 */
export function detectSymbolType(symbol: string): SymbolDetection {
    const s = symbol.trim().toUpperCase()

    if (!s) {
        return { type: 'UNKNOWN', normalized: '', label: '', provider: '', format: '' }
    }

    // A股检测: 6位数字
    const aSharePatterns = [
        /^6\d{5}$/,      // 上海主板 600xxx, 601xxx, 603xxx, 688xxx
        /^0[0-3]\d{4}$/, // 深圳主板/中小板 000xxx, 001xxx, 002xxx, 003xxx
        /^300\d{3}$/,    // 创业板
        /^8\d{5}$/,      // 北交所
    ]
    for (const pattern of aSharePatterns) {
        if (pattern.test(s)) {
            return {
                type: 'A_STOCK',
                normalized: s,
                label: 'A股',
                provider: 'AKShare',
                format: '6位数字 (如 600519, 000001)'
            }
        }
    }

    // 港股检测: 5位数字 或 .HK后缀
    if (/^\d{5}$/.test(s) || s.endsWith('.HK')) {
        const normalized = s.replace('.HK', '').padStart(5, '0')
        return {
            type: 'HK_STOCK',
            normalized: normalized,
            label: '港股',
            provider: 'AKShare',
            format: '5位数字 (如 00700, 09988)'
        }
    }

    // 加密货币检测: USDT/BUSD结尾 或 含分隔符
    const cryptoPatterns = [
        /^[A-Z]+USDT$/,   // BTCUSDT
        /^[A-Z]+BUSD$/,   // BTCBUSD
        /^[A-Z]+\/USDT$/, // BTC/USDT
        /^[A-Z]+-USDT$/,  // BTC-USDT
    ]
    for (const pattern of cryptoPatterns) {
        if (pattern.test(s)) {
            // 标准化为XXXUSDT格式
            const normalized = s.replace(/[\/\-]/, '').replace('BUSD', 'USDT')
            return {
                type: 'CRYPTO',
                normalized: normalized,
                label: '加密货币',
                provider: 'Binance',
                format: '交易对 (如 BTCUSDT, ETHUSDT)'
            }
        }
    }

    // 美股检测: 1-5位纯字母
    if (/^[A-Z]{1,5}$/.test(s)) {
        return {
            type: 'US_STOCK',
            normalized: s,
            label: '美股',
            provider: 'Finnhub',
            format: '1-5位字母 (如 AAPL, TSLA)'
        }
    }

    // 无法识别
    return {
        type: 'UNKNOWN',
        normalized: s,
        label: '未知',
        provider: '',
        format: '请输入正确格式: A股(6位数字), 港股(5位数字), 美股(字母), 加密(XXXUSDT)'
    }
}

/**
 * 获取资产类型的颜色样式
 */
export function getAssetTypeColor(type: AssetType): string {
    switch (type) {
        case 'A_STOCK': return 'text-slate-900 bg-slate-100 dark:bg-slate-700 dark:text-white'
        case 'HK_STOCK': return 'text-slate-600 bg-slate-50 dark:bg-slate-800 dark:text-slate-300'
        case 'CRYPTO': return 'text-slate-800 bg-slate-200 dark:bg-slate-600 dark:text-white'
        case 'US_STOCK':
        case 'EQUITY':
        case 'ETF_EQUITY': return 'text-slate-900 bg-slate-100 dark:bg-slate-700 dark:text-white'
        case 'ETF_BOND': return 'text-slate-500 bg-slate-50 dark:bg-slate-800'
        case 'ETF_COMMODITY': return 'text-slate-700 bg-slate-100 dark:bg-slate-700'
        case 'FOREX': return 'text-slate-600 bg-slate-200 dark:bg-slate-600'
        default: return 'text-slate-500 bg-slate-50 dark:bg-slate-800'
    }
}

/**
 * 获取资产类型的中文名称
 */
export function getAssetTypeLabel(type: AssetType): string {
    switch (type) {
        case 'A_STOCK': return 'A股'
        case 'HK_STOCK': return '港股'
        case 'CRYPTO': return '加密货币'
        case 'US_STOCK': return '美股'
        case 'EQUITY': return '股票'
        case 'ETF_EQUITY': return '股票型ETF'
        case 'ETF_BOND': return '债券ETF'
        case 'ETF_COMMODITY': return '商品ETF'
        case 'FOREX': return '外汇'
        case 'CASH': return '现金'
        default: return type
    }
}

/**
 * 获取资产类型的十六进制颜色值 (用于图表 - 灰色系/单色系)
 */
export function getAssetTypeHexColor(type: string): string {
    switch (type) {
        case 'A_STOCK': return '#0f172a' // slate-900
        case 'HK_STOCK': return '#334155' // slate-700
        case 'CRYPTO': return '#64748b' // slate-500
        case 'US_STOCK':
        case 'EQUITY':
        case 'ETF_EQUITY': return '#0f172a' // slate-900
        case 'ETF_BOND': return '#94a3b8' // slate-400
        case 'ETF_COMMODITY': return '#cbd5e1' // slate-300
        case 'FOREX': return '#475569' // slate-600
        case 'CASH': return '#e2e8f0' // slate-200
        default: return '#94a3b8' // slate-400
    }
}
