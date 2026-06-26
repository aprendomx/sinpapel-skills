---
name: sinpapel-drf
description: Usar siempre que el usuario exponga flujos sinpapel por API REST con Django REST Framework, instale sinpapel-drf, use expose_endpoints=True / endpoint_slug en @workflow_enabled, monte SinpapelRouter, llame los endpoints available-transitions / transition / history / preview-transition / metadatos / sla-status, exporte / importe flujos por HTTP, o configure permisos sobre transiciones. Cubre el dispatch polimórfico de firma y el mapeo de errores.
tested_against:
  - sinpapel-drf==0.2.1
  - sinpapel==0.6.0
applies_to:
  - "**/urls.py"
  - "**/viewsets.py"
  - "**/api/**/*.py"
---

# API REST con sinpapel-drf

## Instalación

```bash
pip install "sinpapel-drf @ git+ssh://git@github.com/aprendomx/sinpapel-drf.git@v0.2.1"
```

`sinpapel-drf` requiere `sinpapel>=0.6.0` y `djangorestframework>=3.14`.
Si no quieres CRUD admin de condiciones/SLAs, no instales el extra
`[admin]` — los endpoints quedan disponibles solo si DRF está instalado.

## INSTALLED_APPS

```python
INSTALLED_APPS = [
    ...,
    "simple_history",
    "rest_framework",
    "sinpapel",
    "sinpapel_drf",   # ← este
    "tu_app",
]
```

## Habilitar endpoints por modelo

```python
# tu_app/models.py
@workflow_enabled(
    state_field="estado",
    workflow_key="solicitud",
    expose_endpoints=True,        # ← habilita auto-routing
    endpoint_slug="solicitudes",  # opcional: default = workflow_key + "s"
)
class Solicitud(MetadatosCapturables, models.Model):
    ...
```

`endpoint_slug` debe ser kebab-case `[a-z0-9-]+`. Sin él, la URL base será
`workflow_key + "s"` (ej. `solicitud` → `/solicituds/` — explícita el slug
para evitar pluralizaciones raras).

## Montar las URLs

```python
# proyecto/urls.py
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("sinpapel/api/", include("sinpapel_drf.urls")),
]
```

`sinpapel_drf.urls` monta:

- `SinpapelRouter` (auto-itera `WorkflowRegistry.list_exposed()`).
- `DefaultRouter` con `/condiciones/` y `/slas/`.
- `/flujos/<pk>/export/` y `/flujos/import/`.

## Endpoints por instancia (auto-generados)

Para cada modelo con `expose_endpoints=True` se generan 6 acciones en
`<slug>`:

| Método + URL | Acción | Permiso |
|---|---|---|
| `GET /<slug>/<pk>/available-transitions/` | Estados destino válidos. | `IsAuthenticated` |
| `POST /<slug>/<pk>/preview-transition/` | Previsualiza una transición. | `IsAuthenticated` |
| `POST /<slug>/<pk>/transition/` | Ejecuta la transición. | `IsAuthenticated` (+ grupos vía engine) |
| `GET /<slug>/<pk>/history/` | Historial paginado de simple-history. | `IsAuthenticated` |
| `GET/PATCH /<slug>/<pk>/metadatos/` | Schema + valores; PATCH actualiza. | `IsAuthenticated` |
| `POST /<slug>/<pk>/sla-status/` | Evalúa SLAs (puede mutar si `alertar`). | `IsAdminUser` |

Detalle de payloads en `references/endpoints-reference.md`.

**`preview-transition` desde sinpapel 0.6.0:** el método de instancia
`instance.preview_transition(target_state, user)` ya está inyectado por
`@workflow_enabled` (antes faltaba y forzaba a invocar
`WorkflowEngine().preview_transition(...)` directamente como workaround). Un
viewset propio puede volver al método de instancia. Además, su reporte ahora
enforca requisitos documentales finos: `documentos_faltantes` puede traer
entradas `{"tipo": "requisito_documento", ...}` y `POST /transition/` responde
**403** (`PermissionError`) si un requisito no se satisface (ver
`sinpapel-transitions`).

## Endpoints admin (top-level)

