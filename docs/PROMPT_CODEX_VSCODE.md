> Antecedente V1. Para el alcance vigente al detalle consultar README.md, docs/PLAN_ARQUITECTURA.md, docs/contratos/DETALLE_V2.md y docs/arquitectura/IMPLEMENTADA.md. Se conserva el texto histórico.

# Prompt completo para Codex en VS Code

Copia el texto siguiente en Codex. Antes, coloca los documentos en `docs/diseno/` y el `AGENTS.md` propuesto en la raíz del repositorio, como indica la guía.

---

Implementa la primera versión local funcional del sistema multiagente de la lavandería Aqua Clean S.A.C. No te detengas en un nuevo plan ni en archivos vacíos: construye, ejecuta las comprobaciones disponibles y deja una aplicación dockerizada reproducible. Conserva cualquier trabajo existente y avanza por etapas hasta cumplir el alcance.

Lee primero:

- `AGENTS.md` de la raíz.
- `docs/diseno/PLAN_ARQUITECTURA.md`, versión 1.2, especialmente secciones 9 y 10.
- `docs/diseno/DESCRIPCIONES_PROCESOS.md` y las descripciones por proceso.
- `docs/diseno/bpmn/01-to-be-integral.bpmn`, `02`–`05` y `06-orquestacion-multiagente.bpmn`.
- `docs/diseno/IMPLEMENTACION_V1_LOCAL.md`, `FRONTEND_Y_SISTEMA_VISUAL.md` y `arquitectura/despliegue-local.md`.

Inspecciona el repositorio y el entorno, identifica lo que ya existe y resume las decisiones de implementación. Luego ejecuta el trabajo sin pedir confirmación para cambios reversibles propios de esta implementación. Si falta una credencial o Docker, completa lo independiente, documenta el bloqueo y no inventes resultados.

## Producto obligatorio

Aplicación en `http://localhost:8000`, interfaz de chat multimodal con texto, imágenes JPG/PNG/WebP, PDF y audio MP3/WAV o formatos normalizados compatibles. Historial persistente, conversaciones, previsualización de adjuntos, respuestas en streaming, fuentes y estado de caso. Abre directamente el chat sin login en `AUTH_MODE=demo_local`, con actor `demo_operator` y organización sintética fijados en backend. No otorgues permisos desde selector de rol ni mensaje. Integra aprobaciones y vistas mínimas de pedido/agenda/expediente como tarjetas e inspector del chat. El perfil real autenticado es una extensión; la demo no acredita identidad de personas reales.

Usa Python, FastAPI, LangChain y LangGraph. Implementa el frontend en `web/` con Astro + React + TypeScript + Tailwind CSS + shadcn/ui. Una sola isla React `ChatWorkspace` con `client:load` concentra conversación, paneles y estado. Compila en una etapa Node del Dockerfile y sirve recursos desde FastAPI, con API bajo `/api/`. Gemini es el proveedor inicial de chat y embeddings configurado por variables de entorno. Verifica sus APIs y los modelos disponibles en documentación oficial y en la cuenta configurada; no copies nombres de modelos o clases obsoletos. Mantén puertos/adaptadores para otros proveedores.

Docker Compose debe levantar `api`, `worker`, `db` con PostgreSQL + pgvector y `migrate` temporal. Incluye Dockerfile, `.dockerignore`, `.env.example`, dependencias fijadas, migraciones, healthchecks y volúmenes de DB/adjuntos. Publica la API en 127.0.0.1. La base se comunica por red interna. No añadas Redis, Kubernetes ni un contenedor por agente sin una necesidad concreta.

## Frontend y sistema visual obligatorio

Sigue `FRONTEND_Y_SISTEMA_VISUAL.md`: sidebar colapsable de 248 px, chat centrado hasta 760 px, compositor multimodal y panel opcional de actividad/caso/fuentes de 340 px. Incluye cuatro sugerencias editables relacionadas con P1–P4. Al pulsarlas no ejecutes acciones de negocio.

Usa tokens de tema claro/oscuro: aqua `#0F766E`, superficies `#FFFFFF`, fondo `#F8FAFC`, texto `#0F172A`. Inter para interfaz y JetBrains Mono para detalle técnico, empaquetadas localmente. Estados con texto/iconos y contraste validado. En móvil, usa Sheet/Drawer y conserva chat/compositor accesibles.

shadcn/ui es el kit base. Puedes reutilizar componentes presentacionales de AI Elements si son compatibles; no cambies a Vercel AI SDK ni adoptes `useChat` sin implementar/documentar un adaptador que conserve el contrato FastAPI/LangGraph. Si resulta innecesario, crea los componentes de chat sobre shadcn/ui.

Muestra agente activo, herramientas, estados, duración, fuentes y resultados mediante eventos reales tipados del backend. La sección «Cómo se resolvió» usa `rationale_summary`, hechos y fuentes. Nunca solicites ni expongas pensamiento privado, prompts del sistema o claves. No inventes trazas para decorar la UI. La reconexión recupera estado y no repite comandos.

## Procesos y agentes

Implementa un supervisor y cuatro especialistas con contratos y herramientas propios:

1. Atención: interpretar solicitudes, aclarar, confirmar siete campos y registrar mediante servicio determinista.
2. Logística: interpretar preferencias, obtener alternativas calculadas, negociar dentro de límites y reservar de forma atómica.
3. Calidad: contrastar observaciones con evidencia/procedimientos y producir una recomendación; la inspección, reproceso y liberación son humanos.
4. Incidencias: reconstruir hechos, proponer soluciones y esperar aprobación/cumplimiento antes del cierre.

