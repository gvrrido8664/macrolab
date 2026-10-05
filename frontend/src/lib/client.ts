import { isPlaybook, isPlayerMatches, isHistory, isTrackedPlayer } from '@/types/playbook';

export async function requestLab<T>(body: Record<string, string>): Promise<T> {
  const response = await fetch('/api/riot', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body), signal: AbortSignal.timeout(30_000) });
  const data = await response.json();
  if (!response.ok) {
    const detail = data && typeof data.detail === 'string' ? data.detail : 'Solicitud inválida.';
    const retry = response.headers.get('Retry-After');
    throw new Error(`${detail}${retry ? ` Reintenta en ${retry} s.` : ''}`);
  }
  if ((body.action === 'analyze' && !isPlaybook(data)) || (body.action === 'search' && !isPlayerMatches(data))) {
    throw new Error('El servicio devolvió un formato incompatible. Actualiza la página o inténtalo más tarde.');
  }
  if (body.action === 'history' && !isHistory(data)) {
    throw new Error('El historial tiene un formato incompatible. Tus datos siguen guardados.');
  }
  if (body.action === 'players' && (!Array.isArray(data) || !data.every(isTrackedPlayer))) throw new Error('El listado de jugadores no es compatible.');
  return data as T;
}

export function timeLabel(milliseconds: number) {
  const seconds = Math.floor(milliseconds / 1000);
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`;
}
