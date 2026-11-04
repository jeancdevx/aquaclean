> Antecedente V1 corporativo, superado para el alcance seleccionado. Versión vigente: [descripciones V2](../DESCRIPCIONES_PROCESOS.md). Original conservado en [antecedentes](../antecedentes/v1/descripciones/04-calidad.md).

# P3. Analizar observaciones de calidad y recomendar tratamiento

**Diagrama:** `bpmn/04-to-be-calidad.bpmn`. **Proceso:** `Process_P3`. **Especialista:** agente de calidad. **Responsable humano:** personal de planta y control de calidad.

## Descripción textual del TO BE

El proceso comienza cuando planta o control de calidad detecta prendas observadas. El operario realiza la inspección física y registra hallazgos concretos, referencias a la guía y evidencia disponible. Las fotografías pueden incorporarse si el personal dispone de ellas y existe un procedimiento de captura; no se supone que ya haya cámaras o un modelo de visión desplegado.

El sistema recupera guía, historial de tratamiento y procedimientos aprobados vigentes. El agente contrasta esas fuentes con la descripción de planta, diferencia hechos de hipótesis y propone una disposición: verificar más información, liberar un lote físicamente conforme, reprocesar según un procedimiento autorizado o abrir una incidencia por daño, pérdida o riesgo.

Si la evidencia es insuficiente, el personal completa los datos o descarta la evaluación automática. El piloto admite una solicitud adicional antes de dejar el caso pendiente de evaluación técnica. El agente no inventa el material de una prenda, la causa de una mancha ni la responsabilidad de la empresa.

La aplicación comprueba que la recomendación cite fuentes vigentes y respete las restricciones conocidas. Control de calidad revisa la propuesta y autoriza la disposición. Si existe verificación física conforme, el sistema registra la liberación. Si se autoriza reproceso, el operario lo ejecuta físicamente según el procedimiento. Después se verifica el resultado. El piloto admite un ciclo de reproceso; una nueva observación abre una incidencia o requiere otra evaluación humana, evitando un bucle automático de tratamientos.

Un daño, pérdida, riesgo o reproceso no conforme abre un expediente para P4 y conserva el lote retenido. La apertura no equivale a reconocer responsabilidad ni a autorizar compensación. El resultado que habilita el empaque es una liberación humana registrada con evidencia.

## Datos y conocimiento necesarios

| Categoría | Contenido requerido |
|---|---|
| Identidad | Pedido, lote y prendas identificables |
| Observación | Quién inspeccionó, fecha, hallazgos y referencias de evidencia |
| Historial | Tratamiento ejecutado, observaciones previas y contador de reprocesos |
| Conocimiento | Procedimientos y criterios de calidad aprobados, con versión/vigencia |
| Resultado agentic | Hipótesis diferenciadas de hechos, disposición propuesta y evidencia |
| Resultado humano | Disposición autorizada, verificación física y responsable |

El AS IS incluye inspección, reproceso y derivación por prendas dañadas o extraviadas. El registro estructurado y la recuperación de procedimientos son mejoras propuestas. Antes del piloto deben obtenerse y aprobarse las fuentes de dominio, ya que el expediente actual no suministra criterios suficientes para recomendar tratamientos reales.

## Por qué se emplea un especialista

Las observaciones en lenguaje natural pueden admitir interpretaciones diferentes y requerir contraste con historial y procedimientos. El especialista aporta recuperación de evidencia y una recomendación explicada; el supervisor coordina el caso y deriva incidencias. Los conteos, las incompatibilidades conocidas y los cambios de estado se aplican en código.

Un lote que no presenta observaciones puede seguir una verificación por reglas y control humano sin invocar al LLM. La especialización se reserva para los casos que necesitan análisis contextual, evitando cargar todo pedido con razonamiento innecesario.

## Trazabilidad del BPMN

| Elementos | Función | Código futuro |
|---|---|---|
| `P3_Inspeccion` | Observación física real | Formulario de calidad |
| `P3_Evidencia` | Fuentes vigentes y permitidas | `KnowledgeRepository`, `EvidenceRepository` |
| `P3_Analizar` | Propuesta con citas | `agents/quality.py` |
| `P3_Suficiente`, `P3_Completar`, `P3_Nueva` | Pedir evidencia y limitar el retorno | Grafo y política |
| `P3_Validar`, `P3_Revisar`, `P3_Decision` | Restricciones y autorización | Dominio y panel de calidad |
| `P3_Reproceso`, `P3_Verificar`, `P3_Conforme` | Operación y comprobación físicas | Eventos registrados por operario |
| `P3_Registrar` | Disposición conforme persistida | Ejecutor determinista |
| `P3_Incidencia` | Expediente enlazado a P4 | Evento `QualityIncidentOpened` |

## Aceptación y límites

Ejemplo sintético: una mancha persiste después del lavado y la descripción del material no está documentada. El agente identifica el dato faltante y cita el procedimiento disponible; no prescribe una sustancia ni una dosis. Si el operario verifica el material y aprueba un reproceso compatible, se ejecuta y se documenta el resultado. Si no se puede verificar, se retiene el lote y se deriva.

Pruebas mínimas: evidencia insuficiente, procedimiento vencido, hipótesis contradictorias, recomendación fuera de restricciones, reproceso autorizado, reproceso persistente y pérdida de prenda. Ninguna tarea del agente acciona máquinas. Ningún resultado textual reemplaza la inspección ni libera automáticamente un lote observado.
