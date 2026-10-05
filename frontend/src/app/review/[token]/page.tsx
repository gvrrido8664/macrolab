import { getServerSession } from 'next-auth';
import Link from 'next/link';
import { authOptions } from '@/lib/auth';
import { backend } from '@/lib/backend';
import ReportView from '@/components/ReportView';
import { isPlaybook } from '@/types/playbook';

export const metadata = { title: 'Revisión compartida | MacroLab', robots: { index: false, follow: false }, referrer: 'no-referrer' as const };

export default async function SharedPage({ params }: { params: Promise<{token:string}> }) {
  const { token } = await params;
  if (!/^[A-Za-z0-9_-]{43}$/.test(token)) return <main className="panel m-8">Enlace inválido.</main>;
  const response = await backend(`/api/v1/shares/${token}`);
  if (!response.ok) return <main className="panel m-8"><h1 className="text-xl font-bold">Revisión no disponible</h1><p>{response.status === 404 ? 'El enlace venció o fue revocado.' : 'No fue posible conectar. Intenta de nuevo.'}</p><Link href="/">Volver a MacroLab</Link></main>;
  const report: unknown = await response.json();
  if (!isPlaybook(report)) return <main className="panel m-8">El informe no tiene un formato compatible. Tus datos siguen guardados.</main>;
  const session = await getServerSession(authOptions);
  return <main className="mx-auto w-full max-w-6xl space-y-6 px-4 py-8"><Link href="/" className="text-cyan-300">MacroLab</Link><h1 className="text-3xl font-bold">Revisión compartida</h1><p className="muted">Acceso mediante enlace; el autor puede revocarlo. No compartas el enlace sin su permiso.</p><ReportView report={report} shareToken={token} canComment={Boolean(session?.user.id)} /></main>;
}
