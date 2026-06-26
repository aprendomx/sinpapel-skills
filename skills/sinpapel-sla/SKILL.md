---
name: sinpapel-sla
description: Usar siempre que el usuario defina tiempos máximos por estado, escalamiento o alertas de vencimiento; use SLAConfiguracion, SLAEngine, las acciones notificar / escalar / rechazar / alertar, el comando sinpapel_verificar_slas, o los signals sla_breached y sla_action_executed. Cubre cómo configurar el cron, el dry-run y la integración con webhooks/notificaciones.
tested_against:
  - sinpapel==0.6.0
applies_to:
  - "**/migrations/*seed*sla*.py"
---

# SLAs en sinpapel

## Concepto

Una `SLAConfiguracion` define cuánto tiempo puede una instancia permanecer
en un estado dado antes de disparar una **acción**. Lo evalúa `SLAEngine`
en un cron periódico (no es event-driven: lo dispara un comando o tarea
programada).

Módulos:

- Modelo: `sinpapel/models/sla.py` (`SLAConfiguracion`).
- Motor: `sinpapel/services/sla_engine.py` (`SLAEngine`).
- Comando: `python manage.py sinpapel_verificar_slas`.
- Signals: `sla_breached`, `sla_action_executed` (en `sinpapel.signals`).

## El modelo `SLAConfiguracion`

| Campo | Tipo | Notas |
|---|---|---|
| `estado` | `FK(Estado)` | Estado al que aplica. |
| `dias_maximos` | `IntegerField` | Cuántos días máximo en el estado. |
| `accion_vencimiento` | `CharField` | `"notificar"`, `"escalar"`, `"rechazar"`, `"alertar"`. |
| `configuracion_accion` | `JSONField` | Parámetros de la acción (ver abajo). |
| `activo` | `BooleanField` | Si `False`, no se evalúa. |

## Acciones (`accion_vencimiento`)

| Acción | Qué hace |
|---|---|
| `notificar` | Envía notificación (email/webhook) al grupo configurado. No muta estado. |
| `escalar` | Cambia el estado al `estado_destino` definido en `configuracion_accion`. Equivale a una transición automatizada. |
| `rechazar` | Cambia al estado de rechazo configurado. Transición automatizada. |
| `alertar` | Marca/logea (estado **no muta**). Útil para dashboards. |

`configuracion_accion` típico:

```json
{
  "grupo_id": 1,
  "template": "expiration.html",
  "estado_destino": "RECHAZADA_POR_VENCIMIENTO"
}
```

Las keys exactas dependen de la acción. Consulta
`sinpapel/services/sla_engine.py` (`_accion_notificar`, `_accion_escalar`,
`_accion_rechazar`, `_accion_alertar`) para el contrato actual.

## Evaluar SLAs

### Por instancia

```python
from sinpapel.services.sla_engine import SLAEngine

acciones = SLAEngine.evaluar_instancia(solicitud)
# → lista de strings con las acciones ejecutadas
```

`evaluar_instancia` resuelve cuántos días lleva la instancia en su estado
(consultando `SeguimientoWorkflow`) y ejecuta las acciones cuya fecha
haya vencido.

### Masivamente (todos los `SLAConfiguracion` activos)

```bash
python manage.py sinpapel_verificar_slas
python manage.py sinpapel_verificar_slas --dry-run   # no ejecuta acciones, solo reporta
```

Programa este comando en un cron (típico: cada hora). En entornos serios,
considera `celery beat` u otro scheduler.

## Signals

```python
from django.dispatch import receiver
from sinpapel.signals import sla_breached, sla_action_executed

@receiver(sla_breached)
def on_breach(sender, target, sla, dias_transcurridos, **kwargs):
    # Métricas, logs, alertas.
    ...

@receiver(sla_action_executed)
def on_action(sender, target, sla, accion, resultado, **kwargs):
    # Confirmación tras la acción.
    ...
```

`sinpapel-webhooks` ya emite ambos signals como webhooks
(`sla.breached`, `sla.action.executed`).

## Sembrar un SLA

```python
# tu_app/migrations/0004_seed_sla.py
def seed(apps, schema_editor):
    Estado = apps.get_model("sinpapel", "Estado")
    SLA = apps.get_model("sinpapel", "SLAConfiguracion")

    en_revision = Estado.objects.get(nombre="EN_REVISION")
    SLA.objects.create(
        estado=en_revision,
        dias_maximos=3,
        accion_vencimiento="notificar",
        configuracion_accion={"grupo_id": 1, "template": "expiration.html"},
        activo=True,
    )
```

## Endpoint REST

`sinpapel-drf` expone CRUD admin (`/slas/`), evaluación masiva
(`POST /slas/verificar/`) y estado por instancia
(`POST /<slug>/<pk>/sla-status/`). Ver `sinpapel-drf`.

## Anti-patrones

- **No** uses `accion_vencimiento="escalar"` sin verificar que existe la
  `ConfiguracionTransicion` desde el estado actual al destino: el motor
  fallará la transición.
- **No** pongas `dias_maximos=0` salvo en pruebas: provoca falsos
  positivos en cada ejecución del cron.
- **No** ejecutes `sinpapel_verificar_slas` dentro de un request
  síncrono: puede ser lento. Úsalo desde cron/Celery.
- **No** asumas que la acción es transaccional con el cron: si un
  `escalar` falla por un predicado bloqueante, la acción no se ejecuta
  (queda registrada como fallo).
- **No** dupliques `SLAConfiguracion` activos para el mismo estado: se
  evalúan ambos. Usa uno único por (estado, escenario) o desactiva el
  redundante.

## Patrón de operación

1. Sembrar SLAs en una data migration por estado relevante.
2. Programar `sinpapel_verificar_slas` cada hora (cron / Celery beat).
3. Conectar `sla_breached` y `sla_action_executed` a tu logging /
   métricas.
4. (Opcional) Suscribir `sinpapel-webhooks` a `sla.breached` para enviar
   alertas a sistemas externos.

## Siguiente paso

- Programación de la tarea: combina con tu orquestador.
- Para acción tipo "notificar": considera `sinpapel-webhooks` como
  transporte.
