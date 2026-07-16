import { AdminShell } from '@/components/navigation/AdminShell'

export default function AdminLayout({ children }: { children: React.ReactNode }) {
    return <AdminShell>{children}</AdminShell>
}
