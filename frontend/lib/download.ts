export interface BlobDownloadPayload {
    blob: Blob
    filename: string
}

export function filenameFromContentDisposition(contentDisposition: string | null, fallbackFilename: string): string {
    if (!contentDisposition) return fallbackFilename

    const encodedMatch = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i)
    if (encodedMatch?.[1]) {
        return cleanFilename(decodeURIComponent(encodedMatch[1]), fallbackFilename)
    }

    const quotedMatch = contentDisposition.match(/filename="([^"]+)"/i)
    if (quotedMatch?.[1]) {
        return cleanFilename(quotedMatch[1], fallbackFilename)
    }

    const plainMatch = contentDisposition.match(/filename=([^;]+)/i)
    if (plainMatch?.[1]) {
        return cleanFilename(plainMatch[1], fallbackFilename)
    }

    return fallbackFilename
}

export async function buildBlobDownloadFromResponse(response: Response, fallbackFilename: string): Promise<BlobDownloadPayload> {
    const blob = await response.blob()
    const filename = filenameFromContentDisposition(response.headers.get('Content-Disposition'), fallbackFilename)

    return { blob, filename }
}

export function downloadBlob(filename: string, blob: Blob): void {
    if (typeof window === 'undefined' || typeof document === 'undefined') {
        throw new Error('Blob downloads require a browser environment.')
    }

    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    link.style.display = 'none'

    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
}

function cleanFilename(candidate: string, fallbackFilename: string): string {
    const trimmed = candidate.trim().replace(/^['"]|['"]$/g, '')
    const withoutPath = trimmed.split(/[\\/]/).pop()?.trim()

    return withoutPath || fallbackFilename
}
