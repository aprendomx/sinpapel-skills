---
name: sinpapel-transitions
description: Usar siempre que el usuario ejecute una transición de estado, llame transition() / available_transitions() / can_transition_to() / preview_transition(), maneje PermissionError o ValueError al transicionar, o use WorkflowEngine directamente. Cubre payload de firma (firma_payload), kwargs (comentarios, monto_aprobado, condiciones, ip_address) y la consulta del audit log SeguimientoWorkflow.
tested_against:
  - sinpapel==0.5.1
applies_to:
  - "**/views.py"
  - "**/services/**/*.py"
  - "**/api/**/*.py"
---

# Transiciones de estado en sinpapel

## El motor: `WorkflowEngine`

El servicio canónico es `sinpapel.services.workflow_engine.WorkflowEngine`.
Atómico (`@transaction.atomic`): valida grupos, predicados, requisitos
documentales, ejecuta la transición, persiste `SeguimientoWorkflow`,
ejecuta side effects y opcionalmente persiste `RegistroFirma`.

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
| `monto_aprobado` | `Decimal` | Si la transición aprueba un monto. |
| `condiciones` | `str` | Condiciones libres de la transición. |
| `ip_address` | `str` | IP del cliente. |
| `firma_payload` | `dict` | Payload de firma. Ver "Firma electrónica" abajo. |

Estos kwargs son los que el motor **conoce explícitamente**; ignora otros
silenciosamente. Si necesitas pasar metadata adicional, considera
`MetadatosCapturables` (`sinpapel-metadata`) o un side effect
(`sinpapel-side-effects`).

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
    "razones_bloqueo": [{"tipo": "predicado", "mensaje": "Monto < $100,000"}],
    "documentos_faltantes": [{"tipo_documento": "RFC", "porcentaje": 100}],
    "predicados_fallidos": [...],
    "aprobadores_requeridos": [...],
    "side_effects": ["DISPERSADA"],   # nombres de handlers que se invocarían
    "historial_reciente": [...],
}
```

Si `SINPAPEL_EMIT_PREVIEW_EVENTS=True`, además se dispara el signal
`transition_preview_requested` por cada preview.

## Excepciones que puede lanzar `transition()`

| Excepción | Significado | HTTP sugerido |
|---|---|---|
| `PermissionError` | El usuario no pertenece a ningún `grupos_permitidos` de esa transición. | 403 |
| `ValueError` | El nombre del estado destino no es válido, no existe la transición desde el estado actual, o falta un requisito. | 400 |
| `sinpapel.signing.exceptions.SignatureValidationError` | El `firma_payload` no verifica. | 400 |
| `sinpapel.signing.exceptions.SignatureBackendNotConfiguredError` | `SINPAPEL_SIGNATURE_BACKEND` apunta a algo no importable. | 500 |
| `WorkflowConfigurationError` | El flujo está mal configurado (estados inactivos, sin aristas). | 500 |

`sinpapel-drf` ya mapea estas excepciones a códigos HTTP correctos. Si
escribes una vista propia, replica el mapeo.

## Firma electrónica en la transición

Si la transición debe firmarse, pasa `firma_payload`. El motor soporta
dos formas (ver `WorkflowEngine.cambiar_estado` y `sinpapel-signing`):

**Forma A — el caller ya creó el `RegistroFirma`:**

```python
firma_payload = {"registro_firma_id": 17}
```

**Forma B — el motor crea el `RegistroFirma` invocando `FielBackend`
(Modo A, client-side):**

```python
firma_payload = {
    "contenido": canonical_bytes,           # bytes que el cliente firmó
    "firma_b64": "...",                     # firma RSA-SHA256 base64
    "certificado_cer_b64": "...",           # certificado X.509 DER base64
}
```

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
- `comentarios`, `monto_aprobado`, `condiciones`, `ip_address`
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
  si tu código wrappea el motor en una transacción y luego revierte,
  obviamente todo el cambio se pierde.

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
