const AUTH_ERROR_MESSAGES: Array<[pattern: RegExp, message: string]> = [
    [/incorrect email or password/i, '邮箱或密码错误'],
    [/login failed/i, '邮箱或密码错误'],
    [/invalid invitation code/i, '邀请码无效，请检查后重试'],
    [/email already registered/i, '该邮箱已注册，请直接登录'],
    [/inactive user|user(?: account)? is inactive/i, '账户已停用，请联系管理员'],
    [/at least 8 characters/i, '密码至少需要 8 个字符'],
    [/failed to fetch|network\s*error|load failed/i, '无法连接服务器，请稍后重试'],
    [/request failed/i, '请求失败，请稍后重试'],
    [/current password is incorrect|incorrect current password/i, '当前密码错误'],
    [/account not found|invalid account_id/i, '交易账户无效，请刷新后重试'],
]

export function getLocalizedUiError(error: unknown, fallback: string): string {
    const rawMessage = error instanceof Error
        ? error.message.trim()
        : typeof error === 'string'
            ? error.trim()
            : ''

    if (!rawMessage) return fallback

    const matched = AUTH_ERROR_MESSAGES.find(([pattern]) => pattern.test(rawMessage))
    if (matched) return matched[1]

    // Preserve actionable Chinese messages but never expose an unknown raw English API detail.
    return /[\u3400-\u9fff]/.test(rawMessage) ? rawMessage : fallback
}

export function getLocalizedAuthError(error: unknown, fallback: string): string {
    return getLocalizedUiError(error, fallback)
}
