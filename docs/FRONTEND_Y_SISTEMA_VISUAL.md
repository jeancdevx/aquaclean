# Frontend y sistema visual de Aqua Clean

Especificación de diseño, versión 1.2, 14/10/2026. El frontend todavía no está implementado. Este documento completa las funciones de la versión 1.1 con acceso demo, composición de pantalla, componentes, eventos y estilos.

## 1. Experiencia principal

La V1 es una aplicación centrada en el chat, con historial y entrada multimodal. Se abre directamente en localhost, sin landing page ni pantalla de login. Las acciones operativas se presentan en tarjetas de conversación y paneles laterales; no hace falta un dashboard general como pantalla de entrada.

Distribución de escritorio:

| Zona | Contenido | Tamaño propuesto |
|---|---|---|
| Barra lateral | Marca, nueva conversación, búsqueda, historial y accesos a revisiones/conocimiento | 248 px, colapsable |
| Cabecera | Título de conversación, estado del modelo, modo demo, tema y botón de actividad | 56 px |
| Conversación | Mensajes, citas, adjuntos, confirmaciones y tarjetas de negocio | Columna centrada, máximo 760 px |
| Compositor | Texto, adjuntar imagen/PDF/audio, archivos pendientes y envío | Multilínea con crecimiento limitado |
| Inspector opcional | Actividad, caso y fuentes | 340 px; cerrado por defecto |

En pantalla pequeña, historial e inspector se abren como Sheet/Drawer. El chat mantiene prioridad y el compositor no tapa los mensajes. Cuando llega contenido nuevo, se sigue el final solo si el usuario ya estaba allí; si está leyendo arriba, aparece «Ir al último mensaje».

## 2. Acceso sin login en la demo

El perfil `AUTH_MODE=demo_local` abre el chat y establece una sesión demo en el backend, con actor fijo `demo_operator` y organización sintética. Ese operador tiene las capacidades de demostración para atención, logística, calidad y administración. Las aprobaciones se registran con ese actor y el origen demo.

No hay selector libre de rol que conceda permisos ni identidad tomada del mensaje. La API sigue validando caso, organización, comandos y propuesta/versiones. «Sin login» describe la entrada a la demo; no acredita autenticación de personas reales ni separación de funciones entre varios empleados.

La demo utiliza datos sintéticos y publicación en localhost. Para operar con clientes/usuarios reales o desplegar en red se habilita el perfil autenticado, con cuentas/roles y pantalla de acceso cuando corresponda. Esa pantalla no forma parte del frontend mínimo de la demo local. Las pruebas de permisos se conservan en fixtures/contextos controlados.

## 3. Inicio y sugerencias

Estado vacío: título «¿Qué necesitas coordinar hoy?» y cuatro sugerencias relacionadas con capacidades reales:

1. «Programar un recojo».
2. «Reprogramar una entrega».
3. «Revisar una observación de calidad».
4. «Consultar un reclamo».

Pulsar una sugerencia introduce un mensaje editable. No registra un pedido ni ejecuta una acción de negocio automáticamente. Después de una respuesta pueden aparecer siguientes pasos sustentados en el estado real, como confirmar datos, aportar una guía o revisar una propuesta.

El ejemplo de bienvenida no muestra pedidos, tiempos, conteos ni herramientas ficticios como si se acabaran de ejecutar.

## 4. Mensajes y acciones de negocio

| Contenido | Presentación |
|---|---|
| Mensaje del usuario | Burbuja discreta alineada a la derecha, fondo aqua claro |
| Respuesta del asistente | Texto sobre superficie limpia, markdown y citas |
| Imagen | Miniatura y apertura ampliada; referencia al adjunto |
| PDF | Nombre, tipo y páginas cuando se conozcan; acceso al documento autorizado |
| Audio | Reproductor y transcripción/interpretación editable |
| Borrador de recojo | Tarjeta con campos y acciones Confirmar / Corregir / Cancelar |
| Alternativas logísticas | Opciones realmente calculadas y selección explícita |
| Revisión humana | Propuesta, motivo, evidencia y acciones Aprobar / Rechazar / Corregir |
| Resultado persistido | Número/estado real devuelto por el servicio |
| Error | Mensaje concreto, recuperación disponible y estado del caso |

