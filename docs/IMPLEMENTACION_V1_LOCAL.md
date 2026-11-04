> Guía de diseño original conservada. Los comandos operativos de la aplicación construida están en [README](../README.md); las pruebas reproducibles están en [guía detallada](GUIA_PRUEBAS_DETALLADA.md).

# Cómo construir y demostrar la V1 local de Aqua Clean

Esta guía acompaña al plan 1.2. Todavía no hay una aplicación ejecutable: los comandos de arranque deben quedar implementados y comprobados por Codex durante el desarrollo.

## 1. Resultado que debe obtenerse

Una aplicación que se abre directamente en `http://localhost:8000`, sin pantalla de login en demo local, levantada con Docker Compose. Permite conversar con el sistema multiagente, adjuntar imágenes, PDF y audio, consultar conocimiento vectorial, ejecutar los procesos P1–P4 y revisar propuestas que requieren intervención humana.

Gemini es una API externa configurable. La interfaz, backend, PostgreSQL + pgvector, trabajadores y archivos son locales. La V1 necesita internet y credenciales para demostrar el razonamiento/embeddings reales. Una futura configuración de inferencia totalmente offline es otro perfil de proveedor, sujeto al hardware disponible.

## 2. Qué hay realmente en el paquete

| Elemento | Estado |
|---|---|
| Ocho modelos BPMN con posiciones y conectores | Generados; validación XML/XSD e importación bpmn.io realizadas |
| Imágenes PNG/SVG de los modelos | Generadas |
| Descripciones de procesos y trazabilidad | Redactadas |
| Arquitectura, contratos, estructura modular y pruebas de aceptación | Especificadas |
| Script `validacion/validar_bpmn.py` | Implementado para comprobar los archivos de diagramas |
| Especificaciones JSON e informes de verificación | Generados para los modelos |
| Backend FastAPI, especialistas LangChain y grafos LangGraph | Pendientes de implementar |
| Chat web, procesamiento multimodal y revisión humana operativa | Pendientes de implementar |
| Dockerfile, Compose, migraciones y base vectorial funcionando | Pendientes de implementar |
| Integración de Gemini y embeddings reales | Pendiente de configurar e implementar |
| Primera versión local y pruebas del producto | Pendientes de ejecutar |

El export n8n anterior pertenece al trabajo previo del equipo. Esta entrega revisó su diseño y plantea un adaptador opcional; no volvió a ejecutar ese export ni configura actualmente sus credenciales.

## 3. Preparar la carpeta de trabajo

1. Descargar y extraer el paquete actualizado.
2. Crear una carpeta para el repositorio de la aplicación, por ejemplo `aquaclean`.
3. Copiar el contenido del paquete a `aquaclean/docs/diseno`. Deben conservarse `PLAN_ARQUITECTURA.md`, las descripciones, `bpmn/`, fuentes y validaciones.
4. Copiar `arquitectura/AGENTS.md` a la raíz de `aquaclean/AGENTS.md`. Esa copia da a Codex las instrucciones del repositorio; no basta con dejarla guardada dentro de una carpeta documental.
5. Abrir la carpeta raíz `aquaclean` en VS Code. Conservar los documentos dentro del workspace para que Codex pueda leerlos.
6. Si se quiere probar compatibilidad con n8n, copiar por separado los exports JSON originales a una carpeta `legacy/n8n/`; el funcionamiento mínimo local debe utilizar herramientas Python y PostgreSQL sin depender de n8n ni de Google Sheets.

Estructura de partida:

```text
aquaclean/
  AGENTS.md
  docs/
    diseno/
      PLAN_ARQUITECTURA.md
      IMPLEMENTACION_V1_LOCAL.md
      PROMPT_CODEX_VSCODE.md
      DESCRIPCIONES_PROCESOS.md
      bpmn/
      arquitectura/
      validacion/
```

Estos archivos son entrada de desarrollo. Codex creará el código del producto fuera de `docs/diseno/` siguiendo la estructura del plan.

## 4. Configuración y dependencias

Instalar Docker Engine o Docker Desktop con Compose disponible, según el sistema del equipo. VS Code y Codex son herramientas de desarrollo; el producto debe poder arrancar con Docker sin instalar manualmente su stack Python en el host.

