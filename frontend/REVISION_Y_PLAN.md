# MacroLab: revisión técnica, oportunidad de mercado y plan de implementación

Fecha: 6 de septiembre de 2026.

**Recomendación:** convertir el MVP en un entrenador postpartida que muestre hasta tres decisiones revisables, explique qué evidencia las respalda y proponga un hábito para las próximas partidas. Primero corregir la fiabilidad del análisis; después validar si este ciclo produce uso recurrente.

## 1. Alcance y evidencia

Se revisaron todos los archivos propios de código fuente del frontend y backend, tipos, configuración, documentación, ejemplos de entorno, pruebas y workflows de ambos repositorios. Se consultó la guía local de Route Handlers de Next.js 16.3.4. Se excluyeron dependencias, archivos generados, secretos y contenido binario de imágenes. No se modificó código de aplicación.

Verificación ejecutada:

- `npm run check`: ESLint, TypeScript y compilación de producción correctos.
- Backend: `venv/Scripts/python.exe -m unittest -v`, 11 pruebas correctas.
- Comprobaciones adicionales sin red: sin clave Riot y con PUUID el análisis devuelve 502; composición vacía selecciona FRONT_TO_BACK; `info: null` provoca AttributeError.
- No se ejecutó una sesión interactiva completa de navegador, consultas reales a Riot, prueba de carga ni auditoría de vulnerabilidades de dependencias. Los resultados de compilación no demuestran que el login funcione en producción ni que las recomendaciones sean correctas.
- Ambos repositorios muestran sus archivos principales como no rastreados por Git. No se alteró ese estado. Antes de colaborar o desplegar, establecer una versión base revisada sin incorporar secretos.

## 2. Arquitectura y estado actual

Flujo: navegador → sesión NextAuth → `POST /api/riot` → FastAPI → Account-V1/Match-V5 → reglas Python → estadísticas, composición y eventos → dashboard SVG.

La base es razonable para este tamaño: pocas dependencias, TypeScript estricto, secreto y clave Riot en servidor, validación de entradas, timeouts, mapa SVG responsivo, pruebas deterministas y CI en ambos repositorios. Mantener Next.js y FastAPI; una reescritura no resuelve el problema principal.

El producto obtiene datos reales cuando Riot está configurado. Sus ocho «modelos» son puntuaciones heurísticas sobre listas de campeones, no modelos entrenados. El plan es una plantilla por arquetipo. Las sugerencias suelen reformular estadísticas finales; todavía no detectan decisiones concretas ni evalúan su ejecución. El historial son diez registros en localStorage, sin identidad del jugador consultado.

## 3. Hallazgos priorizados

P1: resolver antes de una beta pública fiable. P2: corregir durante la preparación del piloto. Las referencias son líneas del estado revisado.

