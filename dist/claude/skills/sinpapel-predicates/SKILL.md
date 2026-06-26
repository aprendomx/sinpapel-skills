---
name: sinpapel-predicates
description: Usar siempre que el usuario defina reglas de negocio que bloqueen una transición (montos, fechas, validaciones cruzadas), use CondicionTransicion, PredicateEngine, los backends python_path / json_logic / django_orm, o vea el signal predicate_failed. Cubre cómo configurar SINPAPEL_PREDICATE_MODULES como whitelist de seguridad y el JSON Logic restringido del framework.
tested_against:
  - sinpapel==0.6.0
applies_to:
  - "**/predicates.py"
  - "**/migrations/*seed*predicates*.py"
---

# Predicados de transición

## Qué son

Reglas evaluadas **antes** de cambiar de estado. Si fallan, `transition()`
lanza `ValueError` (mapeable a 400). Se modelan como filas en
`sinpapel.models.CondicionTransicion`, una por arista de transición.

Implementación: `sinpapel/services/predicate_engine.py`. El modelo está
en `sinpapel/models/predicates.py` (re-exportado en `sinpapel.models`).

## El modelo `CondicionTransicion`

| Campo | Tipo | Notas |
|---|---|---|
| `transicion` | `FK(ConfiguracionTransicion)` | A qué arista pertenece. |
| `tipo` | `CharField` | Uno de: `"python_path"`, `"json_logic"`, `"django_orm"`. |
| `configuracion` | `JSONField` | Datos específicos del backend (ver abajo). |
| `mensaje_error` | `TextField` | Lo que ve el usuario si falla. |
| `orden` | `IntegerField` | Orden de evaluación (asc). |
| `activo` | `BooleanField` | Si `False`, no se evalúa. |

Con `HistoricalRecords` (auditable).

## Los 3 backends de `PredicateEngine`

### `python_path`

Apunta a un callable que devuelve `bool` (o levanta `ValueError`).

```python
# configuracion JSONField:
{"path": "tu_app.predicates.monto_minimo_aprobado"}

# tu_app/predicates.py
def monto_minimo_aprobado(instance, user, target_state, **context):
    return instance.monto >= 100_000
```

**Seguridad — `SINPAPEL_PREDICATE_MODULES`**: el motor importa solamente
módulos cuya raíz está en la whitelist. Sin esa whitelist (`None` por
default), el backend `python_path` **rechaza todo**.

```python
# settings.py
SINPAPEL_PREDICATE_MODULES = ["tu_app.predicates", "otra_app.rules"]
```

### `json_logic`

Evaluador JSON Logic **restringido** (solo operadores seguros, sin acceso
a funciones del host). Implementado en `sinpapel/json_logic.py`.

```python
# configuracion JSONField:
{
  "rule": {
    ">=": [{"var": "meta.monto_solicitado"}, 100000]
  }
}
```

Variables disponibles:

- `instance.<field>` — campos del modelo (incluye `estado.nombre`).
- `meta.<key>` — metadatos capturados (`MetadatosCapturables`).
- `target_state` — el nombre del estado destino.
- `user.id`, `user.username` — usuario que ejecuta.

### `django_orm`

Ejecuta un `.exists()` sobre un QuerySet declarativo.

```python
# configuracion JSONField:
{
  "model": "tu_app.Documento",
  "filter": {
    "solicitud_id": "{instance.pk}",
    "tipo__nombre": "RFC",
    "verificado": true
  },
  "expect": "exists"           # o "not_exists"
}
```

El placeholder `{instance.pk}` se sustituye en runtime con el campo
correspondiente.

## Cómo se invocan

El motor las evalúa automáticamente en `puede_cambiar_estado()` y antes
de mutar el estado en `cambiar_estado()`. Si una falla:

- `preview_transition()` retorna `permitido=False`,
  `predicados_fallidos=[{...}]`, y `razones_bloqueo`.
- `transition()` lanza `ValueError(predicado.mensaje_error)` y dispara el
  signal `predicate_failed`.

## Sembrar predicados

Igual que cualquier otra config del flujo: data migrations
(`sinpapel-migrations-seeding`).

```python
# tu_app/migrations/0003_seed_predicado.py
def seed(apps, schema_editor):
    Cond = apps.get_model("sinpapel", "CondicionTransicion")
    CT = apps.get_model("sinpapel", "ConfiguracionTransicion")

    transicion = CT.objects.get(
        flujo__nombre="solicitudes",
        estado_origen__nombre="EN_REVISION",
        estado_destino__nombre="APROBADA",
    )
    Cond.objects.create(
        transicion=transicion,
        tipo="json_logic",
        configuracion={"rule": {">=": [{"var": "instance.monto"}, 100000]}},
        mensaje_error="El monto debe ser mayor o igual a $100,000",
        orden=1,
        activo=True,
    )
```

## Reaccionar a un predicado fallido (signal)

```python
from django.dispatch import receiver
from sinpapel.signals import predicate_failed

@receiver(predicate_failed)
def on_predicate_failed(sender, target, condicion, user, target_state, **kwargs):
    # logear, registrar métrica, notificar, etc.
    ...
```

## Anti-patrones

- **No** uses `python_path` sin configurar `SINPAPEL_PREDICATE_MODULES`:
  no se cargará nada y todas las transiciones quedarán bloqueadas (o se
  caerán con error de configuración, según versión).
- **No** importes `os`, `subprocess`, lectura de archivos u operaciones
  pesadas dentro de un predicado: corre dentro de la transacción y se
  evalúa en cada `transition()` y cada `preview_transition()`.
- **No** dependas del orden de evaluación entre tipos distintos: ordena
  con el campo `orden` y mantén consistencia.
- **No** mezcles validación de **datos** con predicados: la validación de
  campos va en `clean()` / `MetadatosCapturables`. Los predicados son
  reglas de **transición**.
- **No** uses JSON Logic para algo que requiera lookups en BD: usa
  `django_orm`.
- **No** olvides el `mensaje_error`: es lo que ve el usuario. "false" o
  cadena vacía hace inutilizable la UI.

## Patrón: predicados compuestos

Si necesitas "A y B y C", crea **tres** filas con orden 1, 2, 3 — son
AND implícito. Para "A o B", combínalo dentro de un único JSON Logic
con `{"or": [...]}`.

## Verificar predicados desde un test

```python
from sinpapel.services.workflow_engine import WorkflowEngine

engine = WorkflowEngine()
puede, mensaje = engine.puede_cambiar_estado(
    instancia, "APROBADA", user
)
assert puede is False
assert "monto" in mensaje.lower()
```

## Siguiente paso

- Si quieres validar **metadatos** (no transición): `sinpapel-metadata`.
- Si quieres reglas temporales (vencimientos): `sinpapel-sla`.
