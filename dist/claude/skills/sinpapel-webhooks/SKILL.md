---
name: sinpapel-webhooks
description: Usar siempre que el usuario emita o consuma webhooks con sinpapel-webhooks; configure WebhookSubscription / WebhookEvent / WebhookDelivery / InboundWebhookEvent; use el decorador @webhook_receiver, los backends de entrega inline / outbox / celery, HMAC-SHA256 con X-Sinpapel-Signature, política de reintentos con backoff y dead letter, idempotencia inbound, o el Admin REST API. Cubre el cron del worker y la verificación de firmas desde cliente.
tested_against:
  - sinpapel-webhooks==0.2.1
  - sinpapel==0.7.0
applies_to:
  - "**/webhooks.py"
  - "**/receivers/**/*.py"
---

# Webhooks con sinpapel-webhooks

## Arquitectura

- **Outbound**: signals de dominio → `emit_event()` → `WebhookEvent` +
  N `WebhookDelivery` → `backend.enqueue(delivery_id)` → worker hace
  `POST` HMAC-firmado al `url` de la subscription.
- **Inbound**: `POST /sinpapel/api/webhooks/in/<source>/` →
  `ReceiverDispatcher` (HMAC verify + dedup) → handler decorado con
  `@webhook_receiver(source, event)`.

## Instalación

```bash
pip install "sinpapel-webhooks @ git+ssh://git@github.com/aprendomx/sinpapel-webhooks.git@v0.2.1"
# Extras:
pip install "sinpapel-webhooks[celery] @ git+...@v0.2.1"   # backend celery
pip install "sinpapel-webhooks[admin] @ git+...@v0.2.1"    # Admin REST API
```

```python
INSTALLED_APPS = [..., "sinpapel", "sinpapel_webhooks", ...]

# urls.py
urlpatterns += [
    path("sinpapel/api/webhooks/", include("sinpapel_webhooks.urls")),
]
```

```bash
python manage.py migrate
```

## Modelos

- `WebhookSubscription` — `name`, `url`, `events` (lista),
  `secret` (32-byte hex), `active`. Con `HistoricalRecords`.
- `WebhookEvent` — evento canónico: `event_id` (UUID), `event_type`,
  `payload`, `source_object` (GFK), `occurred_at`.
- `WebhookDelivery` — intento de entrega:
  `status` ∈ `{pending, delivering, delivered, failed, dead_letter}`,
  `attempts`, `scheduled_at`, `last_response_status`, `last_error`.
- `InboundWebhookEvent` — dedup inbound. `unique_together = (source, event_id)`.

## Eventos emitidos por sinpapel

| Event type | Disparo |
|---|---|
| `workflow.transition.completed` | `SeguimientoWorkflow` creado. |
| `signature.completed` | `RegistroFirma` creado. |
| `document.uploaded` | `InstanciaDocumento` creado. |
| `workflow.predicate.configured` | `CondicionTransicion` create/update. |
| `workflow.predicate.failed` | signal `predicate_failed`. |
| `sla.configured` | `SLAConfiguracion` create/update. |
| `sla.breached` | signal `sla_breached`. |
| `sla.action.executed` | signal `sla_action_executed`. |
| `workflow.transition.preview` | opt-in `SINPAPEL_EMIT_PREVIEW_EVENTS=True`. |

Los handlers internos capturan un **snapshot** sincrónico del payload y
encolan el `emit_event()` en `transaction.on_commit()` para garantizar
que solo se emite tras commit.

## Subscribirse a eventos (outbound)

```python
from sinpapel_webhooks.models import WebhookSubscription

WebhookSubscription.objects.create(
    name="consumer-X",
    url="https://consumer.example.com/webhook",
    events=["workflow.transition.completed", "sla.breached"],
    secret="hex-32-bytes-aleatorios",  # ej. secrets.token_hex(32)
    active=True,
)
```

## Backend de entrega

