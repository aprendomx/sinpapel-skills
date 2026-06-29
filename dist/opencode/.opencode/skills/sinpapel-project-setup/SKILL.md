---
name: sinpapel-project-setup
description: Usar siempre que el usuario instale sinpapel en un proyecto Django nuevo o existente, configure INSTALLED_APPS, MIDDLEWARE o cualquier setting con prefijo SINPAPEL_*; mencione errores como "Estado no resuelto" / "history_user is None" / "AppRegistryNotReady"; o pregunte por dependencias (django-simple-history, cryptography), versiones soportadas o el orden correcto de las apps. Cubre el primer migrate, la instalación desde git@v0.7.0 y la verificación post-setup.
tested_against:
  - sinpapel==0.7.0
applies_to:
  - "**/settings*.py"
  - "**/requirements*.txt"
  - "**/pyproject.toml"
---

# Setup de un proyecto Django con sinpapel

## Requisitos

- Python ≥ 3.10
- Django ≥ 5.0
- Una base de datos relacional (PostgreSQL recomendado en producción;
  SQLite vale para dev)

## Instalación

`sinpapel` se distribuye por git (no publicado en PyPI todavía). Fija una
versión exacta:

```bash
pip install "sinpapel @ git+ssh://git@github.com/aprendomx/sinpapel.git@v0.7.0"
```

**Al actualizar desde 0.5.x — cambio potencialmente breaking:** desde 0.6.0
el motor **enforca** los `RequisitoEstadoDocumento` finos en las transiciones
(antes se sembraban/exportaban pero nunca se evaluaban). Si tu base ya tiene
requisitos configurados, transiciones que antes pasaban ahora pueden lanzar
`PermissionError` hasta que existan las `InstanciaDocumento` con el porcentaje
requerido. Flujos sin requisitos documentales se comportan igual que 0.5.x; el
flag coarse `expediente_obligatorio` no cambia. Corre `python manage.py migrate`
para la migración `0004` (añade `InstanciaDocumento.porcentaje`, default 100).
Detalle en `sinpapel-transitions` y `sinpapel-migrations-seeding`.

Dependencias transitivas que se instalan automáticamente:

- `Django>=5.0`
- `django-simple-history>=3.5`
- `cryptography>=42.0` (la usa `FielBackend`)

**No instales `trazable` por separado**: el mixin está inlined en
`sinpapel/mixins.py`.

## INSTALLED_APPS — orden requerido

```python
INSTALLED_APPS = [
    # Django built-ins
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.admin",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Dependencias de sinpapel
    "simple_history",       # antes de sinpapel

    # sinpapel
    "sinpapel",             # antes de tus apps de dominio

    # Tu(s) app(s) de dominio
    "tu_app",
]
```

**Por qué este orden**: `simple_history` registra los modelos históricos;
`sinpapel` define modelos con `HistoricalRecords` que dependen de ello; y
las apps de dominio referencian `sinpapel.Estado` por FK string.

## MIDDLEWARE — middleware de history

```python
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "simple_history.middleware.HistoryRequestMiddleware",  # ← tras AuthenticationMiddleware
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
```

**Por qué**: `HistoryRequestMiddleware` puebla `history_user` en cada
`HistoricalRecords`. Sin él, todos los cambios quedan con `history_user =
None`. Va **después** de `AuthenticationMiddleware` porque depende de
`request.user`.

## Settings `SINPAPEL_*`