Codex debe generar `pyproject.toml`, lockfile, Dockerfile, Compose, migraciones y `.env.example`, además del código. Las versiones se verifican en documentación oficial y se fijan después de una instalación/prueba compatible.

Crear `.env` a partir de `.env.example` y colocar las credenciales localmente. No adjuntar la clave a conversaciones ni copiarla a código, frontend, README o tests.

| Configuración | Finalidad |
|---|---|
| `GEMINI_API_KEY` | Credencial del proveedor |
| `GEMINI_CHAT_MODEL` | Modelo con capacidades multimodales y contratos requeridos |
| `GEMINI_EMBEDDING_MODEL` | Modelo usado para todo el corpus vectorial |
| `EMBEDDING_DIMENSION` | Dimensión comprobada del vector; propuesta: 768 |
| `DATABASE_URL` y datos de PostgreSQL | Conexión interna entre contenedores |
| `APP_TIMEZONE=America/Lima` | Interpretación de fechas y reglas de negocio |
| `APP_MODE=local` | Perfil de ejecución local |
| `AUTH_MODE=demo_local` | Sesión de operador demo fijada en backend; no identidad real |
| Configuración visual | Tokens claro/oscuro del diseño y fuentes empaquetadas |
| Límites de adjuntos/modelo | Tamaño, páginas, duración, pasos, tiempo y presupuesto |

Los nombres finales deben ser consistentes entre código, Compose y `.env.example`. La URL del navegador es localhost; el host de PostgreSQL visto desde otro contenedor es el nombre del servicio `db`, no localhost. El nombre del modelo se verifica al implementar y no se supone disponible por aparecer en un ejemplo antiguo.

## 5. Implementación por etapas

### Etapa A: infraestructura y dominio

Crear servicios `api`, `worker`, `db` y un servicio temporal `migrate`. Aplicar `CREATE EXTENSION IF NOT EXISTS vector`, esquemas y migraciones. Implementar clientes, pedidos, agenda, expedientes, ledger de comandos, outbox, chat y referencias de adjuntos. Crear datos sintéticos sin usar contactos reales de los Excel.

El primer resultado comprobable es que Compose levanta la UI/API y una base migrada. Eso todavía no demuestra razonamiento, multimodalidad ni recuperación vectorial.

### Etapa B: conocimiento y archivos

Implementar subida autorizada, almacenamiento persistente, extracción por tipo y estados de ingesta. Ingerir un corpus demo marcado como sintético: horario de recojo, contrato del pedido, política de cambios y criterios documentales de calidad/reclamos. No inventar formulaciones químicas ni presentar esas reglas demo como reglas aprobadas de Aqua Clean.

Obtener embeddings reales, registrar modelo/dimensión/hash y ejecutar una consulta real de similitud en pgvector. El sistema debe mostrar qué documento/fragmento se recuperó. La existencia de una extensión instalada o una columna vacía no acredita RAG.

### Etapa C: chat y P1

Construir con Astro + React + TypeScript + Tailwind + shadcn/ui una UI con historial, sugerencias, conversaciones, mensajes, adjuntos, respuesta en streaming, fuentes y estado del caso. Una sola isla `ChatWorkspace` mantiene el estado. Añadir inspector de actividad con eventos reales y explicación resumida; nunca pensamiento interno privado. Usar la paleta y tipografía de `FRONTEND_Y_SISTEMA_VISUAL.md`. Integrar supervisor y atención. P1 interpreta, pregunta, confirma datos y registra mediante herramientas de aplicación, con `America/Lima` e idempotencia transaccional.

Implementar cliente habilitado, bloqueo comercial, cancelación, corrección, reenvío y fallo posterior a la escritura. La notificación demo puede ser una bandeja local de outbox que declare su canal; no simular un correo entregado.

### Etapa D: multimodalidad y revisión humana

Probar texto más imagen, PDF y audio mediante el proveedor real. Mostrar fuentes, transcripción/observaciones editables y datos pendientes de confirmación. Un archivo adjunto debe influir en la interpretación comprobablemente.