| Prioridad | Hallazgo y evidencia | Consecuencia | Corrección mínima y validación |
|---|---|---|---|
| P1 | Único proveedor `riot-mock`; `src/app/api/auth/[...nextauth]/route.ts:13` rechaza siempre en producción. | `next start` no permite nuevas sesiones; el CTA de demo conduce a un acceso inutilizable. | Demo pública con datos estáticos claramente identificados; proveedor real para cuentas. Probar login, logout y rechazo sin sesión en una compilación de producción. |
| P1 | No hay filtro de cola/mapa en `riot_api.py:33` ni guardia de compatibilidad en `main.py:104`; el mapa siempre es Summoner's Rift. | Una partida ARAM u otro modo recibe zonas y estrategia de otro mapa. | Admitir inicialmente Solo/Dúo en mapa 11; filtrar listado y comprobar detalles antes del motor. Una partida incompatible debe devolver un estado explícito sin playbook. |
| P1 | El proxy corta a 12 s (`src/app/api/riot/route.ts:10`), pero búsqueda y análisis hacen dos peticiones Riot secuenciales con timeout de 10 s cada una (`riot_api.py:18`, `main.py:98`, `main.py:113`). | Puede fallar una operación cuyos dos pasos habrían terminado. El timeout de requests tampoco es un presupuesto total del flujo. | Definir deadline total compatible con el hosting y repartirlo por llamada; medir duración. Probar dos respuestas lentas y corte controlado. |
| P1 | `_get` no conserva cabeceras de límite ni tiene caché; FastAPI retransmite 429 sin Retry-After y el proxy vuelve a descartar cabeceras. | Reanálisis consumen cuota; la interfaz no sabe cuándo reintentar. | Caché de partidas terminadas, propagación de Retry-After y límites de admisión antes de Riot. No reintentar 401/403 ni hacer bucles de reintento ilimitados. |
| P1 condicional | Rutas FastAPI sin autenticación de servicio (`main.py:87`, `main.py:104`). | Si el backend se publica directamente, se puede eludir la sesión de Next y consumir la cuota Riot. No se verificó exposición pública actual. | Mantenerlo en red privada; si debe ser público, autenticar Next→FastAPI y aplicar límites. Verificar que una llamada externa sin credencial no llegue a Riot. |
| P1 | Historial global `macrolab-history`, sin PUUID, y deduplicación solo por matchId (`DashboardClient.tsx:44`, `:76`). | Consultar varios jugadores mezcla su supuesto progreso; analizar dos participantes de una misma partida reemplaza el registro. | Clave por cuenta de app + PUUID + matchId; no atribuir registros antiguos sin identidad. Probar dos jugadores en la misma partida y cambio de sesión. |
| P1 | `InteractiveMap.tsx:9` filtra por minuto truncado. Un evento de 10:59 aparece al seleccionar 10:00. | El cursor muestra información del futuro respecto de su etiqueta. | Filtrar timestamp en milisegundos o etiquetar explícitamente intervalos completos. Probar 10:00 frente a un evento de 10:59. |
| P1 de producto | Wards acumulados indefinidamente, círculo fijo `r=10` (`InteractiveMap.tsx:31`) y polilínea entre muestras llamada «Tu ruta real» (`DashboardClient.tsx:254`). | Puede interpretarse como visión activa o recorrido exacto; el código no reconstruye ninguno de ellos. | Mostrar colocaciones históricas, quitar cobertura ficticia y denominar la ruta «posiciones muestreadas». Ventana temporal seleccionable y antigüedad de cada muestra. |
| P1 de producto | `main.py:125` solo entrega composición aliada a `select_archetype`; zonas y fases son estáticas (`riot_api.py:180`, `:208`, `:322`). | El mismo equipo recibe el mismo plan aunque cambien rival, ventaja, objetivos y contexto. Incluso sin composición se elige FRONT_TO_BACK. | Añadir «evidencia insuficiente», alternativas y reglas por contexto observado; no presentar plantilla como evaluación de disciplina. Validar con revisión humana independiente. |
| P2 | Sin clave, búsqueda devuelve 503; análisis usa mock sin participantes y falla con PUUID (`main.py:96`, `riot_api.py:39`). | El modo demo no cubre el recorrido completo. Reproducido: 502 con PUUID. | Fixture completa separada de integración real; `data_source=demo` explícito. Sin clave en modo real debe responder error de configuración. |
| P2 | `patch` se inventa como major.minor.1 (`riot_api.py:253`). | Puede solicitar imágenes de una versión inexistente o inadecuada. | Resolver versión publicada de Data Dragon y mantener fallback local. Riot documenta que versiones de cliente y assets no siempre equivalen. |
| P2 | Respuestas anidadas como dict, casteo `as T`, comprobaciones incompletas (`main.py:35`, `DashboardClient.tsx:17`, `riot_api.py:356`). | Datos nulos o malformados pueden provocar 500 o romper el render. Reproducido AttributeError con `info=null`. | Modelos Pydantic concretos y validación de estructura externa. No convertir campos desconocidos en cero; comprobar contrato frontend/backend en CI. |
| P2 | localStorage se escribe dentro del actualizador de estado y sin manejo de fallo; lectura valida solo Array.isArray. | Cuota agotada o contenido antiguo/corrupto puede afectar al análisis o al render. | Separar persistencia de la actualización, validar registros y permitir análisis aunque falle el guardado. |
| P2 | La landing presenta 45% fijo, simulador/editor y hábitos a largo plazo (`src/app/page.tsx:79`, `:188`, `:196`). | Promete capacidades que el producto todavía no implementa; su comparación competitiva no refleja el mercado observado. | Etiquetar ejemplo ilustrativo y anunciar únicamente capacidades disponibles; sustituir comparaciones genéricas por afirmaciones verificables. |

