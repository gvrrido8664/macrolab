import Link from 'next/link';
import { connection } from 'next/server';
import LoginButtons from '@/components/LoginButtons';

export default async function Home() {
  await connection();
  return <main className="mx-auto w-full max-w-6xl px-5 py-8">
    <nav className="flex items-center justify-between gap-4"><span className="text-xl font-bold text-cyan-300">MacroLab</span><Link className="button" href="/demo">Abrir demo</Link></nav>
    <section className="max-w-3xl py-20"><span className="badge">Laboratorio postpartida · Piloto LAS</span><h1 className="mt-6 text-4xl font-bold leading-tight sm:text-6xl">Tu próxima mejora empieza con una decisión.</h1><p className="mt-6 text-xl leading-relaxed text-slate-300">Revisa hasta tres momentos de tu partida, explora alternativas y sigue un hábito durante tus próximas cinco partidas.</p><div className="mt-8 flex flex-wrap gap-3"><Link href="/demo" className="button primary">Probar con una partida de ejemplo</Link><Link href="/dashboard" className="button">Mi laboratorio</Link></div><div className="mt-6"><LoginButtons github={Boolean(process.env.GITHUB_ID && process.env.GITHUB_SECRET)} local={process.env.NODE_ENV !== 'production' && process.env.ALLOW_MOCK_AUTH === 'true'} /></div></section>
    <section className="grid gap-5 pb-16 md:grid-cols-3">{[['01 · Observa','Conecta cada conclusión con eventos y tiempos concretos.'],['02 · Considera','Compara alternativas y sus costes antes de revelar el desenlace.'],['03 · Revisa tu hábito','Sigue capturas de objetivos y tu exposición en cinco partidas nuevas.']].map(([title,text]) => <article className="panel" key={title}><h2 className="text-lg font-bold">{title}</h2><p className="muted mt-3">{text}</p></article>)}</section>
    <section className="panel mb-12"><h2 className="text-xl font-bold">Evidencia con límites claros</h2><p className="mt-3 text-slate-300">Las reglas son experimentales. No calculamos tu MMR ni prometemos victorias. Los datos disponibles no reconstruyen tu visión ni tu recorrido exacto. Cuando falta evidencia, lo indicamos.</p><p className="muted mt-3">La demo contiene datos sintéticos y funciona sin cuenta ni conexión a Riot. El análisis real admite Solo/Dúo en LAS.</p></section>
  </main>;
}
