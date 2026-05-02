import Link from 'next/link'
import { AlertTriangle, CheckCircle2, ChevronRight } from 'lucide-react'

import { getInboxSeverityAccent } from '@/lib/adapters/timeline'
import type { ReviewInboxItem } from '@/lib/read-models'

interface ReviewInboxCardProps {
    item: ReviewInboxItem
}

export function ReviewInboxCard({ item }: ReviewInboxCardProps) {
    return (
        <div className={`rounded-xl border p-4 ${getInboxSeverityAccent(item.severity)}`}>
            <div className="flex items-start justify-between gap-3">
                <div>
                    <p className="text-sm font-semibold">{item.summary}</p>
                    <p className="mt-1 text-xs opacity-80">{item.reason}</p>
                </div>
                {item.severity === 'CRITICAL' ? (
                    <AlertTriangle className="mt-0.5 w-4 h-4 shrink-0" />
                ) : (
                    <CheckCircle2 className="mt-0.5 w-4 h-4 shrink-0 opacity-70" />
                )}
            </div>
            <div className="mt-3 flex items-center justify-between gap-3">
                <div className="text-[11px] opacity-70">
                    {new Date(item.occurred_at).toLocaleString('zh-CN')}
                </div>
                <Link
                    href={item.recommended_action.href}
                    className="inline-flex items-center gap-1 text-xs font-semibold hover:opacity-80"
                >
                    {item.recommended_action.label}
                    <ChevronRight className="w-3 h-3" />
                </Link>
            </div>
        </div>
    )
}
