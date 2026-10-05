'use client';
import icons from '@/data/champion-icons.json';

export default function GameIcon({ kind, champion, className }: { kind: 'champion' | 'tower' | 'inhibitor' | 'ward' | 'combat' | 'objective'; champion?: string; className?: string }) {
  const url = champion ? (icons as Record<string, string>)[champion] : undefined;
  return <svg viewBox="0 0 24 24" className={className} aria-hidden="true">
    <rect x="1" y="1" width="22" height="22" rx="4" fill="#0f172a" stroke="#cbd5e1" />
    {kind === 'champion' ? <>
      <text x="12" y="16" textAnchor="middle" fill="white" fontSize="10">{champion?.slice(0, 2) || '?'}</text>
      {url && <image href={url} x="2" y="2" width="20" height="20" onError={e => { e.currentTarget.style.display = 'none'; }} />}
    </> : <g fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      {kind === 'tower' && <path d="M6 20h12M8 19V10L6 8V4h3v3h2V4h2v3h2V4h3v4l-2 2v9M11 19v-5h2v5" />}
      {kind === 'inhibitor' && <path d="m12 4 5 7-5 7-5-7 5-7Zm-7 13v3h14v-3" />}
      {kind === 'ward' && <><path d="M4 10s3-5 8-5 8 5 8 5-3 5-8 5-8-5-8-5Zm8 5v5M8 20h8" /><circle cx="12" cy="10" r="2" /></>}
      {kind === 'combat' && <path d="m5 4 3 1 11 14M4 16l4 4M4 20l4-4M19 4l-3 1L5 19m11-3 4 4m0-4-4 4" />}
      {kind === 'objective' && <path d="m12 3 3 5 5 2-2 7-6 4-6-4-2-7 5-2 3-5Zm-4 9 2 1m6-1-2 1m-4 4h4" />}
    </g>}
  </svg>;
}
