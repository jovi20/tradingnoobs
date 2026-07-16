'use client'

import * as TabsPrimitive from '@radix-ui/react-tabs'
import { forwardRef } from 'react'

import { cn } from '@/lib/cn'

export const Tabs = TabsPrimitive.Root

export const TabsList = forwardRef<
    React.ElementRef<typeof TabsPrimitive.List>,
    React.ComponentPropsWithoutRef<typeof TabsPrimitive.List>
>(({ className, ...props }, ref) => (
    <TabsPrimitive.List
        ref={ref}
        className={cn(
            'inline-flex items-center gap-1 rounded-lg border border-line bg-panel-subtle p-1',
            className,
        )}
        {...props}
    />
))
TabsList.displayName = 'TabsList'

export const TabsTrigger = forwardRef<
    React.ElementRef<typeof TabsPrimitive.Trigger>,
    React.ComponentPropsWithoutRef<typeof TabsPrimitive.Trigger>
>(({ className, ...props }, ref) => (
    <TabsPrimitive.Trigger
        ref={ref}
        className={cn(
            'inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium text-ink-muted transition-colors outline-none',
            'hover:text-ink focus-visible:ring-2 focus-visible:ring-ink/30',
            'data-[state=active]:bg-panel data-[state=active]:text-ink data-[state=active]:shadow-panel dark:data-[state=active]:shadow-none dark:data-[state=active]:border dark:data-[state=active]:border-line-strong',
            className,
        )}
        {...props}
    />
))
TabsTrigger.displayName = 'TabsTrigger'

export const TabsContent = forwardRef<
    React.ElementRef<typeof TabsPrimitive.Content>,
    React.ComponentPropsWithoutRef<typeof TabsPrimitive.Content>
>(({ className, ...props }, ref) => (
    <TabsPrimitive.Content
        ref={ref}
        className={cn('mt-4 outline-none focus-visible:ring-2 focus-visible:ring-ink/20', className)}
        {...props}
    />
))
TabsContent.displayName = 'TabsContent'

/**
 * Underline-style tab bar variant — for page-level view switching where a
 * pill group would feel heavy. Compose manually with Tabs/TabsTrigger via the
 * `variant` prop on a wrapper, or use these class names directly.
 */
export const tabsUnderlineList =
    'flex items-center gap-5 border-b border-line'
export const tabsUnderlineTrigger =
    'relative -mb-px border-b-2 border-transparent px-0.5 pb-2.5 text-sm font-medium text-ink-muted transition-colors hover:text-ink outline-none data-[state=active]:border-ink data-[state=active]:text-ink focus-visible:text-ink'
