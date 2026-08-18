---
name: sinpapel-transitions
description: Usar siempre que el usuario ejecute una transición de estado, llame transition() / available_transitions() / can_transition_to() / preview_transition(), maneje PermissionError o ValueError al transicionar, o use WorkflowEngine directamente. Cubre payload de firma (firma_payload), kwargs (comentarios, condiciones, ip_address) y la consulta del audit log SeguimientoWorkflow.
tested_against:
  - sinpapel==0.8.2
applies_to:
  - "**/views.py"
  - "**/services/**/*.py"
  - "**/api/**/*.py"
---

# Transiciones de estado en sinpapel

## El motor: `WorkflowEngine`

El servicio canónico es `sinpapel.services.workflow_engine.WorkflowEngine`.
Atómico (`transaction.atomic`): valida grupos, predicados, requisitos
documentales, ejecuta la transición, persiste `SeguimientoWorkflow` y
opcionalmente persiste `RegistroFirma`. Los **side effects corren después
del commit** de la transacción del motor (ver `sinpapel-side-effects`).

**Concurrencia segura (0.7.1):** dentro de la transacción, `cambiar_estado`
re-lee el row con `SELECT ... FOR UPDATE` y **revalida sobre el estado
fresco**. Dos transiciones concurrentes desde el mismo estado (o una copia
stale de la instancia, ej. doble-submit) ya no pueden pasar ambas la
validación: la segunda recibe `PermissionError`. No hay carrera
check-then-act.

**`WorkflowService` no existe.** Si ves código que lo importa, hay que
migrarlo a `WorkflowEngine`.

## Métodos inyectados en el modelo decorado

Después de `@workflow_enabled(...)`, el modelo expone:

```python
instance.available_transitions(user)              # list[Estado]
instance.can_transition_to(target_state, user)    # (bool, str | None)
instance.transition(target_state, user, **kwargs) # dict
instance.preview_transition(target_state, user)   # dict
```

`target_state` es el **nombre** del estado destino (ej. `"EN_REVISION"`),
no el id ni el objeto.

**`available_transitions` desde 0.7.1** filtra por el `VersionFlujo`
resuelto para la instancia y usa cache (antes devolvía transiciones de
**todos** los flujos con el mismo estado origen). Además, con
`SINPAPEL_ENFORCE_ESTADO_ACTIVO=True` (setting nuevo en 0.8.1, default
`False`), un `Estado.activo=False` no es destino válido y desaparece de
la lista.

## Flujo recomendado en una vista

```python
from django.http import JsonResponse
from sinpapel.exceptions import WorkflowConfigurationError

def avanzar_solicitud(request, pk):
    solicitud = Solicitud.objects.get(pk=pk)

    # 1) Preview (sin mutar nada)
    preview = solicitud.preview_transition("EN_REVISION", request.user)
    if not preview["permitido"]:
        return JsonResponse(
            {"error": preview["razones_bloqueo"]},
            status=400,
        )

    # 2) Ejecutar
    try:
        result = solicitud.transition(
            "EN_REVISION",
            request.user,
            comentarios="Pasa a revisión por monto bajo",
        )
    except PermissionError as exc:
        return JsonResponse({"error": str(exc)}, status=403)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    except WorkflowConfigurationError as exc:
        # El flujo está mal configurado (no es culpa del usuario): 500
        return JsonResponse({"error": str(exc)}, status=500)

    return JsonResponse(result, status=200)
```

## `kwargs` reconocidos por `transition()`

Los pasa el método inyectado al `WorkflowEngine`:

| kwarg | Tipo | Para qué |
|---|---|---|
| `comentarios` | `str` | Texto libre, se guarda en `SeguimientoWorkflow.comentarios`. |
| `condiciones` | `str` | Condiciones libres de la transición. |
| `ip_address` | `str` | IP del cliente. |
| `firma_payload` | `dict` | Payload de firma. Ver "Firma electrónica" abajo. |

Estos kwargs son los que el motor **conoce explícitamente**; ignora otros
silenciosamente. Si necesitas pasar metadata adicional, considera
`MetadatosCapturables` (`sinpapel-metadata`) o un side effect
(`sinpapel-side-effects`).

> **Breaking (sinpapel 0.7.0):** se eliminó el kwarg `monto_aprobado`
> (`transition()` / `WorkflowEngine.cambiar_estado()` ya no lo aceptan). Era un
> concepto de dominio filtrado en el framework genérico. Para datos de dominio
> usa `MetadatosCapturables`, o `condiciones` / `comentarios`.

