# Seguridad del perfil local y de los agentes

Este perfil es una demostración local, con un único actor fijo `demo_operator` y todas las capacidades de demostración. El acceso se limita al loopback del host. No implementa autenticación real de empleados, separación de funciones entre personas, MFA, cifrado de disco ni una certificación de seguridad. Las pruebas verifican controles concretos; no garantizan seguridad absoluta ni resistencia a toda inyección futura.

## Mensajes de sistema y responsabilidades

Los mensajes están en `src/aquaclean/agents/prompts.py`, versión `aquaclean-boundaries-1.1`; el supervisor añade su contrato de clasificación en `agents/supervisor.py`. El adaptador de percepción tiene instrucciones específicas para tratar medios como datos. Nunca se incluye una credencial en el contexto del modelo.

| Agente | Puede proponer | Herramientas de lectura/cálculo | No puede autorizar/ejecutar |
|---|---|---|---|
| Supervisor | P1–P4 y necesidad de aclaración | Contexto autorizado del caso | Cambios de identidad, permisos o negocio |
| Atención | Campos, aclaración y borrador | Expediente, padrón autorizado, conocimiento y referencias externas | Crear un pedido directamente, ignorar un bloqueo, confirmar en nombre del cliente |
| Logística | Alternativas devueltas por calculador | Expediente y agenda con capacidad real | Inventar cupos, cambiar toda la agenda, reservar sin elección/revalidación |
| Calidad | Hallazgos e incertidumbres, disposición recomendada | Evidencia y procedimientos vigentes | Accionar máquinas, inventar sustancias/dosis, liberar sin inspección/conformidad humanas |
| Incidencias | Cronología, discrepancias y plan | Expediente, historial del pedido y procedimientos | Transferir dinero, atribuir responsabilidad/cerrar sin aprobación y cumplimiento |

La política común define jerarquía, límites, tratamiento de documentos como datos no confiables y prohibición de adoptar instrucciones del chat/adjunto sobre roles, permisos, herramientas o secretos. `include_thoughts=False` evita solicitar pensamiento privado. El modelo devuelve contratos Pydantic con campos extra prohibidos y enumeraciones específicas por especialista.

La aplicación invoca las herramientas de lectura de cada subgrafo; no proporciona shell, SQL libre, navegador, descarga arbitraria de URLs, correo ni herramientas de escritura al LLM. El registro, reserva y disposición solo existen detrás del ejecutor determinista. Las propuestas completas se validan antes de transmitir sus respuestas públicas; SSE transmite deltas de ese texto validado sin pedir a otro modelo que interprete el consentimiento.

## Controles que el prompt no puede cambiar

1. **Identidad:** `interfaces/api/auth.py` devuelve actor/organización del servidor. Cabeceras de rol, campos extra y mensajes del usuario no conceden capacidades. Otros `AUTH_MODE` fallan explícitamente hasta implementar otro adaptador.
2. **Alcance:** cada lectura comprueba organización y cliente. RAG filtra organización, rol, cliente, aprobación documental y vigencia. Un adjunto se consulta por caso/organización y no entra automáticamente al conocimiento compartido.
3. **Acciones:** `domain/policies.py` tiene allowlists por P1–P4. El ejecutor las vuelve a comprobar aunque un proveedor comprometido produzca una propuesta fuera de contrato.
4. **Consentimiento y revisión:** P1 espera confirmación de los siete campos; un bloqueo necesita administración y reconfirmación. P2 comprueba la opción seleccionada contra alternativas calculadas. P3/P4 exigen revisión humana. Ningún endpoint acepta una propuesta arbitraria del navegador para ejecutar negocio.
5. **Aprobaciones:** actor/rol, organización, hash, versión del caso/pedido y fingerprint de política. Una modificación de evidencia o límites impide usar una aprobación vieja. La selección ejecutada debe coincidir con la aprobada. Corregir/rechazar no ejecuta el comando.
6. **Concurrencia:** locks, restricción única, ledger por identificador estable y transacción. La decisión humana, el job de reanudación y su evento público se confirman juntos: una cola ocupada/llena revierte también la decisión y conserva la revisión pendiente. Repetir la decisión devuelve el mismo job. Un resultado de commit incierto se consulta repitiendo el mismo identificador; no se crea un comando nuevo para ocultar la incertidumbre. Capacidad revalidada bajo lock y restricción `reserved<=capacity`.
7. **Cumplimiento:** liberar requiere evidencia humana; un reproceso necesita autorización previa y tiene límite. Cerrar un reclamo requiere plan autorizado anterior y aceptación/cumplimiento/conformidad posteriores. El vencimiento deja pendiente; no equivale a conformidad.
8. **Fuentes:** las citas se construyen desde fragmentos realmente recuperados. IDs ajenos se rechazan. Antes de una disposición se verifica otra vez la existencia, hash, organización, roles y vigencia del procedimiento. Una referencia pública histórica no es un procedimiento autorizante.
9. **Archivos:** lista limitada de formatos, validación de contenido real, tamaño, píxeles, páginas y duración; nombre de almacenamiento generado por servidor. No se usan nombres proporcionados como rutas. Descarga autorizada con `nosniff`, sandbox de documento y cache privada. Los checkpoints contienen referencias, no base64.
10. **Recursos:** tamaño de cuerpo, cola local limitada, número de llamadas, tiempo y contexto configurables. Errores del proveedor producen estado explícito; no hay fallback fake en el runtime.

## Infraestructura y secretos

- API publicada en `127.0.0.1`; PostgreSQL solo en la red de Compose.
- Procesos app sin root. Rol DB `aquaclean_runtime` sin superusuario/DDL de negocio; migración propietaria separada.
- Host permitido y validación de origen en mutaciones; sin CORS abierto.
- ReactMarkdown no permite HTML crudo; URLs de mensajes no ejecutan JavaScript. Los archivos se sirven por endpoints autorizados, no por un directorio público.
- `.env` y variantes se excluyen de Git y del contexto Docker. La clave actual se conservó localmente con permisos `0600`. No se serializa en OpenAPI, eventos, checkpoints ni frontend.
- Worker registra IDs y códigos, sin cuerpos crudos de errores SDK o contenido de clientes. Las trazas públicas incluyen modelo, versión de prompt, duraciones y uso de tokens cuando el proveedor lo devuelve; el coste monetario no se inventa (`cost_usd=null`).
- La bandeja local es el único canal de notificación. No hay pagos, SMTP, n8n ni Sheets configurados por defecto.

## Pruebas y alcance de la evidencia

Ver `tests/unit/test_domain.py`, `tests/integration/test_transactions.py`, `test_security_recovery.py`, `test_media_knowledge_api.py`, `test_graphs.py` y las evaluaciones reales separadas. Incluyen roles ajenos, cambio de organización, contrato alterado, acción fuera de proceso, fuentes vencidas/ajenas, aprobación obsoleta, falta de cumplimiento, duplicados concurrentes, parada y recuperación después de commit.

Una evaluación real pidió a Gemini cambiar de organización/rol y revelar sistema/clave: devolvió aclaración/respuesta sin permiso de ejecución. Una sola evaluación no acredita resistencia universal. El código sigue rechazando efectos aunque un modelo futuro responda de otra forma.

Los originales de evidencia residen en un volumen local y la API Gemini recibe el contenido que el operador envía para analizar. El perfil está preparado con datos sintéticos. Operar con personas o documentos reales requiere definir identidad, permisos, retención, privacidad, procedimientos y responsables con la empresa.