| Método + URL | Acción | Permiso |
|---|---|---|
| `CRUD /condiciones/` | `CondicionTransicionViewSet`. Filtros `?transicion=`, `?activo=`. | `IsAdminUser` |
| `CRUD /slas/` | `SLAConfiguracionViewSet`. Filtros `?estado=`, `?activo=`. | `IsAdminUser` |
| `POST /slas/verificar/` | Evaluación masiva de SLAs. | `IsAdminUser` |
| `GET /flujos/<pk>/export/` | Descarga JSON v0.2. | `IsAdminUser` |
| `POST /flujos/import/` | Importa JSON. `?dry_run=true` y `?activo=true`. | `IsAdminUser` |

## Dispatch polimórfico de firma

`POST /<slug>/<pk>/transition/` acepta `signature` con un de cuatro
formas. El serializer `SignatureRequestSerializer` despacha al
sub-serializer apropiado.

**FIEL — client-side (default y recomendado):**

```json
{
  "target_state": "APROBADA",
  "comentarios": "OK",
  "signature": {
    "backend": "fiel",
    "mode": "client-side",
    "firma_b64": "...",
    "certificado_cer_b64": "..."
  }
}
```

**FIEL — server-side (gated por `SINPAPEL_ALLOW_SERVER_SIGNING=True`):**

```bash
curl -X POST -H "Authorization: Token <t>" \
  -F "target_state=APROBADA" \
  -F "signature[backend]=fiel" \
  -F "signature[mode]=server-side" \
  -F "signature[cer_file]=@firma.cer" \
  -F "signature[key_file]=@firma.key" \
  -F "signature[password]=••••" \
  https://host/sinpapel/api/solicitudes/42/transition/
```

**Manual / Fake**: ver `references/endpoints-reference.md`.

## Mapeo de errores

`WorkflowViewSet` traduce las excepciones del motor a códigos HTTP:

| Excepción | HTTP |
|---|---|
| `PermissionError` (grupos_permitidos, predicado, o requisito documental faltante desde 0.6.0) | 403 |
| `ValueError` | 400 |
| `SignatureValidationError` | 400 (`{"signature": [...]}`) |
| `SignatureBackendNotConfiguredError` | 400 |
| `django.core.exceptions.ValidationError` | 400 |

Si escribes vistas propias en paralelo, replica este mapeo (`sinpapel-transitions`).

## Schema OpenAPI

`sinpapel-drf` soporta `drf-spectacular` vía extra `[openapi]`. Hay
warnings conocidos en el polimorfismo de `SignatureRequestSerializer`
(roadmap post-1.0). Para schemas estrictos, ajusta `OpenApiSerializerExtension`
manualmente.

## Anti-patrones

- **No** dejes `expose_endpoints=True` sin `endpoint_slug` si el plural
  natural es raro o colisiona con otro modelo.
- **No** uses `ModelViewSet` propio para el modelo decorado sin
  desactivar `SinpapelRouter`: tendrás rutas duplicadas.
- **No** habilites `SINPAPEL_ALLOW_SERVER_SIGNING=True` sin checklist
  legal y seguridad (ver `sinpapel-signing` y ADR-012).
- **No** llames `available_transitions(request.user)` desde el cliente y
  hagas la lógica de permisos en el frontend: la **autoridad** son
  `grupos_permitidos` y el engine. El frontend solo refleja.
- **No** sobrescribas `WorkflowViewSet.transition()` sin reproducir el
  mapeo de excepciones: pierdes 403/400 consistentes.
- **No** asumas que `?dry_run=true` aplica a `transition`: solo aplica a
  `/flujos/import/`. Para transiciones, usa `preview-transition`.

## Verificar el setup

```python
# manage.py shell
from sinpapel.registry import WorkflowRegistry
for cfg in WorkflowRegistry.list_exposed():
    print(cfg.workflow_key, "→", cfg.effective_slug)
```

```bash
# Lista de URLs registradas
python manage.py show_urls | grep sinpapel
```

## Settings relevantes

| Setting | Default | Propósito |
|---|---|---|
| `SINPAPEL_ALLOW_SERVER_SIGNING` | `False` | Habilita FIEL Modo B en `POST /transition/`. |
| `REST_FRAMEWORK.DEFAULT_AUTHENTICATION_CLASSES` | — | Token, JWT, Session — lo que prefieras. |

## Siguiente paso

- Para webhooks complementarios: `sinpapel-webhooks`.
- Para tests de viewsets: `sinpapel-testing`.