`SINPAPEL_WEBHOOKS_BACKEND` (default `"outbox"`):

| Backend | Cuándo |
|---|---|
| `"inline"` | Dev / smoke. Síncrono, sin retry. **No** usar en producción. |
| `"outbox"` | Producción sin broker. DB-backed queue. Requiere worker. |
| `"celery"` | Producción con Celery. Requiere broker (Redis/RabbitMQ). |
| dotted path | Custom (implementa `WebhookDeliveryBackend`). |

### Worker para outbox

```bash
python manage.py sinpapel_webhooks_worker
python manage.py sinpapel_webhooks_worker --batch-size 50 --poll-interval 5
python manage.py sinpapel_webhooks_worker --once   # un solo ciclo (cron)
```

Recomendado: PostgreSQL en producción. SQLite no soporta múltiples
workers concurrentes para outbox.

## Headers outbound

```
POST /your-webhook HTTP/1.1
Content-Type: application/json; charset=utf-8
User-Agent: sinpapel-webhooks/0.2.1
X-Sinpapel-Signature: t=<unix-ts>,v1=<sha256-hex>
X-Sinpapel-Event-Id: <uuid>
X-Sinpapel-Event-Type: <event_type>
X-Sinpapel-Webhook-Id: <subscription_id>
```

## Verificar la firma (consumer-side)

Algoritmo: `HMAC-SHA256(secret, f"{t}.".encode() + raw_body)`.

```python
# Python (consumer)
import hmac, hashlib, time

def verify_sinpapel_signature(raw_body: bytes, header_value: str, secret: str, tolerance: int = 300):
    parts = dict(p.split("=", 1) for p in header_value.split(","))
    t = int(parts["t"])
    if abs(time.time() - t) > tolerance:
        raise ValueError("timestamp out of tolerance")
    mac = hmac.new(secret.encode(), f"{t}.".encode() + raw_body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(mac, parts["v1"]):
        raise ValueError("bad signature")
```

Ejemplos en Node.js, Ruby y Go en `references/hmac-verify-examples.md`.

## Reintentos y dead letter

- `SINPAPEL_WEBHOOKS_MAX_ATTEMPTS = 5` (default).
- `SINPAPEL_WEBHOOKS_RETRY_BACKOFF = [60, 300, 1800, 7200, 43200]` segundos.
- Jitter ±10% para evitar thundering herd.
- **No retry**: 2xx (éxito), 4xx semánticas (400, 401, 403, 404, 410, 422).
- **Retry**: timeouts, 5xx, 408, 429.
- Tras agotar intentos, status pasa a `dead_letter` (si
  `SINPAPEL_WEBHOOKS_DEAD_LETTER_AFTER_ATTEMPTS=True`, default).

Re-encolar manualmente:

```bash
python manage.py sinpapel_webhooks_requeue_dead_letter --all
python manage.py sinpapel_webhooks_requeue_dead_letter --id 17
```

## Recibir webhooks (inbound)

```python
# tu_app/webhooks.py — auto-descubierto en AppConfig.ready()
from sinpapel_webhooks import webhook_receiver

@webhook_receiver(source="proveedor_x", event="payment.confirmed")
def on_payment_confirmed(payload, request):
    # payload: dict completo del envelope
    # request: HttpRequest (headers, etc.)
    pago_id = payload["data"]["pago_id"]
    ...
    return {"acked": True, "pago_id": pago_id}   # opcional
```

Settings para inbound:

```python
SINPAPEL_WEBHOOKS_INBOUND_SECRETS = {
    "proveedor_x": "secret-32-byte-hex-aaa",
    "otro_servicio": "secret-32-byte-hex-bbb",
}
```

URL: `POST /sinpapel/api/webhooks/in/<source>/`.

### Códigos de status inbound

