'use client'

import * as DropdownMenuPrimitive from '@radix-ui/react-dropdown-menu'
import { forwardRef } from 'react'

import { cn } from '@/lib/cn'

export const DropdownMenu = DropdownMenuPrimitive.Root
export const DropdownMenuTrigger = DropdownMenuPrimitive.Trigger
export const DropdownMenuGroup = DropdownMenuPrimitive.Group

export const DropdownMenuContent = forwardRef<
    React.ElementRef<typeof DropdownMenuPrimitive.Content>,
    React.ComponentPropsWithoutRef<typeof DropdownMenuPrimitive.Content>
>(({ className, sideOffset = 6, ...props }, ref) => (
    <DropdownMenuPrimitive.Portal>
        <DropdownMenuPrimitive.Content
            ref={ref}
            sideOffset={sideOffset}
            className={cn(
                'z-50 min-w-[10rem] overflow-hidden rounded-md border border-line bg-panel p-1 shadow-pop data-[state=open]:animate-scale-in',
                className,
            )}
            {...props}
        />
    </DropdownMenuPrimitive.Portal>
))
DropdownMenuContent.displayName = 'DropdownMenuContent'

export const DropdownMenuItem = forwardRef<
    React.ElementRef<typeof DropdownMenuPrimitive.Item>,
    React.ComponentPropsWithoutRef<typeof DropdownMenuPrimitive.Item> & { tone?: 'default' | 'danger' }
>(({ className, tone = 'default', ...props }, ref) => (
    <DropdownMenuPrimitive.Item
        ref={ref}
        className={cn(
            'relative flex cursor-pointer select-none items-center gap-2 rounded-sm px-2.5 py-1.5 text-sm outline-none transition-colors',
            'data-[disabled]:pointer-events-none data-[disabled]:opacity-50',
            tone === 'danger'
                ? 'text-loss data-[highlighted]:bg-loss/10'
                : 'text-ink-soft data-[highlighted]:bg-panel-subtle data-[highlighted]:text-ink',
            className,
        )}
        {...props}
    />
))
DropdownMenuItem.displayName = 'DropdownMenuItem'

export function DropdownMenuLabel({ className, ...props }: React.ComponentPropsWithoutRef<typeof DropdownMenuPrimitive.Label>) {
    return <DropdownMenuPrimitive.Label className={cn('px-2.5 py-1.5 text-[11px] font-semibold uppercase tracking-wider text-ink-faint', className)} {...props} />
}

export function DropdownMenuSeparator({ className, ...props }: React.ComponentPropsWithoutRef<typeof DropdownMenuPrimitive.Separator>) {
    return <DropdownMenuPrimitive.Separator className={cn('my-1 h-px bg-line', className)} {...props} />
}
