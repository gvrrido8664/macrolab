# Implementación del plan — 6 de septiembre de 2026

## Disponible en el código

- Demo pública `/demo`, con fixture sintética explícita y sin login, backend o Riot.
- Login de aplicación GitHub mediante NextAuth, configurable con credenciales OAuth. El proveedor simulado existe exclusivamente en desarrollo; las sesiones simuladas ya emitidas también se rechazan en producción.
- Backend protegido por secreto de servicio; identidad obtenida de sesión en Next, límites por usuario y admisión global para Riot.
- Solo/Dúo LAS, rechazo de mapas/colas incompatibles, errores de configuración explícitos, `Retry-After` propagado y presupuesto temporal del cliente Riot.
- Caché SQLite de listados y partidas, payloads crudos con vencimiento de 30 días; limpieza periódica cada hora.
- Contrato Pydantic v2 con TypeScript y validadores de ejecución generados, mediciones ausentes como `null` y abstención ante timelines incompletos.
- Tres reglas temporales versionadas: muerte previa a objetivo, compra previa a objetivo y participación en baja seguida por objetivo del equipo. Ventana experimental de 60 s.
- Evidencia por identificador y timestamp, interpretación, alternativas, límites y contexto de oro de la muestra anterior. La composición rival modifica alternativas heurísticas; las fases se identifican como guía general.
- Ejercicio antes de revelar el desenlace; mapa sin eventos futuros, filtros y ventana temporal. Wards sin coordenada no se inventan y posiciones muestreadas no se unen como ruta exacta.
- Historial persistente por usuario y PUUID, deduplicación por partida/versión, selección de jugadores seguidos y un hábito evaluado sobre cinco partidas nuevas elegibles.
- Enlaces de lectura que vencen en siete días, revocación por propietario, comentarios por decisión de usuarios autenticados y revisiones visibles al autor.
- Exportación y borrado de datos del usuario, aviso de no afiliación y landing ajustada a capacidades disponibles.
- Comandos de backup, restauración a destino nuevo, retención y contadores de piloto. Pruebas de integridad/restauración, aislamiento y errores HTTP.

Se conservaron Next.js, FastAPI y las dependencias existentes. SQLite utiliza la biblioteca estándar. Las tablas contienen las identidades de OAuth; no se añadió una tabla de usuarios duplicada sin datos propios. Las imágenes de campeones con versión inventada se sustituyeron por nombres, eliminando esa dependencia de assets. No se introdujeron un LLM, microservicios ni una cola de trabajos.

## Verificación reproducible

Frontend: `npm run check` pasa lint, 3 pruebas (tiempo, contrato e identidad), TypeScript y build.

Backend: `venv/Scripts/python.exe -m unittest -v` pasa 19 pruebas de reglas y casos límite, aislamiento, persistencia, hábitos, caché, límites, backup/restauración y HTTP real sobre un servidor efímero.

Sincronización del contrato y demo, desde el backend:

```powershell
.\venv\Scripts\python.exe export_contract.py ../macrolab/src/types/playbook.ts --check
.\venv\Scripts\python.exe demo.py ../macrolab/src/data/demo.json
```

Se probó en navegador la demo con build de producción y el recorrido autenticado en un entorno de desarrollo aislado con respuestas Riot sintéticas: búsqueda, análisis, historial, hábito, enlace compartido y comentario. El script `dev_fixture_server.py` utiliza una base temporal y solo escucha en localhost. La demo final se comprobó sin errores de consola y sin desbordamiento horizontal a 390 px. No representa validación de credenciales OAuth reales, calidad de coaching, capacidad de producción ni partidas reales de Riot.

## Continuación local — 6 de septiembre de 2026

Por decisión del usuario, el alcance actual es exclusivamente local. Frontend en `http://127.0.0.1:3000` con `npm run dev`, cuenta «Desarrollo» habilitada y backend en `127.0.0.1:8000`. `NEXTAUTH_URL` coincide con ese origen. Hosting, dominio y OAuth público quedan aplazados.

