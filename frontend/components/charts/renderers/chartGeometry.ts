export interface ChartPoint {
    x: number
    y: number
}

export interface SvgLinePoint extends ChartPoint {
    cx: number
    cy: number
}

export interface PieSliceGeometry {
    value: number
    startAngle: number
    endAngle: number
    largeArcFlag: 0 | 1
    path: string
}

export interface ScatterPointGeometry extends ChartPoint {
    cx: number
    cy: number
    r: number
}

export interface SankeyNodeInput {
    name?: string
    id?: string | number
}

export interface SankeyLinkInput {
    source: string | number
    target: string | number
    value: number
}

export interface NormalizedSankeyLink extends SankeyLinkInput {
    value: number
}

export interface NormalizedSankeyData {
    nodes: SankeyNodeInput[]
    links: NormalizedSankeyLink[]
    isEmpty: boolean
    emptyReason: string | null
}

export function scaleLinear(domainMin: number, domainMax: number, rangeMin: number, rangeMax: number) {
    if (domainMin === domainMax) {
        const midpoint = rangeMin + (rangeMax - rangeMin) / 2
        return () => midpoint
    }
    return (value: number) => {
        const ratio = (value - domainMin) / (domainMax - domainMin)
        return rangeMin + ratio * (rangeMax - rangeMin)
    }
}

function extent(values: number[]): [number, number] {
    if (values.length === 0) return [0, 0]
    return [Math.min(...values), Math.max(...values)]
}

function polarToCartesian(radius: number, angle: number) {
    return {
        x: radius + radius * Math.cos(angle),
        y: radius + radius * Math.sin(angle),
    }
}

export function buildLinePath(points: ChartPoint[], width: number, height: number): string {
    if (points.length === 0) return ''
    const [minX, maxX] = extent(points.map((point) => point.x))
    const [minY, maxY] = extent(points.map((point) => point.y))
    const scaleX = scaleLinear(minX, maxX, 0, width)
    const scaleY = scaleLinear(minY, maxY, height, 0)
    return points
        .map((point, index) => `${index === 0 ? 'M' : 'L'}${scaleX(point.x).toFixed(2)},${scaleY(point.y).toFixed(2)}`)
        .join(' ')
}

export function buildPieSlices(values: number[], radius: number): PieSliceGeometry[] {
    const positiveValues = values.map((value) => Math.max(0, value))
    const total = positiveValues.reduce((sum, value) => sum + value, 0)
    if (total <= 0) return []

    let cursor = 0
    return positiveValues.map((value) => {
        const startAngle = cursor
        const endAngle = cursor + (value / total) * Math.PI * 2
        cursor = endAngle
        const start = polarToCartesian(radius, startAngle)
        const end = polarToCartesian(radius, endAngle)
        const largeArcFlag: 0 | 1 = endAngle - startAngle > Math.PI ? 1 : 0
        return {
            value,
            startAngle,
            endAngle,
            largeArcFlag,
            path: [
                `M${radius},${radius}`,
                `L${start.x.toFixed(2)},${start.y.toFixed(2)}`,
                `A${radius},${radius} 0 ${largeArcFlag} 1 ${end.x.toFixed(2)},${end.y.toFixed(2)}`,
                'Z',
            ].join(' '),
        }
    })
}

export function buildScatterPoints(points: ChartPoint[], width: number, height: number): ScatterPointGeometry[] {
    if (points.length === 0) return []
    const [minX, maxX] = extent(points.map((point) => point.x))
    const [minY, maxY] = extent(points.map((point) => point.y))
    const scaleX = scaleLinear(minX, maxX, 0, width)
    const scaleY = scaleLinear(minY, maxY, height, 0)
    return points.map((point) => ({
        ...point,
        cx: scaleX(point.x),
        cy: scaleY(point.y),
        r: 4,
    }))
}

export function normalizeSankeyLinks(data: {
    nodes: SankeyNodeInput[]
    links: SankeyLinkInput[]
}): NormalizedSankeyData {
    const validLinks = data.links
        .filter((link) => Number.isFinite(link.value) && link.value > 0)
        .map((link) => ({ ...link, value: Number(link.value) }))

    if (validLinks.length === 0) {
        return {
            nodes: [],
            links: [],
            isEmpty: true,
            emptyReason: 'No sankey links available',
        }
    }

    return {
        nodes: data.nodes,
        links: validLinks,
        isEmpty: false,
        emptyReason: null,
    }
}
