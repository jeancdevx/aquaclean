> Estado actual del producto: consultar [README de ejecución](../README.md), [arquitectura implementada](arquitectura/IMPLEMENTADA.md) y [resultados de la V1](validacion/PRODUCTO_V1.md). El contenido de diseño original se conserva debajo.

# Aqua Clean S.A.C.: procesos y arquitectura multiagente

Diseño académico propuesto, versión 1.2, 14 de octubre de 2026. Entorno de implementación: **VS Code + Codex + Python + LangChain + LangGraph**. V1 prevista: chat multimodal en localhost sin login en demo, Astro + React + shadcn/ui, Gemini configurable, Docker Compose y PostgreSQL + pgvector.

La entrega contiene modelos y especificaciones para construir el software. No acredita que los nuevos agentes, las integraciones o las políticas hayan sido implementados o desplegados.

## Por dónde comenzar

1. Leer `PLAN_ARQUITECTURA.md`: decisiones de alcance, agentes, módulos, contratos, persistencia, pruebas y secuencia de construcción.
2. Abrir `bpmn/01-to-be-integral.bpmn` en [bpmn.io](https://demo.bpmn.io/). Muestra cómo se conectan los cuatro procesos escogidos.
3. Abrir cada proceso de `02` a `05` junto con su descripción correspondiente.
4. Revisar `bpmn/06-orquestacion-multiagente.bpmn` para comprender la coordinación técnica de los agentes y las aprobaciones.
5. Leer `IMPLEMENTACION_V1_LOCAL.md`, preparar la carpeta del repositorio y copiar `arquitectura/AGENTS.md` a su raíz.
6. Entregar a Codex el contenido de `PROMPT_CODEX_VSCODE.md` junto con los documentos de diseño. El objetivo es implementar y demostrar la V1, no generar otro plan.
7. El diseño de navegación, actividad y estilos está en `FRONTEND_Y_SISTEMA_VISUAL.md`.

Cada BPMN incluye información de diagramación BPMN DI: posiciones, carriles, etiquetas y conectores. Se importa como XML BPMN 2.0, no como imagen. Los modelos son descriptivos (`isExecutable="false"`): LangGraph implementará su comportamiento mediante código y contratos; no ejecutará directamente estos XML.

## Catálogo de diagramas

| Archivo | Propósito | Descripción |
|---|---|---|
| `bpmn/00-as-is-revisado.bpmn` | Revisión documental del modelo corporativo recibido | `descripciones/00-as-is-revisado.md` |
| `bpmn/01-to-be-integral.bpmn` | Pedido corporativo completo y relación de P1–P4 | `descripciones/01-to-be-integral.md` |
| `bpmn/02-to-be-solicitudes.bpmn` | P1: interpretación conversacional y registro | `descripciones/02-solicitudes.md` |
| `bpmn/03-to-be-coordinacion-logistica.bpmn` | P2: negociación de agenda y excepciones | `descripciones/03-coordinacion-logistica.md` |
| `bpmn/04-to-be-calidad.bpmn` | P3: análisis contextual de observaciones de calidad | `descripciones/04-calidad.md` |
| `bpmn/05-to-be-reclamos-incidencias.bpmn` | P4: investigación, propuesta y resolución de reclamos | `descripciones/05-reclamos-incidencias.md` |
| `bpmn/06-orquestacion-multiagente.bpmn` | Coordinación, políticas, HITL y ejecución | `descripciones/06-orquestacion.md` |
| `bpmn/07-rpa-determinista-referencia.bpmn` | Copia del TO BE determinista adjunto, conservada como referencia | `descripciones/07-rpa-referencia.md` |

En `vistas/` hay exportaciones SVG y PNG para consultar o insertar en el informe. Para editar, se usan los `.bpmn`.

## Alcance que necesita ratificación

Los BPMN y n8n adjuntos desarrollan **atención corporativa**. El Laboratorio 01 selecciona **atención al detalle** y excluye el servicio institucional. Esta entrega conserva el alcance corporativo para continuar con los modelos y el RPA existentes. El equipo debe ratificar ese alcance con la empresa y el docente y alinear el acta y los instrumentos. No se han alterado los Excel ni convertido sus mediciones en una línea base corporativa.

P4 es un piloto supervisado hasta contar con expedientes suficientes. La matriz anterior lo consideró no viable para RPA por falta de datos; incorporar agentes no elimina esa carencia.

## Lectura de la notación

- Pool externo: cliente corporativo. Los mensajes intercambian información entre pools.
- Carriles: responsabilidad humana, agente o servicio. Un carril no implica un microservicio ni un proceso del sistema operativo.
- Tarea de servicio con nombre de agente: razonamiento con LLM y salida estructurada.
- Tarea de regla de negocio: decisión explícita en código.
- Tarea de usuario: decisión o registro humano mediante interfaz.
- Tarea manual: operación física de lavandería.
- Actividad de llamada con borde grueso: referencia a uno de los procesos detallados.
- Compuerta exclusiva: una salida según el resultado del caso. Las salidas por defecto cubren los estados restantes.
- Temporizador de borde: vence la espera y deriva el caso. Las 24 h son una política piloto propuesta.
- Compuerta basada en eventos del integral: espera una observación o el término de la ventana documental de 48 h que traía el AS IS; requiere ratificación y no restringe la recepción futura de reclamos.

Los nombres de condiciones son especificaciones de diseño; no son expresiones listas para un motor BPMN. Las llamadas `ac:Process_P1` a `ac:Process_P4` se resuelven con los archivos del catálogo. bpmn.io muestra la actividad de llamada; el proceso detallado se abre en otro archivo.

## Fuentes y evidencia

`arquitectura/fuentes-y-decisiones.md` identifica los archivos revisados, las páginas relevantes del PDF y la documentación oficial consultada. `validacion/` contiene las comprobaciones técnicas realizadas sobre los modelos. Los resultados de n8n y del muestreo anteriores son evidencia documental recibida, no ejecuciones repetidas en esta entrega.