La clave Riot local respondió HTTP 200. Se analizaron tres partidas Solo/Dúo reales: todas produjeron estado `ready`, con 3, 2 y 2 decisiones. También se verificó por HTTP el recorrido completo de sesión local → Next → FastAPI → Riot → análisis guardado; la primera partida está disponible en el historial de la cuenta Desarrollo. Esto verifica integración, no la calidad de las recomendaciones.

Se generó `macrolab-backend/data/pilot-cases-2026-09-06.csv` con siete casos reales y etiquetas humanas vacías. Es material local inicial de un solo jugador; no reemplaza la muestra independiente de 50 casos ni incluye evaluación de coaches. No se publicó ni envió a terceros.

La portada ahora lee la configuración de acceso en cada solicitud, evitando congelarla al compilar. SQLite carga el `.env` del backend tanto en el servidor como en los comandos de operación y resuelve rutas relativas desde ese directorio: ejecutar un respaldo desde otra carpeta ya no puede seleccionar accidentalmente otra base. Una prueba comprueba la ruta y el contenido del respaldo.

## Pendientes externos para una futura publicación

La presentación de informes se revisó para traducir estructuras, objetivos y tipos de visión también en análisis guardados. Las ubicaciones ausentes se explican por evento y las compras no muestran un aviso de ubicación innecesario. El mapa utiliza retratos para las posiciones del jugador y símbolos de estructuras, visión, combate y objetivos; las composiciones incluyen retratos. El catálogo de imágenes se verificó contra [Data Dragon de Riot](https://developer.riotgames.com/docs/lol#data-dragon), versión 16.17.1, con iniciales como respaldo si una imagen no está disponible. No se atribuyen campeones a bajas que el informe no identifica. La revisión se comprobó en navegador y con cuatro pruebas frontend, lint, TypeScript y build.

1. Crear/configurar el cliente OAuth GitHub y colocar `GITHUB_ID`, `GITHUB_SECRET` y `NEXTAUTH_URL` del entorno. Callback: `<origen>/api/auth/callback/github`. No inventar credenciales ni confundir esta cuenta con propiedad de Riot.
2. Configurar clave Riot adecuada al uso autorizado, registrar el producto y completar los requisitos externos del portal. RSO queda sujeto al acceso correspondiente; no se implementó un supuesto RSO sin credenciales.
3. Elegir hosting con disco persistente para SQLite, mantener FastAPI en red privada o protegido, configurar HTTPS, backups externos y probar la restauración en el destino elegido. Esta entrega no publica el servicio.
4. Ejecutar el piloto y revisión humana descritos en `PILOTO.md`. Las reglas son experimentales y no cuentan aún con el conjunto independiente de 50 decisiones revisadas por coaches.
5. Decidir precio y proveedor de cobro después de validar retorno e intención de pago. El plan original condiciona Pro y pagos a esos resultados: no se activaron suscripciones ni se implementó un checkout sin esa definición.

## Operación y límites

La base usa `PRAGMA user_version=2` y migración transaccional desde v1 para la telemetría por recurso. Guardar una nueva `analysis_version` al cambiar las reglas: informes existentes de una versión son inmutables, incluidos los compartidos. Copia de seguridad antes de migraciones. Para revertir el frontend/backend, desplegar la versión anterior compatible con el esquema; no borrar tablas para hacer rollback.

Los límites locales de Riot son conservadores y globales a esta base. Los 429 del proveedor se devuelven con su espera; no se reintentan automáticamente. Ajustar la capacidad según las cuotas concedidas y mediciones del piloto. El deadline Riot es 18 s con comprobación por bloque y timeout de lectura de hasta 4 s; Next reserva 25 s. Un socket bloqueado puede agotar su timeout antes de detectar el deadline. El hosting debe permitir ese margen.

Un proceso SQLite en disco local sirve al piloto; varias máquinas requieren otra base compartida y límites coordinados. `manage.py metrics` distingue usuarios que buscaron y abrieron evidencia y retorno a una segunda partida en siete días, excluyendo cohortes demasiado recientes y repeticiones de la misma partida. No demuestra mejora ni sustituye evaluación humana. `manage.py evaluation casos.csv` exporta una hoja local de revisión con etiquetas vacías. Las revisiones se conservan aunque venza o se revoque el enlace, hasta que el autor borre sus datos. Backups necesitan su propia rotación y control de acceso.
