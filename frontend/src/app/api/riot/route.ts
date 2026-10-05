import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';
import { backend } from '@/lib/backend';

export async function POST(request: Request) {
  // JSON + same-origin requests; never accept identity or service headers from the caller.
  if (request.headers.get('origin') !== new URL(process.env.NEXTAUTH_URL ?? request.url).origin || !request.headers.get('content-type')?.startsWith('application/json')) {
    return Response.json({ detail: 'Origen inválido.' }, { status: 403 });
  }
  const session = await getServerSession(authOptions);
  if (!session?.user.id) return Response.json({ detail: 'Inicia sesión para continuar.' }, { status: 401 });
  const reader = request.body?.getReader();
  if (!reader) return Response.json({ detail: 'Solicitud vacía.' }, { status: 400 });
  const chunks: Uint8Array[] = [];
  let size = 0;
  while (true) {
    const { value: chunk, done } = await reader.read();
    if (done) break;
    size += chunk.length;
    if (size > 4096) { await reader.cancel(); return Response.json({ detail: 'Solicitud demasiado grande.' }, { status: 413 }); }
    chunks.push(chunk);
  }
  const raw = Buffer.concat(chunks).toString('utf8');
  let input: Record<string, unknown>;
  try { input = JSON.parse(raw); } catch { return Response.json({ detail: 'JSON inválido.' }, { status: 400 }); }
  if (!input || typeof input !== 'object' || Array.isArray(input)) return Response.json({ detail: 'Solicitud inválida.' }, { status: 400 });
  const value = (key: string) => typeof input[key] === 'string' ? input[key] as string : '';
  const puuid = value('puuid');
  const token = value('token');
  const enc = encodeURIComponent;
  let path = '', method = 'GET', body: unknown;
  switch (input.action) {
    case 'players': path = '/api/v1/players'; break;
    case 'search': {
      const name = value('gameName').trim(), tag = value('tagLine').trim();
      if (name.length < 3 || name.length > 16 || !/^[A-Za-z0-9]{3,5}$/.test(tag)) break;
      path = `/api/v1/players/by-riot-id/${enc(name)}/${enc(tag)}/matches?region=LAS&count=5`; break;
    }
    case 'analyze':
      if (/^LA2_[0-9]{1,20}$/.test(value('matchId')) && puuid.length >= 10 && puuid.length <= 100) path = `/api/v1/matches/${value('matchId')}/playbook?puuid=${enc(puuid)}`;
      break;
    case 'history': case 'stopHabit':
      if (puuid.length >= 10 && puuid.length <= 100) { path = `/api/v1/${input.action === 'history' ? 'history' : 'habits'}?puuid=${enc(puuid)}`; method = input.action === 'history' ? 'GET' : 'DELETE'; } break;
    case 'habit': path = '/api/v1/habits'; method = 'POST'; body = { puuid }; break;
    case 'share': path = '/api/v1/shares'; method = 'POST'; body = { puuid, match_id: value('matchId'), version: value('version') }; break;
    case 'revoke': case 'feedback':
      if (/^[A-Za-z0-9_-]{43}$/.test(token)) {
        path = `/api/v1/shares/${token}${input.action === 'feedback' ? '/feedback' : ''}`;
        method = input.action === 'feedback' ? 'POST' : 'DELETE';
        if (input.action === 'feedback') body = { decision: value('decision'), verdict: value('verdict'), comment: value('comment') };
      } break;
    case 'telemetry': path = '/api/v1/telemetry'; method = 'POST'; body = { event: value('event'), match_id: value('matchId'), decision: value('decision') }; break;
    case 'export': path = '/api/v1/account/export'; break;
    case 'deleteAccount': path = '/api/v1/account'; method = 'DELETE'; break;
  }
  if (!path) return Response.json({ detail: 'Solicitud inválida.' }, { status: 400 });
  const response = await backend(path, session.user.id, method, body);
  const data = await response.json().catch(() => ({ detail: 'Respuesta inválida del servicio.' }));
  const headers = new Headers({ 'Cache-Control': 'no-store' });
  for (const name of ['Retry-After', 'X-Request-ID']) { const value = response.headers.get(name); if (value) headers.set(name, value); }
  return Response.json(data, { status: response.status, headers });
}
