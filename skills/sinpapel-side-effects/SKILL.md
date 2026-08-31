---
name: sinpapel-side-effects
description: Usar siempre que el usuario quiera ejecutar lógica adicional tras una transición de sinpapel (notificaciones, generación de oficios, integración con sistemas externos, llamadas a otros servicios), genere un documento al entrar a un estado (InstanciaDocumento.archivo_generado, auto_carga), use el decorador register_side_effect, registre handlers en AppConfig.ready(), o pregunte qué pasa si un handler falla, cuándo se ejecuta y cómo afecta a la atomicidad de la transición.
tested_against:
  - sinpapel==0.8.4
applies_to:
  - "**/apps.py"
  - "**/side_effects.py"
  - "**/services/side_effects*.py"
---

# Side effects en transiciones

## Qué es un side effect

Una función que `WorkflowEngine` invoca **después del commit** de la
transacción de la transición (estado + `SeguimientoWorkflow` ya
persistidos), **antes** de devolver el resultado. Está pensado para tareas
asociadas al estado **destino**: generar un oficio, enviar email, encolar
una tarea Celery, llamar a un servicio externo.

Implementado en `sinpapel/services/side_effects.py`: decorador
`register_side_effect`, registro global `SIDE_EFFECTS`, registro por flujo
`SIDE_EFFECTS_SCOPED` (0.8.1) y resolutor `resolver_handler`.

## Registrar un handler

```python
# tu_app/side_effects.py
from sinpapel.services.side_effects import register_side_effect

@register_side_effect("APROBADA")
def on_aprobada(instance, user, **kwargs):
    """Handler que se invoca al entrar al estado APROBADA."""
    # Para datos de dominio usa metadatos de la instancia (sinpapel-metadata);
    # los comentarios de la transición ya están persistidos en el
    # SeguimientoWorkflow más reciente de la instancia.
    oficio = generar_oficio(instance)
    enviar_email_notificacion(instance, oficio)
    return {"oficio_id": oficio.id}   # se incluye en el dict de transition()
```

### Scoping por flujo (0.8.1)

Dos flujos con un estado homónimo pueden tener handlers distintos:

```python
@register_side_effect("DISPERSADA")                      # global: cualquier flujo
def _global(instance, user, **kwargs): ...

@register_side_effect("DISPERSADA", workflow_key="pyme") # solo el flujo "pyme"
def _pyme(instance, user, **kwargs): ...
```

En el dispatch, el handler **scoped tiene precedencia** sobre el global
homónimo. El registro global sigue funcionando igual (compat). El resolutor
público es `resolver_handler(estado_nombre, workflow_key)`: scoped primero,
global después; los scoped viven en el dict
`SIDE_EFFECTS_SCOPED[(workflow_key, estado_nombre)]`.

**Reglas:**

- La clave es el `nombre` del estado **destino**, exactamente como está en
  `Estado.nombre` (case-sensitive).
- Solo se permite **un** handler global por estado y **uno** scoped por
  `(workflow_key, estado)`. Registrar dos veces sobrescribe.
- La firma es `(instance, user, **kwargs)`. Ojo (verificado en 0.8.1): al
  despachar desde `transition()`, el motor actualmente **no reenvía** los
  kwargs de la transición (`comentarios`, `condiciones`, `ip_address`) al
  handler; si los necesitas, léelos del `SeguimientoWorkflow` más reciente
  de la instancia. (`ejecutar_side_effects` sí propaga `**kwargs` cuando se
  invoca directo.) *(sinpapel 0.7.0 eliminó `monto_aprobado`; usa metadatos
  para datos de dominio.)*
- Si retornas un `dict`, sus keys se fusionan en el `dict` que devuelve
  `transition()`. Si no retornas nada, queda `{}`.
- El handler debe ser **idempotente** (o tolerar reintentos externos):
  corre fuera de la transacción del motor, ya sin posibilidad de rollback.

## Registro de los handlers (cuándo se importan)

Los handlers deben estar registrados **antes** de que se invoque la
primera transición. El patrón canónico es importarlos en `AppConfig.ready()`:

```python
# tu_app/apps.py
from django.apps import AppConfig

class TuAppConfig(AppConfig):
    name = "tu_app"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        # Importa el módulo para ejecutar el decorador register_side_effect
        from . import side_effects  # noqa: F401
```

Sin esto, el handler **no existe** para el motor y la transición se
ejecuta sin él (silenciosamente).

