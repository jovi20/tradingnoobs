'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'

/**
 * Redirect to new Positions page
 * The old trades/new is replaced by positions/new
 */
export default function NewTradePage() {
    const router = useRouter()

    useEffect(() => {
        router.replace('/positions/new')
    }, [router])

    return null
}
