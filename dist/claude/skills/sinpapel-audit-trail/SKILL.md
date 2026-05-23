---
name: sinpapel-audit-trail
description: Usar siempre que el usuario configure auditoría, use Trazable, HistoricalRecords o django-simple-history, consulte el historial de un modelo o de SeguimientoWorkflow, mencione HistoryRequestMiddleware o history_user nulo en jobs/background, o pregunte cómo persistir quién y cuándo cambió qué en sinpapel.
tested_against:
  - sinpapel==0.5.1
applies_to:
  - "**/models.py"
  - "**/models/*.py"
  - "**/admin.py"
---

# Audit trail en sinpapel

## Dos mecanismos complementarios

| Mecanismo | Qué registra | Dónde |
|---|---|---|
| **`SeguimientoWorkflow`** | Cada **transición** de estado: anterior → nuevo, usuario, fecha, comentarios, firma, side effects. | `sinpapel/models/workflow.py` |
| **`HistoricalRecords`** (simple-history) | Cada **cambio de fila** en modelos auditados: `INSERT`, `UPDATE`, `DELETE` con todos los campos. | Modelos con `history = HistoricalRecords()` |

Usa **ambos**: transiciones quedan en `SeguimientoWorkflow` (granularidad
de negocio), y los cambios de campos en `Historical*` (granularidad de
fila).

## `Trazable` (mixin del framework)

`sinpapel/mixins.py:Trazable`. Inlined en el framework (no instalar `trazable`):

```python
class Trazable(models.Model):
    creado = models.DateTimeField(auto_now_add=True, null=True)
    actualizado = models.DateTimeField(auto_now=True, null=True)
    autor = models.ForeignKey(User, null=True, related_name="%(class)s_autor", on_delete=CASCADE)
    modificador = models.ForeignKey(User, null=True, related_name="%(class)s_modificador", on_delete=CASCADE)
    caducidad = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True
```

Hereda donde quieras `creado`/`actualizado`/`autor`/`modificador` en tu
modelo de dominio (`Solicitud(MetadatosCapturables, Trazable)`).

## `SeguimientoWorkflow` — historial de transiciones

Cada `transition()` exitosa crea una fila. Campos relevantes:

- `target_content_type` + `target_object_id` + `target` (GFK).
- `estado_anterior` (nullable la primera vez), `estado_nuevo`.
- `usuario_accion`, `fecha_accion`.
- `comentarios`, `monto_aprobado`, `condiciones`, `ip_address`.
- `documentos_adjuntos` (JSONField).
- `firma_registro` (OneToOne nullable a `RegistroFirma`).

Consulta canónica:

```python
from django.contrib.contenttypes.models import ContentType
from sinpapel.models import SeguimientoWorkflow

ct = ContentType.objects.get_for_model(Solicitud)
historia = (
    SeguimientoWorkflow.objects
    .filter(target_content_type=ct, target_object_id=solicitud.pk)
    .select_related("usuario_accion", "estado_anterior", "estado_nuevo", "firma_registro")
    .order_by("-fecha_accion")
)
```

`SeguimientoWorkflow` **no se borra**: la auditoría asume inmutabilidad.
Si necesitas anular una transición, ejecuta otra transición de "reversa";
**no** borres ni edites filas existentes.

## `HistoricalRecords` (simple-history)

Modelos con historia en sinpapel (revisa el código por la lista actual):

- `VersionFlujo`
- `ConfiguracionTransicion` (incl. `grupos_permitidos` M2M)
- `RequisitoEstadoDocumento`
- `CondicionTransicion`
- `SLAConfiguracion`
- `RegistroFirma`
- `InstanciaDocumento`

Para auditar tus propios modelos, agrega:

```python
from simple_history.models import HistoricalRecords

class Solicitud(MetadatosCapturables, models.Model):
    folio = models.CharField(max_length=50, unique=True)
    estado = models.ForeignKey("sinpapel.Estado", on_delete=models.PROTECT)
    history = HistoricalRecords()
```

Y luego `python manage.py migrate` para generar la tabla `Historical*`.

Consultar:

```python
for h in solicitud.history.all().order_by("-history_date"):
    print(h.history_date, h.history_user, h.history_type)
    # history_type: '+' creado, '~' modificado, '-' borrado
```

## `history_user` — quién hizo el cambio

Se puebla por `simple_history.middleware.HistoryRequestMiddleware` desde
`request.user`. **Va después de `AuthenticationMiddleware`** en `MIDDLEWARE`.

**Casos donde `history_user` es `None` (esperado):**

- Management commands (`call_command("...")`).
- Tareas en background (Celery, RQ) si no propagas el usuario.
- Signals disparados fuera del ciclo de request (cron, scripts).
- Data migrations (`RunPython`).

**Si necesitas atribuir un usuario en background:**

```python
from simple_history.utils import update_change_reason
from simple_history.signals import pre_create_historical_record

# Opción A: pasarlo manualmente al guardar
instance._history_user = system_user
instance.save()

# Opción B: usar update_change_reason para registrar contexto adicional
update_change_reason(instance, "Recálculo nocturno")
```

## Comentarios / razones de cambio

`SeguimientoWorkflow.comentarios` captura el "por qué" de la transición.
`HistoricalRecords.history_change_reason` captura el "por qué" del UPDATE:

```python
from simple_history.utils import update_change_reason
solicitud.monto = 200_000
solicitud.save()
update_change_reason(solicitud, "Ajuste por validación SAT")
```

## Exponer historial por API

`sinpapel-drf` expone:

- `GET /<slug>/<pk>/history/` — paginado, devuelve entradas de
  `HistoricalRecords` del modelo decorado.

Para `SeguimientoWorkflow`, escribe tu propio serializer/endpoint (no
está expuesto por defecto en `sinpapel-drf` v0.2.1).

## Anti-patrones

- **No** uses `bulk_update` / `bulk_create` para modelos auditados: no
  dispara los signals de simple-history. Si tienes que hacerlo, registra
  manualmente la entrada histórica.
- **No** edites filas de `SeguimientoWorkflow` ni `Historical*`: rompe
  la inmutabilidad.
- **No** asumas que `history_user` está poblado en background; defensivo:
  `(h.history_user.username if h.history_user else "system")`.
- **No** olvides `HistoryRequestMiddleware` después de
  `AuthenticationMiddleware`: o `history_user` queda en `None` siempre.
- **No** auditees todos los modelos sin pensar: `Historical*` duplica
  filas en cada UPDATE. Audita lo que importa.

## Anonimización / retención

`simple-history` provee `bulk_history_create`, `clean_old_history` (3.5+).
Si necesitas borrar histórico por GDPR/aviso de privacidad, hazlo a través
de comandos explícitos, no `DELETE` directo de SQL.

## Siguiente paso

- Para registrar transiciones: `sinpapel-transitions`.
- Para registrar y verificar firmas: `sinpapel-signing`.