## Comportamiento ante errores

Si el handler lanza una excepción:

- El error se **logea** pero **no se re-lanza** (ADR-004).
- La transición ya commiteó atómicamente (estado + `SeguimientoWorkflow`)
  **antes** de invocar el handler.
- El `dict` devuelto incluye `{"error": True, "estado": "<destino>"}` en
  lugar de los datos del handler.

**Implicación:** un side effect que falla **no** revierte el cambio de
estado — no "porque el motor atrapa la excepción dentro de la transacción",
sino porque la transición **ya persistió** cuando el handler corre. Si
necesitas atomicidad estricta entre estado y efecto, ejecuta la lógica
**antes** de transicionar (en un predicado o en la vista) y **no** la
pongas como side effect.

## Atomicidad: el handler corre POST-commit

Desde sinpapel 0.7.1 (ADR-004 corregido), los side effects corren
**después** de que la transacción del motor commiteó — antes corrían
dentro de ella:

```
┌── transaction.atomic ──────────────────────────────┐
│  0. SELECT ... FOR UPDATE + revalidación           │
│  1. validate (grupos, predicados, requisitos)      │
│  2. RegistroFirma (si firma_payload)               │
│  3. SeguimientoWorkflow.objects.create(...)        │
│  4. instance.estado = nuevo; instance.save()       │
└────────────── COMMIT ──────────────────────────────┘
   5. side_effect(instance, user, **kwargs) ← AQUÍ (post-commit)
```

Ventaja: un handler fallido nunca puede dejar efectos externos de una
transición que hizo rollback. Contrapartida: el handler **no puede**
revertir la transición de ninguna forma (`transaction.set_rollback` ya no
aplica: no hay transacción del motor abierta).

Excepción: si el **caller** envuelve `transition()` en su propia
transacción exterior, el "commit" del motor queda dentro de ella y la
garantía post-commit pasa a ser responsabilidad del caller.

La lógica crítica va como **predicado** (bloquea antes); deja los side
effects para lo no-bloqueante (notificar, encolar). Y como el handler puede
reintentar tras un fallo parcial, hazlo **idempotente**.

## Ejemplos típicos

### Enviar email tras aprobar

```python
@register_side_effect("APROBADA")
def notificar_aprobacion(instance, user, **kwargs):
    send_mail(
        subject=f"Solicitud {instance.folio} aprobada",
        message="...",
        from_email="no-reply@tudominio.com",
        recipient_list=[instance.solicitante.email],
        fail_silently=True,  # no rompas la transición por SMTP caído
    )
    return {"email_enviado": True}
```

### Encolar tarea Celery

```python
@register_side_effect("EN_DISPERSION")
def encolar_dispersion(instance, user, **kwargs):
    from tu_app.tasks import dispersar_pago
    task = dispersar_pago.delay(instance.pk)
    return {"task_id": task.id}
```

### Llamar a un servicio externo

```python
@register_side_effect("PUBLICADA")
def publicar_en_portal(instance, user, **kwargs):
    try:
        resp = requests.post(PORTAL_URL, json=serialize(instance), timeout=5)
        return {"portal_status": resp.status_code}
    except requests.RequestException as exc:
        # El error se logea por el motor; devolvemos info para diagnóstico.
        return {"portal_error": str(exc)}
```

### Generar un documento al entrar a un estado (`archivo_generado`)

sinpapel distingue **dos tipos** de documento, ambos en `InstanciaDocumento`
(`sinpapel/models/documents.py`):

| Campo | Tipo | Quién lo pone |
|---|---|---|
| `archivo` | **Requisito documental** — lo sube el usuario para satisfacer un `RequisitoEstadoDocumento`. | Usuario |
| `archivo_generado` | **Documento producido por el sistema** (`documentos_generados/`) al entrar a un estado. | Sistema |

El **documento generado** se produce en un **side effect** del estado destino
— **no** en una señal de Django. (sinpapel tiene señales —`predicate_failed`,
`sla_breached`, `transition_preview_requested`— pero ninguna se dispara
genéricamente "al entrar a un estado"; ese trigger es el side effect, cuya
clave es el `Estado.nombre` destino.)

