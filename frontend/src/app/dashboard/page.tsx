import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';
import { redirect } from 'next/navigation';
import DashboardClient from './DashboardClient';
import SignOutButton from '@/components/SignOutButton';
import Link from 'next/link';

export default async function DashboardPage() {
  const session = await getServerSession(authOptions);
  if (!session?.user.id) redirect('/');
  return <main className="mx-auto w-full max-w-6xl space-y-8 px-4 py-8"><header className="flex flex-wrap items-center justify-between gap-4"><div><Link href="/" className="text-cyan-300">MacroLab</Link><h1 className="text-3xl font-bold">Tu laboratorio de decisiones</h1><p className="muted">{session.user.name}</p></div><SignOutButton /></header><DashboardClient /></main>;
}
