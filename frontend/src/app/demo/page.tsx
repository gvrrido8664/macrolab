import Link from 'next/link';
import ReportView from '@/components/ReportView';
import demo from '@/data/demo.json';
import { isPlaybook } from '@/types/playbook';

export default function Demo() {
  if (!isPlaybook(demo)) throw new Error('Regenera la fixture de demostración.');
  return <main className="mx-auto w-full max-w-6xl space-y-6 px-4 py-8"><Link href="/" className="text-cyan-300">← MacroLab</Link><h1 className="text-3xl font-bold">Prueba el laboratorio</h1><ReportView report={demo} /></main>;
}
