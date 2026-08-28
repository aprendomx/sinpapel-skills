# Referencia de modelos del workflow

Resumen de campos clave de cada modelo del subsistema workflow.
Verificado contra `sinpapel/models/workflow.py` (v0.8.3).

## `Etapa`

Agrupación visual de estados.

| Campo | Tipo | Notas |
|---|---|---|
| `nombre` | `CharField(250)` | **No** tiene constraint de unicidad (a diferencia de `Estado`). El import de flujos rechaza nombres ambiguos en destino. |
| `descripcion` | `TextField` | |
| `activo` | `BooleanField` | Default `False`. |
| `orden` | `IntegerField` | |
| `color` | `CharField(7)` | Hex, default `#4DEFE2`. |

Hereda `Catalogo` (→ `Trazable`).

## `Estado`

Nodo del grafo.

| Campo | Tipo | Notas |
|---|---|---|
| `nombre` | `CharField(250)` | Único a nivel BD (`sin_estado_nombre_uniq`, 0.8.0). Convención: `MAYÚSCULAS_GUION_BAJO`. |
| `descripcion` | `TextField` | |
| `activo` | `BooleanField` | Solo excluye destinos si `SINPAPEL_ENFORCE_ESTADO_ACTIVO=True` (default `False`, 0.8.1). |
| `color` | `CharField(7)` | Default `#4DEFE2`. |
| `orden` | `IntegerField` | Default `0`. |
| `etapa` | `FK(Etapa)` | Nullable. |
| `permite_expediente` | `BooleanField` | ¿Acepta documentos? |
| `expediente_obligatorio` | `BooleanField` | ¿Requiere ≥1? |
| `icono` | `CharField(80)` | Material Icons. |

Hereda `Catalogo` (→ `Trazable`).

## `VersionFlujo`

Versión del workflow.

| Campo | Tipo | Notas |
|---|---|---|
| `nombre` | `CharField(100)` | Sin constraint propio; la unicidad se enforca sobre `(nombre, activo=True)`. |
| `descripcion` | `TextField` | |
| `activo` | `BooleanField` | Solo **una** versión activa por `nombre`, forzado a nivel BD (`sin_versionflujo_activa_uniq`, 0.8.0). |
| `metadatos` | `JSONField` | Para designer (positions, etc.). |
| `creado` | `DateTimeField(auto_now_add)` | |
| `creado_por` | `FK(User)` | |

Con `HistoricalRecords`.

## `ConfiguracionTransicion`

Arista del grafo.

| Campo | Tipo | Notas |
|---|---|---|
| `flujo` | `FK(VersionFlujo, CASCADE)` | |
| `estado_origen` | `FK(Estado, CASCADE)` | |
| `estado_destino` | `FK(Estado, CASCADE)` | |
| `grupos_permitidos` | `M2M(Group)` | Vacío = cualquiera. |
| `requiere_firma` | `BooleanField` | Default `False` (0.8.0). Con `True`, `transition()` sin `firma_payload` lanza `PermissionError` y `preview_transition()` devuelve `firma_requerida: True`. Viaja en el JSON v0.2 desde 0.8.2. |

`unique_together = (flujo, estado_origen, estado_destino)`.

Con `HistoricalRecords` (incluye `grupos_permitidos`).

Relaciones reversa:

- `condiciones` → `CondicionTransicion` (predicados).
- `slas` → vía `Estado` destino, no directa.

## `SeguimientoWorkflow`

Audit log inmutable de transiciones.

| Campo | Tipo | Notas |
|---|---|---|
| `target_content_type` | `FK(ContentType)` | GFK al modelo decorado. |
| `target_object_id` | `PositiveIntegerField` | |
| `target` | `GenericForeignKey` | |
| `estado_anterior` | `FK(Estado, PROTECT)` | Nullable la primera vez. |
| `estado_nuevo` | `FK(Estado, PROTECT)` | |
| `usuario_accion` | `FK(settings.AUTH_USER_MODEL, PROTECT)` | Desde 0.8.3 respeta un usuario custom (antes fijaba `auth.User` y rompía el system check). |
| `fecha_accion` | `DateTimeField(auto_now_add)` | |
| `comentarios` | `TextField` | |
| `documentos_adjuntos` | `JSONField` | Lista de docs asociados. |
| `condiciones` | `TextField` | |
| `ip_address` | `GenericIPAddressField` | |
| `firma_registro` | `OneToOneField(RegistroFirma, PROTECT)` | Nullable. `PROTECT` desde 0.8.0. |

Índices: `(target_content_type, target_object_id)`, `estado_nuevo`,
`usuario_accion`.

**No editar manualmente.** Desde 0.8.0 el ORM lo enforca: `save()` sobre un
registro existente y `delete()` lanzan `ValueError`. Hereda `Trazable`, así
que también trae `creado`/`actualizado`/`autor`/`modificador`.

## `RequisitoEstadoDocumento`

Documento requerido para **avanzar desde** un estado (el motor enforca los
requisitos del estado **actual** de la instancia, no del destino).

| Campo | Tipo | Notas |
|---|---|---|
| `estado` | `FK(Estado)` | Estado origen al que aplica el requisito. |
| `tipo_documento` | `FK(TipoDocumento)` | |
| `porcentaje` | `IntegerField` | 0–100, default 100. Mínimo exigido. |
| `auto_carga` | `BooleanField` | Default False. `True` = documento que genera el sistema → **no bloquea** la transición. |

`unique_together = (estado, tipo_documento)`.

Con `HistoricalRecords`.

**Desde sinpapel 0.6.0 estos requisitos se enforcan** en la transición (ver
`sinpapel-transitions`). El porcentaje **presente** por instancia vive en
`InstanciaDocumento.porcentaje` (`IntegerField`, 0–100, default 100), que liga
el tipo vía `documento.tipo_documento` y la instancia vía su GFK `target`; el
actual evaluado es `max(InstanciaDocumento.porcentaje)` de ese tipo, 0 si no
hay ninguno.

## Cómo se relacionan

```
VersionFlujo ──< ConfiguracionTransicion >── Estado
                       │
                       └─< CondicionTransicion (predicados)

Estado ──< RequisitoEstadoDocumento >── TipoDocumento

Estado ──< SLAConfiguracion (timers)

[modelo decorado] ──< SeguimientoWorkflow (audit log) ──> Estado (ant/nuevo)
                                              │
                                              └── RegistroFirma (opcional)
```

`PROTECT` en los FKs principales evita borrar accidentalmente un Estado
o un Usuario referenciado por audit log.
