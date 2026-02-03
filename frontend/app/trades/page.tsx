'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'

/**
 * Redirect to unified Positions page
 * The old trades list is replaced by positions (持仓记录)
 */
export default function TradesPage() {
    const router = useRouter()

    useEffect(() => {
        router.replace('/positions')
    }, [router])

    return null
}
