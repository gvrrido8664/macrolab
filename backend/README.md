# MacroLab API

FastAPI + SQLite, sin servicios adicionales. Python 3.12+.

## Desarrollo

```powershell
py -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Configura `RIOT_API_KEY` y `MACROLAB_SERVICE_SECRET` (>=32 caracteres aleatorios, idéntico al frontend). Opcional: `MACROLAB_DB_PATH`; por defecto `data/macrolab.sqlite3` junto al código. No agregues `.env` ni la base a Git.

```powershell
.\venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000 --no-access-log
```

Todas las rutas, salvo salud, requieren `X-Service-Key`. Los recursos privados exigen además `X-User-ID`, que solo Next debe generar desde su sesión. No exponer esa cabecera como identidad confiable sin autenticar el servicio. `/docs` y `/openapi.json` también requieren la clave interna. Se desactiva el log de acceso porque las URLs contienen identificadores y tokens de revisión; el middleware registra solo id, estado y duración.

La demo no es un fallback de errores: sin clave, las consultas reales devuelven 503. `dev_fixture_server.py` arranca un servidor aislado con datos sintéticos en 127.0.0.1:8011 y base temporal para pruebas de navegador.

## Pruebas y contrato

```powershell
.\venv\Scripts\python.exe -m unittest -v
.\venv\Scripts\python.exe export_contract.py ../frontend/src/types/playbook.ts
.\venv\Scripts\python.exe demo.py ../frontend/src/data/demo.json
```

Las pruebas HTTP usan requests y uvicorn con puertos efímeros y no consumen Riot. El contrato se valida con el mismo comando de exportación agregando `--check`.

## Operación

SQLite requiere disco persistente en un solo host. El esquema inicial es idempotente (`user_version=2`, migración transaccional desde v1). Incrementa la versión de esquema para migraciones futuras y la de análisis al modificar reglas; no reescribas reportes compartidos de una versión existente.

Servidor y comandos cargan el `.env` junto a `storage.py`, sin reemplazar variables del entorno. `MACROLAB_DB_PATH` relativa se resuelve desde el directorio del backend, independientemente de dónde ejecutes el comando; los destinos explícitos de backup/exportación son relativos al directorio de ejecución.

```powershell
.\venv\Scripts\python.exe manage.py backup backups/antes-del-cambio.db
.\venv\Scripts\python.exe manage.py restore backups/antes-del-cambio.db data/restaurada.sqlite3
.\venv\Scripts\python.exe manage.py prune
.\venv\Scripts\python.exe manage.py metrics
.\venv\Scripts\python.exe manage.py evaluation casos.csv
```

Backup y restore rechazan destinos existentes. Para recuperar, detener el servicio y configurar `MACROLAB_DB_PATH` al archivo restaurado. Verifica integridad y comportamiento antes de reabrir tráfico. Guarda backups fuera del host con acceso restringido y rotación definida; el comando local no los sube a ningún tercero.

La retención elimina caché vencida y telemetría de más de 30 días cada hora con el servicio activo. Las revisiones de coaches sobreviven al vencimiento/revocación del enlace, pero se eliminan al borrar los datos del autor. Los informes permanecen hasta que el usuario los borra. Ejecutar `prune` explícitamente si el servicio estuvo detenido. Las claves de caché de Match-V5 incluyen identificador regional de partida.

El deadline de integración es de 18 s con timeout de lectura de hasta 4 s y límite de 10 MB por respuesta; Next permite 25 s. Sin reintentos automáticos. El despliegue debe admitir esos tiempos. La cuota de admisión local (15/s y 80/2min) es conservadora y no sustituye las cuotas que conceda Riot.
