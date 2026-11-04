# Verificación de los modelos entregados

Fecha: 14/10/2026. Se validaron **ocho archivos BPMN**.

| Comprobación ejecutada | Resultado |
|---|---|
| XML contra `BPMN20.xsd` y esquemas dependientes distribuidos con bpmn-moddle | 8/8 válidos |
| Lectura con bpmn-moddle 10.3.1 | 8/8, sin advertencias |
| Importación en el modelador bpmn-js 18.31.0, componente de bpmn.io | 8/8, sin advertencias |
| Referencias, IDs, ámbitos de secuencia e incoming/outgoing | 8/8 sin errores |
| Carriles de nodos principales y elementos BPMN DI | 8/8 sin errores |
| Procesos llamados P1–P4 resueltos en el catálogo | Sin referencias faltantes |
| Alcanzabilidad y ruta a un fin, incluyendo activación de eventos de borde | 8/8 sin errores en esta comprobación estructural |
| Condiciones y salidas por defecto de las compuertas nuevas | Presentes |
| Conectores de secuencia de los seis diagramas nuevos atravesando nodos ajenos | Cero en la comprobación geométrica |
| Exportación visual SVG/PNG y revisión de presentación | Realizada para los ocho diagramas |

Los modelos de referencia previos usan algunas condiciones solo como etiquetas. Se conservan como notas de legado en el reporte, ya que no se está convirtiendo el archivo original en un workflow ejecutable. Todos los modelos son descriptivos (`isExecutable=false`).

Se corrigieron durante la revisión el orden XML de incoming/outgoing, una salida pendiente que no estaba enlazada a su fin y conectores que atravesaban tareas ajenas. También se verificó que la autorización humana de P1 retorne a resumen, confirmación del cliente y validación antes del registro, y que P4 no cierre sin cumplimiento acreditado.

Los detalles técnicos están en `estructura-bpmn.json` e `importacion-bpmn-io.json`. La comprobación estructural se puede repetir con:

```bash
python validacion/validar_bpmn.py
```

Para repetir además XSD, instalar lxml y suministrar la ubicación de los esquemas OMG:

```bash
python validacion/validar_bpmn.py --schema /ruta/a/BPMN20.xsd
```

Estos resultados acreditan el intercambio y la estructura de los diagramas. No acreditan una ejecución de LangGraph, la calibración de un LLM, las integraciones con Google Sheets ni un piloto en la lavandería. La comprobación de rutas no equivale a una prueba formal exhaustiva de todos los comportamientos de un motor BPMN. Los tests de aceptación del software se especifican como trabajo posterior en el plan.
