import { forwardRef } from 'react'

import { cn } from '@/lib/cn'

const fieldClasses =
    'w-full rounded-md border border-line bg-panel px-3.5 py-2.5 text-sm text-ink placeholder:text-ink-faint transition-colors outline-none focus:border-ink/40 focus:ring-2 focus:ring-ink/15 disabled:cursor-not-allowed disabled:opacity-60'

export const Input = forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
    ({ className, ...props }, ref) => (
        <input ref={ref} className={cn(fieldClasses, className)} {...props} />
    ),
)
Input.displayName = 'Input'

export const Textarea = forwardRef<HTMLTextAreaElement, React.TextareaHTMLAttributes<HTMLTextAreaElement>>(
    ({ className, ...props }, ref) => (
        <textarea ref={ref} className={cn(fieldClasses, 'min-h-24 resize-y leading-6', className)} {...props} />
    ),
)
Textarea.displayName = 'Textarea'

/** Field label + optional hint/error wrapper for form rows. */
export function Field({
    label,
    hint,
    error,
    htmlFor,
    children,
    className,
}: {
    label?: string
    hint?: string
    error?: string
    htmlFor?: string
    children: React.ReactNode
    className?: string
}) {
    return (
        <div className={cn('space-y-1.5', className)}>
            {label && (
                <label htmlFor={htmlFor} className="block text-xs font-semibold text-ink-soft">
                    {label}
                </label>
            )}
            {children}
            {error ? (
                <p className="text-xs text-loss">{error}</p>
            ) : hint ? (
                <p className="text-xs text-ink-faint">{hint}</p>
            ) : null}
        </div>
    )
}
