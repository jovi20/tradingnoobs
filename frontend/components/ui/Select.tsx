'use client'

import * as SelectPrimitive from '@radix-ui/react-select'
import { Check, ChevronDown } from 'lucide-react'
import { forwardRef } from 'react'

import { cn } from '@/lib/cn'

export const Select = SelectPrimitive.Root
export const SelectGroup = SelectPrimitive.Group
export const SelectValue = SelectPrimitive.Value

export const SelectTrigger = forwardRef<
    React.ElementRef<typeof SelectPrimitive.Trigger>,
    React.ComponentPropsWithoutRef<typeof SelectPrimitive.Trigger> & { size?: 'sm' | 'md' }
>(({ className, children, size = 'md', ...props }, ref) => (
    <SelectPrimitive.Trigger
        ref={ref}
        className={cn(
            'inline-flex w-full items-center justify-between gap-2 rounded-md border border-line bg-panel text-sm text-ink outline-none transition-colors',
            'focus:border-ink/40 focus:ring-2 focus:ring-ink/15 data-[placeholder]:text-ink-faint disabled:cursor-not-allowed disabled:opacity-60',
            size === 'sm' ? 'h-8 px-2.5' : 'h-10 px-3.5',
            className,
        )}
        {...props}
    >
        {children}
        <SelectPrimitive.Icon asChild>
            <ChevronDown className="h-4 w-4 text-ink-faint" />
        </SelectPrimitive.Icon>
    </SelectPrimitive.Trigger>
))
SelectTrigger.displayName = 'SelectTrigger'

export const SelectContent = forwardRef<
    React.ElementRef<typeof SelectPrimitive.Content>,
    React.ComponentPropsWithoutRef<typeof SelectPrimitive.Content>
>(({ className, children, position = 'popper', ...props }, ref) => (
    <SelectPrimitive.Portal>
        <SelectPrimitive.Content
            ref={ref}
            position={position}
            className={cn(
                'relative z-50 max-h-72 min-w-[8rem] overflow-hidden rounded-md border border-line bg-panel shadow-pop data-[state=open]:animate-scale-in',
                position === 'popper' && 'w-[var(--radix-select-trigger-width)]',
                className,
            )}
            {...props}
        >
            <SelectPrimitive.Viewport className="p-1">{children}</SelectPrimitive.Viewport>
        </SelectPrimitive.Content>
    </SelectPrimitive.Portal>
))
SelectContent.displayName = 'SelectContent'

export const SelectItem = forwardRef<
    React.ElementRef<typeof SelectPrimitive.Item>,
    React.ComponentPropsWithoutRef<typeof SelectPrimitive.Item>
>(({ className, children, ...props }, ref) => (
    <SelectPrimitive.Item
        ref={ref}
        className={cn(
            'relative flex cursor-pointer select-none items-center rounded-sm py-1.5 pl-8 pr-2 text-sm text-ink-soft outline-none',
            'data-[highlighted]:bg-panel-subtle data-[highlighted]:text-ink data-[state=checked]:text-ink data-[disabled]:pointer-events-none data-[disabled]:opacity-50',
            className,
        )}
        {...props}
    >
        <span className="absolute left-2 flex h-4 w-4 items-center justify-center">
            <SelectPrimitive.ItemIndicator>
                <Check className="h-4 w-4" />
            </SelectPrimitive.ItemIndicator>
        </span>
        <SelectPrimitive.ItemText>{children}</SelectPrimitive.ItemText>
    </SelectPrimitive.Item>
))
SelectItem.displayName = 'SelectItem'

export function SelectLabel({ className, ...props }: React.ComponentPropsWithoutRef<typeof SelectPrimitive.Label>) {
    return <SelectPrimitive.Label className={cn('px-2 py-1.5 text-[11px] font-semibold uppercase tracking-wider text-ink-faint', className)} {...props} />
}
