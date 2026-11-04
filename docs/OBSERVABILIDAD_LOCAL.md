# Observabilidad local para la entrega

Estos registros son auxiliares para depurar y explicar la aplicación. La interpretación anterior que los proponía como sustituto queda corregida por la instrucción vigente: la semana 10 requiere trazas reales de LangSmith utilizando su plan gratuito. Ver [LANGSMITH.md](LANGSMITH.md). Este visor no acredita ese punto ni muestra la interfaz de LangSmith.

La exportación y el visor funcionan sin cuenta ni API key de LangSmith y no realizan llamadas nuevas al modelo. Las ejecuciones que originaron los registros sí usaron Gemini configurado. Los fakes de pruebas se conservan aparte. El paquete anterior mantiene intactas sus fechas y resultados; generar esta exportación no constituye una nueva inferencia.

## Mostrarlo al profesor

1. Iniciar la aplicación con `docker compose up -d` y abrir el chat local. Abrir **Actividad y caso** en un caso sintético ejecutado para mostrar eventos persistidos, herramientas y revisión.
2. Ejecutar `uv run python scripts/export_local_observability.py`. Lee los casos sintéticos del recorrido guardado y su estado por API, sin escribir órdenes ni ejecutar agentes. `--from-artifacts` permite exportar sin API ni conexión de red.
3. Ejecutar `node web/scripts/capture-local-observability.mjs`. Playwright verifica los datos contra el HTML, filtra eventos y captura el reporte y la aplicación real; no utiliza `page.route`.
4. Abrir `05-observabilidad-local/REPORTE_LOCAL.html` del directorio indicado en `artifacts/semana10/CURRENT`. El HTML funciona offline, incluye selector de run y filtro de eventos, y se comparte en el ZIP. Revisar el resumen, una investigación Deep Agents y la tabla de pausas/reanudaciones.

## Qué demuestra y qué no registra

| Registro | Fuente y lectura |
|---|---|
| JSON, JSONL y CSV | Eventos públicos persistidos; no mensajes completos, contactos, claves ni razonamiento privado. Proyección de campos permitidos en `scripts/local_log_report.py`. |
| Caso / run / hilo / revisión | IDs locales de aplicación. Una revisión vincula la ejecución que pausa con otra ejecución que reanuda el mismo hilo. No son IDs de LangSmith. |
| Duración | Diferencia entre eventos originales de inicio y fin; el SDK Deep Agents conserva además su propia duración. Espera humana se presenta por separado. Un dato ausente permanece desconocido. |
| Planificación y herramientas | Journal real SDK: write_todos, task, Evidencias, Procedimientos y lecturas acotadas. Se conserva el orden observado; no se reconstruye un árbol interno de spans. |
| Tokens | Uso conservado por respuesta o ejecución Deep Agents canónica. El evento P4 repite ese uso y se excluye para no duplicarlo. No se infieren retries, uso ausente ni total de facturación. |
| Coste | Desconocido cuando no fue devuelto. Una clave no permite deducir por sí sola un importe o modalidad de pago. |
| Logs operativos Docker | Complemento filtrado por run y código de error, cuando el contenedor aún los conserva. Un archivo vacío indica ausencia de líneas conservadas, no ausencia de eventos persistidos en PostgreSQL. |

`registros-locales.json` conserva procedencia, hashes de fuentes, fecha de exportación y fechas de ejecución originales. Los registros incluyen intentos fallidos y resultados satisfactorios. La captura de Actividad corresponde al backend real; las otras tres son renderizados Playwright del reporte técnico exacto, identificados como tales.

Verificar el exportador: `uv run pytest tests/unit/test_local_log_report.py`. Sus entradas controladas prueban la proyección y la correlación, no acreditan nuevas llamadas al proveedor. La captura verifica por separado los datos reales ya registrados.

La configuración y verificación futura del servicio externo siguen en [LANGSMITH.md](LANGSMITH.md). No se requieren para abrir esta evidencia local.