El supervisor delega según intención validada. Los especialistas no deben ser funciones que devuelven respuestas prefijadas. Usa subgrafos, estado tipado y herramientas reales del dominio. Los efectos se ejecutan únicamente mediante la capa de aplicación después de validar permisos, evidencia, versiones y autorizaciones.

P1 se implementa primero como corte vertical. Continúa con P2–P4 hasta completar la V1; no presentes la V1 como terminada si solo funciona P1. Las tareas físicas se representan con formularios/eventos de operador. Los límites piloto del plan se configuran, no se presentan como políticas reales confirmadas por la empresa.

## Arquitectura y datos

Respeta módulos `domain`, `application`, `agents`, `graphs`, `infrastructure`, `interfaces` y `workers`. El dominio no importa frameworks de IA, HTTP ni clientes de DB. Centraliza modelos en `infrastructure/llm/provider.py` y embeddings en su adaptador. No mezcles UI, prompts, grafo y SQL en un archivo.

Usa PostgreSQL como fuente de verdad para clientes, pedidos, agenda, casos, mensajes, aprobaciones, ledger y outbox. Mantén checkpoints LangGraph persistentes por caso, con `thread_id` estable y separación de tablas/esquemas. Un checkpoint no sustituye los pedidos ni garantiza por sí solo idempotencia.

Cada comando tiene identificador estable, restricción única y transacción. Maneja concurrencia, versión obsoleta y resultado de escritura incierto. Si falla una notificación después del registro, conserva el pedido y reintenta la notificación. El canal demo puede ser una bandeja local; no afirmes que enviaste un correo real.

Implementa RAG real desde la V1: extensión vector activa, ingesta de documentos aprobados, fragmentación, embeddings reales persistidos, modelo/dimensión/hash y búsqueda por similitud con filtros de organización, cliente/rol y vigencia. Proponer dimensión 768 y comprobarla con el modelo elegido. No mezclar modelos/dimensiones en una colección. La búsqueda exacta por similitud basta para el corpus pequeño; HNSW es opcional.

Crea corpus y clientes demo sintéticos, identificados. No copies datos de contacto personales de los instrumentos. Separa conocimiento compartido aprobado y evidencia de cada caso. Una subida de cliente no entra automáticamente al corpus global. Las citas deben corresponder a documentos/fragmentos realmente recuperados.

Los adaptadores n8n/Sheets son opcionales y no bloquean la V1. El backend mínimo usa servicios Python. No hagas depender el arranque de Google Sheets, del coordinador n8n previo ni de un sistema externo que no se haya configurado.

## Multimodalidad y HITL

Procesa medios con el proveedor real, no solo nombres de archivo. Guarda originales en volumen y conserva MIME, hash, caso y fuente. No pongas blobs base64 en checkpoints. Valida tamaño/tipo y acceso. Para imágenes/audio, conserva observaciones/transcripción editable; para PDF, referencias de página cuando sea posible. Un campo extraído de un medio requiere la confirmación correspondiente antes del comando.

Usa `America/Lima` y reloj inyectable. Implementa `interrupt()` y reanudación con `Command(resume=...)`, mismo thread y validación del actor. Las aprobaciones se vinculan a hash/versión; se invalidan si cambia la propuesta. No escribas ni envíes efectos no idempotentes antes de un nodo que puede reejecutarse al reanudar.

Mantén revisión humana en excepciones comerciales, cambios fuera de contrato, calidad observada y soluciones/compensaciones. Un chat de cliente no puede otorgar rol administrativo ni saltar políticas. No cierres un reclamo por silencio ni sin evidencia de cumplimiento.

## Trabajo, pruebas y entrega

Implementa por cortes comprobables: infraestructura/dominio, archivos/RAG, chat/P1, multimodalidad/HITL, P2–P4, pruebas/demo. Después de cada corte actualiza `IMPLEMENTATION_STATUS.md` con módulos implementados, pruebas ejecutadas, bloqueos y siguiente paso. Comunica avances concretos y corrige fallos antes de continuar sobre ellos.

Configura Ruff, tests y validación de tipos apropiada. Prueba A01–A14, M01–M08 y U01–U10: idempotencia concurrente, capacidad, cancelación, evidencia insuficiente, aprobaciones ajenas/obsoletas, falta de cumplimiento, error de proveedor, aislamiento, archivos inválidos y reanudación tras reinicio. Comprueba la UI con automatización de navegador si el entorno lo permite.

Separa fakes de pruebas deterministas y smoke tests de Gemini/embeddings reales. Una V1 sin clave puede abrir el chat y mostrar datos demo, pero debe señalar que IA/embeddings no están disponibles. No uses fallback simulado silencioso para pasar una demo real. Si una capacidad no puede verificarse, indícalo exactamente.

Implementa CLI con subcomandos idempotentes `seed-demo`, `ingest-demo`, `verify-vector-store` y `smoke-local`, o actualiza de forma coherente la guía si eliges otros nombres. Deja operativos y prueba cuando el entorno permita:

```bash
docker compose config
docker compose up --build -d
docker compose ps
docker compose exec api python -m aquaclean.cli seed-demo
docker compose exec api python -m aquaclean.cli ingest-demo
docker compose exec api python -m aquaclean.cli verify-vector-store
docker compose exec api python -m aquaclean.cli smoke-local
```

Mantén datos al reiniciar. No uses `docker compose down -v` para recuperar errores rutinarios. Las claves se configuran en `.env` local excluido del repositorio; no solicites pegarlas en el chat ni las imprimas en logs.

Entrega README de instalación/ejecución, `.env.example`, OpenAPI, arquitectura actualizada, matriz BPMN–código, resultados reales de tests y guion de demostración. Al finalizar explica qué funciona, cómo arrancarlo, qué variables debo completar y qué no pudo comprobarse. La condición de cierre es código funcional y una V1 local reproducible, no un plan adicional.
