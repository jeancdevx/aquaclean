# Fuentes, alcance y decisiones de diseño

## Archivos del equipo revisados

| Fuente | Evidencia utilizada | Límite |
|---|---|---|
| `proceso-lavanderia-as-is.bpmn` y su SVG | Proceso corporativo, cinco responsabilidades, recojo, planta, calidad, entrega e incidencias | Modelo recibido; no se vuelve a observar en campo |
| `proceso-recojo-to-be.bpmn` y su SVG | Contrato, padrón, duplicados, turno normal, errores y derivación administrativa | RPA determinista; no demuestra interpretación contextual de los demás dominios |
| `n8n-flujo-principal-registrar-recojo.json` | Webhook, validación, Google Sheets y notificación | Export revisado; no se ejecutó ni se usaron credenciales |
| `n8n-subflujo-registrar-recojo.json` | Herramienta determinista y contrato de resultado | Requiere adaptador y pruebas de compatibilidad |
| `n8n-flujo-multiagente-recojo.json` | Coordinador conversacional, registrador, memoria y parser estructurado | El registrador envuelve una acción por reglas; se propone convertirlo en servicio |
| `n8n-flujo-cola-fallidos.json` | Cola y consulta de errores | Se conserva el requisito de trazabilidad de fallos |
| `multiagente.png`, `subagente.png`, `subflujo.png`, `proceso-recojo-to-be-n8n.png` | Vista visual de los flujos y evidencia documental del prototipo previo | Las capturas no certifican las integraciones actuales |
| `Instrumentos_Laboratorio_01.xlsx` | Selección al detalle, muestra de 18 órdenes, línea base, entrevista y roles | Su alcance excluye el servicio institucional; sus métricas no se trasladan al corporativo |
| `Instrumentos_Laboratorio_02.xlsx` | Trazabilidad del RPA, siete obligatorios, idempotencia y catálogo de errores | Pruebas registradas por el equipo; no fueron repetidas aquí |
| `Sesión 06 Arquitectura de Multiagentes y su Implementación.pdf`, pp. 2–6 | Componentes de agente, catálogo TO BE, supervisor, especialistas y política/HITL | Arquitectura de un ejemplo académico distinto |
| Mismo PDF, pp. 9 y 11–12 | Modelo entrenado del ejemplo y práctica de implementación en video | Ni entrenamiento ni sus resultados se atribuyen a Aqua Clean |

No se reproducen los datos de contacto de la organización ni del equipo en esta entrega: no hacen falta para revisar la arquitectura.

## Video compartido en Drive

[Enlace recibido](https://drive.google.com/file/d/1AyXU96G-PVu9fMWxkg9b84XeYIMNyeHJ/view?usp=sharing).

**Archivo descargado y revisado visualmente.** Nombre: `InShot_20261012_192235988.mp4`. Duración comprobada: 11 min 46 s. Se inspeccionaron 24 fotogramas muestreados a intervalos de 30 s y se ampliaron pantallas relevantes. No se realizó una transcripción de su audio; las observaciones siguientes se limitan al contenido visible.

Se observa un catálogo BPMN, arquitectura de supervisor/especialistas, separación entre decisión y política, instrucciones de repositorio, trabajo en Antigravity con Claude Code, organización del código, comandos de pruebas y una interfaz local con indicadores y fuentes. Una pantalla exige leer el BPMN antes de escribir el agente, salidas tipadas, aislamiento de datos, autorización independiente de probabilidad y aritmética en código. Estas prácticas se adaptan a VS Code + Codex mediante el plan modular y el `AGENTS.md` propuesto. El número de agentes y los resultados del ejemplo no se trasladan a la lavandería.

No se incluyen capturas del video en la entrega. Sus pantallas sirven como referencia de la metodología, no como evidencia de funcionamiento de Aqua Clean.

## Documentación oficial consultada el 14/10/2026

| Documento | Aplicación en el diseño |
|---|---|
| [LangChain: agents](https://docs.langchain.com/oss/python/langchain/agents) | Construcción de especialistas mediante modelos, herramientas e instrucciones |
| [LangChain: structured output](https://docs.langchain.com/oss/python/langchain/structured-output) | Contratos validados y salida estructurada |
| [LangChain: multi-agent](https://docs.langchain.com/oss/python/langchain/multi-agent) | Separación de dominios y necesidad de contrastar el beneficio frente a un agente único |
| [LangGraph: subgraphs](https://docs.langchain.com/oss/python/langgraph/use-subgraphs) | Procesos especializados como subgrafos |
| [LangGraph: persistence](https://docs.langchain.com/oss/python/langgraph/persistence) | Diferencia entre checkpoint por caso y memoria transversal |
| [LangGraph: interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts) | Pausa/reanudación, mismo thread y reejecución del nodo |
| [OMG: BPMN 2.0.2](https://www.omg.org/spec/BPMN/2.0.2) | Elementos estándar y formatos XML/DI de intercambio |
| [Gemini: imágenes](https://ai.google.dev/gemini-api/docs/image-understanding), [documentos](https://ai.google.dev/gemini-api/docs/document-processing) y [audio](https://ai.google.dev/gemini-api/docs/audio) | Capacidades de entrada a comprobar para el chat multimodal V1 |
| [LangChain: ChatGoogleGenerativeAI](https://docs.langchain.com/oss/python/integrations/chat/google_generative_ai) | Adaptador Gemini y bloques multimodales compatibles con la versión instalada |
| [Gemini: embeddings](https://ai.google.dev/gemini-api/docs/embeddings) | Dimensión configurable y espacio vectorial del corpus |
| [pgvector](https://github.com/pgvector/pgvector) | Recuperación vectorial en PostgreSQL e imagen Docker del proyecto |
| [Docker Compose: arranque](https://docs.docker.com/compose/how-tos/startup-order/) y [volúmenes](https://docs.docker.com/engine/storage/volumes/) | Dependencias saludables, migraciones y persistencia local |
| [OpenAI: AGENTS.md](https://developers.openai.com/codex/guides/agents-md) e [IDE Codex](https://developers.openai.com/codex/ide/features) | Instrucciones y contexto del repositorio en VS Code |

Estas fuentes describen capacidades técnicas. La elección de cuatro especialistas, módulos, límites del piloto y políticas concretas es una decisión propuesta para la lavandería, no una prescripción de la documentación.

## Estado de la entrega

- Modelos BPMN y descripciones: entregados para revisión y apertura en bpmn.io.
- Arquitectura de software y contratos: propuestos, con fases y aceptación.
- Aplicación LangGraph, integraciones operativas y calibración: pendientes de implementación y evaluación.
- Línea base corporativa, políticas de calidad y evidencia de reclamos: pendientes de ratificación/captura.
- Excel y exports originales de n8n: conservados sin modificación.

La versión 1.1 incorpora la indicación adicional del usuario: chat multimodal local, Docker, IA configurable y base vectorial desde la primera versión. La precisión de formatos, contenedores y aceptación se fija en el plan; la aplicación sigue pendiente de implementación.

La versión 1.2 define acceso demo sin login, interfaz centrada en chat, explicación pública resumida y actividad de herramientas. Se consultaron [shadcn/ui con Astro](https://ui.shadcn.com/docs/installation/astro), [hidratación de componentes Astro](https://docs.astro.build/en/guides/framework-components/) y [AI Elements](https://elements.ai-sdk.dev/docs). La paleta, tipografía y composición son decisiones de diseño propuestas; la UI del producto no está implementada.
