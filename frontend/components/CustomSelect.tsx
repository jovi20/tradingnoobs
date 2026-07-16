'use client'

import { useState, useRef, useEffect } from 'react'
import { ChevronDown, Check } from 'lucide-react'

interface Option {
    value: string | number
    label: string
}

interface CustomSelectProps {
    options: Option[]
    value: string | number
    onChange: (value: any) => void
    placeholder?: string
    className?: string
    size?: 'sm' | 'md'
}

export default function CustomSelect({
    options,
    value,
    onChange,
    placeholder = '请选择',
    className = '',
    size = 'md'
}: CustomSelectProps) {
    const [isOpen, setIsOpen] = useState(false)
    const [openUpward, setOpenUpward] = useState(false)
    const containerRef = useRef<HTMLDivElement>(null)

    const selectedOption = options.find(opt => opt.value === value)

    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
                setIsOpen(false)
            }
        }
        document.addEventListener('mousedown', handleClickOutside)
        return () => document.removeEventListener('mousedown', handleClickOutside)
    }, [])

    const handleToggle = () => {
        if (!isOpen && containerRef.current) {
            // Calculate if we should open upward
            const rect = containerRef.current.getBoundingClientRect()
            const dropdownHeight = Math.min(options.length * 40 + 16, 250) // Approximate dropdown height
            const spaceBelow = window.innerHeight - rect.bottom
            const spaceAbove = rect.top

            // Open upward if not enough space below but enough above
            setOpenUpward(spaceBelow < dropdownHeight && spaceAbove > dropdownHeight)
        }
        setIsOpen(!isOpen)
    }

    return (
        <div className={`relative ${isOpen ? 'z-50' : 'z-10'} ${className}`} ref={containerRef}>
            {/* Trigger */}
            <button
                type="button"
                onClick={handleToggle}
                className={`w-full ${size === 'sm' ? 'h-8 px-2.5 text-xs' : 'h-10 px-3.5 text-sm'} flex items-center justify-between gap-2 bg-panel border border-line rounded-md hover:border-line-strong transition-colors font-medium focus:outline-none focus:ring-2 focus:ring-ink/15`}
            >
                <span className="truncate">
                    {selectedOption ? selectedOption.label : placeholder}
                </span>
                <ChevronDown className={`${size === 'sm' ? 'w-3 h-3' : 'w-4 h-4'} text-ink-faint transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`} />
            </button>

            {/* Dropdown Menu */}
            {isOpen && (
                <div
                    className={`absolute z-[60] w-full min-w-[160px] bg-panel border border-line rounded-md shadow-pop py-1 animate-scale-in max-h-[200px] overflow-y-auto ${openUpward
                            ? 'bottom-full mb-2 origin-bottom'
                            : 'top-full mt-2 origin-top'
                        }`}
                >
                    {options.map((option) => (
                        <button
                            key={option.value}
                            type="button"
                            onClick={() => {
                                onChange(option.value)
                                setIsOpen(false)
                            }}
                            className={`w-full px-3 py-2 text-left text-sm flex items-center justify-between transition-colors
                                ${value === option.value
                                    ? 'bg-panel-subtle text-ink font-medium'
                                    : 'text-ink-soft hover:bg-panel-subtle'
                                }
                            `}
                        >
                            <span className="truncate">{option.label}</span>
                            {value === option.value && <Check className="w-4 h-4 shrink-0" />}
                        </button>
                    ))}
                </div>
            )}
        </div>
    )
}
