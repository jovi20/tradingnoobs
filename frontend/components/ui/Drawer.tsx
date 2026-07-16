'use client'

import * as DialogPrimitive from '@radix-ui/react-dialog'
import { X } from 'lucide-react'
import { forwardRef } from 'react'

import { cn } from '@/lib/cn'

/**
 * Drawer / Sheet — Radix Dialog docked to an edge. Used for the right context
 * rail on mobile (side="right") and bottom sheets for quick capture (side="bottom").
 */
export const Drawer = DialogPrimitive.Root
export const DrawerTrigger = DialogPrimitive.Trigger
export const DrawerClose = DialogPrimitive.Close

const DrawerOverlay = forwardRef<
    React.ElementRef<typeof DialogPrimitive.Overlay>,
    React.ComponentPropsWithoutRef<typeof DialogPrimitive.Overlay>
>(({ className, ...props }, ref) => (
    <DialogPrimitive.Overlay
        ref={ref}
        className={cn('fixed inset-0 z-50 bg-ink/40 backdrop-blur-[2px] data-[state=open]:animate-fade-in', className)}
        {...props}
    />
))
DrawerOverlay.displayName = 'DrawerOverlay'

type DrawerSide = 'right' | 'left' | 'bottom'

const sideClasses: Record<DrawerSide, string> = {
    right: 'inset-y-0 right-0 h-full w-[min(88vw,26rem)] border-l data-[state=open]:animate-slide-in-right rounded-l-lg',
    left: 'inset-y-0 left-0 h-full w-[min(88vw,26rem)] border-r data-[state=open]:animate-slide-in-right rounded-r-lg',
    bottom: 'inset-x-0 bottom-0 max-h-[88vh] w-full border-t data-[state=open]:animate-slide-up rounded-t-xl',
}

interface DrawerContentProps extends React.ComponentPropsWithoutRef<typeof DialogPrimitive.Content> {
    side?: DrawerSide
    hideClose?: boolean
}

export const DrawerContent = forwardRef<
    React.ElementRef<typeof DialogPrimitive.Content>,
    DrawerContentProps
>(({ className, children, side = 'right', hideClose, ...props }, ref) => (
    <DialogPrimitive.Portal>
        <DrawerOverlay />
        <DialogPrimitive.Content
            ref={ref}
            className={cn(
                'fixed z-50 flex flex-col bg-panel shadow-pop focus:outline-none',
                sideClasses[side],
                className,
            )}
            {...props}
        >
            {side === 'bottom' && (
                <div className="mx-auto mt-3 h-1.5 w-10 shrink-0 rounded-full bg-line-strong" />
            )}
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
DrawerContent.displayName = 'DrawerContent'

export function DrawerHeader({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
    return <div className={cn('flex flex-col gap-1 border-b border-line px-5 py-4', className)} {...props} />
}

export function DrawerTitle({ className, ...props }: React.ComponentPropsWithoutRef<typeof DialogPrimitive.Title>) {
    return <DialogPrimitive.Title className={cn('text-base font-semibold tracking-tight text-ink', className)} {...props} />
}

export function DrawerDescription({ className, ...props }: React.ComponentPropsWithoutRef<typeof DialogPrimitive.Description>) {
    return <DialogPrimitive.Description className={cn('text-sm text-ink-muted', className)} {...props} />
}

export function DrawerBody({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
    return <div className={cn('flex-1 overflow-y-auto px-5 py-4', className)} {...props} />
}