## El `dict` que devuelve `transition()`

```python
{
    "success": True,
    "instance_id": 42,
    "estado_anterior": "CAPTURA",
    "estado_nuevo": "EN_REVISION",
    "seguimiento_id": 1834,
    # extra: lo que retorne el side effect, si existe
}
```

`seguimiento_id` es la PK del `SeguimientoWorkflow` recién creado.

## `preview_transition()` — el reporte

Devuelve un dict sin mutar nada (no ejecuta side effects ni firma):

```python
{
    "permitido": False,
    "razones_bloqueo": [{"tipo": "documento", "mensaje": "Falta el documento 'RFC' (requerido 100%, actual 0%)."}],
    "documentos_faltantes": [
        # Flag coarse Estado.expediente_obligatorio (sin tipo):
        {"tipo": "expediente", "mensaje": "Se requiere adjuntar al menos un documento..."},
        # Regla fina RequisitoEstadoDocumento (desde 0.6.0):
        {
            "tipo": "requisito_documento",
            "tipo_documento": "RFC",
            "porcentaje_requerido": 100,
            "porcentaje_actual": 0,
            "mensaje": "Falta el documento 'RFC' (requerido 100%, actual 0%).",
        },
    ],
    "predicados_fallidos": [...],
    "aprobadores_requeridos": [...],
    "side_effects": ["DISPERSADA"],   # nombres de handlers que se invocarían
    "firma_requerida": False,         # nueva key en 0.8.0
    "historial_reciente": [...],
}
```

**`firma_requerida` (0.8.0):** `True` si la `ConfiguracionTransicion` de la
arista tiene `requiere_firma=True`. Úsalo en la UI para pedir la firma
**antes** de ejecutar: `transition()` sin `firma_payload` lanzará
`PermissionError`.

**`historial_reciente` (fix 0.7.1):** ahora regresa contenido real — los
últimos 5 `SeguimientoWorkflow` de la instancia (antes SIEMPRE `[]` por un
bug de filtro sobre la GFK). Cada entrada trae `fecha`, `transicion`
(`"ORIGEN → DESTINO"`), `usuario` y `comentarios`.

**Desde sinpapel 0.6.0** los `RequisitoEstadoDocumento` del estado actual
**se enforcan** en la transición (antes solo se sembraban/exportaban). Cada
faltante fino agrega su entrada `requisito_documento` a `documentos_faltantes`
y pone `permitido=False`; el porcentaje actual sale del campo
`InstanciaDocumento.porcentaje` (default 100). Requisitos con `auto_carga=True`
(documento que genera el sistema) **no bloquean**. El flag coarse
`Estado.expediente_obligatorio` sigue produciendo la entrada `expediente`.
Detalle de modelado/semántica en `sinpapel-migrations-seeding`.

Como `cambiar_estado` delega en `puede_cambiar_estado`, **un requisito
documental no satisfecho hace que `transition()` lance `PermissionError`**
(con el `mensaje` del primer bloqueo), igual que un permiso o predicado
fallido.

Si `SINPAPEL_EMIT_PREVIEW_EVENTS=True`, además se dispara el signal
`transition_preview_requested` por cada preview.

## Excepciones que puede lanzar `transition()`

| Excepción | Significado | HTTP sugerido |
|---|---|---|
| `PermissionError` | Cualquier bloqueo de `puede_cambiar_estado`: el usuario no pertenece a ningún `grupos_permitidos`, un predicado falla, o (desde 0.6.0) falta un requisito documental. Lleva el `mensaje` del primer bloqueo. Desde 0.7.1 también: transición concurrente / copia stale (la revalidación bajo lock la rechaza). Desde 0.8.0 también: transición con `requiere_firma=True` sin `firma_payload`, o un `registro_firma_id` (Modo B) que no pasa las validaciones (ver abajo). | 403 |
| `ValueError` | El nombre del estado destino no es válido o no existe la transición desde el estado actual. | 400 |
| `sinpapel.signing.exceptions.SignatureValidationError` | El `firma_payload` no verifica. | 400 |
| `sinpapel.signing.exceptions.SignatureBackendNotConfiguredError` | `SINPAPEL_SIGNATURE_BACKEND` apunta a algo no importable. | 500 |
| `WorkflowConfigurationError` | El flujo está mal configurado (estados inactivos, sin aristas). | 500 |

`sinpapel-drf` ya mapea estas excepciones a códigos HTTP correctos. Si
escribes una vista propia, replica el mapeo.

