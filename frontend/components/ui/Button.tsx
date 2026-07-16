'use client'

import { forwardRef } from 'react'
import { Slot } from '@radix-ui/react-slot'
import { cva, type VariantProps } from 'class-variance-authority'
import { Loader2 } from 'lucide-react'

import { cn } from '@/lib/cn'

export const buttonVariants = cva(
    'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md font-medium transition-colors outline-none focus-visible:ring-2 focus-visible:ring-ink/40 disabled:pointer-events-none disabled:opacity-50 select-none',
    {
        variants: {
            variant: {
                primary: 'bg-ink text-canvas hover:bg-ink-soft',
                secondary: 'border border-line bg-panel-subtle text-ink-soft hover:border-line-strong hover:bg-panel',
                outline: 'border border-line bg-transparent text-ink-soft hover:bg-panel-subtle',
                ghost: 'text-ink-muted hover:bg-panel-subtle hover:text-ink',
                danger: 'bg-loss text-white hover:opacity-90',
                ai: 'bg-ai text-white hover:opacity-90',
            },
            size: {
                sm: 'h-8 px-3 text-xs',
                md: 'h-10 px-4 text-sm',
                lg: 'h-11 px-5 text-sm',
                icon: 'h-9 w-9',
                'icon-sm': 'h-8 w-8',
            },
        },
        defaultVariants: {
            variant: 'primary',
            size: 'md',
        },
    },
)

export interface ButtonProps
    extends React.ButtonHTMLAttributes<HTMLButtonElement>,
        VariantProps<typeof buttonVariants> {
    loading?: boolean
    asChild?: boolean
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
    ({ className, variant, size, loading, disabled, asChild, children, ...props }, ref) => {
        if (asChild) {
            // Render the child element (e.g. a Link) with button styling.
            return (
                <Slot ref={ref} className={cn(buttonVariants({ variant, size }), className)} {...props}>
                    {children}
                </Slot>
            )
        }
        return (
            <button
                ref={ref}
                className={cn(buttonVariants({ variant, size }), className)}
                disabled={disabled || loading}
                {...props}
            >
                {loading && <Loader2 className="h-4 w-4 animate-spin" />}
                {children}
            </button>
        )
    },
)
Button.displayName = 'Button'