```python
# tu_app/side_effects.py
from django.contrib.contenttypes.models import ContentType
from sinpapel.services.side_effects import register_side_effect
from sinpapel.models import Documento, InstanciaDocumento

@register_side_effect("APROBADA")        # se dispara al ENTRAR a este estado
def generar_oficio(instance, user, **kwargs):
    plantilla = Documento.objects.get(valor="OFICIO_APROBACION")
    archivo = render_plantilla(plantilla, instance)   # ← tu render DOCX/PDF
    ct = ContentType.objects.get_for_model(type(instance))
    inst_doc = InstanciaDocumento.objects.create(
        documento=plantilla,
        target_content_type=ct,
        target_object_id=instance.pk,
        archivo_generado=archivo,        # ← documento del sistema, NO archivo
        porcentaje=100,
        autor=user, modificador=user,
    )
    return {"instancia_documento_id": inst_doc.id}
```

**El núcleo NO renderiza plantillas.** `Documento` describe la plantilla
(`plantilla` FileField, `contenido`, `tipo_plantilla` DOCX/PDF,
`configuracion_overlay`), pero el render corre dentro del side effect. Dos
opciones:

1. **`sinpapel-reports` (recomendado):** `ReportEngine.generar(plantilla,
   instance, actor=user)` renderiza (PDF overlay o DOCX) **y** persiste la
   `InstanciaDocumento` con `archivo_generado` atómicamente — sustituye todo
   el bloque `render_plantilla` + `InstanciaDocumento.objects.create` del
   ejemplo. Ver la skill `sinpapel-reports`.
2. **Render propio:** como en el ejemplo, tú produces el archivo y creas la
   instancia; sinpapel solo persiste el resultado en `archivo_generado`.

Si el render es lento, encólalo (Celery) y retorna rápido — recuerda que un
fallo del side effect **no** revierte la transición.

**Conexión con `auto_carga`:** si ese documento generado además es un
**requisito** de un estado posterior, decláralo como `RequisitoEstadoDocumento`
con `auto_carga=True`. Así no bloquea al usuario (lo produce el sistema) pero
queda modelado como requisito — el motor lo da por satisfecho
(`satisfecho = requisito.auto_carga or porcentaje_actual >= requisito.porcentaje`).
El side effect lo genera; el `auto_carga=True` evita que su ausencia bloquee
las transiciones. Ver `sinpapel-migrations-seeding` para el modelado de
`RequisitoEstadoDocumento`.

## Side effects y previsualización

`preview_transition()` **no** ejecuta side effects. En su lugar, devuelve
en `report["side_effects"]` la lista de nombres de handlers que se
invocarían. Útil para advertir al usuario antes de confirmar.

## Anti-patrones

- **No** levantes excepciones para abortar la transición desde un side
  effect: la transición ya commiteó cuando el handler corre; el motor solo
  logea la excepción.
- **No** llames `instance.transition(...)` recursivamente desde un side
  effect: provoca recursión.
- **No** registres handlers en el `__init__.py` de la app: usa
  `AppConfig.ready()`. El orden de imports no está garantizado fuera de
  ahí.
- **No** asumas que el handler corre dentro de la transacción: desde 0.7.1
  corre **después** del commit. Aun así, el caller espera la respuesta de
  `transition()`: si tu lógica hace I/O lento (HTTP, email), considera
  encolar y retornar rápido.
- **No** registres dos handlers para el mismo estado en el mismo scope
  (global o mismo `workflow_key`): el último gana. Un scoped y un global
  homónimos sí conviven — gana el scoped para su flujo.
- **No** escribas handlers no idempotentes: la transición persistió aunque
  el handler falle, así que el reintento llega por fuera (reejecución
  manual, cola, etc.).
- **No** uses el side effect para validar: usa **predicados**
  (`sinpapel-predicates`). Los predicados sí bloquean.
- **No** olvides el `noqa: F401` en el import dentro de `ready()`: los
  linters lo marcan como import sin uso, pero el side effect existe en
  el import en sí.

## Verificar que están registrados

```python
from sinpapel.services.side_effects import (
    SIDE_EFFECTS, SIDE_EFFECTS_SCOPED, resolver_handler,
)
print(list(SIDE_EFFECTS.keys()))          # ['APROBADA', 'EN_DISPERSION', ...]
print(list(SIDE_EFFECTS_SCOPED.keys()))   # [('pyme', 'DISPERSADA'), ...]
resolver_handler("DISPERSADA", "pyme")    # el handler que aplicaría (o None)
```

## Siguiente paso

- Para bloqueos previos a la transición: `sinpapel-predicates`.
- Para webhooks como side effect canónico: `sinpapel-webhooks`.
