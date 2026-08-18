---
name: sinpapel-migrations-seeding
description: Usar siempre que el usuario siembre datos iniciales de Estado, Etapa, VersionFlujo o ConfiguracionTransicion vía data migrations; importe o exporte flujos con sinpapel_export_flujo / sinpapel_import_flujo (JSON schema v0.2); diseñe migraciones reversibles para catálogos del framework, o pregunte por requisitos documentales (RequisitoEstadoDocumento).
tested_against:
  - sinpapel==0.8.2
applies_to:
  - "**/migrations/*.py"
---

# Sembrado de flujos con data migrations

## Por qué data migrations (y no fixtures)

- Migran junto con el esquema. Un `migrate` en un entorno nuevo deja el
  sistema operacional.
- Reversibles si las escribes bien (`reverse_code`).
- Visibles en `git log` y revisables en PR.
- `loaddata` requiere mantener fixtures sincronizados a mano y pierde el
  contexto histórico.

## Patrón canónico

```python
# tu_app/migrations/0002_seed_flujo_inicial.py
from django.db import migrations


def seed(apps, schema_editor):
    Etapa = apps.get_model("sinpapel", "Etapa")
    Estado = apps.get_model("sinpapel", "Estado")
    VersionFlujo = apps.get_model("sinpapel", "VersionFlujo")
    ConfiguracionTransicion = apps.get_model("sinpapel", "ConfiguracionTransicion")

    # 1. Etapas (agrupación visual, opcional)
    etapa_inicial, _ = Etapa.objects.get_or_create(
        nombre="Inicial", defaults={"activo": True, "orden": 1}
    )
    etapa_final, _ = Etapa.objects.get_or_create(
        nombre="Final", defaults={"activo": True, "orden": 2}
    )

    # 2. Estados (catálogo, idempotente)
    captura, _ = Estado.objects.get_or_create(
        nombre="CAPTURA",
        defaults={"activo": True, "etapa": etapa_inicial, "orden": 1, "color": "#4DEFE2"},
    )
    revision, _ = Estado.objects.get_or_create(
        nombre="EN_REVISION",
        defaults={"activo": True, "etapa": etapa_inicial, "orden": 2, "color": "#FFA500"},
    )
    aprobada, _ = Estado.objects.get_or_create(
        nombre="APROBADA",
        defaults={"activo": True, "etapa": etapa_final, "orden": 3, "color": "#00C853"},
    )
    rechazada, _ = Estado.objects.get_or_create(
        nombre="RECHAZADA",
        defaults={"activo": True, "etapa": etapa_final, "orden": 4, "color": "#D32F2F"},
    )

    # 3. Versión del flujo (única activa por nombre; ver nota 0.8.0 abajo)
    flujo, _ = VersionFlujo.objects.get_or_create(
        nombre="solicitudes",
        defaults={"activo": True, "descripcion": "Flujo estándar de solicitudes v1"},
    )

    # 4. Transiciones (aristas). `requiere_firma` (0.8.0, default False)
    # es seedeable: con True, transition() sin firma_payload lanza
    # PermissionError.
    aristas = [
        (captura, revision, False),
        (revision, aprobada, True),   # aprobar exige firma
        (revision, rechazada, False),
    ]
    for origen, destino, firma in aristas:
        ConfiguracionTransicion.objects.get_or_create(
            flujo=flujo,
            estado_origen=origen,
            estado_destino=destino,
            defaults={"requiere_firma": firma},
        )


def unseed(apps, schema_editor):
    # Solo para entornos de dev: en prod, no revertir datos del flujo.
    VersionFlujo = apps.get_model("sinpapel", "VersionFlujo")
    VersionFlujo.objects.filter(nombre="solicitudes").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("sinpapel", "0001_initial"),
        ("tu_app", "0001_initial"),
    ]
    operations = [
        migrations.RunPython(seed, reverse_code=unseed),
    ]
```

Plantilla generadora en `assets/seed_flujo_template.py`.

## Constraints de unicidad (0.8.0)

