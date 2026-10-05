'use client';
import { FormEvent, useEffect, useState } from 'react';
import type { PlayerMatches, Playbook, History, TrackedPlayer as Tracked } from '@/types/playbook';
import { requestLab } from '@/lib/client';
import ReportView from '@/components/ReportView';

const empty: History = { analyses: [], habit: null, shares: [], feedback: [] };

export default function DashboardClient() {
  const [gameName,setName] = useState('');
  const [tagLine,setTag] = useState('');
  const [player,setPlayer] = useState<PlayerMatches | null>(null);
  const [tracked,setTracked] = useState<Tracked[]>([]);
  const [puuid,setPuuid] = useState('');
  const [report,setReport] = useState<Playbook | null>(null);
  const [history,setHistory] = useState<History>(empty);
  const [busy,setBusy] = useState(false);
  const [error,setError] = useState('');
  const [notice,setNotice] = useState('');
  const [deleting,setDeleting] = useState(false);
  useEffect(() => {
    let active = true;
    requestLab<Tracked[]>({ action: 'players' }).then(data => { if (active) setTracked(data); }).catch(e => { if (active) setError(e.message); });
    return () => { active = false; };
  }, []);
  async function run(task: () => Promise<void>) {
    setBusy(true); setError(''); setNotice('');
    try { await task(); } catch(e) { setError(e instanceof Error ? e.message : 'La operación no pudo completarse.'); }
    finally { setBusy(false); }
  }
  async function refresh(id = puuid) { setHistory(await requestLab<History>({ action: 'history', puuid: id })); }
  function search(event: FormEvent) {
    event.preventDefault();
    void run(async () => {
      setReport(null); setPlayer(null); setPuuid(''); setHistory(empty);
      const result = await requestLab<PlayerMatches>({ action: 'search', gameName, tagLine });
      setPlayer(result); setPuuid(result.account.puuid);
      setTracked(await requestLab<Tracked[]>({ action: 'players' }));
      await refresh(result.account.puuid);
    });
  }
  function analyze(matchId: string) {
    void run(async () => {
      setReport(null);
      const result = await requestLab<Playbook>({ action: 'analyze', matchId, puuid });
      setReport(result);
      await refresh();
    });
  }
  async function exportData() {
    const data = await requestLab({ action: 'export' });
    const url = URL.createObjectURL(new Blob([JSON.stringify(data,null,2)], { type: 'application/json' }));
    const link = document.createElement('a'); link.href = url; link.download = 'macrolab-datos.json'; link.click(); URL.revokeObjectURL(url);
  }
  return <div className="space-y-6">
    <section className="panel"><h2 className="text-xl font-bold">Buscar partidas reales</h2><p className="muted mt-2">Piloto LAS · Solo/Dúo · últimas cinco partidas. La cuenta de MacroLab es independiente de Riot.</p>
      <form onSubmit={search} className="mt-4 flex flex-wrap items-end gap-3"><label className="grow">Nombre en Riot<input required minLength={3} maxLength={16} value={gameName} onChange={e => setName(e.target.value)} className="field mt-1" placeholder="Nombre de juego" /></label><label>Etiqueta (sin #)<input required minLength={3} maxLength={5} pattern="[A-Za-z0-9]{3,5}" value={tagLine} onChange={e => setTag(e.target.value)} className="field mt-1" placeholder="Ej.: LUCKY" /></label><button className="button primary" disabled={busy}>{busy ? 'Procesando…' : 'Buscar'}</button></form>
      {player && <div className="mt-4"><p>{player.account.gameName}#{player.account.tagLine}</p><div className="mt-3 flex flex-wrap gap-2">{player.matches.filter(id => id.startsWith('LA2_')).map((id,i) => <button className="button" key={id} disabled={busy} onClick={() => analyze(id)}>Analizar partida {i+1}</button>)}</div>{!player.matches.some(id => id.startsWith('LA2_')) && <p className="muted mt-3">No se encontraron partidas LAS compatibles en este listado.</p>}</div>}
    </section>
    {error && <p className="panel border-red-700 text-red-200" role="alert">{error}</p>}
    {notice && <p className="panel text-cyan-200" role="status">{notice}</p>}
    {tracked.length > 0 && <section className="panel"><h2 className="text-xl font-bold">Jugadores seguidos</h2><div className="mt-3 flex flex-wrap gap-2">{tracked.map(p => <button className="button" key={p.puuid} disabled={busy} aria-pressed={puuid === p.puuid} onClick={() => void run(async () => { setPuuid(p.puuid); setReport(null); setPlayer(null); await refresh(p.puuid); })}>{p.name}</button>)}</div></section>}
    {puuid && <section className="panel"><h2 className="text-xl font-bold">Un hábito durante cinco partidas</h2><p className="mt-2">Llegar con vida a las peleas por dragón y Barón.</p><p className="muted mt-2">Contamos cuántas veces moriste durante el minuto anterior a que un equipo consiguiera dragón o Barón. Ese dato te ayuda a revisar el riesgo que tomaste; por sí solo no indica un error. El seguimiento cuenta las próximas cinco partidas que juegues y analices con datos completos y objetivos registrados.</p>
      {history.habit ? <div className="mt-4"><progress aria-label="Partidas revisadas del hábito" value={history.habit.completed} max={5} className="w-full accent-cyan-400" /><p>{history.habit.completed}/5 partidas · {history.habit.numerator}/{history.habit.denominator} capturas precedidas por tu muerte{history.habit.completed === 5 && ' · Ciclo terminado'}</p><p className="muted">Compara estos momentos entre partidas para reconocer situaciones que se repiten. Un número más bajo, por sí solo, no demuestra que hayas jugado mejor.</p><button className="button mt-3" disabled={busy} onClick={() => void run(async () => { await requestLab({ action: 'stopHabit', puuid }); await refresh(); })}>{history.habit.completed === 5 ? 'Cerrar ciclo para elegir otro' : 'Finalizar hábito'}</button></div> : <button className="button primary mt-4" disabled={busy || !history.analyses.some(r => r.habit_metric.eligible)} onClick={() => void run(async () => { await requestLab({ action: 'habit', puuid }); await refresh(); })}>Empezar seguimiento de cinco partidas</button>}
    </section>}
    {report && <ReportView key={`${puuid}:${report.match_id}:${report.analysis_version}`} report={report} telemetry />}
    {history.analyses.length > 0 && <section className="panel"><h2 className="text-xl font-bold">Historial de este jugador</h2><p className="muted">Guardado en tu cuenta. Las versiones anteriores permanecen ligadas a sus enlaces de revisión.</p><div className="mt-4 space-y-3">{history.analyses.map(r => <div key={r.match_id} className="flex flex-wrap items-center justify-between gap-3 rounded-lg bg-slate-800 p-4"><button className="text-left hover:text-cyan-300" onClick={() => setReport(r)}>{r.match_stats?.champion_name} · {r.match_stats?.win ? 'Victoria' : 'Derrota'} · {r.match_stats && new Date(r.match_stats.game_created_at).toLocaleDateString('es-CL', { timeZone: 'UTC' })}<span className="muted block">{r.match_id}</span></button><button className="button" disabled={busy} onClick={() => void run(async () => { const data = await requestLab<{token:string}>({ action: 'share', puuid, matchId: r.match_id, version: r.analysis_version }); setNotice(`Enlace creado por 7 días: ${window.location.origin}/review/${data.token}`); await refresh(); })}>Crear enlace de revisión</button></div>)}</div><p className="muted mt-3">Cualquier persona con el enlace puede leer el informe. Puedes revocarlo abajo.</p></section>}
    {history.shares.length > 0 && <section className="panel"><h2 className="font-bold">Enlaces activos</h2><ul className="mt-3 space-y-3">{history.shares.map(s => <li className="flex flex-wrap gap-3" key={s.token}><a href={`/review/${s.token}`} target="_blank" rel="noreferrer" className="text-cyan-300 underline">{s.match_id} · vence {new Date(s.expires*1000).toLocaleDateString('es-CL')}</a><button className="button" disabled={busy} onClick={() => void run(async () => { await requestLab({ action: 'revoke', token: s.token }); await refresh(); })}>Revocar</button></li>)}</ul></section>}
    {history.feedback.length > 0 && <section className="panel"><h2 className="font-bold">Revisiones recibidas</h2><ul className="mt-3 space-y-3">{history.feedback.map((f,i) => <li key={i}><strong>{f.match_id} · {f.verdict === 'agree' ? 'De acuerdo' : f.verdict === 'incorrect' ? 'Incorrecto' : 'Falta contexto'}</strong><p>{f.comment || 'Sin comentario adicional.'}</p></li>)}</ul></section>}
    <details className="panel"><summary className="cursor-pointer font-bold">Tus datos</summary><p className="muted mt-3">Puedes exportar o borrar tus análisis, jugadores seguidos, hábitos, enlaces y revisiones. No afecta tu cuenta Riot.</p><div className="mt-3 flex flex-wrap gap-3"><button className="button" disabled={busy} onClick={() => void run(exportData)}>Exportar mis datos</button><button className="button" disabled={busy} onClick={() => setDeleting(true)}>Borrar mis datos</button></div>{deleting && <div className="mt-4 rounded-lg border border-red-700 p-4"><p>Se borrarán tus datos de MacroLab y se revocarán tus enlaces. Esta acción no se puede deshacer.</p><div className="mt-3 flex gap-3"><button className="button" onClick={() => setDeleting(false)}>Cancelar</button><button className="button" disabled={busy} onClick={() => void run(async () => { await requestLab({ action: 'deleteAccount' }); setHistory(empty); setReport(null); setTracked([]); setPuuid(''); setPlayer(null); setDeleting(false); setNotice('Tus datos fueron borrados.'); })}>Confirmar borrado</button></div></div>}</details>
  </div>;
}
