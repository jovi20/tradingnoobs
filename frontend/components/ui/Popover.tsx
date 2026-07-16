'use client'

import * as PopoverPrimitive from '@radix-ui/react-popover'
import { forwardRef } from 'react'

import { cn } from '@/lib/cn'

export const Popover = PopoverPrimitive.Root
export const PopoverTrigger = PopoverPrimitive.Trigger
export const PopoverAnchor = PopoverPrimitive.Anchor
export const PopoverClose = PopoverPrimitive.Close

export const PopoverContent = forwardRef<
    React.ElementRef<typeof PopoverPrimitive.Content>,
    React.ComponentPropsWithoutRef<typeof PopoverPrimitive.Content>
>(({ className, align = 'center', sideOffset = 6, ...props }, ref) => (
    <PopoverPrimitive.Portal>
        <PopoverPrimitive.Content
            ref={ref}
            align={align}
            sideOffset={sideOffset}
            className={cn(
                'z-50 w-72 rounded-lg border border-line bg-panel p-4 shadow-pop outline-none data-[state=open]:animate-scale-in',
                className,
            )}
            {...props}
        />
    </PopoverPrimitive.Portal>
))
PopoverContent.displayName = 'PopoverContent'
