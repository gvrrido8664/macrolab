# MacroLab

Laboratorio postpartida de League of Legends: decisiones con evidencia, hábitos y revisión compartida.

## Inicio local

1. Configura `macrolab-backend` siguiendo su README.
2. Copia `.env.example` a `.env.local`. Genera `AUTH_SECRET` y un `MACROLAB_SERVICE_SECRET` aleatorio de al menos 32 caracteres, igual en ambos proyectos. No los publiques.
3. Configura `NEXTAUTH_URL` con el origen exacto que abrirás (incluido puerto; localhost y 127.0.0.1 son distintos).
4. Ejecuta `npm install` y `npm run dev`.

`/demo` funciona sin backend, sin claves y sin sesión. `ALLOW_MOCK_AUTH=true` habilita una cuenta simulada solo en desarrollo. Esa cuenta sirve para pruebas locales, nunca como autenticación pública.

El entorno actual se mantiene local: abre `http://127.0.0.1:3000` y pulsa **Cuenta local de desarrollo**. El frontend debe arrancar con `npm run dev -- --hostname 127.0.0.1 --port 3000`; `npm start` usa producción y deshabilita ese acceso. La copia de portafolio no incluye análisis ni cuentas reales guardadas.

## Producción

Configura `GITHUB_ID` y `GITHUB_SECRET` para login real. Callback OAuth: `<NEXTAUTH_URL>/api/auth/callback/github`. Mantén `AUTH_SECRET` estable entre reinicios. Define `MACROLAB_API_URL` y el secreto interno; usa HTTPS y backend privado. Ejecuta `npm run check` y `npm start`. La demo funciona con build de producción incluso sin proveedor OAuth.

No hay cobros activos, RSO ni verificación de propiedad de cuentas Riot. Consulta [estado de implementación](IMPLEMENTACION.md) y [protocolo del piloto](PILOTO.md).

## Verificación

`npm run check`: lint, prueba temporal, TypeScript y build. Node 22.18+ (CI usa Node 22).

Para probar el flujo completo sin consumir Riot: inicia `dev_fixture_server.py` desde el backend; ejecuta Next en desarrollo con `MACROLAB_API_URL=http://127.0.0.1:8011`, `NEXTAUTH_URL=http://127.0.0.1:3001` y puerto 3001. Usa la cuenta local y busca `Ejemplo#LAS`. La base del servidor de fixtures es temporal y desaparece al cerrarlo.

El contrato TypeScript se genera con `export_contract.py` del backend. Después de cambiar modelos, regenera y ejecuta ambos checks. Las reglas nuevas requieren una `analysis_version` nueva y evaluación humana independiente antes de anunciar precisión.
