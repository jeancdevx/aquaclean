# Estado real y ajustes del plan 1.2

## Contraste con lo indicado en clase

La versión 1.0 cumplía la preparación de los procesos y el diseño modular. No especificaba Docker ni el chat multimodal como entregables mínimos y dejaba la búsqueda vectorial para después. Por ello, no cubría completamente la nueva indicación.

La versión 1.1 corrigió esas omisiones. La versión 1.2 completa el frontend: chat sin login en demo local, Astro + React + shadcn/ui, sugerencias, actividad real, explicación resumida, paleta y tipografía. **Cubre los requisitos como planificación; todavía no los acredita como software implementado.**

| Requisito | Diseño actual | Implementación real actual |
|---|---|---|
| Procesos TO BE | Diagramas detallados e integral disponibles | XML y vistas generados y comprobados |
| Arquitectura multiagente | Supervisor + atención, logística, calidad e incidencias | Agentes del producto pendientes |
| Arquitectura de software | Módulos, puertos, contratos, persistencia y pruebas | Backend y frontend pendientes |
| Chat local | UI, componentes, demo sin login y rutas especificadas | No hay servidor local ejecutable todavía |
| Chat multimodal | Texto, imágenes, PDF y audio desde V1 | Procesamiento de esos medios pendiente |
| IA Gemini configurable | Adaptadores y variables de entorno definidos | Llamadas y credenciales pendientes |
| Docker | Servicios, orden de arranque, volúmenes y salud definidos | Dockerfile/Compose del producto pendientes |
| Base vectorial | PostgreSQL + pgvector obligatorio y RAG definido | DB, embeddings e ingesta pendientes |
| Primera versión local | Condiciones de aceptación y demo definidas | Pendiente de construir y demostrar |

## Qué representa cada parte del diseño

Los BPMN indican cómo se desarrolla el negocio: quién actúa, qué decisión toma, cuándo debe esperar, qué excepciones existen y qué resultado permite continuar. Los cuatro TO BE detallan los casos de interpretación; el integral conecta esos casos con las tareas físicas de la lavandería.

La arquitectura multiagente distribuye el razonamiento. El supervisor identifica el dominio y coordina; atención aclara solicitudes; logística negocia opciones calculadas; calidad contrasta observaciones; incidencias organiza evidencias y propuestas de solución. El LLM propone y explica; código y personas autorizadas deciden qué se puede ejecutar.

La arquitectura modular separa la UI/API, los casos de uso, las reglas, los agentes, los grafos y las integraciones. LangChain construye los especialistas y LangGraph controla el estado, la delegación y las pausas. Los escritores deterministas aplican comandos idempotentes y resultados comprobables.

PostgreSQL conserva pedidos, agenda, mensajes y expedientes. pgvector busca fragmentos de conocimiento por similitud. Los checkpoints guardan el punto de ejecución de un caso. Los archivos originales quedan en un volumen. Estas funciones son distintas aunque varias utilicen la misma base de datos.

El chat multimodal añade una capa de percepción: recibe texto, analiza fotos/PDF y obtiene una transcripción o interpretación del audio. El resultado se entrega al proceso correspondiente con referencia a su fuente. Adjuntar una foto no elimina la revisión física y humana necesaria para calidad.

Docker hace reproducible el entorno local. La API y el worker ejecutan el producto, PostgreSQL + pgvector conserva los datos, y las migraciones preparan el esquema antes de servir. Gemini continúa siendo un proveedor externo cuando se usa por API.

El frontend del plan 1.2 se construirá con Astro, una isla React interactiva y shadcn/ui. Su diseño visual y contrato de eventos están definidos en `FRONTEND_Y_SISTEMA_VISUAL.md`, pero los componentes todavía no se han instalado ni se ha ejecutado una interfaz.

## Qué se ha implementado en esta entrega

Se implementó el **código de soporte de los diagramas**, en particular el validador BPMN y los informes de importación/estructura. Se generaron los XML, SVG/PNG y las especificaciones/documentación. Se revisaron los exports n8n previos del equipo.

No se implementó todavía el código de la aplicación: ni agentes ejecutables LangChain, ni grafo operativo, ni chat, ni Docker ni base vectorial en funcionamiento. La estructura de carpetas del plan es una propuesta, no un listado de módulos ya desarrollados.

## Cómo pasar del diseño a la V1

Colocar el paquete en `docs/diseno` de un repositorio, poner el `AGENTS.md` propuesto en su raíz y entregar a Codex el prompt completo. Codex debe construir primero infraestructura/contratos y un corte funcional P1, después multimodalidad/HITL y finalmente P2–P4. La guía enumera los comandos que debe dejar implementados y las pruebas/demostraciones que acreditan la V1.

El cierre exige abrir y usar el chat desde localhost, procesar medios reales con el proveedor configurado, mostrar consultas vectoriales y conservar el estado al reiniciar. Esos resultados deberán registrarse cuando se ejecute la aplicación.
