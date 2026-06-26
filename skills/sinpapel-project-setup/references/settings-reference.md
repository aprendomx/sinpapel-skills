# Referencia de settings `SINPAPEL_*`

Lectura recomendada solo cuando necesites afinar configuración avanzada
(producción, multi-tenant, performance). Para setup inicial basta la skill
principal `sinpapel-project-setup`.

## Firma electrónica

### `SINPAPEL_SIGNATURE_BACKEND`

Dotted path del backend de firma. Default:
`"sinpapel.signing.backends.manual.ManualBackend"`.

Backends incluidos:

- `sinpapel.signing.backends.manual.ManualBackend` — escaneo + sello, sin
  criptografía. Bueno para procesos donde el documento físico se firma a
  mano.
- `sinpapel.signing.backends.fiel.FielBackend` — RSA-SHA256 + X.509 (FIEL
  del SAT México).
- `sinpapel.signing.backends.fake.FakeBackend` — para tests. **No** usar
  en producción.

Para un backend custom, ver `sinpapel-signing`.

### `SINPAPEL_ALLOW_SERVER_SIGNING`

Bool. Default `False`. Habilita el Modo B de `FielBackend` (el servidor
recibe `.cer` + `.key` + password). Implicaciones legales — revisar
ADR-012.

### `SINPAPEL_RSA_PRIVATE_KEY_PATH` / `SINPAPEL_RSA_PUBLIC_KEY_PATH`

Rutas a archivos PEM/PFX. Solo se leen si activas server-side signing.

## Cache

### `SINPAPEL_CACHE_ALIAS`

String. Default `"default"`. Alias del cache de Django que sinpapel usa
internamente (catálogos de Estado, VersionFlujo activa, transitions por
flujo, requisitos). Si tienes múltiples caches (por ejemplo `redis` para
sinpapel y `default` para sesiones), apunta aquí al alias correcto.

### `SINPAPEL_CACHE_TIMEOUT`

Int (segundos). Default `3600`. TTL de las entradas internas del
framework. La invalidación es signal-based (post_save / post_delete /
m2m_changed), así que en operación normal el TTL es un fallback.

## Eventos

### `SINPAPEL_EMIT_PREVIEW_EVENTS`

Bool. Default `False`. Si `True`, cada `preview_transition()` dispara el
signal `transition_preview_requested`. Útil para auditar intenciones de
transición que no se ejecutaron. `sinpapel-webhooks` lo expone como
`workflow.transition.preview` cuando está activo.

## Predicados

### `SINPAPEL_PREDICATE_MODULES`

`list[str] | None`. Default `None`. Whitelist de módulos cuyos callables
pueden invocarse desde un predicado `python_path`. Sin whitelist (default
`None`), el backend `python_path` **rechaza todo** por seguridad.

Ejemplo:

```python
SINPAPEL_PREDICATE_MODULES = [
    "tu_app.predicates",
    "compartido.reglas",
]
```

El motor permite cualquier dotted path cuya raíz coincida con uno de los
módulos listados. No expandas la whitelist a paquetes muy generales
(`tu_app.*` está bien; `django.*` o `os.*` sería suicida).

## Settings de paquetes adicionales

Los siguientes settings los leen paquetes hermanos. Documentados aquí
para referencia rápida; ver sus skills propias para el detalle.

### `sinpapel-webhooks`

- `SINPAPEL_WEBHOOKS_BACKEND` — `"inline"` / `"outbox"` (default) / `"celery"` / dotted path.
- `SINPAPEL_WEBHOOKS_REQUEST_TIMEOUT` — int (s), default `10`.
- `SINPAPEL_WEBHOOKS_TIMESTAMP_TOLERANCE` — int (s), default `300`.
- `SINPAPEL_WEBHOOKS_MAX_ATTEMPTS` — int, default `5`.
- `SINPAPEL_WEBHOOKS_RETRY_BACKOFF` — `list[int]`, default `[60, 300, 1800, 7200, 43200]`.
- `SINPAPEL_WEBHOOKS_DEAD_LETTER_AFTER_ATTEMPTS` — bool, default `True`.
- `SINPAPEL_WEBHOOKS_INBOUND_SECRETS` — `dict[str, str]`.
- `SINPAPEL_WEBHOOKS_ADMIN_PERMISSION` — dotted path. Default
  `"rest_framework.permissions.IsAdminUser"`.
- `SINPAPEL_WEBHOOKS_ADMIN_PAGE_SIZE` — int, default `50`.

## Cómo saber qué settings está leyendo realmente el framework

Si te quedan dudas, busca en el código:

```bash
grep -rn 'settings\.\bSINPAPEL_' /Users/jadrians/aprendo/sinpapel/
```

Cada uso en el código fuente es vinculante; lo que aparece arriba es la
foto del momento (v0.6.0). Si trabajas contra otra versión, valida los
defaults contra el repo.