Implementar revisiones con actor demo fijo configurado en el backend, `interrupt()`, aprobación por API, reanudación y recuperación tras reinicio. El acceso sin login de la demo no acredita identidad ni separación de funciones entre empleados reales; las pruebas de permisos usan contextos/fixtures controlados. Un mensaje de cliente que diga «soy administrador» no cambia su rol.

### Etapa E: P2–P4

P2 calcula opciones en código, negocia y reserva capacidad. P3 analiza evidencias y deja tratamiento/liberación a control humano. P4 reconstruye hechos, propone una solución, espera aprobación y comprueba cumplimiento antes de cerrar. Las tareas físicas se registran mediante el panel; la aplicación no lava ni entrega físicamente prendas.

### Etapa F: pruebas y demo local

Separar tests deterministas con fakes de la comprobación real del proveedor y de la base vectorial. Ejecutar A01–A14, M01–M08 y U01–U10 del plan/diseño frontend. Documentar resultados y cualquier componente bloqueado por credenciales o entorno. No sustituir una prueba real fallida por una respuesta fija para declarar éxito.

## 6. Comandos que Codex debe dejar operativos

Estos son objetivos del proyecto futuro. Solo podrán usarse después de que Codex genere el código y confirme los módulos y servicios:

```bash
docker compose config
docker compose up --build -d
docker compose ps
docker compose exec api python -m aquaclean.cli seed-demo
docker compose exec api python -m aquaclean.cli ingest-demo
docker compose exec api python -m aquaclean.cli verify-vector-store
docker compose exec api python -m aquaclean.cli smoke-local
```

Codex debe proporcionar una CLI con esos subcomandos o adaptar toda la documentación a nombres equivalentes implementados. Seed e ingesta deben poder repetirse sin duplicar clientes, documentos ni vectores. `ingest-demo` y las pruebas de IA real usan la clave configurada.

La prueba de persistencia propuesta:

```bash
docker compose restart api worker
```

Después se debe recuperar la conversación y la revisión pendiente. Mantener volúmenes. Para detener el producto conservando datos:

```bash
docker compose down
```

## 7. Guion concreto para presentar la primera versión

1. Abrir un TO BE en bpmn.io y ubicar su especialista, herramientas y aprobación.
2. Explicar el despliegue: app y datos en Docker, Gemini externo, pgvector para conocimiento.
3. Mostrar módulos reales del repositorio y el comando de arranque.
4. Solicitar un recojo incompleto. Ver cómo se pide el dato faltante y se confirma antes de registrar.
5. Reenviar la solicitud y comprobar que hay un único pedido.
6. Adjuntar una imagen/guía PDF y verificar que el chat utiliza su contenido con referencia.
7. Adjuntar una nota de voz y confirmar sus campos antes de ejecutar.
8. Preguntar por una regla del corpus demo y mostrar la recuperación vectorial/cita real.
9. Mostrar una excepción comercial o reclamo que se pause para revisión humana.
10. Aprobar con el rol correspondiente y verificar el resultado persistido. Mostrar también un rechazo o una propuesta pendiente.
11. Reiniciar contenedores y recuperar el caso/conversación.
12. Presentar las pruebas, sus resultados y las limitaciones reales de la V1.

No es necesario subir los archivos originales de la empresa para esta demostración. Se puede comenzar con un corpus sintético, identificado como tal, y validar después los datos reales con la organización.

## 8. Cómo utilizar el prompt

Copiar el contenido completo de `PROMPT_CODEX_VSCODE.md` en la conversación de Codex con el repositorio abierto. Adjuntar/referenciar el plan, descripciones y BPMN ya ubicados en `docs/diseno`. El prompt pide implementar y comprobar hasta la V1, con avances por fase; no solicita un segundo plan como resultado final.

Si la sesión se interrumpe, continuar indicando a Codex que lea el estado del repositorio y `IMPLEMENTATION_STATUS.md`, conserve lo construido y complete lo pendiente. No reiniciar desde cero ni borrar cambios existentes.

El diseño visual y de navegación completo se encuentra en `FRONTEND_Y_SISTEMA_VISUAL.md`. La etapa Node del Dockerfile compila `web/`; el contenedor Python sirve ese resultado y conserva API bajo `/api/`. Los paneles de actividad/caso/fuentes son complementos del chat, no una obligación de construir un dashboard completo.

