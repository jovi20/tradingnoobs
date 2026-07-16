import type { AdminBackupResponse, AdminPasswordResetResponse } from '../api.ts'

function formatDateTime(value: string): string {
    return new Date(value).toLocaleString('zh-CN')
}

function formatBackupBackend(value: string): string {
    if (value === 'sqlite') return 'SQLite'
    if (value === 'postgresql') return 'PostgreSQL'
    return value
}

function formatOperationStatus(value: string): string {
    if (value === 'SUCCESS') return '成功'
    if (value === 'FAILED') return '失败'
    return value
}

function fileNameFromPath(path: string): string {
    return path.split(/[\\/]/).filter(Boolean).at(-1) || path
}

export function formatBackupResult(result: AdminBackupResponse) {
    return {
        statusLabel: formatOperationStatus(result.status),
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
        sessionNotice: `已撤销 ${result.revoked_session_count} 个会话和 ${result.revoked_token_count} 个令牌。`,
        securityNotice: '临时密码仅显示一次，请通过安全渠道发送，并要求用户登录后立即修改。',
    }
}

export function isValidUserPublicIdInput(value: string): boolean {
    return value.trim().length > 0
}