Enter envía y Shift+Enter agrega línea. El envío se deshabilita si no hay contenido o un adjunto sigue sin terminar de subir. «Detener respuesta» detiene la generación/visualización cuando el backend lo permite; nunca revierte silenciosamente un comando ya confirmado. La UI informa el resultado de cualquier acción que ya haya ocurrido.

## 5. Actividad y explicación visible

Debajo de la respuesta aparece un resumen colapsable «Cómo se resolvió». Contiene una explicación breve de los hechos, restricciones y evidencia que sustentan la recomendación. El inspector «Actividad» muestra la secuencia verificable del caso:

- Supervisor: dominio identificado y especialista seleccionado.
- Especialista: inició/finalizó su tarea y estado actual.
- Herramienta: nombre legible, entrada permitida, estado, duración y resultado resumido.
- Evidencia: documentos realmente recuperados y referencias.
- Decisión: propuesta y razones públicas resumidas.
- Aprobación: qué falta, quién la resolvió en demo y resultado.
- Ejecución: comando persistido, error o estado pendiente.

**No se muestra ni se solicita la cadena privada de pensamiento.** El componente de explicación recibe `rationale_summary` y referencias, no pensamiento interno bruto, prompts del sistema ni deliberación privada del proveedor. Tampoco se fabrica una animación de herramientas para aparentar ejecución.

Durante una ejecución, las etiquetas cambian según eventos reales: «Interpretando solicitud», «Consultando agenda», «Pendiente de revisión», «Registrado» o «Error de integración». El detalle técnico de tool/trace queda en el inspector; el chat usa nombres comprensibles para el operador.

## 6. Stack y componentes

**Stack elegido para el diseño:** Astro + React + TypeScript + Tailwind CSS + shadcn/ui. Una única isla React `ChatWorkspace` hidratada con `client:load` concentra conversación, compositor, estado, paneles y streaming. Astro genera la estructura/recursos; FastAPI conserva la API y la orquestación.

| Necesidad | Componentes base |
|---|---|
| Historial y navegación | Sidebar, Button, Input, ScrollArea |
| Compositor y archivos | Textarea/InputGroup, Button, Tooltip, tarjetas de adjunto |
| Estado y carga | Badge, Skeleton, Spinner, Toast/Alert |
| Panel de actividad | Sheet, Tabs, Collapsible/Accordion, Card |
| Confirmaciones y revisión | Card, AlertDialog/Dialog, Button |
| Opciones y configuración | Select/Combobox, DropdownMenu, Switch |

AI Elements puede aportar componentes presentacionales de Message, Conversation, PromptInput, Tool, Sources y Suggestion si sus dependencias encajan con el frontend. Es una ampliación opcional del kit base. No se adopta automáticamente su runtime ni `useChat` del AI SDK: debe existir un adaptador compatible con los eventos FastAPI/LangGraph. Si un componente añade dependencias/protocolo innecesarios, crear su equivalente sobre shadcn/ui y mantener el transporte propio. El backend sigue siendo LangChain/LangGraph.

El diseño emplea iconos Lucide. No se necesita generar imágenes para iconos, botones ni estados.

## 7. Paleta y tipografía

Tema claro por defecto, con opción oscura. Los colores se implementan como tokens CSS/Tailwind y variables de shadcn/ui; no se repiten hexadecimales por componente.

| Token | Claro | Oscuro | Uso |
|---|---|---|---|
| Fondo | `#F8FAFC` | `#0F172A` | Base de la aplicación |
| Superficie | `#FFFFFF` | `#111827` | Chat, menús y tarjetas |
| Barra lateral | `#F1F5F9` | `#0B1220` | Historial |
| Texto principal | `#0F172A` | `#E2E8F0` | Mensajes y etiquetas |
| Texto secundario | `#475569` | `#94A3B8` | Metadatos y descripción |
| Bordes | `#E2E8F0` | `#334155` | Separación discreta |
| Acción principal | `#0F766E` | `#2DD4BF` | Enviar y confirmar |
| Texto sobre acción principal | `#FFFFFF` | `#042F2E` | Etiqueta del botón |
| Mensaje del usuario | `#F0FDFA` | `#134E4A` | Burbuja propia |