| Status | Significado |
|---|---|
| 200 | Handler ejecutado, o evento duplicado (idempotencia). |
| 400 | Headers obligatorios faltantes o JSON inválido. |
| 401 | HMAC inválido o source desconocido. |
| 404 | No hay handler registrado para `(source, event_type)`. |
| 500 | El handler lanzó una excepción. |

## Admin REST API (extra `[admin]`)

`GET/POST /admin/subscriptions/`, `POST /admin/subscriptions/{id}/test/`,
`POST /admin/subscriptions/{id}/rotate-secret/`,
`GET /admin/deliveries/?status=`, `POST /admin/deliveries/{id}/retry/`,
`POST /admin/deliveries/requeue-dead-letter/`, etc.

Permiso default: `SINPAPEL_WEBHOOKS_ADMIN_PERMISSION` (default
`rest_framework.permissions.IsAdminUser`).

## Settings completos

| Setting | Default | Propósito |
|---|---|---|
| `SINPAPEL_WEBHOOKS_BACKEND` | `"outbox"` | Backend de entrega. |
| `SINPAPEL_WEBHOOKS_REQUEST_TIMEOUT` | `10` | Timeout HTTP POST (s). |
| `SINPAPEL_WEBHOOKS_TIMESTAMP_TOLERANCE` | `300` | Tolerancia replay (s). |
| `SINPAPEL_WEBHOOKS_MAX_ATTEMPTS` | `5` | Max intentos antes de dead letter. |
| `SINPAPEL_WEBHOOKS_RETRY_BACKOFF` | `[60,300,1800,7200,43200]` | Backoff. |
| `SINPAPEL_WEBHOOKS_DEAD_LETTER_AFTER_ATTEMPTS` | `True` | True→`dead_letter`, False→`failed`. |
| `SINPAPEL_WEBHOOKS_INBOUND_SECRETS` | `{}` | Dict `{source: secret_hex}`. |
| `SINPAPEL_WEBHOOKS_ADMIN_PERMISSION` | `"rest_framework.permissions.IsAdminUser"` | Permission class. |
| `SINPAPEL_WEBHOOKS_ADMIN_PAGE_SIZE` | `50` | Paginación admin. |
| `SINPAPEL_EMIT_PREVIEW_EVENTS` | `False` | (núcleo) Emite `workflow.transition.preview`. |

## Anti-patrones

- **No** uses `"inline"` en producción: no hay retry; un consumer caído
  pierde eventos.
- **No** uses `bulk_create` para crear modelos auditados: no dispara
  signals, los webhooks no se emiten.
- **No** confíes en `secret` con baja entropía: usa
  `secrets.token_hex(32)` o equivalente.
- **No** apliques tu lógica de negocio antes de verificar HMAC: si el
  dispatcher rechaza, tu handler nunca se invoca; si lo bypaseas, abres
  vector de spoofing.
- **No** retornes 5xx por un duplicado: el framework ya idempotenta
  vía `InboundWebhookEvent.unique_together`. Un duplicado responde 200.
- **No** asumas orden de entrega entre eventos: cada delivery se reintenta
  independientemente.
- **No** olvides programar el worker (`sinpapel_webhooks_worker`) en
  producción: con backend `outbox` y sin worker, las deliveries quedan
  `pending` para siempre.

## Patrón de operación

1. Configurar `SINPAPEL_WEBHOOKS_BACKEND = "outbox"` (default) en prod.
2. Sembrar `WebhookSubscription` para los consumers conocidos.
3. Programar `sinpapel_webhooks_worker` como systemd / Kubernetes deployment.
4. Configurar `SINPAPEL_WEBHOOKS_INBOUND_SECRETS` por cada proveedor entrante.
5. Implementar `@webhook_receiver` en `tu_app/webhooks.py`.
6. (Opcional) Habilitar Admin REST API para operadores.

## Siguiente paso

- Para emitir eventos custom (no del workflow): llama directamente
  `sinpapel_webhooks.emit.emit_event(event_type, payload, source=instance)`
  desde tu código.
