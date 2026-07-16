'use client'

import * as TooltipPrimitive from '@radix-ui/react-tooltip'
import { forwardRef } from 'react'

import { cn } from '@/lib/cn'

export const TooltipProvider = TooltipPrimitive.Provider
export const TooltipRoot = TooltipPrimitive.Root
export const TooltipTrigger = TooltipPrimitive.Trigger

export const TooltipContent = forwardRef<
    React.ElementRef<typeof TooltipPrimitive.Content>,
    React.ComponentPropsWithoutRef<typeof TooltipPrimitive.Content>
>(({ className, sideOffset = 6, ...props }, ref) => (
    <TooltipPrimitive.Portal>
        <TooltipPrimitive.Content
            ref={ref}
            sideOffset={sideOffset}
            className={cn(
                'z-50 max-w-xs rounded-md border border-line-strong bg-ink px-2.5 py-1.5 text-xs font-medium text-canvas shadow-pop data-[state=delayed-open]:animate-fade-in',
                className,
            )}
            {...props}
        />
    </TooltipPrimitive.Portal>
))
TooltipContent.displayName = 'TooltipContent'

/** Convenience wrapper: <Tooltip label="…"><button/></Tooltip> */
export function Tooltip({
    label,
    children,
    side = 'top',
    delayDuration = 200,
}: {
    label: React.ReactNode
    children: React.ReactNode
    side?: 'top' | 'right' | 'bottom' | 'left'
    delayDuration?: number
}) {
    return (
        <TooltipPrimitive.Root delayDuration={delayDuration}>
            <TooltipTrigger asChild>{children}</TooltipTrigger>
            <TooltipContent side={side}>{label}</TooltipContent>
        </TooltipPrimitive.Root>
    )
}
