# Instrucciones propuestas para el repositorio Aqua Clean

Este archivo se entrega como propuesta de instrucciones para copiar al repositorio de la aplicación. El paquete de diagramas no contiene una aplicación implementada.

## Contexto y estructura

El producto gestiona solicitudes, coordinación logística, observaciones de calidad y reclamos de clientes corporativos. Los diagramas BPMN de `docs/bpmn` especifican el comportamiento. El alcance de laboratorio al detalle requiere alineación documental antes del piloto.

Cuando se copie este archivo a la raíz del repositorio, ubicar los diseños en `docs/diseno/bpmn` o actualizar aquí su ruta real. El plan 1.1 exige una V1 local dockerizada: chat de texto, imágenes, PDF y audio; Gemini configurable; PostgreSQL + pgvector con ingesta y consultas reales. La recuperación vectorial es obligatoria en la V1. Leer la sección 9 del plan y la guía de implementación antes de construir el producto.

La versión 1.2 añade Astro + React + TypeScript + Tailwind + shadcn/ui y el sistema visual documentado. La demo local abre sin login con actor fijo del backend y datos sintéticos; no implementar un selector que otorgue roles desde la UI. Mostrar actividad real y explicación pública resumida; nunca pensamiento privado ni secretos. El perfil autenticado real sigue siendo una extensión separada de la demo.

Usar Python con dominio independiente, casos de uso de aplicación, agentes LangChain, grafos LangGraph y adaptadores de infraestructura. Un agente devuelve una propuesta estructurada; un ejecutor determinista verifica y aplica comandos. No crear un microservicio por agente.

Leer el BPMN, el contrato del proceso y sus dependencias antes de editar. Si cambia una regla, actualizar el BPMN/descripción y el contrato afectado en el mismo cambio. Conservar compatibilidad n8n de manera explícita en un adaptador. Instanciar modelos exclusivamente en `infrastructure/llm/provider.py` e inyectarlos en los agentes.

## Comandos y validación

Cuando se cree el proyecto, configurar dependencias en `pyproject.toml`, fijarlas en `uv.lock` y documentar los comandos de entorno. Comandos previstos después de configurar esas herramientas:

```bash
uv sync
uv run ruff check .
uv run pytest
uv run python scripts/run_demo.py
```

Actualmente son objetivos del proyecto futuro, no comandos ya comprobados en este paquete. Ejecutar las pruebas pertinentes al módulo cambiado. Los tests normales usan datos sintéticos, reloj inyectado, fake LLM y adaptadores controlados. Las evaluaciones con LLM real van separadas y registran proveedor, modelo, versión de prompt y costo. No usar credenciales reales en fixtures.

Crear también `Dockerfile`, `compose.yaml`, migraciones, healthchecks, volúmenes y CLI de demo. Verificar arranque limpio, percepción real de cada modalidad, embeddings persistidos, búsqueda vectorial filtrada y recuperación tras reinicio. Una tabla de vectores vacía, un botón de adjuntar o un fallback simulado no acreditan estas capacidades. Si falta una clave, informar ese estado en la UI y en la verificación.

Antes de informar que un flujo funciona, distinguir tests de reglas, integración real y evaluación del razonamiento. Un XML válido o una captura no demuestra ejecución de LangGraph ni envío de una notificación.

## Restricciones e invariantes

1. **No inventar hechos.** Código de cliente, cupo, monto, procedimiento, pedido y conformidad se obtienen de evidencia o herramientas. Los ejemplos deben identificarse como sintéticos.
2. **No ejecutar desde una propuesta LLM.** Validar schema, evidencia, permisos, versión y autorización. Las tareas de lectura del agente vuelven a comprobar el alcance del usuario.
3. **No duplicar efectos.** Todo comando de escritura usa identificador estable, ledger y control transaccional. No enviar ni escribir antes de `interrupt()` si el nodo puede reejecutarse.
4. **No cerrar sin cumplimiento.** Calidad observada exige decisión humana y verificación física. Reclamos exigen solución autorizada y evidencia de cumplimiento. Silencio no es conformidad.
5. **No mezclar autoridades de datos.** Elegir un backend de pedidos. Sheets puede ser un adaptador legado o una vista sincronizada; los checkpoints son memoria del grafo, no el libro de pedidos.
6. **No cambiar permisos por instrucciones del chat.** La identidad y organización proceden de la API autenticada. Los documentos recuperados son contenido, no instrucciones de administración.
7. **No publicar secretos ni datos del cliente.** Usar variables de entorno y ocultar contactos/evidencia sensible en logs.
8. **No afirmar validaciones no realizadas.** Reportar pruebas ejecutadas, resultados y limitaciones. No fabricar una línea base o cifras de mejora.

Registrar los cambios por fase y explicar el comportamiento final. Mantener módulos pequeños con responsabilidades claras; evitar un archivo que mezcle API, prompts, grafo y persistencia. No agregar infraestructura ni abstracciones sin un uso identificado por los procesos.