Dos reglas que ahora se enforcan **a nivel BD** y que todo seed debe
respetar:

- **`Estado.nombre` es único** (constraint `sin_estado_nombre_uniq`). Dos
  estados homónimos ya no pueden existir; `get_or_create(nombre=...)` sigue
  siendo el patrón correcto — `nombre` es la clave natural del catálogo.
- **Solo una `VersionFlujo` activa por `nombre`** (constraint condicional
  `sin_versionflujo_activa_uniq`). Un seed que **active una versión nueva**
  de un flujo existente debe desactivar la anterior **antes**, o en la
  misma transacción, o el constraint rechaza el INSERT/UPDATE:

```python
def seed(apps, schema_editor):
    VersionFlujo = apps.get_model("sinpapel", "VersionFlujo")
    # Desactivar la versión activa anterior ANTES de activar la nueva
    # (RunPython corre en una transacción, así que ambas van juntas).
    VersionFlujo.objects.filter(nombre="solicitudes", activo=True).update(activo=False)
    VersionFlujo.objects.create(
        nombre="solicitudes", activo=True, descripcion="Flujo de solicitudes v2"
    )
```

## Idempotencia con `get_or_create`

Usa `get_or_create` (no `create`) para que la migración sea segura ante
re-ejecuciones manuales o entornos parcialmente migrados. Para catálogos,
la clave natural es `nombre`.

## Requisitos documentales por estado

```python
# tu_app/migrations/0003_seed_requisitos.py
def seed(apps, schema_editor):
    Estado = apps.get_model("sinpapel", "Estado")
    TipoDocumento = apps.get_model("sinpapel", "TipoDocumento")
    Requisito = apps.get_model("sinpapel", "RequisitoEstadoDocumento")

    revision = Estado.objects.get(nombre="EN_REVISION")
    rfc = TipoDocumento.objects.get_or_create(nombre="RFC", defaults={"activo": True})[0]
    ine = TipoDocumento.objects.get_or_create(nombre="INE", defaults={"activo": True})[0]

    Requisito.objects.get_or_create(estado=revision, tipo_documento=rfc, defaults={"porcentaje": 100})
    Requisito.objects.get_or_create(estado=revision, tipo_documento=ine, defaults={"porcentaje": 100})
```

**Desde sinpapel 0.6.0 estos requisitos SE ENFORCAN en la transición**
(antes solo se sembraban/exportaban). Al avanzar desde el estado que los
declara, `WorkflowEngine` bloquea si no se satisfacen y `transition()` lanza
`PermissionError` (ver `sinpapel-transitions`). Semántica del seed:

- **`porcentaje`** (en `RequisitoEstadoDocumento`): porcentaje mínimo exigido
  para ese tipo de documento en ese estado.
- **`auto_carga`** (bool, default `False`): si es `True`, el documento lo
  **genera el sistema** y el requisito **no bloquea** al usuario; solo se
  enforcan los `auto_carga=False`. Siembra `auto_carga=True` para documentos
  generados (oficios, acuses), no para los que sube el usuario.
- El **porcentaje real presente** no vive en el requisito sino en el campo
  `InstanciaDocumento.porcentaje` (`IntegerField`, 0–100, **default 100** =
  documento completo, backward-compatible). El actual evaluado es
  `max(InstanciaDocumento.porcentaje)` de ese tipo ligado a la instancia
  (0 si no hay ninguno). Campo añadido en la migración reversible `0004`.

El JSON v0.2 de export/import **no cambia**: sigue serializando la **regla**
(`RequisitoEstadoDocumento`, en `flujo.requisitos`), no el estado por
instancia (`InstanciaDocumento`/`porcentaje`), que es dato operacional.

## Predicados / SLAs en migrations

Igual de declarativos. Ver `sinpapel-predicates` y `sinpapel-sla` para
los ejemplos de seed por subsistema.

## Comandos del framework

### Exportar un flujo

