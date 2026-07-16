import { ProductShell } from '@/components/navigation/ProductShell'

export default function ProductLayout({ children }: { children: React.ReactNode }) {
    return <ProductShell>{children}</ProductShell>
}
