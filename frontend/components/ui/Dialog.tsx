'use client'

import * as DialogPrimitive from '@radix-ui/react-dialog'
import { X } from 'lucide-react'
import { forwardRef } from 'react'

import { cn } from '@/lib/cn'

export const Dialog = DialogPrimitive.Root
export const DialogTrigger = DialogPrimitive.Trigger
export const DialogClose = DialogPrimitive.Close

const DialogOverlay = forwardRef<
    React.ElementRef<typeof DialogPrimitive.Overlay>,
    React.ComponentPropsWithoutRef<typeof DialogPrimitive.Overlay>
>(({ className, ...props }, ref) => (
    <DialogPrimitive.Overlay
        ref={ref}
        className={cn(
            'fixed inset-0 z-50 bg-ink/40 backdrop-blur-[2px] data-[state=open]:animate-fade-in',
            className,
        )}
        {...props}
    />
))
DialogOverlay.displayName = 'DialogOverlay'

interface DialogContentProps extends React.ComponentPropsWithoutRef<typeof DialogPrimitive.Content> {
    hideClose?: boolean
    size?: 'sm' | 'md' | 'lg'
}

const sizeClasses = {
    sm: 'max-w-md',
    md: 'max-w-lg',
    lg: 'max-w-2xl',
}

export const DialogContent = forwardRef<
    React.ElementRef<typeof DialogPrimitive.Content>,
    DialogContentProps
>(({ className, children, hideClose, size = 'md', ...props }, ref) => (
    <DialogPrimitive.Portal>
        <DialogOverlay />
        <DialogPrimitive.Content
            ref={ref}
            className={cn(
                'fixed left-1/2 top-1/2 z-50 w-[calc(100vw-2rem)] -translate-x-1/2 -translate-y-1/2 rounded-lg border border-line bg-panel p-6 shadow-pop focus:outline-none data-[state=open]:animate-scale-in',
                sizeClasses[size],
                className,
            )}
            {...props}
        >
            {children}
            {!hideClose && (
                <DialogPrimitive.Close className="absolute right-4 top-4 rounded-md p-1 text-ink-faint transition-colors hover:bg-panel-subtle hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink/40">
                    <X className="h-4 w-4" />
                    <span className="sr-only">关闭</span>
                </DialogPrimitive.Close>
            )}
        </DialogPrimitive.Content>
    </DialogPrimitive.Portal>
))
DialogContent.displayName = 'DialogContent'

export function DialogHeader({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
    return <div className={cn('mb-4 flex flex-col gap-1.5', className)} {...props} />
}

export function DialogTitle({ className, ...props }: React.ComponentPropsWithoutRef<typeof DialogPrimitive.Title>) {
    return <DialogPrimitive.Title className={cn('text-lg font-semibold tracking-tight text-ink', className)} {...props} />
}

export function DialogDescription({ className, ...props }: React.ComponentPropsWithoutRef<typeof DialogPrimitive.Description>) {
    return <DialogPrimitive.Description className={cn('text-sm leading-6 text-ink-muted', className)} {...props} />
}

export function DialogFooter({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
    return <div className={cn('mt-6 flex items-center justify-end gap-3', className)} {...props} />
}
