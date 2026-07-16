import { buildPieSlices } from './chartGeometry'

interface SvgPieChartProps<T> {
    data: T[]
    getLabel: (item: T) => string
    getValue: (item: T) => number
    getColor: (item: T) => string
    onSliceClick?: (item: T) => void
}

export function SvgPieChart<T>({ data, getLabel, getValue, getColor, onSliceClick }: SvgPieChartProps<T>) {
    const radius = 92
    const slices = buildPieSlices(data.map(getValue), radius)
    const total = data.reduce((sum, item) => sum + Math.max(0, getValue(item)), 0) || 1

    return (
        <div className="grid h-full min-h-[300px] gap-4 md:grid-cols-[minmax(0,1fr)_180px] md:items-center">
            <svg role="img" aria-label="资产配置饼图" className="h-full min-h-[220px] w-full" viewBox={`0 0 ${radius * 2} ${radius * 2}`}>
                {slices.map((slice, index) => {
                    const item = data[index]
                    return (
                        <path
                            key={`${getLabel(item)}-${index}`}
                            d={slice.path}
                            fill={getColor(item)}
                            stroke="white"
                            strokeWidth={2}
                            className={onSliceClick ? 'cursor-pointer transition opacity-90 hover:opacity-100' : undefined}
                            onClick={() => onSliceClick?.(item)}
                        >
                            <title>{`${getLabel(item)}: ${((getValue(item) / total) * 100).toFixed(1)}%`}</title>
                        </path>
                    )
                })}
                <circle cx={radius} cy={radius} r={54} className="fill-panel" />
                <text x={radius} y={radius - 4} textAnchor="middle" className="fill-ink-muted text-[11px]">
                    类别
                </text>
                <text x={radius} y={radius + 16} textAnchor="middle" className="fill-ink text-[16px] font-bold">
                    {data.length}
                </text>
            </svg>
            <div className="space-y-2">
                {data.map((item, index) => (
                    <button
                        key={`${getLabel(item)}-${index}`}
                        type="button"
                        onClick={() => onSliceClick?.(item)}
                        className="flex w-full items-center justify-between gap-3 rounded-md px-2 py-1.5 text-left text-xs hover:bg-panel-subtle"
                    >
                        <span className="flex min-w-0 items-center gap-2">
                            <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ backgroundColor: getColor(item) }} />
                            <span className="truncate">{getLabel(item)}</span>
                        </span>
                        <span className="font-semibold">{((getValue(item) / total) * 100).toFixed(1)}%</span>
                    </button>
                ))}
            </div>
        </div>
    )
}
