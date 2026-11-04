# Estado actual semana 10 · 2026-11-04, America/Lima

Trabajo local en fix/semana10-alineacion-detalle; V2 vigente. Recepción/ciclo, LCEL, LangGraph/HITL e investigación Deep Agents tienen evidencia previa: 83 pruebas deterministas, 10 evaluaciones Gemini y recorrido real DET-E53D7546AB CLOSED, con fechas conservadas. La corrección vigente del usuario exige trazas reales de LangSmith en plan gratuito; los logs locales no las sustituyen. Se revisó la instrumentación, se preparó consulta directa de trazas existentes y recorrido mínimo con captura real. No hay LANGSMITH_API_KEY, destino/workspace configurado ni sesión CDP autorizada en este entorno: la búsqueda remota no pudo realizarse, no se afirma que no existan trazas y el requisito permanece pendiente. Ver docs/LANGSMITH.md y el manifest actual. No se declara completada la semana 10.

---

Los apartados siguientes son el registro histórico V1, con su fecha original. No se convierten en pruebas nuevas de V2.

# Estado de implementación V1

**Estado actual: V1 local implementada y validada.** Ver el cierre final al pie y `docs/validacion/PRODUCTO_V1.md`. Los cortes anteriores conservan el registro cronológico de problemas ya resueltos.

Solicitud: implementación local de los procesos P1–P4 sobre el diseño 1.2.
Los originales se conservan en `docs/`; no estaban en `docs/diseno/`.

## Corte A — infraestructura y dominio (en curso)

Repositorio inicial: solo diseños, sin código ni AGENTS en raíz. Se conserva la documentación y se copia la propuesta de instrucciones a raíz. Docker Engine y Compose disponibles; Python 3.12 y uv disponibles. No se detectó `GEMINI_API_KEY` en el entorno.

Implementado: configuración, actor demo fijo, reloj Lima inyectable, validación de siete campos, reglas de evidencia y migración relacional/vectorial/checkpoints separados.

Comprobaciones: lectura de planes, contratos y nodos BPMN 01–06; consulta de documentación oficial iniciada. Todavía no se han ejecutado tests del producto.

Siguiente: repositorios transaccionales, Compose, seed, archivos y RAG.

## Cortes A/B — implementados; validación parcial

PostgreSQL 17 con pgvector 0.8.2 arrancó mediante Compose (sin puerto de DB publicado). Migración y seed-demo ejecutados contra DB real. Checkpoints en esquema separado. Ledger y outbox transaccionales, control de versión y capacidad, filtros por organización/cliente/rol/vigencia, ingesta idempotente y aislamiento por colección/modelo/dimensión. Originals de medios validados por contenido, límites, hash y volumen; percepción real vía Gemini, observaciones editables.

Bloqueo verificable: falta GEMINI_API_KEY; no se han ingerido embeddings Gemini ni probado percepción real. Los vectores fake son exclusivos de la base `_test` y se identifican con modelo `fake-test-only-sha256`.

## Cortes C/D/E — implementados; pruebas en curso

Supervisor y cuatro subgrafos LangGraph, propuestas tipadas LangChain, herramientas reales de lectura/cálculo y ejecutor determinista. Pausa HITL y reanudación en thread estable. P1 normal/excepción comercial con reconfirmación; P2 selección/reserva/cancelación; P3 disposición supervisada y tareas humanas; P4 plan autorizado, aceptación/cumplimiento/conformidad y cierre protegido. Worker de jobs persistentes, leases, outbox local y vencimientos.

Frontend Astro/React/TS/Tailwind/shadcn generado: isla única, historial, sugerencias editables, compositor, medios, aprobación, inspector, temas y fuentes locales. `pnpm check` sin errores y `pnpm build` correcto. Ruff y mypy del dominio/contratos correctos antes de la última ampliación de tests; se repetirán al finalizar.

Nueva indicación del usuario: reforzar mensajes de sistema y seguridad. Se implementan contratos que rechazan campos extra, allowlist de acciones por proceso, permisos server-side y pruebas de inyección/aislamiento. No se atribuye garantía absoluta a prompts.

Siguiente: corregir cualquier fallo de integración, completar pruebas de medios/RAG/API/navegador, documentar resultados y comprobar reinicio de contenedores.

## Corte F — evidencia disponible y cierre en curso

El usuario configuró GEMINI_API_KEY localmente. Se consultó models.list en la cuenta: Gemini 3.8 estaba disponible, pero en evaluación hubo 429/504 y latencias; se eligió `gemini-3.5-flash-lite`, probado en 10 evaluaciones reales (texto/contrato, streaming, PNG/JPG/WebP/PDF/MP3/WAV, embeddings 768 e inyección). La clave se preservó sin imprimirla; `.env` tiene permisos 0600 y exclusión de imagen/repositorio.

14 fragmentos con embeddings Gemini reales ingeridos; consulta vectorial real relevante comprobada. Se pobló el histórico con 3.000 pedidos, 150 clientes adicionales y 12.750 eventos sintéticos. Se descargaron/importaron 151 registros públicos CPSC, 1974-02-15–2026-09-17, en esquema separado y con snapshot/hash. La aclaración del usuario autorizó datos de apariencia real; permanecen identificados como sintéticos, nunca como historia operativa auténtica de Aqua Clean.

52 pruebas deterministas pasaron en PostgreSQL `_test`; 10 evaluaciones reales separadas pasaron; 5 pruebas de navegador de UI/medios/fuentes y un P1 real con aprobación/recarga pasaron. pnpm check/build, Ruff y mypy correctos. Compose compila con pnpm; DB/API/worker saludables y migración temporal correcta. Seed e importación/ingesta repetidos no duplicaron datos.

