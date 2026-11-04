# LangSmith requerido para semana 10

El requisito vigente exige **trazas reales de LangSmith utilizando su plan gratuito**. Los logs locales son auxiliares; la interpretación anterior que los proponía como sustituto queda corregida. Instalar la dependencia o ejecutar pruebas controladas no acredita envío, consulta ni captura de trazas externas.

La [página oficial de precios](https://www.langchain.com/pricing), consultada el 2026-11-04, ofrece Developer con una plaza gratuita y hasta 5.000 trazas base mensuales. No se contrató ningún plan, ampliación de retención o despliegue. El plan efectivo y el consumo disponible de esta cuenta no se han podido verificar. Inferencia Gemini y monitoreo LangSmith son servicios distintos; exportar trazas existentes no invoca al modelo.

## Estado comprobado

En entorno/.env y backend falta LANGSMITH_API_KEY; trazado desactivado, proyecto/agente/workspace sin configurar. El endpoint por defecto apunta a US, lo que no verifica la región de la cuenta. No hay conexión CDP autorizada ni configuración local del CLI LangSmith. Existe Chrome abierto, pero sin puerto de automatización disponible; no se cerró ni copió su perfil. No se accedió a cookies ni se capturó login.

La tabla local app.trace_links tiene cero filas. **No permite concluir que no existan ejecuciones en LangSmith.** La consulta remota no pudo realizarse por falta de acceso. No se efectuaron nuevas llamadas Gemini para compensarlo. La evidencia requerida continúa pendiente.

## Configuración y compatibilidad

`langsmith==0.14.11` está fijado en pyproject.toml/uv.lock. `infrastructure/observability/tracing.configure` se usa en backend/worker, valida proyecto O agente y limpia destinos/workspace anteriores. Solo `infrastructure/llm/provider.py` construye el modelo. No se cambia el plan de la cuenta ni se añaden tarjetas de pago.

La [documentación oficial de trazado](https://docs.langchain.com/langsmith/trace-with-langchain) exige endpoint de la región correcta y workspace cuando una clave abarca varios. Un workspace basado en agentes usa agente/entorno; uno clásico puede usar proyecto. No se deduce el tipo a partir de una dependencia instalada. El SDK resuelve el agente al tracer session y verifica el tenant/workspace del destino mediante API.

```dotenv
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=COMPLETAR_SOLO_LOCALMENTE
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
# EU: https://eu.api.smith.langchain.com
# APAC: https://apac.api.smith.langchain.com
LANGSMITH_WORKSPACE_ID=IDENTIFICADOR_AUTORIZADO
# Destino clásico:
LANGSMITH_PROJECT=aquaclean-semana10
LANGSMITH_AGENT_ID=
# O destino agente ya existente: vaciar PROJECT y usar ID/entorno reales.
# LANGSMITH_PROJECT=
# LANGSMITH_AGENT_ID=identificador-existente
LANGSMITH_AGENT_ENVIRONMENT=local
```

Las claves permanecen exclusivamente en el entorno local; nunca en chat, frontend, logs, capturas, Git, ZIP, HAR o storageState. La configuración de credenciales y la sesión autorizada no se pueden obtener creando valores ficticios. El acceso a una cuenta requiere autorización efectiva o login humano; no se simula.

## Buscar y reutilizar primero

```bash
uv run python scripts/verify_langsmith.py --output "$(cat artifacts/semana10/CURRENT)/05-langsmith/verificacion.json"
uv run python scripts/export_langsmith_traces.py
```

Son operaciones de lectura, sin inferencia. `scripts/langsmith_evidence.py` consulta `client.runs.query` y `client.traces.list_runs`, disponibles en el SDK instalado y recomendados en [consulta oficial de trazas](https://docs.langchain.com/langsmith/export-traces). Busca raíces AquaClean.application_run de los últimos 14 días, hasta 20 por invocación; acepta `--days`/`--limit`. Exporta solo trazas marcadas sintéticas. Si no hay destino explícito, puede resolver un único proyecto visible cuyo nombre contiene aquaclean; ante ambigüedad no elige otro cliente/proyecto ni crea destinos.

La consulta es independiente de app.trace_links: puede encontrar trazas existentes aunque falte la correlación local. Si hay resultados, se reutilizan y no se llama de nuevo al modelo. Si una ejecución existente carece de Deep Agents/HITL, se señala esa cobertura faltante sin presentarla como recorrido completo. Si la consulta falla, se distingue de una búsqueda satisfactoria sin resultados. La exportación conserva IDs, URL, nombre/tipo, relaciones padre, metadatos permitidos, tiempos, tokens/coste cuando el servicio los devuelve. No exporta prompts, entradas/salidas completas, cabeceras ni cuerpos de error.

## Recorrido mínimo preparado cuando no haya ejecuciones

```bash
# Solo prepara el recorrido: cero inferencias y cero escrituras de negocio.
node web/scripts/run-langsmith-minimal.mjs
# Después de acceso verificado y backend/worker con trazado real habilitado:
uv run python scripts/write_build_revision.py
docker compose up --build -d api worker
node web/scripts/run-langsmith-minimal.mjs --execute
uv run python scripts/export_langsmith_traces.py
```

El ejecutor consulta LangSmith primero. Reutiliza resultados existentes; solo una consulta satisfactoria sin trazas permite el nuevo recorrido. Comprueba trazado activo en API/worker y reutiliza la orden sintética del recorrido anterior, sin repetir recepción ni ingesta. Abre un P4 separado mediante API para una consulta posterior al servicio, adjunta el PNG sintético existente y solicita percepción real, RAG, planificación write_todos y delegación task a Evidencias/Procedimientos. Propone resolve_incident, comprueba pausa sin plan aplicado y aprueba mediante API. Command(resume) continúa el mismo hilo con otro app_run_id. El plan permanece abierto hasta posterior cumplimiento humano; no simula cierre, transporte, cobro ni conformidad.

Los IDs de solicitud/comando se guardan para reintentos; no hay retry automático de inferencia ante fallo. Presupuesto de aplicación/Deep Agents limita llamadas. La ejecución preparada no se presenta como ejecutada. El recorrido completo P1/P4 previo sigue en 07-aplicacion con sus fechas, sin convertirlo retrospectivamente en LangSmith.

## Instrumentación y correlación

Raíz AquaClean.application_run → LangGraph/nodos → cadenas LCEL/modelo/herramientas, recuperación pgvector y P4.DeepAgents.investigation con sus subagentes. Percepción/embeddings SDK directo y ejecutor tienen instrumentación explícita. La cobertura y métricas efectivas solo se acreditan tras leer el árbol remoto.

Metadatos: commit, source_sha256, prompt_version, process, app_run_id, case_id y thread_id. approval_id y application_status distinguen pausa, fallo y reanudación de la finalización técnica del span. `app.trace_links` guarda IDs reales del RunTree, nunca UUID de la aplicación reutilizados como trace IDs. La espera humana no mantiene abierta una traza: solicitud y reanudación corresponden a raíces distintas correlacionadas por hilo/revisión. Duración/tokens/coste ausentes quedan desconocidos; no se deduce un coste de una clave API.

## Capturar la interfaz real

```bash
# Conexión a navegador ya autenticado y autorizado; mantener solo en entorno/.env local.
# LANGSMITH_CDP_URL=http://127.0.0.1:PUERTO_AUTORIZADO
node web/scripts/capture-langsmith.mjs
uv run python scripts/package_langsmith_evidence.py
```

Playwright abre únicamente URLs verificadas por el SDK en dominios oficiales: listado, árbol expandido, modelo, herramienta, Deep Agents y ambas trazas del HITL. Verifica nombres esperados y registra controles/cobertura ausentes. Sin sesión o trazas genera capturas.json con bloqueo y cero imágenes; no captura pantallas de login ni genera una imitación. No guarda cookies, estado, HAR ni claves. La UI puede cambiar: controles no identificados quedan pendientes, nunca se afirman capturados.

`evidencias-langsmith-semana10.zip` contiene exportaciones, descripción del recorrido, fuentes de los scripts, pruebas controladas y las capturas reales que existan. El manifest distingue listo/pendiente y registra hashes. Si está bloqueado, el ZIP preparatorio no acredita el requisito.
