import 'server-only';

export async function backend(path: string, user?: string, method = 'GET', body?: unknown) {
  const secret = process.env.MACROLAB_SERVICE_SECRET;
  if (!secret || secret.length < 32) return Response.json({ detail: 'El servicio necesita configuración. Puedes usar la demo.' }, { status: 503 });
  try {
    return await fetch(new URL(path, process.env.MACROLAB_API_URL ?? 'http://127.0.0.1:8000'), {
      method, cache: 'no-store', signal: AbortSignal.timeout(25_000),
      headers: { 'X-Service-Key': secret, ...(user ? { 'X-User-ID': user } : {}), 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    return Response.json({ detail: 'No fue posible conectar con el servicio. Intenta de nuevo.' }, { status: 502 });
  }
}
