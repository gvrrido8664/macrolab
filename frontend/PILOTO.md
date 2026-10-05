# Protocolo del piloto

No hay resultados de usuarios ni validaciones de coaches inventados en esta entrega.

## Preparación

Responsables: una persona de producto para entrevistas, una de desarrollo para operación y dos revisores de macrojuego que no hayan ajustado las reglas. Reclutar 10 entrevistados y después 20–30 jugadores LAS Solo/Dúo, empezando por soporte como hipótesis. Solicitar participación y tratamiento de datos de forma clara antes de recopilar material.

Entrevista inicial: qué revisan después de perder; ejemplo reciente de una decisión dudosa; herramientas que ya usan; qué les resulta poco útil; si volverían a revisar otra partida con esta propuesta. Mostrar la demo y observar dónde se atascan. No afirmar que subirán de rango.

## Evaluación de reglas

Reunir al menos 20 partidas autorizadas variadas. Separar partidas de ajuste y de evaluación. Los dos coaches revisan de forma independiente al menos 50 decisiones/casos negativos. Registrar en una hoja: partida anonimizada, versión, regla, tiempo, evidencia, juicio del revisor, contexto faltante y explicación. No usar la victoria como etiqueta automática de buena decisión.

Etiquetas: sustentada; parcialmente sustentada; incorrecta; no evaluable. Incluir casos sin recomendación para detectar omisiones. Resolver desacuerdos después de registrar ambos juicios. Meta provisional: ≥80% sustentadas, mostrando denominador y desacuerdos. Si falla, desactivar o acotar la regla, incrementar versión y repetir con partidas nuevas.

## Dos semanas de uso

Medir cuántos jugadores abren una evidencia, revisan una segunda partida durante los siguientes siete días y completan al menos tres partidas nuevas con hábito. Contadores técnicos: `python manage.py metrics` desde el backend. El comando distingue el retorno a otra partida dentro de siete días y excluye cohortes sin siete días de observación. Su ventana de observación son los últimos 30 días retenidos. No equivale a retención desde registro ni demuestra mejora causal. `python manage.py evaluation casos.csv` crea una hoja local con etiquetas de revisores vacías; añadir casos negativos manualmente.

Umbrales iniciales de decisión: activación 60%, segunda revisión 35%, adopción de hábito 25%, peticiones elegibles completadas 98%. Estos valores son hipótesis del plan, no benchmarks ni garantías. Con esta muestra, interpretar señales cualitativas y cuantitativas en conjunto.

Registrar falsos positivos, recomendaciones peligrosamente tajantes, tiempos, 429, fallos de guardado y dudas de privacidad. Un aumento de errores o consejos injustificados justifica volver a la versión anterior antes de ampliar funcionalidades.

## Decisión comercial

Probar revisión compartida con tres coaches y conversar con cinco posibles compradores. Activar un trabajo de monetización solamente con uso repetido, precio elegido, requisitos externos satisfechos y validación de intención de pago. Cobros futuros requieren idempotencia de webhooks, pruebas sandbox, gestión de cancelación y autorización por nivel de acceso. No hay pagos activos en esta versión.