| Setting | Default | Propósito |
|---|---|---|
| `SINPAPEL_SIGNATURE_BACKEND` | `"sinpapel.signing.backends.manual.ManualBackend"` | Dotted path del backend de firma. Otros: `sinpapel.signing.backends.fiel.FielBackend`, `sinpapel.signing.backends.fake.FakeBackend`. |
| `SINPAPEL_ALLOW_SERVER_SIGNING` | `False` | Habilita Modo B (server-side) en `FielBackend`. Requiere revisión legal. |
| `SINPAPEL_RSA_PRIVATE_KEY_PATH` | `None` | Ruta a `.key` privada (solo si server-side signing). |
| `SINPAPEL_RSA_PUBLIC_KEY_PATH` | `None` | Ruta a `.cer` / `.pub` (solo si server-side signing). |
| `SINPAPEL_EMIT_PREVIEW_EVENTS` | `False` | Opt-in: dispara `transition_preview_requested` en cada preview. |
| `SINPAPEL_CACHE_ALIAS` | `"default"` | Alias del cache backend (django.core.cache.caches). |
| `SINPAPEL_CACHE_TIMEOUT` | `3600` | TTL en segundos para cache interna. |
| `SINPAPEL_PREDICATE_MODULES` | `None` | Whitelist de módulos para predicados `python_path` (seguridad). Lista de dotted paths. |

Detalle por setting en `references/settings-reference.md`.

## Settings recomendados para desarrollo

```python
# settings/dev.py
SINPAPEL_SIGNATURE_BACKEND = "sinpapel.signing.backends.manual.ManualBackend"
SINPAPEL_ALLOW_SERVER_SIGNING = False
SINPAPEL_PREDICATE_MODULES = ["tu_app.predicates"]  # whitelist explícita

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}
```

## Primer migrate

```bash
python manage.py migrate
```

Aplica:

- Tablas de `simple_history` (sus históricos por modelo).
- Tablas de `sinpapel` (`sinpapel_estado`, `sinpapel_versionflujo`,
  `sinpapel_configuraciontransicion`, `sinpapel_seguimientoworkflow`,
  `sinpapel_registrofirma`, `sinpapel_condiciontransicion`,
  `sinpapel_slaconfiguracion`, etc.).

## Verificación post-setup

```python
# Django shell: python manage.py shell
from sinpapel import workflow_enabled  # noqa
from sinpapel.registry import WorkflowRegistry
from sinpapel.signing import get_signature_backend

print(WorkflowRegistry.list_keys())     # ['solicitud', ...] tras decorar modelos
print(get_signature_backend().name)     # 'manual' | 'fiel' | 'fake'
```

## Anti-patrones

- **No** uses `pip install sinpapel` (no está en PyPI). Usa la URL git con
  tag fijo.
- **No** uses `>=0.5,<0.6`. La 0.x admite breaking changes; fija un tag/commit.
- **No** pongas `simple_history` después de `sinpapel`.
- **No** olvides `HistoryRequestMiddleware` — el audit trail funciona, pero
  `history_user` queda en `None`.
- **No** pongas `WorkflowService` en ningún sitio: ese servicio no existe;
  el motor es `WorkflowEngine`.
- **No** dejes `SINPAPEL_PREDICATE_MODULES = None` si vas a usar predicados
  `python_path` con código de tu proyecto: explícita la whitelist.
- **No** crees fixtures de datos vía `loaddata` para `Estado`/`VersionFlujo`:
  usa data migrations (ver `sinpapel-migrations-seeding`).

## Troubleshooting

| Síntoma | Causa probable | Solución |
|---|---|---|
| `AppRegistryNotReady` al importar `WorkflowRegistry` | Importas fuera de `apps.ready()` o antes de Django setup. | Mover el import dentro de la función/método donde se usa. |
| `history_user is None` en todos los cambios | Falta `HistoryRequestMiddleware`, o el cambio ocurre fuera de un request (management command, signal sin middleware). Es esperado en background. | Añadir middleware; en jobs en background, asume `None`. |
| `LookupError: No installed app with label 'simple_history'` al migrar | `simple_history` falta o va después de `sinpapel`. | Añadirlo y ponerlo **antes** de `sinpapel`. |
| `WorkflowConfigurationError: state_field 'estado' not on model` | Decorador `@workflow_enabled(state_field=...)` apunta a un campo inexistente. | Corregir el nombre del campo FK a `sinpapel.Estado`. |
| Falla `cryptography` al instalar | Falta toolchain de compilación. | `pip install --upgrade pip wheel` y/o instalar headers de OpenSSL. |

## Siguiente paso

Cuando termines el setup, ve a `sinpapel-workflow-modeling` para decorar
tu primer modelo de dominio y sembrar el flujo inicial.
