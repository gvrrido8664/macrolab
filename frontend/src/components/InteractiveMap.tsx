'use client';
import type { Event, RoutePoint } from '@/types/playbook';
import { eventTitle } from '@/lib/report-copy';
import { timeLabel } from '@/lib/client';
import GameIcon from './GameIcon';

export default function InteractiveMap({ events, currentTime, playerRoute, champion, highlighted, onHighlight }: { events: Event[]; currentTime: number; playerRoute: RoutePoint[]; champion?: string; highlighted: string | null; onHighlight: (id: string | null) => void }) {
  const points = playerRoute.filter(p => p.timestamp <= currentTime && p.timestamp >= currentTime - 180_000);
  const markers = [
    ...points.map(p => ({ id: `position:${p.timestamp}`, timestamp: p.timestamp, position: p.position_pct, title: `Posición de ${champion ?? 'tu campeón'}`, kind: 'champion' as const })),
    ...events.filter(e => e.timestamp <= currentTime && e.position_pct).map(e => ({ id: e.id, timestamp: e.timestamp, position: e.position_pct!, title: eventTitle(e), kind: e.type === 'BUILDING_KILL' ? (e.detail === 'INHIBITOR_BUILDING' ? 'inhibitor' as const : 'tower' as const) : e.type === 'CHAMPION_KILL' ? 'combat' as const : e.type === 'WARD_PLACED' ? 'ward' as const : 'objective' as const })),
  ].sort((a, b) => a.timestamp - b.timestamp);
  const active = markers.find(m => m.id === highlighted);
  // Draw the selected marker last so overlapping positions remain inspectable.
  const drawn = active ? [...markers.filter(m => m.id !== active.id), active] : markers;
  return <div>
    <svg viewBox="0 0 100 100" className="aspect-square w-full max-w-lg rounded-2xl border border-slate-700" role="group" aria-label="Mapa de eventos. Pasa sobre un icono para resaltar su hora en la lista.">
      <image href="/summoners-rift.jpg" width="100" height="100" preserveAspectRatio="none" />
      <rect width="100" height="100" fill="#020617" fillOpacity="0.25" />
      {drawn.map(m => {
        const x = Math.max(0, Math.min(92, m.position.x - 4));
        const y = Math.max(0, Math.min(89, m.position.y - 3));
        const label = `${timeLabel(m.timestamp)} · ${m.title}`;
        return <g key={m.id} transform={`translate(${x} ${y})`} role="button" tabIndex={0} aria-label={label} aria-pressed={active?.id === m.id} className="cursor-pointer text-amber-200 focus:outline focus:outline-2 focus:outline-cyan-300" onMouseEnter={() => onHighlight(m.id)} onMouseLeave={() => onHighlight(null)} onFocus={() => onHighlight(m.id)} onBlur={() => onHighlight(null)} onClick={() => onHighlight(m.id)} onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onHighlight(m.id); } }}>
          <title>{label}</title>
          {active?.id === m.id && <rect x="-.5" y="-.5" width="9" height="7" rx="1" fill="#083344" stroke="#67e8f9" strokeWidth=".5" />}
          <svg x="1" width="6" height="6"><GameIcon kind={m.kind} champion={champion} /></svg>
        </g>;
      })}
    </svg>
  </div>;
}