Estados claros: éxito `#047857` sobre `#ECFDF5`; pendiente `#92400E` sobre `#FFFBEB`; error `#B91C1C` sobre `#FEF2F2`. En oscuro se definen parejas equivalentes de contraste comprobado al implementar. Cada estado tiene texto/icono; no depende solo del color.

- **Inter** para interfaz y mensajes, empaquetada localmente.
- **JetBrains Mono** para IDs y fragmentos técnicos dentro del inspector.
- Mensajes: 16 px, peso 400, interlineado 1.6.
- Etiquetas: 14 px, peso 500; metadatos: 12–13 px.
- Bienvenida: 28–32 px, peso 600; encabezados normales: 18–20 px.
- Espaciado en múltiplos de 4/8 px, controles de aproximadamente 40 px de alto.
- Radio: 8 px en controles, 12 px en tarjetas, 16 px en compositor.
- Sombras suaves solo en elementos flotantes. Evitar degradados intensos y movimientos decorativos continuos.

## 8. Transporte y modularidad

El frontend recibe eventos públicos tipados con `event_id`, `run_id`, `case_id`, secuencia, fecha y payload autorizado. Familias mínimas: `run.started`, `message.delta`, `agent.started`, `tool.started`, `tool.completed`, `decision.summary`, `approval.requested`, `approval.resolved`, `run.completed`, `run.failed`.

El backend filtra entradas/resultados antes de enviarlos. Nunca expone claves, contraseñas, prompts privados, pensamiento interno ni datos ajenos. La UI deduplica/reordena eventos por identificador/secuencia y recupera estado persistido después de reconectar; no repite un comando de negocio por reconectar al stream.

Código previsto:

```text
web/
  package.json
  astro.config.mjs
  tsconfig.json
  components.json
  src/pages/index.astro
  src/components/chat/ChatWorkspace.tsx
  src/components/chat/ConversationSidebar.tsx
  src/components/chat/MessageList.tsx
  src/components/chat/PromptComposer.tsx
  src/components/chat/ActivityPanel.tsx
  src/components/chat/ApprovalCard.tsx
  src/components/ui/
  src/hooks/useChatSession.ts
  src/hooks/useRunEvents.ts
  src/lib/api.ts
  src/lib/event-types.ts
  src/styles/global.css
  public/fonts/
```

Docker usa una etapa Node para compilar Astro. Copia el `dist/` al contenedor Python y FastAPI sirve los recursos estáticos. En la V1 empaquetada no hace falta un servidor Node de larga duración. API bajo `/api/`; las rutas estáticas no interceptan errores/eventos de la API. Durante desarrollo, usar un proxy explícito hacia FastAPI y mantener fuera del navegador las credenciales Gemini.

## 9. Aceptación del frontend

| ID | Prueba |
|---|---|
| U01 | Abre chat sin login en demo; actor/organización vienen del servidor |
| U02 | Sugerencias editables sin ejecutar pedidos automáticamente |
| U03 | Streaming, cancelación, reconexión e historial sin duplicados |
| U04 | Adjuntos de cada modalidad con carga, error y previsualización |
| U05 | Actividad y herramientas corresponden a eventos reales |
| U06 | Explicación resumida y fuentes, sin pensamiento privado ni secretos |
| U07 | Aprobación vinculada a la versión del caso; doble clic no duplica efectos |
| U08 | Tema claro/oscuro, teclado y anchos 360/768/1440 px sin recortes |
| U09 | Recursos de Astro servidos en Docker; `/api/` conserva su comportamiento |
| U10 | Modelo no configurado o proveedor caído se informa sin fingir respuesta |

Validar contraste, foco, etiquetas accesibles, estados de carga y retorno al chat desde paneles. Usar automatización de navegador al implementar la UI. Esta entrega define el diseño; no acredita que esos componentes ya estén instalados o esas pruebas del producto se hayan ejecutado.

Fuentes técnicas: [shadcn/ui con Astro](https://ui.shadcn.com/docs/installation/astro), [componentes interactivos de Astro](https://docs.astro.build/en/guides/framework-components/), [AI Elements](https://elements.ai-sdk.dev/docs) y sus componentes [Tool](https://elements.ai-sdk.dev/components/tool) / [Prompt Input](https://elements.ai-sdk.dev/components/prompt-input). La composición, acceso demo, paleta y tipografía son decisiones propuestas para Aqua Clean.