```bash
python manage.py sinpapel_export_flujo <version_flujo_id> > flujo.json
# v0.2 con catálogos inline (estados, etapas, grupos, tipos doc):
python manage.py sinpapel_export_flujo <id> --inline-catalogs > flujo.json
```

Produce un JSON v0.2 portable:

```json
{
  "schema_version": "0.2",
  "exported_at": "...",
  "catalogos": {"estados": [...], "etapas": [...], "grupos": [...], "tipos_documento": [...]},
  "flujo": {
    "nombre": "solicitudes",
    "descripcion": "...",
    "activo": true,
    "metadatos": {"positions": {...}},
    "transiciones": [
      {
        "estado_origen": "CAPTURA",
        "estado_destino": "EN_REVISION",
        "grupos_permitidos": [],
        "condiciones": [...]
      }
    ],
    "requisitos": [...]
  }
}
```

### Importar un flujo

```bash
python manage.py sinpapel_import_flujo flujo.json
```

Crea `VersionFlujo` (por defecto `activo=False` por seguridad) + sus
`ConfiguracionTransicion` y `RequisitoEstadoDocumento`. Rechaza
referencias faltantes (estados/grupos/tipos doc no existentes). Al
activar después la versión importada, recuerda desactivar la anterior
antes o en la misma transacción (constraint
`sin_versionflujo_activa_uniq`, 0.8.0).

`sinpapel-drf` expone los mismos como `GET /flujos/<pk>/export/` y
`POST /flujos/import/` (`?dry_run=true` para validar sin persistir).

## Patrón: importar desde el designer

1. Diseñas en `sinpapel-designer`, exportas JSON v0.2.
2. Commiteas el JSON en `tu_app/flujos/solicitudes_v2.json`.
3. Migración:

```python
# tu_app/migrations/0007_import_flujo_v2.py
import json
from pathlib import Path
from django.db import migrations

def seed(apps, schema_editor):
    from sinpapel.schemas.flujo_export import deserialize_flujo
    fpath = Path(__file__).parent.parent / "flujos" / "solicitudes_v2.json"
    deserialize_flujo(json.loads(fpath.read_text()), activate=False)
```

(`deserialize_flujo` es la API canónica; consulta su firma actual antes
de copiar el ejemplo a un proyecto.)

Desde 0.8.0 `deserialize_flujo` **valida la estructura del payload**
(`flujo`, `flujo.nombre`, `transiciones`, `requisitos`): un JSON malformado
lanza un `ValueError` accionable en vez de un `KeyError` opaco. Si tu
migración de import falla con `ValueError`, el mensaje te dice qué key
falta en el JSON.

## Anti-patrones

- **No** uses `loaddata` para catálogos del framework. Pierdes
  reversibilidad y trazabilidad.
- **No** uses `Estado.objects.get_or_create(nombre=...)` sin `defaults`:
  si la fila ya existe pero está inactiva, no la reactivas.
- **No** uses `Estado.objects.create()` sin `get_or_create`: la migración
  falla al re-ejecutarse en un entorno donde el dato ya existe.
- **No** importes los modelos del framework directamente
  (`from sinpapel.models import Estado`): usa `apps.get_model(...)` —
  con el modelo "real" pierdes el historic-aware del estado de la
  migración.
- **No** uses `flujo__activo=True` como criterio único: en un entorno
  con varias versiones inactivas y una activa, te quedas sin filtrar al
  importar. Filtra por `(workflow_key implícito + activo=True)`.
- **No** dejes `unseed` vacío para producción: hacer `migrate sinpapel
  zero` en prod por error puede destruir catálogos. Considera bloquear
  reverse con `migrations.RunPython.noop` para data migrations críticas.

## Reversibilidad explícita

```python
operations = [
    migrations.RunPython(seed, reverse_code=migrations.RunPython.noop),
]
```

Usar `noop` indica "no se puede revertir esta data migration" sin
fallar. Más honesto que un `unseed` que destruya catálogos en prod.

## Siguiente paso

- Para diseñar visualmente y luego importar: `sinpapel-designer`.
- Para exponer export/import por API: `sinpapel-drf`.
