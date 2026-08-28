---
name: sinpapel-metadata
description: Usar siempre que el usuario capture metadatos estructurados por instancia, defina SCHEMA_METADATOS con CampoMetadato, herede de MetadatosCapturables, genere formularios o serializers DRF con MetaFormFactory, acceda a instance.meta, o pregunte cómo validar y serializar datos arbitrarios sin crear columnas físicas en el modelo.
tested_against:
  - sinpapel==0.8.3
applies_to:
  - "**/models.py"
  - "**/models/*.py"
---

# Metadatos estructurados

## Qué resuelve

Capturar datos por instancia sin crear columnas nuevas en cada migración
de dominio. Define el schema en código (`SCHEMA_METADATOS`) y el framework
te da formularios/serializers y validación.

Módulos:

- `sinpapel/mixins.py` — `MetadatosCapturables`, `CampoMetadato`,
  `MetadatosProxy`.
- `sinpapel/forms.py` — `MetaFormFactory.build_form()` y
  `MetaFormFactory.build_serializer()`.

## Modelar con `MetadatosCapturables`

```python
# tu_app/models.py
from decimal import Decimal
from django.db import models
from sinpapel import workflow_enabled
from sinpapel.mixins import CampoMetadato, MetadatosCapturables, Trazable

@workflow_enabled(state_field="estado", workflow_key="solicitud")
class Solicitud(MetadatosCapturables, Trazable):
    SCHEMA_METADATOS = [
        CampoMetadato(
            nombre="rfc",
            tipo=str,
            requerido=True,
            etiqueta="RFC",
            ayuda="13 caracteres alfanuméricos.",
        ),
        CampoMetadato(
            nombre="monto_solicitado",
            tipo=Decimal,
            requerido=True,
        ),
        CampoMetadato(
            nombre="nivel",
            tipo=str,
            choices=["A", "B", "C"],
            default="B",
        ),
    ]

    folio = models.CharField(max_length=50, unique=True)
    estado = models.ForeignKey("sinpapel.Estado", on_delete=models.PROTECT)
```

**`Trazable` no es opcional aquí.** `@workflow_enabled` valida en tiempo de
decoración que el modelo tenga el campo `actualizado` (el motor persiste la
transición con `save(update_fields=[state_field, "actualizado"])`). Un
`class Solicitud(MetadatosCapturables, models.Model)` sin `Trazable` lanza
`WorkflowConfigurationError` al importar el módulo.

## `CampoMetadato` — campos

| Campo | Tipo | Notas |
|---|---|---|
| `nombre` | `str` | Clave del valor. |
| `tipo` | `type` | `str`, `int`, `bool`, `Decimal`, `date`. |
| `requerido` | `bool` | Default `False`. |
| `default` | `Any \| None` | Valor inicial. |
| `choices` | `list \| None` | Lista de opciones permitidas. |
| `etiqueta` | `str` | Label legible. |
| `ayuda` | `str` | Help text. |

## Leer / escribir valores

`MetadatosCapturables` añade un proxy `.meta`. El acceso es **por atributo**
(`MetadatosProxy.__getattr__` / `__setattr__`); **no** es dict-like: no
implementa `__getitem__`, `__setitem__` ni `update()`.

```python
solicitud.meta.rfc = "ABCD010101ABC"
solicitud.meta.monto_solicitado = Decimal("150000.00")
solicitud.save()

print(solicitud.meta.to_dict())
# {'rfc': 'ABCD010101ABC', 'monto_solicitado': Decimal('150000.00'), 'nivel': 'B'}
```

La superficie del proxy es exactamente: acceso por atributo, `to_dict()` y
`errores()`. Verificado contra 0.8.3:

| Operación | Resultado |
|---|---|
| `meta.rfc = "ABC"` | asigna y valida |
| `meta.to_dict()` | dict con todo el schema (incluye defaults) |
| `meta["rfc"]` | `TypeError: 'MetadatosProxy' object is not subscriptable` |
| `meta.update({...})` | `AttributeError: Campo 'update' no definido en el schema` |
| key fuera del schema | `AttributeError: Campo 'X' no definido en el schema` |
| tipo equivocado | `TypeError: Campo 'rfc' espera str, recibió int` |
| valor fuera de `choices` | `ValueError: Campo 'nivel' solo acepta [...]` |

Los valores viven en el `JSONField` **`datos_capturados`**, declarado por el
propio mixin. `Decimal` se serializa como `str` y `date` como ISO-8601; el
proxy los reconstruye al leer.

