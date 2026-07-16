import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

/**
 * Merge conditional class names and resolve Tailwind conflicts.
 * The single class-composition helper used across the component library.
 */
export function cn(...inputs: ClassValue[]): string {
    return twMerge(clsx(inputs))
}
