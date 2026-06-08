'use client'

import Link from 'next/link'
import { useParams } from 'next/navigation'
import { ArrowLeft, Loader2 } from 'lucide-react'

import { InsightArtifactDetailCard } from '@/components/insights/InsightArtifactDetailCard'
import { useAuth } from '@/contexts/AuthContext'
import { useInsightArtifact } from '@/hooks/useInsightArtifact'

export default function InsightArtifactDetailPage() {
    const { token } = useAuth()
    const params = useParams()
    const artifactId = params.artifactId as string
    const query = useInsightArtifact(token, artifactId)

    if (query.isLoading) {
        return (
            <div className="flex items-center justify-center py-20">
                <Loader2 className="h-8 w-8 animate-spin text-primary-500" />
            </div>
        )
    }

    if (query.error || !query.data) {
        return (
            <div className="card p-8 text-center">
                <p className="text-sm text-slate-500">Insight artifact not found.</p>
                <Link href="/insights" className="mt-4 inline-flex text-sm font-semibold text-primary-600">
                    Back to insights
                </Link>
            </div>
        )
    }

    return (
        <div className="space-y-4 pb-20 md:pb-6">
            <Link href="/insights" className="inline-flex items-center gap-2 text-sm font-semibold text-primary-600">
                <ArrowLeft className="h-4 w-4" />
                Back to insights
            </Link>
            <InsightArtifactDetailCard artifact={query.data} />
        </div>
    )
}
