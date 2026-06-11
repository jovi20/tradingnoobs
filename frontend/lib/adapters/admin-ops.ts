import type { AdminBackupResponse, AdminPasswordResetResponse } from '../api.ts'

function formatDateTime(value: string): string {
    return new Date(value).toLocaleString('zh-CN')
}

function formatBackupBackend(value: string): string {
    if (value === 'sqlite') return 'SQLite'
    if (value === 'postgresql') return 'PostgreSQL'
    return value
}

function fileNameFromPath(path: string): string {
    return path.split(/[\\/]/).filter(Boolean).at(-1) || path
}

export function formatBackupResult(result: AdminBackupResponse) {
    return {
        statusLabel: result.status,
        backendLabel: formatBackupBackend(result.database_backend),
        fileName: fileNameFromPath(result.path),
        path: result.path,
        createdLabel: formatDateTime(result.created_at),
        description: result.message,
    }
}

export function formatPasswordResetNotice(result: AdminPasswordResetResponse) {
    return {
        userPublicId: result.user_public_id,
        temporaryPassword: result.temporary_password,
        sessionNotice: `${result.revoked_session_count} sessions and ${result.revoked_token_count} tokens revoked`,
        securityNotice: `${result.message} Share it through a secure channel and ask the user to rotate it after login.`,
    }
}

export function isValidUserPublicIdInput(value: string): boolean {
    return value.trim().length > 0
}
