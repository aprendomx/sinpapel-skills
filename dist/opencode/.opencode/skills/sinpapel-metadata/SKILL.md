---
name: sinpapel-metadata
description: Usar siempre que el usuario capture metadatos estructurados por instancia, defina SCHEMA_METADATOS con CampoMetadato, herede de MetadatosCapturables, genere formularios o serializers DRF con MetaFormFactory, acceda a instance.meta, o pregunte cómo validar y serializar datos arbitrarios sin crear columnas físicas en el modelo.
tested_against:
  - sinpapel==0.7.0
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
from sinpapel.mixins import MetadatosCapturables, CampoMetadato

@workflow_enabled(state_field="estado", workflow_key="solicitud")
class Solicitud(MetadatosCapturables, models.Model):
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

`MetadatosCapturables` añade un proxy `.meta`:

```python
solicitud.meta["rfc"] = "ABCD010101ABC"
solicitud.meta["monto_solicitado"] = Decimal("150000.00")
solicitud.save()

print(solicitud.meta.to_dict())
# {'rfc': 'ABCD010101ABC', 'monto_solicitado': Decimal('150000.00'), 'nivel': 'B'}
```

Internamente se guardan en un único `JSONField`. La validación contra el
schema corre al asignar y al construir Form/Serializer.

## Generar Form / Serializer dinámicos

```python
from sinpapel.forms import MetaFormFactory

# Para vistas Django:
FormCls = MetaFormFactory.build_form(Solicitud)
form = FormCls(request.POST)
if form.is_valid():
    solicitud.meta.update(form.cleaned_data)
    solicitud.save()

# Para DRF (lo usa sinpapel-drf):
SerializerCls = MetaFormFactory.build_serializer(Solicitud)
serializer = SerializerCls(data=request.data, partial=True)
serializer.is_valid(raise_exception=True)
solicitud.meta.update(serializer.validated_data)
solicitud.save()
```

`MetaFormFactory` cachea las clases generadas con `functools.lru_cache`
por modelo, así que llamar repetido es barato.

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
- **No** asumas que `instance.meta["x"]` existe sin chequear: usa
  `.get("x")` o define un `default`.
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
