# MacroLab — análisis postpartida

Proyecto personal de **Ignacio Garrido**, Ingeniero en Informática titulado. Desarrollo propio de la aplicación; librerías, plantillas, datos e imágenes de terceros conservan su autoría.

Next.js/React y FastAPI/SQLite reunidos en un repositorio con `frontend/` y `backend/`. Analiza eventos y posiciones de una partida, propone momentos para revisar y permite guardar informes y feedback con controles de acceso.

![Demo sin claves](docs/demo.jpg)

## Primera demostración, sin backend ni credenciales
Node 22.18+:
```powershell
cd frontend
npm ci
npm run dev -- --hostname 127.0.0.1 --port 3000
```
Abre `http://127.0.0.1:3000/demo`. La partida es sintética; tus elecciones de la demo no se guardan. Para regenerarla, instala dependencias Python del backend y ejecuta desde `backend/`: `python demo.py ../frontend/src/data/demo.json`.

## Verificación
Desde `backend/`, Python 3.12+:
```powershell
python -m pip install -r requirements.txt
python -m unittest -v
python export_contract.py ../frontend/src/types/playbook.ts --check
```
Desde `frontend/`:
```powershell
npm run check
```
Verificado: 19 pruebas del backend, 4 del frontend, contrato, lint y tipos. También se clonó el repositorio publicado, se instalaron dependencias con npm ci y se ejecutó npm run check completo: lint, pruebas, tipos y build Turbopack aprobados. El typecheck genera primero los tipos de rutas para funcionar desde una copia limpia.

## Flujo completo local
Sigue los README de ambas carpetas. Para datos sintéticos usa `backend/dev_fixture_server.py`, puerto 8011, y el frontend en desarrollo con `ALLOW_MOCK_AUTH=true`, `MACROLAB_API_URL=http://127.0.0.1:8011` y un secreto interno local compartido. No se distribuyen secretos ni bases de usuarios.

## Límites
Las reglas permiten reflexionar sobre eventos observados; no son predicciones calibradas. Las posiciones discretas no reconstruyen todos los movimientos o la visión del jugador. No hay cobros activos ni verificación RSO. La integración real con Riot requiere clave propia y no fue ejecutada. SQLite supone un único host con disco persistente. Ver [créditos](THIRD_PARTY.md).

English: evidence-based post-match review, a credential-free synthetic demo, isolated HTTP/storage tests and a generated frontend/backend contract.

## Comprobación del flujo completo

Dashboard restaurado. 19 pruebas backend, 4 frontend, contrato, lint, tipos y build Turbopack aprobados con /dashboard incluida. Flujo en navegador con backend y base temporal: login local, búsqueda ficticia, análisis, alternativas, navegación temporal, hábito, historial persistente al recargar, enlace de revisión, comentario recuperado por el autor y revocación comprobados. API Riot y OAuth reales pendientes.

La cuenta de desarrollo y las respuestas Riot son simuladas: esta prueba no acredita una integración real con Riot ni con GitHub OAuth. La base temporal persiste durante la sesión de prueba y desaparece al detener el servidor. El hábito se inició en 0/5; no se completaron cinco partidas en navegador. La exportación y el borrado de cuenta solo tienen cobertura automatizada, no se ejecutaron desde la interfaz.

![Dashboard local con informe recuperado](docs/dashboard-prueba.jpg)
