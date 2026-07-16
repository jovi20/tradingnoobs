import { normalizeSankeyLinks, type SankeyLinkInput, type SankeyNodeInput } from './chartGeometry'

interface SvgSankeyChartProps {
    data: {
        nodes: SankeyNodeInput[]
        links: SankeyLinkInput[]
    }
    totalAssets: number
    isMobile: boolean
}

interface LayoutNode {
    index: number
    name: string
    value: number
    depth: number
    x: number
    y: number
    width: number
    height: number
    color: string
}

function nodeColor(name: string) {
    if (name.includes('Total Assets') || name.includes('总资产')) return '#8b5cf6'
    if (name.includes('负债') || name.includes('空头') || name.includes('Short') || name.includes('Borrowed')) return '#f87171'
    if (name.includes('资产') || name.includes('多头') || name.includes('现金') || name.includes('Long') || name.includes('Owned') || name.includes('Cash')) return '#34d399'
    return '#94a3b8'
}

function inferDepths(nodeCount: number, links: SankeyLinkInput[]) {
    const depths = Array.from({ length: nodeCount }, () => 0)
    for (let pass = 0; pass < nodeCount; pass += 1) {
        let changed = false
        for (const link of links) {
            const source = Number(link.source)
            const target = Number(link.target)
            if (!Number.isInteger(source) || !Number.isInteger(target)) continue
            if (depths[target] <= depths[source]) {
                depths[target] = depths[source] + 1
                changed = true
            }
        }
        if (!changed) break
    }
    return depths
}

function buildNodeValues(nodeCount: number, links: SankeyLinkInput[]) {
    const incoming = Array.from({ length: nodeCount }, () => 0)
    const outgoing = Array.from({ length: nodeCount }, () => 0)
    for (const link of links) {
        const source = Number(link.source)
        const target = Number(link.target)
        const value = Math.max(0, Number(link.value || 0))
        if (Number.isInteger(source) && source >= 0 && source < nodeCount) outgoing[source] += value
        if (Number.isInteger(target) && target >= 0 && target < nodeCount) incoming[target] += value
    }
    return incoming.map((value, index) => Math.max(value, outgoing[index], 1))
}

function layoutNodes(nodes: SankeyNodeInput[], links: SankeyLinkInput[], width: number, height: number): LayoutNode[] {
    const nodeWidth = 16
    const columnGap = 22
    const depths = inferDepths(nodes.length, links)
    const maxDepth = Math.max(1, ...depths)
    const values = buildNodeValues(nodes.length, links)
    const columns = new Map<number, number[]>()
    depths.forEach((depth, index) => {
        const column = columns.get(depth) || []
        column.push(index)
        columns.set(depth, column)
    })

    return nodes.map((node, index) => {
        const depth = depths[index]
        const column = columns.get(depth) || [index]
        const columnTotal = column.reduce((sum, nodeIndex) => sum + values[nodeIndex], 0) || 1
        const availableHeight = height - columnGap * Math.max(0, column.length - 1)
        let yCursor = 0
        for (const nodeIndex of column) {
            if (nodeIndex === index) break
            yCursor += Math.max(18, (values[nodeIndex] / columnTotal) * availableHeight) + columnGap
        }
        const nodeHeight = Math.max(18, (values[index] / columnTotal) * availableHeight)
        const x = (depth / maxDepth) * (width - nodeWidth)
        return {
            index,
            name: node.name || `节点 ${index + 1}`,
            value: values[index],
            depth,
            x,
            y: yCursor,
            width: nodeWidth,
            height: nodeHeight,
            color: nodeColor(node.name || ''),
        }
    })
}

export function SvgSankeyChart({ data, totalAssets, isMobile }: SvgSankeyChartProps) {
    const normalized = normalizeSankeyLinks(data)
    if (normalized.isEmpty) {
        return <div className="flex h-full min-h-[260px] items-center justify-center text-sm text-ink-muted">暂无资金流向数据</div>
    }

    const width = 760
    const height = isMobile ? 300 : 380
    const padding = { top: 28, right: isMobile ? 20 : 130, bottom: 24, left: 28 }
    const innerWidth = width - padding.left - padding.right
    const innerHeight = height - padding.top - padding.bottom
    const nodes = layoutNodes(normalized.nodes, normalized.links, innerWidth, innerHeight)
    const maxLinkValue = Math.max(...normalized.links.map((link) => Number(link.value)), 1)
    const total = totalAssets || 1

    return (
        <svg role="img" aria-label="组合资金流向桑基图" className="h-full w-full" viewBox={`0 0 ${width} ${height}`}>
            <g transform={`translate(${padding.left},${padding.top})`}>
                {normalized.links.map((link, index) => {
                    const source = nodes[Number(link.source)]
                    const target = nodes[Number(link.target)]
                    if (!source || !target) return null
                    const startX = source.x + source.width
                    const startY = source.y + source.height / 2
                    const endX = target.x
                    const endY = target.y + target.height / 2
                    const controlOffset = Math.max(40, Math.abs(endX - startX) * 0.55)
                    const strokeWidth = Math.max(2, (Number(link.value) / maxLinkValue) * 18)
                    return (
                        <path
                            key={`${link.source}-${link.target}-${index}`}
                            d={`M${startX},${startY} C${startX + controlOffset},${startY} ${endX - controlOffset},${endY} ${endX},${endY}`}
                            fill="none"
                            stroke="#cbd5e1"
                            strokeOpacity={0.42}
                            strokeWidth={strokeWidth}
                            strokeLinecap="round"
                        >
                            <title>{`${source.name} → ${target.name}: ${Number(link.value).toLocaleString()}`}</title>
                        </path>
                    )
                })}
                {nodes.map((node) => {
                    const percent = ((node.value / total) * 100).toFixed(1)
                    const labelOnLeft = node.x > innerWidth / 2
                    return (
                        <g key={`${node.name}-${node.index}`}>
                            <rect x={node.x} y={node.y} width={node.width} height={node.height} rx={3} fill={node.color} opacity={0.9} />
                            {!isMobile && (
                                <>
                                    <text
                                        x={labelOnLeft ? node.x - 8 : node.x + node.width + 8}
                                        y={node.y + node.height / 2 - 5}
                                        textAnchor={labelOnLeft ? 'end' : 'start'}
                                        className="fill-ink-soft text-[12px] font-semibold"
                                    >
                                        {node.name}
                                    </text>
                                    <text
                                        x={labelOnLeft ? node.x - 8 : node.x + node.width + 8}
                                        y={node.y + node.height / 2 + 11}
                                        textAnchor={labelOnLeft ? 'end' : 'start'}
                                        className="fill-ink-muted text-[11px]"
                                    >
                                        {percent}%（{node.value.toLocaleString()}）
                                    </text>
                                </>
                            )}
                            <title>{`${node.name}: ${percent}%（${node.value.toLocaleString()}）`}</title>
                        </g>
                    )
                })}
            </g>
        </svg>
    )
}
