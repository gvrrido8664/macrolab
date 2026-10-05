'use client';
import { useEffect, useRef, useState } from 'react';
import type { Playbook } from '@/types/playbook';
import InteractiveMap from './InteractiveMap';
import GameIcon from './GameIcon';
import { requestLab, timeLabel } from '@/lib/client';
import { visibleEvents } from '@/lib/timeline';
import { eventNames, eventTitle, locationNote, reportText } from '@/lib/report-copy';

const roles: Record<string, string> = { TOP: 'Superior', JUNGLE: 'Jungla', MIDDLE: 'Medio', BOTTOM: 'ADC', UTILITY: 'Soporte' };

export default function ReportView({ report, telemetry = false, shareToken, canComment = false }: { report: Playbook; telemetry?: boolean; shareToken?: string; canComment?: boolean }) {
  const [currentTime, setTime] = useState(0);
  const [highlighted, setHighlighted] = useState<string | null>(null);
  const eventList = useRef<HTMLUListElement>(null);
  useEffect(() => {
    if (!highlighted) return;
    const list = eventList.current;
    const row = list?.querySelector<HTMLElement>('[data-highlighted="true"]');
    if (list && row) {
      const top = row.getBoundingClientRect().top - list.getBoundingClientRect().top;
      if (top < 0 || top + row.offsetHeight > list.clientHeight) list.scrollTop += top - (list.clientHeight - row.offsetHeight) / 2;
    }
  }, [highlighted]);
  const [selected, setSelected] = useState<string | null>(null);
  const [revealed, setRevealed] = useState(false);
  const [choice, setChoice] = useState<string | null>(null);
  const [filter, setFilter] = useState('all');
  const [windowMs, setWindow] = useState(180_000);
  const [comment, setComment] = useState('');
  const [verdict, setVerdict] = useState('context');
  const [feedbackStatus, setFeedbackStatus] = useState('');
  const [sending, setSending] = useState(false);
  const decision = report.decisions.find(d => d.id === selected);
  const duration = (report.match_stats?.duration_seconds ?? 0) * 1000;
  const events = visibleEvents(report.events, currentTime, windowMs, filter);
  function track(event: string) { if (telemetry && selected) void requestLab({ action: 'telemetry', event, matchId: report.match_id, decision: selected }).catch(() => undefined); }
  function reveal() { setRevealed(true); track('evidence_opened'); }
  async function sendFeedback() {
    if (!decision || !shareToken) return;
    setSending(true); setFeedbackStatus('');
    try { await requestLab({ action: 'feedback', token: shareToken, decision: decision.id, verdict, comment }); setFeedbackStatus('Revisión guardada.'); }
    catch (e) { setFeedbackStatus(e instanceof Error ? e.message : 'No fue posible guardar.'); }
    finally { setSending(false); }
  }
  const stats = report.match_stats;
  const timelineRows = [
    ...events.map(e => ({ id: e.id, timestamp: e.timestamp, title: eventTitle(e), note: locationNote(e) })),
    ...report.player_route.filter(p => p.timestamp <= currentTime && p.timestamp >= currentTime - 180_000).map(p => ({ id: `position:${p.timestamp}`, timestamp: p.timestamp, title: `Posición de ${stats?.champion_name ?? 'tu campeón'}`, note: null })),
  ].sort((a, b) => a.timestamp - b.timestamp);
  return <div className="space-y-6">
    <section className="panel">
      <div className="flex flex-wrap items-center justify-between gap-3"><h2 className="text-2xl font-bold">{stats ? `${stats.champion_name} · ${roles[stats.role] ?? 'Rol no identificado'}` : 'Análisis de partida'}</h2><span className="badge">{report.data_source === 'demo' ? 'Partida de ejemplo' : 'Datos de Riot'}</span></div>
      {stats && <p className="mt-2 text-slate-300">{stats.win ? 'Victoria' : 'Derrota'} · {timeLabel(duration)} · Solo/Dúo · {new Date(stats.game_created_at).toLocaleDateString('es-CL', { timeZone: 'UTC' })} · Parche {report.patch}</p>}
      <p className="mt-3 text-sm text-slate-400">{report.data_source === 'demo' ? 'Practica con una partida de ejemplo. Tus elecciones aquí no se guardan.' : 'Estás revisando una partida terminada. Puedes analizar a este jugador sin vincular su cuenta de Riot.'}</p>
      <ul className="mt-4 space-y-1 text-sm text-amber-200">{report.data_quality.map(q => <li key={q}>{reportText(q)}</li>)}</ul>
    </section>

    {report.status !== 'unsupported' && <>
      <section className="panel" aria-labelledby="moments-title">
        <h2 id="moments-title" className="text-xl font-bold">Momentos para revisar</h2>
        <p className="muted mt-2">1. Elige un momento. 2. Compara qué podrías hacer. 3. Descubre qué pasó.</p>
        {report.decisions.length === 0 && <p className="mt-4">No encontramos momentos con suficiente información para este ejercicio. Puedes explorar los eventos en el mapa.</p>}
        <div className="mt-4 grid gap-3 md:grid-cols-3">{report.decisions.map((d, i) => <button key={d.id} className={`button flex-col items-start gap-1 text-left ${selected === d.id ? 'ring-2 ring-cyan-400' : ''}`} aria-pressed={selected === d.id} onClick={() => { setSelected(d.id); setTime(d.timestamp); setRevealed(false); setChoice(null); setComment(''); setFeedbackStatus(''); }}>
          <span className="block text-xs text-cyan-200">MOMENTO {i+1}</span><span className="block text-xl">{timeLabel(d.timestamp)}</span><span className="text-sm">Explorar este momento</span>
        </button>)}</div>
        {decision && <div className="mt-5 rounded-xl border border-cyan-800 p-5">
          <h3 className="font-semibold">{revealed ? decision.title : decision.prompt}</h3>
          <p className="muted mt-2">Piensa qué harías con la información disponible. Después podrás comparar tu elección con lo que ocurrió; ninguna opción se califica automáticamente como correcta.</p>
          <div className="mt-4 grid gap-3 md:grid-cols-2">{decision.alternatives.map(a => <button key={a.label} className="button flex-col items-start text-left" aria-pressed={choice === a.label} onClick={() => { setChoice(a.label); track('alternative_selected'); reveal(); }}><strong>{a.label}</strong><span className="mt-1 block text-sm text-slate-300">{a.tradeoff}</span></button>)}</div>
          {!revealed && <button className="button mt-4" onClick={reveal}>Mostrar qué pasó</button>}
          {revealed && <div className="mt-5 space-y-4">
            {choice && <p className="text-cyan-200">Tu alternativa: {choice}</p>}
            <div><h4 className="font-bold">Qué ocurrió</h4>{decision.facts.map(f => <p key={f}>{reportText(f)}</p>)}</div>
            <div><h4 className="font-bold">Qué puedes aprender de este momento</h4><p>{reportText(decision.interpretation)}</p></div>
            {decision.context.map(c => <p key={c} className="muted">{reportText(c)}</p>)}
            <p className="text-sm text-amber-200">Lo que estos datos no permiten saber: {decision.limitations.map(reportText).join(' ')}</p>
            <div className="flex flex-wrap gap-2">{decision.evidence_ids.map(id => { const event = report.events.find(e => e.id === id); return event && <button key={id} className="button" onClick={() => setTime(event.timestamp)}>{timeLabel(event.timestamp)} · {eventTitle(event)}</button>; })}</div>
            {shareToken && (canComment ? <div className="space-y-3 border-t border-slate-700 pt-4">
              <h4 className="font-bold">Tu revisión para el autor</h4>
              <label className="block">Evaluación<select className="field mt-1" value={verdict} onChange={e => setVerdict(e.target.value)}><option value="context">Falta contexto</option><option value="agree">De acuerdo</option><option value="incorrect">Incorrecto</option></select></label>
              <label className="block">Comentario en {timeLabel(decision.timestamp)}<textarea className="field mt-1" value={comment} maxLength={1000} onChange={e => setComment(e.target.value)} /></label>
              <button className="button" disabled={sending} onClick={sendFeedback}>{sending ? 'Guardando…' : 'Guardar revisión'}</button><p role="status">{feedbackStatus}</p>
            </div> : <p className="muted">Inicia sesión desde la página principal y vuelve a este enlace para comentar.</p>)}
          </div>}
        </div>}
      </section>

      <section className="panel" aria-labelledby="map-title">
        <h2 id="map-title" className="text-xl font-bold">Mapa de la partida · {timeLabel(currentTime)}</h2>
        <div className="mt-5 grid gap-6 lg:grid-cols-2">
          <div><InteractiveMap events={events} currentTime={currentTime} playerRoute={report.player_route} champion={stats?.champion_name} highlighted={highlighted} onHighlight={setHighlighted} /><p className="muted mt-3">Retrato: tus posiciones registradas en los últimos 3 minutos. Espadas: bajas. Torre y cristal: estructuras destruidas. Ojo: visión colocada. Monstruo: objetivo neutral. Estos símbolos muestran eventos pasados, no el estado actual de las estructuras ni tu visión.</p></div>
          <div className="space-y-4">
            <label className="block">Momento de la partida<input aria-label="Tiempo de la partida" type="range" min={0} max={duration} step={1000} value={currentTime} onChange={e => { setTime(Number(e.target.value)); if (decision && Number(e.target.value) > decision.timestamp && !revealed) { setSelected(null); setChoice(null); } }} className="mt-3 w-full accent-cyan-400" /></label>
            <div className="grid grid-cols-2 gap-3"><label>Mostrar eventos<select className="field mt-1" value={filter} onChange={e => setFilter(e.target.value)}><option value="all">Todos</option>{Object.entries(eventNames).map(([k,v]) => <option key={k} value={k}>{v}</option>)}</select></label><label>Período visible<select className="field mt-1" value={windowMs} onChange={e => setWindow(Number(e.target.value))}><option value={180000}>Últimos 3 min</option><option value={60000}>Último minuto</option><option value={0}>Desde el inicio</option></select></label></div>
            <p className="muted">Pasa el mouse sobre un icono del mapa: su hora se iluminará aquí. También puedes seleccionarlo con el teclado o tocarlo. Las posiciones de tu campeón muestran siempre los últimos 3 minutos.</p>
            <ul ref={eventList} className="max-h-80 space-y-2 overflow-auto" aria-label="Eventos y posiciones hasta el tiempo seleccionado">{timelineRows.map(row => <li key={row.id} data-highlighted={highlighted === row.id} onMouseEnter={() => setHighlighted(row.id)} onMouseLeave={() => setHighlighted(null)} className={`rounded-lg border p-3 text-sm transition-colors ${highlighted === row.id ? 'border-cyan-300 bg-cyan-950' : 'border-transparent bg-slate-800'}`}><div className="flex items-start gap-3"><span className={`rounded px-1 font-semibold tabular-nums ${highlighted === row.id ? 'bg-cyan-300 text-slate-950' : 'text-cyan-200'}`}>{timeLabel(row.timestamp)}</span><div><p className="font-medium">{row.title}</p>{row.note && <p className="mt-1 text-xs text-slate-400">{row.note}</p>}</div></div></li>)}</ul>
            {!timelineRows.length && <p className="muted">No hay eventos para este período y filtro. Avanza en el tiempo o elige otro tipo de evento.</p>}
          </div>
        </div>
      </section>

      <details className="panel"><summary className="cursor-pointer font-bold">Cómo puede jugar cada equipo</summary>
        <p className="mt-4">{report.archetype}: {report.model_reason}</p><p className="muted mt-2">Esta guía se basa en los campeones de ambos equipos. Los puntos indican qué estilo encaja mejor, no la probabilidad de ganar. Es una orientación para toda la partida.</p>
        <div className="mt-4 grid gap-4 md:grid-cols-2">{[['Tu equipo',report.composition],['Rival',report.enemy_composition]].map(([label,picks]) => <div key={String(label)}><h3 className="font-bold">{String(label)}</h3>{(picks as Playbook['composition']).map(p => <p key={p.champion_id} className="mt-2 flex items-center gap-2"><GameIcon kind="champion" champion={p.champion_name} className="h-8 w-8 shrink-0" />{roles[p.role] ?? 'Rol no identificado'}: {p.champion_name}</p>)}</div>)}</div>
        <div className="mt-4 grid gap-3 md:grid-cols-2">{report.model_evaluation.map(m => <div key={m.key} className="rounded-lg bg-slate-800 p-3"><strong>{m.name} · {m.score} pts</strong><p className="muted">{m.reason}</p></div>)}</div>
        {report.game_plan && <div className="mt-4"><p>{report.game_plan.win_condition}</p>{report.game_plan.phases.map(p => <p key={p.title} className="muted mt-2">{p.title}: {p.action}</p>)}</div>}
      </details>
      {stats && <details className="panel"><summary className="cursor-pointer font-bold">Resumen de estadísticas</summary><dl className="mt-4 grid grid-cols-2 gap-4 md:grid-cols-4">{[
        ['Bajas / muertes / asistencias',`${stats.kills ?? '—'} / ${stats.deaths ?? '—'} / ${stats.assists ?? '—'}`],['Súbditos y monstruos por minuto',stats.cs_per_min],['Puntuación de visión por minuto',stats.vision_per_min],['Daño por minuto',stats.damage_per_min],['Oro por minuto',stats.gold_per_min],['Wards colocados',stats.wards_placed],['Wards retirados',stats.wards_killed],['Daño a torres',stats.turret_damage],['Participación en bajas (%)',stats.kill_participation_pct],['Rival de línea',stats.lane_opponent],['Súbditos frente al rival de línea',stats.cs_delta],['Oro frente al rival de línea',stats.gold_delta],
      ].map(([label,value]) => <div key={String(label)}><dt className="muted">{label}</dt><dd className="text-lg font-semibold">{value ?? 'Sin datos'}</dd></div>)}</dl></details>}
    </>}
  </div>;
}
