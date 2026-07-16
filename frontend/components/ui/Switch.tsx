'use client'

import * as SwitchPrimitive from '@radix-ui/react-switch'
import { forwardRef } from 'react'

import { cn } from '@/lib/cn'

export const Switch = forwardRef<
    React.ElementRef<typeof SwitchPrimitive.Root>,
    React.ComponentPropsWithoutRef<typeof SwitchPrimitive.Root>
>(({ className, ...props }, ref) => (
    <SwitchPrimitive.Root
        ref={ref}
        className={cn(
            'peer inline-flex h-6 w-11 shrink-0 cursor-pointer items-center rounded-full border border-transparent transition-colors outline-none',
            'focus-visible:ring-2 focus-visible:ring-ink/30 disabled:cursor-not-allowed disabled:opacity-50',
            'data-[state=checked]:bg-ink data-[state=unchecked]:bg-line-strong',
            className,
        )}
        {...props}
    >
        <SwitchPrimitive.Thumb className="pointer-events-none block h-5 w-5 translate-x-0.5 rounded-full bg-panel shadow-sm transition-transform data-[state=checked]:translate-x-[1.375rem]" />
    </SwitchPrimitive.Root>
))
Switch.displayName = 'Switch'