La demo real completa detectó ambigüedad del contrato: el modelo pedía confirmación con `clarify` aun teniendo todos los campos/opciones. Se reforzaron mensajes y política determinista de preparación de tarjetas; se eliminó la segunda redacción LLM de respuestas ya validadas. Se añadieron control de evidencia cambiada durante análisis, versión de pedido compartida y fingerprint de política. Queda ejecutar otra vez el recorrido completo P1–P4 con reinicio, confirmar las últimas regresiones y cerrar los informes/manual PDF. No se declara todavía terminado el recorrido real completo.

## Cierre final — 16/10/2026, America/Lima

Se completó y repitió el recorrido HTTP + Gemini real P1–P4 con reinicio mientras había una revisión pendiente. El pedido final `DEMO-28CA13D45D` pasó por registro confirmado, reserva calculada/atómica, liberación humana y plan de incidencia que permaneció abierto hasta aceptación/cumplimiento/conformidad posteriores y aprobación del cierre. El mismo adjunto y revisión sobrevivieron al reinicio; la evidencia está en `docs/validacion/full-demo-real.json`.

La revisión final corrigió una ventana entre resolver una aprobación y encolar su reanudación. Decisión, job y evento ahora se confirman en la misma transacción; un caso ocupado conserva la revisión pendiente. La prueba fuerza esa condición y verifica reintento idempotente. También se comprobaron herramientas con permisos propios, reinicio de contadores por proceso, citas obligatorias en P3/P4 y cronología/estado coherentes de los registros históricos sintéticos.

Resultado final: **59 pruebas deterministas pasadas** con PostgreSQL separado `_test`; las 10 evaluaciones reales omitidas en esa batería se ejecutaron aparte y **pasaron las 10**. **8 pruebas Chromium pasadas**, incluido P1 con Gemini, aprobación y recarga. Ruff check/format, mypy acotado y pnpm check/build pasaron. Compose compilado y saludable, migración versión 4; los subcomandos seed/import/ingest repetidos no duplicaron registros. RAG: 14 vectores reales de 768 dimensiones y consulta real relevante. Auditoría sin coincidencias de la clave en archivos/DB examinados, sin exceso de capacidad ni eventos históricos fuera de la cronología.

Entregados README, `.env.example`, OpenAPI, arquitectura implementada, matriz BPMN–código, documento de seguridad, fuentes y resultados con XML/JSON/capturas. La guía detallada incluye 25 pruebas con prompts, casos de uso, pasos, resultados y tres hechos históricos verificables; disponible en Markdown, HTML y PDF de 15 páginas. Los 3.000 pedidos y 12.750 eventos son sintéticos identificados; los 151 avisos CPSC son referencias públicas reales separadas, nunca historia interna de Aqua Clean.

La clave que agregó el usuario ya está configurada, preservada y verificada sin imprimirla. No quedan bloqueos para ejecutar el perfil local. Autenticación empresarial, políticas ratificadas, correo/pagos/operaciones físicas e importación de historia interna autorizada quedan fuera del perfil demo, tal como documentan README e informe. No se declara seguridad absoluta ni una validación de producción.


## Corrección posterior — inicio desde «Programar un recojo»

El usuario reportó un fallo real: enviar el texto sugerido con CLI-0001 derivaba a P2 y exigía un pedido previo. Se reprodujo el mensaje exacto con Gemini. La cobertura anterior pulsaba la sugerencia sin enviarla y probaba P1 con los campos completos, por lo que no detectaba ese recorrido.

Se corrigieron el prompt del supervisor/Atención y la precondición del grafo: sin pedido vinculado, una ruta P2 se deriva a P1 para recoger datos o indicar la vinculación de uno existente. Se valida el permiso de Atención; no se otorga un rol ni se relajan las condiciones de reserva. Los eventos conservan ruta propuesta y efectiva. Prompts versión `aquaclean-boundaries-1.1`.

Se amplió Playwright para enviar la sugerencia exacta, seleccionar CLI-0001, comprobar aclaración/sin efectos, recargar, completar, confirmar y verificar un pedido persistido. Dos regresiones fuerzan clasificación P1/P2 y otra verifica que un actor de logística no gana Atención. Se verificó por HTTP real que el caso QA originalmente fallido puede continuar y que una entrega existente sin vínculo solicita vinculación, sin crear un pedido sustituto. La prueba de outbox ahora drena pendientes acumulados solo en `_test` y verifica que su propio aviso sufrió el intento fallido.

Documentación actualizada: guía T01 y PDF de 16 páginas, descripción de P1, arquitectura/matriz, seguridad e informe de resultados. Ver `docs/validacion/CORRECCION_RECOJO.md` y evidencias asociadas. Los resultados finales y la versión de imagen comprobada están en `docs/validacion/PRODUCTO_V1.md`; se conservan los cortes anteriores como registro de la entrega inicial.

## Aclaración documental — prueba T02

La respuesta reportada por el usuario, que pregunta cuántas bolsas son, coincide con el resultado esperado de la solicitud incompleta. «Son 3 bolsas…» es el segundo mensaje que debe enviar quien prueba; no es un dato que deba inventar el agente. Se separaron explícitamente los cuatro pasos de T02 en mensajes del operador y respuestas esperadas del sistema, con una indicación para sustituir `FECHA_MAÑANA`. Se añadió una leyenda general y se regeneraron HTML/PDF. No se modificaron código, datos ni contratos de negocio para esta aclaración.