## Firma electrónica en la transición

**`ConfiguracionTransicion.requiere_firma` (0.8.0, default `False`):** la
exigencia de firma vive en la configuración de la arista, no en la buena fe
del caller. Con `requiere_firma=True`, `transition()` sin `firma_payload`
lanza `PermissionError`, y `preview_transition()` lo anuncia con
`firma_requerida: True`.

Si la transición debe firmarse, pasa `firma_payload`. El motor soporta
dos modos (ver `WorkflowEngine.cambiar_estado` y `sinpapel-signing`):

**Modo A — el motor crea el `RegistroFirma` invocando el backend
configurado:**

```python
firma_payload = {
    "contenido": canonical_bytes,           # bytes que el cliente firmó
    "firma_b64": "...",                     # firma RSA-SHA256 base64
    "certificado_cer_b64": "...",           # certificado X.509 DER base64
}
```

Desde 0.8.0 el backend se resuelve vía `get_signature_backend()` (respeta
`SINPAPEL_SIGNATURE_BACKEND`) — **ya no** se instancia `FielBackend`
hardcodeado. Los kwargs extra del payload (todo lo que no sea `contenido`)
se pasan al backend.

**Modo B — el caller ya creó el `RegistroFirma`:**

```python
firma_payload = {"registro_firma_id": 17}
```

Desde 0.8.0 el motor **valida** el registro: debe existir, pertenecer al
usuario que transiciona (`signer == user`), estar en estado válido y NO
estar ya vinculado a otro `SeguimientoWorkflow`. Cada violación →
`PermissionError`.

Detalles en la skill `sinpapel-signing`.

## Consultar el historial: `SeguimientoWorkflow`

```python
from django.contrib.contenttypes.models import ContentType
from sinpapel.models import SeguimientoWorkflow

ct = ContentType.objects.get_for_model(Solicitud)
qs = SeguimientoWorkflow.objects.filter(
    target_content_type=ct,
    target_object_id=solicitud.pk,
).order_by("-fecha_accion")

for s in qs:
    print(s.fecha_accion, s.estado_anterior, "→", s.estado_nuevo, s.usuario_accion)
```

Cada `SeguimientoWorkflow` lleva:

- `estado_anterior` / `estado_nuevo`
- `usuario_accion`, `fecha_accion`
- `comentarios`, `condiciones`, `ip_address`
- `documentos_adjuntos` (JSONField)
- `firma_registro` (OneToOne nullable a `RegistroFirma`)

## Anti-patrones

- **No** uses `instance.estado = estado_nuevo; instance.save()` para
  cambiar de estado. Saltas validaciones, predicados, audit log, firma y
  side effects.
- **No** intentes "componer" varias transiciones en una sola llamada:
  ejecuta una por una para que el audit log sea fiel.
- **No** atrapes `Exception` genérico en la vista — pierdes el mapeo a
  códigos HTTP. Captura las excepciones específicas listadas arriba.
- **No** uses `preview_transition()` como sustituto de
  `can_transition_to()` en hot paths: hace más trabajo (incluye side
  effects esperados, historial).
- **No** llames `transition()` desde dentro de un side effect del propio
  motor: provoca recursión.
- **No** asumas que `seguimiento_id` se mantiene tras un rollback externo:
  si tu código wrappea el motor en una transacción exterior y luego
  revierte, todo el cambio se pierde — y además la garantía de que los
  side effects corren post-commit pasa a ser responsabilidad tuya (el
  "commit" del motor queda dentro de tu transacción).

## Patrón "preview → confirm" para UI

```python
# GET /solicitudes/<pk>/preview/?target=EN_REVISION
report = solicitud.preview_transition("EN_REVISION", request.user)

# Mostrar al usuario:
# - documentos faltantes (cargar antes)
# - aprobadores requeridos (notificar)
# - side effects esperados (advertir)
# - razones de bloqueo si aplica

# POST /solicitudes/<pk>/transition/  body={"target":"EN_REVISION", ...}
result = solicitud.transition("EN_REVISION", request.user, comentarios=...)
```

`sinpapel-drf` implementa exactamente este patrón (`POST /<slug>/<pk>/preview-transition/` + `POST /<slug>/<pk>/transition/`).

## Siguiente paso

- Para lógica post-transición: `sinpapel-side-effects`.
- Para reglas que bloquean: `sinpapel-predicates`.
- Para firma electrónica: `sinpapel-signing`.