`MetadatosCapturables.save()` llama a `clean()` en **cada** guardado, y
`clean()` levanta `ValidationError` si falta algún campo `requerido`. Ojo:
eso incluye el `save(update_fields=...)` que hace el motor al transicionar —
una instancia con metadatos requeridos vacíos no puede cambiar de estado.

## Generar Form / Serializer dinámicos

Ambos métodos reciben la **lista de `CampoMetadato`**, no la clase del modelo:

```python
MetaFormFactory.build_form(schema, name=None, **form_class_kwargs)
MetaFormFactory.build_serializer(schema, name=None, **serializer_class_kwargs)
```

```python
from sinpapel.forms import MetaFormFactory

# Para vistas Django:
FormCls = MetaFormFactory.build_form(Solicitud.SCHEMA_METADATOS)
form = FormCls(request.POST)
if form.is_valid():
    for nombre, valor in form.cleaned_data.items():
        setattr(solicitud.meta, nombre, valor)
    solicitud.save()

# Para DRF (lo usa sinpapel-drf):
SerializerCls = MetaFormFactory.build_serializer(Solicitud.SCHEMA_METADATOS)
serializer = SerializerCls(data=request.data, partial=True)
serializer.is_valid(raise_exception=True)
for nombre, valor in serializer.validated_data.items():
    setattr(solicitud.meta, nombre, valor)
solicitud.save()
```

El proxy no tiene `update()`: asigna campo por campo con `setattr` (o por
atributo directo). Cada asignación valida contra el schema.

**`.meta` construye un `MetadatosProxy` nuevo en cada acceso** (es una
`property`). Escribe sobre una variable local si vas a asignar varios campos
en un bucle, o asigna siempre vía `solicitud.meta.<campo>` como arriba —
cada `__setattr__` reescribe `instance.datos_capturados` completo.

`build_form` / `build_serializer` **no** cachean: cada llamada construye una
clase nueva con `type()`. Si generas formularios en un hot path, cachea tú
el resultado.

## Acceder al schema desde otra capa

```python
schema = Solicitud.SCHEMA_METADATOS    # list[CampoMetadato]
for campo in schema:
    print(campo.nombre, campo.tipo, campo.requerido)
```

`sinpapel-drf` expone el schema en `GET /<slug>/<pk>/metadatos/`:

```json
{
  "schema": [
    {"nombre": "rfc", "tipo": "str", "requerido": true, "etiqueta": "RFC", ...}
  ],
  "values": {"rfc": "ABCD010101ABC"}
}
```

## Uso en predicados

Los valores `meta` están disponibles para JSON Logic:

```json
{"rule": {">=": [{"var": "meta.monto_solicitado"}, 100000]}}
```

Y para `python_path` (vía el `**context` del predicado, que incluye
`instance.meta`).

## Anti-patrones

- **No** uses `MetadatosCapturables` para datos que ya son campos del
  modelo (`monto`, `folio`): pierde validación, índices y queryability.
  Si vas a hacer queries por un campo, declara una columna real.
- **No** cambies el schema sin migración de datos: instancias viejas pueden
  tener keys obsoletas o faltar las nuevas. Si añades un campo `requerido`,
  agrega una data migration que rellene un valor por default.
- **No** uses sintaxis de diccionario: el proxy no la implementa.
  `instance.meta["x"]` lanza `TypeError` (no es subscriptable) y
  `instance.meta.update(...)` lanza `AttributeError`. Usa acceso por
  atributo, o `to_dict().get("x")` para leer algo que puede no estar
  seteado.
- **No** pases la clase del modelo a `MetaFormFactory.build_form()`: espera
  la lista `SCHEMA_METADATOS`.
- **No** mezcles distintos `tipo` para la misma key entre versiones:
  rompe deserialización antigua.
- **No** uses `tipo=dict` o `tipo=list`: el factory soporta tipos
  escalares; estructuras anidadas debería ser un modelo aparte.

## Migrar valores existentes

```python
# tu_app/migrations/0005_backfill_meta.py
def backfill(apps, schema_editor):
    Solicitud = apps.get_model("tu_app", "Solicitud")
    for s in Solicitud.objects.all():
        meta = s.metadatos or {}            # o como esté tu JSONField subyacente
        if "nivel" not in meta:
            meta["nivel"] = "B"
            s.metadatos = meta
            s.save(update_fields=["metadatos"])
```

(El nombre del JSONField subyacente lo gestiona `MetadatosCapturables`;
revisa el modelo concreto antes de manipularlo en migrations.)

## Siguiente paso

- Para reglas que dependen del `meta`: `sinpapel-predicates` (JSON Logic).
- Para exponer el schema vía API: `sinpapel-drf` (endpoint `metadatos`).
