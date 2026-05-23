# Referencia de modelos del workflow

Resumen de campos clave de cada modelo del subsistema workflow.
Verificado contra `sinpapel/models/workflow.py` (v0.5.1).

## `Etapa`

Agrupación visual de estados.

| Campo | Tipo | Notas |
|---|---|---|
| `nombre` | `CharField` | Único. |
| `descripcion` | `TextField` | |
| `activo` | `BooleanField` | |
| `orden` | `IntegerField` | |
| `color` | `CharField(7)` | Hex. |

Hereda `Catalogo` (→ `Trazable`).

## `Estado`

Nodo del grafo.

| Campo | Tipo | Notas |
|---|---|---|
| `nombre` | `CharField(250)` | Único. Convención: `MAYÚSCULAS_GUION_BAJO`. |
| `descripcion` | `TextField` | |
| `activo` | `BooleanField` | Estados inactivos no participan. |
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
| `nombre` | `CharField(100)` | Único recomendado. |
| `descripcion` | `TextField` | |
| `activo` | `BooleanField` | Convención: uno activo por workflow_key. |
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
| `usuario_accion` | `FK(User, PROTECT)` | |
| `fecha_accion` | `DateTimeField(auto_now_add)` | |
| `comentarios` | `TextField` | |
| `documentos_adjuntos` | `JSONField` | Lista de docs asociados. |
| `monto_aprobado` | `DecimalField(12,2)` | |
| `condiciones` | `TextField` | |
| `ip_address` | `GenericIPAddressField` | |
| `firma_registro` | `OneToOneField(RegistroFirma)` | Nullable. |

Índices: `(target_content_type, target_object_id)`, `estado_nuevo`,
`usuario_accion`.

**No editar manualmente.** No tiene `update_at` ni mecanismo de mutación.

## `RequisitoEstadoDocumento`

Documentos requeridos para entrar a un estado.

| Campo | Tipo | Notas |
|---|---|---|
| `estado` | `FK(Estado)` | |
| `tipo_documento` | `FK(TipoDocumento)` | |
| `porcentaje` | `IntegerField` | 0–100, default 100. |
| `auto_carga` | `BooleanField` | Default False. |

`unique_together = (estado, tipo_documento)`.

Con `HistoricalRecords`.

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