Otros ajustes acotados: unificar validación de tagline (Unicode en Next frente a ASCII en FastAPI); mensajes distintos para sesión vencida, clave rechazada y límite Riot; estado de búsqueda sin partidas; separar muertes/bajas del jugador de bajas globales; ofrecer lista textual navegable de eventos y foco visible. Los tests actuales ejercitan reglas pero no rutas HTTP, contrato completo, errores de almacenamiento ni la calidad estratégica. Dividir el dashboard por secciones solo al introducir esas funcionalidades, sin crear un sistema genérico de componentes.

## 4. Mercado: qué ya existe y dónde competir

Consulta de páginas oficiales al 06-09-2026. Son capacidades anunciadas por sus proveedores, no pruebas independientes de calidad ni un censo completo del mercado.

| Referente | Oferta observada | Implicación para MacroLab |
|---|---|---|
| [Mobalytics GPI y Challenges](https://mobalytics.gg/lol/lp/gpi) | Perfil de fortalezas/debilidades y retos de mejora. | «Detectar debilidades y proponer hábitos» por sí solo no diferencia. |
| [iTero](https://www.itero.gg/es) | Anuncia Macro Coach, análisis de partidas y estrategia personalizada; tiene página en español. | Ni «macro con IA» ni «en español» bastan como innovación. |
| [Agent by OP.GG](https://op.gg/ai) | Anuncia coaching, alertas, ayuda de builds y voz durante la partida. | Un asistente conversacional o una voz serían costosos de diferenciar. |

**Hipótesis de posicionamiento:** «Revisa tres decisiones de tu partida con evidencia en el mapa y comprueba qué cambió en tus siguientes cinco partidas».

Segmento inicial propuesto, todavía no validado: jugadores hispanohablantes de Solo/Dúo en LAS, con soporte como primer rol. Permite acotar reglas de preparación de objetivos y evitar evaluar cinco roles con la misma profundidad desde el día uno. Entrevistar también junglas; cambiar el rol inicial si muestran una necesidad y retorno superiores.

No afirmar que nadie ofrece estas funciones. La ventaja defendible potencial es un corpus de decisiones corregidas por coaches, reglas versionadas y evidencia de utilidad para ese segmento, no el uso de un LLM.

## 5. Mejoras propuestas y experimentos

| Orden | Mejora | Primera implementación | Evidencia de valor y límite |
|---|---|---|---|
| 1 | Tres momentos para revisar | Detectar muertes cercanas a capturas de objetivos, compras cercanas a esas ventanas y secuencias baja→estructura/objetivo. Cada tarjeta enlaza al tiempo y datos originales. | Dos coaches revisan casos y contraejemplos. Presentar asociación temporal, nunca «causaste perder el dragón». |
| 2 | Explicación de incertidumbre | Cada conclusión distingue dato observado, derivación y estimación; incluye información que falta y motivos de abstención. | El jugador puede explicar por qué recibió el consejo. No asignar probabilidades numéricas sin calibración. |
| 3 | Laboratorio de decisiones | Antes de revelar el desenlace, mostrar dos alternativas de una escena postpartida y explicar costes/condiciones. | Validar sesiones manuales primero; revisar que el enunciado no use información posterior ni simule lo que el jugador veía. No prometer winrate contrafactual. |
| 4 | Un hábito durante cinco partidas | Elegir un solo foco, por ejemplo reducir muertes en ventanas previas a objetivos observados; mostrar numerador, denominador y ejemplos. | Medir adopción y retorno. Comparar solo partidas elegibles; cinco partidas sirven para feedback, no para demostrar causalidad. |
| 5 | Revisión compartida con coach | Enlace revocable a informe, comentarios por timestamp y corrección «de acuerdo / falta contexto / incorrecto». | Pilotar con tres coaches. Añadir trabajo en equipo únicamente si repiten el uso. |
| 6 | Contexto estratégico adaptable | Puntuar varias alternativas con composición rival, rol, ventaja observable y estado de objetivos; versionar reglas. | Comparar contra el motor actual en partidas no usadas para ajustar reglas. Un LLM puede redactar después, sin decidir hechos. |

Ejemplo ilustrativo de tarjeta: «Moriste 32 s antes de que el rival capturara un dragón. Revisa si era razonable exponerte en esa ventana». Evidencia: timestamps de muerte y captura; limitación: esos datos no prueban que debieras disputar el objetivo ni describen la visión disponible. Ofrecer también «ceder e intercambiar recursos» cuando el contexto lo permita.

La API actual no permite reconstruir desde este código cobertura exacta de wards, trayectorias continuas, estado detallado de oleadas ni todos los recursos disponibles. No construir un simulador preciso con esas aproximaciones. Cualquier regla nueva requiere primero confirmar campos y cadencia en muestras reales autorizadas.

## 6. Implementación técnica

Mantener la arquitectura existente. Next gestiona sesión y experiencia; FastAPI mantiene Riot, validación y análisis. Añadir una sola base relacional al necesitar cuentas e historial persistente. La selección de proveedor y coste se hace al conocer hosting y carga; no requiere una nueva arquitectura distribuida.

**Contrato de análisis:** conservar estadísticas útiles y añadir `schema_version`, `analysis_version`, `data_source`, `queue_id`, `map_id`, `patch`, estado `ready/unsupported/insufficient_data`, incidencias de calidad y decisiones. Cada decisión lleva id de regla, timestamp, referencias a eventos, hechos, interpretación, alternativas, limitaciones y confianza categórica definida por cobertura de datos.

**Reglas:** funciones puras en Python, con parámetros versionados para ventanas y umbrales. Conservar timestamps originales. Una regla solo produce recomendación si dispone de los campos necesarios; la ausencia de datos produce «no evaluable». Fixtures con casos positivos, negativos y ambiguos. No añadir un framework de reglas.

**Datos persistentes, incorporados por fase:**

- `users`: identidad del proveedor de autenticación de la aplicación.
- `tracked_players`: user_id, PUUID y región; seguir un jugador no acredita propiedad de su cuenta Riot.
- `match_cache`: región + matchId únicos, detalles/timeline, fecha de obtención y vencimiento de retención.
- `analyses`: región + matchId + PUUID + analysis_version únicos, resultado y fecha.
- `habits`: usuario, jugador, regla, ventana y estado. Derivar progreso de análisis guardados; no crear otra tabla hasta necesitarla.
- `review_feedback` y `share_links`: solo en la fase coach; permisos y revocación por propietario.

Los datos de usuario requieren autorización por recurso. Caché de partida y acceso a informes privados son responsabilidades distintas. Configurar una retención inicial propuesta de 30 días para payloads crudos, con borrado y ajuste tras revisar necesidades/políticas; no conservar todo indefinidamente.

**Riot y rendimiento:** almacenar partidas terminadas, TTL corto para listados, propagar límites, registrar latencia por paso y evitar solicitudes duplicadas. Empezar bajo demanda. Añadir un trabajo en segundo plano únicamente si la latencia medida no cabe en el presupuesto HTTP; Redis/Celery no son prerrequisitos. No descargar historiales masivos por anticipado.

**Interfaz:** resumen primero (tres decisiones + hábito), mapa enlazado a cada tarjeta, estadísticas secundarias en detalles. Historial por jugador con fecha, campeón, resultado y cola. Teclado, contraste, texto alternativo y estado de carga/error verificables. Añadir filtros de eventos sin introducir un motor gráfico.

**Seguridad y operación:** sesión real, backend privado o autenticado, claves solo en servidor, límites por usuario/origen, registros sin tokens ni payloads completos, identificador de petición, migraciones reproducibles, copia/restauración de base probada. Las métricas técnicas esenciales son error, latencia, 429, caché y coste por análisis; no hace falta montar una plataforma de observabilidad propia.

**Dependencia Riot:** RSO requiere acceso de producción, por lo que no debe tratarse como OAuth disponible de inmediato. Una cuenta de la app puede usar otro proveedor; verificar propiedad Riot es un flujo separado. La documentación de Riot también exige registro del producto y establece condiciones de integridad y acceso a partidas personalizadas. Mantener el piloto postpartida y excluir custom del alcance inicial. [Documentación oficial](https://developer.riotgames.com/docs/lol).

Antes de publicar, añadir el aviso de no afiliación exigido y verificar el estado del producto en el portal; antes de cobrar, revisar las condiciones de monetización, incluido acceso gratuito y valor añadido. [Políticas generales](https://developer.riotgames.com/policies/general).

## 7. Plan por fases

Estimación de planificación, no cotización: 12–16 semanas para una persona full-stack dedicada, con apoyo de un coach unas 4 horas/semana y producto/diseño unas 4 horas/semana. Incluye integración, pruebas y margen. Aprobaciones externas y reclutamiento pueden extender el calendario; las fases posteriores se activan según resultados.

| Fase | Tiempo orientativo | Trabajo y archivos principales | Dependencia / criterio de salida |
|---|---|---|---|
| 0. Acordar evidencia | Semana 1 | Inventario de modos y datos, 10 entrevistas, 20 partidas autorizadas variadas y 2 revisores; actualizar README y casos de prueba. Iniciar registro Riot. | Definiciones de las primeras 3 reglas, límites conocidos y segmento seleccionado. |
| 1. Base fiable | Semanas 2–3 | Auth y demo, `api/riot/route.ts`, `main.py`, `riot_api.py`, historial y `InteractiveMap.tsx`; compatibilidad de modo, tiempo exacto, errores, assets, límites y contrato. | Prueba de producción de extremo a extremo; sin P1 abiertos aplicables a la beta. |
| 2. Evidencia temporal | Semanas 4–6 | Extender parser con objetivos, estructuras y compras verificadas; funciones de decisiones, tipos y tarjetas enlazadas al mapa. | Conjunto independiente de al menos 50 decisiones y contraejemplos; objetivo provisional ≥80% de recomendaciones consideradas sustentadas por revisores. Publicar denominador y desacuerdos. |
| 3. Continuidad | Semanas 7–9 | Base de datos y migraciones, identidad, análisis versionados, caché, historial por PUUID, un hábito y progreso. | Dos usuarios no acceden a datos privados ajenos; duplicados idempotentes; historial sobrevive reinicio; errores de persistencia controlados. |
| 4. Piloto | Semanas 10–12 | 20–30 jugadores durante al menos 2 semanas; instrumentar embudo, entrevistas, corregir falsos positivos y probar dos alternativas de decisión. | Decidir continuar, acotar o cambiar propuesta con las métricas siguientes. No activar pagos solo por terminar el código. |
| 5. Extensión condicionada | Semanas 13–16 | Si hay retorno: compartir con coaches y revocar enlaces; si hay intención de pago: plan Pro y cobro con webhooks idempotentes. | Uso repetido por coaches o compromiso de pago, operación estable y requisitos externos satisfechos. |

Responsabilidad: full-stack implementa y valida operación; coach define/etiqueta reglas; producto entrevista, mide y decide alcance. Una persona puede asumir varios roles, pero la validación estratégica debe incluir alguien distinto de quien programó las reglas.

Orden de PRs sugerido: (1) demo/auth y producción; (2) modos y contrato; (3) timestamp/mapa/historial; (4) deadline/límites/caché inicial; (5) parser y decisiones; (6) interfaz de evidencia; (7) persistencia y hábitos; (8) piloto y métricas; (9) compartir; (10) pagos solo si se valida. Cada PR incluye un caso reproducible y criterio de aceptación. No es necesario abrirlos todos de antemano.

## 8. Validación y lanzamiento

**Pruebas mínimas relevantes:** mantener las existentes; añadir fronteras temporales, modo incompatible, jugador ausente, estructuras nulas, ausencia de clave, datos demo explícitos, Riot 401/403/429/5xx y deadline. Para persistencia, probar aislamiento e idempotencia. Un recorrido de navegador cubre login→buscar→analizar→tarjeta→hábito→recargar→logout. Probar también teclado, móvil y almacenamiento bloqueado.

Para el motor, separar partidas de ajuste y evaluación. Comparar con las reglas actuales y registrar tanto recomendaciones correctas como oportunidades omitidas. No usar victoria/derrota como etiqueta automática de «buena decisión». Las métricas observadas después no pueden entrar en la explicación de lo que se sabía antes.

**Despliegue:** staging con demo y credenciales separadas; probar desde build de producción; limitar acceso inicial a cohorte; habilitar reglas nuevas por versión o flag simple. Si aumenta el error o el coach detecta recomendaciones injustificadas, volver a la versión anterior y conservar estadísticas básicas. Migraciones aditivas primero; probar restauración antes de borrar campos.

**Objetivos propuestos del piloto, no benchmarks de mercado:**

| Métrica | Definición | Umbral inicial para decidir |
|---|---|---|
| Activación | Usuarios nuevos que abren una evidencia entre quienes completan onboarding | ≥60% |
| Retorno de valor | Usuarios activados que revisan una segunda partida en 7 días | ≥35% |
| Adopción de hábito | Usuarios que eligen foco y revisan al menos 3 partidas posteriores elegibles | ≥25% de activados |
| Calidad | Recomendaciones sustentadas según revisión humana independiente | ≥80%, con muestra y discrepancias visibles |
| Fiabilidad | Solicitudes elegibles completadas, distinguiendo errores propios y externos | ≥98% en piloto; medir fallos por causa |
| Latencia | P95 con y sin caché | Objetivos iniciales <2 s con caché y <10 s sin caché; validar antes de prometerlos |

Con 20–30 personas estas cifras son señales direccionales, no resultados estadísticos concluyentes. Si la calidad falla, reducir reglas. Si la calidad pasa pero el retorno falla, revisar utilidad y experiencia antes de añadir IA o gamificación.

## 9. Negocio, coste y decisiones pendientes

Modelo a validar: acceso gratuito con análisis acotados; Pro por continuidad, historial ampliado y herramientas de revisión. Coaches como canal inicial de distribución y posible segundo segmento. No fijar precios por intuición: presentar el prototipo a cinco potenciales compradores, contrastar intención con compromiso y medir coste real del servicio.

Presupuesto de infraestructura aún pendiente de proveedor y tráfico. Estimar con: coste fijo de Next + API + base + backups + autenticación, más almacenamiento/transferencia y servicios por uso. Medir coste por usuario activado y por análisis no cacheado. Los límites Riot son una restricción de capacidad que debe probarse, no resolverse suponiendo más gasto. Un LLM opcional añade coste y latencia: incorporarlo solo si una comparación ciega demuestra mejor comprensión que las plantillas.

No implementar ahora: overlay en vivo, app móvil nativa, simulación exacta de visión, predicción de MMR, entrenamiento de modelos propios, vector database, microservicios, marketplace de coaches, multirregión completa o un editor colaborativo en tiempo real. Cada uno requiere demanda o evidencia técnica que hoy no existe en el repositorio.

Decisiones que el piloto debe cerrar: rol inicial, datos realmente suficientes, aprobación Riot, hosting, presupuesto, política de retención y disposición a pagar. El primer incremento útil es una demo completa y honesta más una sola decisión temporal bien sustentada; ampliar a tres después de validarla.
