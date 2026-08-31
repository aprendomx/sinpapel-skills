# sinpapel-skills

Skills multi-proveedor (Claude, Cursor, OpenCode) para el framework
[sinpapel](https://github.com/aprendomx/sinpapel) y sus paquetes
(`sinpapel-drf`, `sinpapel-webhooks`, `sinpapel-reports`, `sinpapel-designer`,
`sinpapel-vue`).

Las skills **no reimplementan el framework**: encapsulan el conocimiento y las
mejores prácticas para usarlo, de modo que cualquier agente de IA o
desarrollador pueda construir un sistema de trámites sobre sinpapel sin
releer todo el código fuente.

**Versiones objetivo:** `sinpapel==0.8.4`, `sinpapel-drf==0.4.5`,
`sinpapel-webhooks==0.2.4`, `sinpapel-reports==0.2.3`,
`sinpapel-designer@v0.1.0`, `sinpapel-vue@0.4.0`.

## Arquitectura: una sola fuente de verdad

```
sinpapel-skills/
├── skills/                       ← FUENTE CANÓNICA (editar aquí)
│   └── <nombre>/
│       ├── SKILL.md              ← frontmatter YAML + cuerpo Markdown
│       ├── references/           ← opcional: heavy reference
│       ├── scripts/              ← opcional: utilidades
│       └── assets/               ← opcional: plantillas
├── commands/                     ← FUENTE CANÓNICA de los slash commands
│   └── sinpapel/<nombre>.md      ← se invocan como /sinpapel:<nombre>
├── build_skills.py               ← generador idempotente
├── Makefile                      ← atajos
└── dist/                         ← GENERADO (no editar a mano)
    ├── claude/skills/...         ← formato Claude / Agent Skills
    ├── claude/commands/...       ← slash commands (solo Claude Code)
    ├── opencode/.opencode/skills ← formato OpenCode (compatible)
    ├── cursor/.cursor/rules/...  ← reglas .mdc para Cursor
    └── AGENTS.md                 ← índice cross-tool
```

**Regla:** cada skill se escribe **una sola vez** en `skills/<nombre>/SKILL.md`.
Las variantes por proveedor se generan con `python build_skills.py` y **no
deben editarse a mano**: los cambios viven en la fuente canónica.

## Comandos

Además de las skills, `commands/` guarda los slash commands del flujo de trabajo
—`/sinpapel:especificar`, `/sinpapel:generar` y `/sinpapel:verificar`—, que
describen cómo se construye un sistema de trámites: descripción en lenguaje
natural → `spec/` → la app → los gates.

Vivían en el template `sinpapel-boilerplate`, pero el flujo que describen no es
específico de ese repositorio: en cuanto exista un segundo proyecto sobre
sinpapel, dos copias divergen. Se vendorizan igual que las skills.

Se emiten **solo para Claude Code**: los slash commands son una convención suya
(`.claude/commands/<espacio>/<nombre>.md`) y no hay equivalente verificado en
los otros destinos. Inventar un mapeo produciría archivos que ninguna
herramienta lee.

## Catálogo de skills

| Skill | Propósito |
|---|---|
| `sinpapel-overview` | Skill índice / router. Punto de entrada y glosario. |
| `sinpapel-project-setup` | Instalación, `INSTALLED_APPS`, `MIDDLEWARE`, settings `SINPAPEL_*`. |
| `sinpapel-workflow-modeling` | `@workflow_enabled`, modelos `Estado`/`VersionFlujo`/`ConfiguracionTransicion`. |
| `sinpapel-transitions` | Ejecutar `transition()`, `preview_transition()`, manejo de excepciones. |
| `sinpapel-side-effects` | `register_side_effect()`, atomicidad, registro en `AppConfig.ready()`. |
| `sinpapel-predicates` | `CondicionTransicion`, `PredicateEngine`, json_logic / python_path / django_orm. |
| `sinpapel-sla` | `SLAConfiguracion`, `SLAEngine`, comandos de verificación, signals SLA. |
| `sinpapel-metadata` | `MetadatosCapturables`, `CampoMetadato`, `MetaFormFactory`. |
| `sinpapel-signing` | `SignatureBackend` Port/Adapter, `FielBackend` Modos A/B, custom backends. |
| `sinpapel-audit-trail` | `Trazable`, `SeguimientoWorkflow`, simple-history, `history_user`. |
| `sinpapel-migrations-seeding` | Sembrar flujos vía data migrations y JSON v0.2 portable. |
| `sinpapel-drf` | API REST: `expose_endpoints`, `SinpapelRouter`, dispatch de firma, endpoints `documentos`/`requisitos`. |
| `sinpapel-webhooks` | Outbox + HMAC + reintentos + inbound idempotente. |
| `sinpapel-reports` | Generación por plantilla: `ReportDataSource`, `ReportEngine.generar`/`generar_paquete`, overlay PDF, DOCX, endpoints DRF. |
| `sinpapel-designer` | SPA Vue/Quasar standalone, round-trip JSON v0.2. |
| `sinpapel-vue-setup` | Instalación de `@aprendomx/sinpapel-vue`, peer deps, `style.css`, temas `--sp-*`, i18n, quick-start. |
| `sinpapel-vue-client` | `createSinpapelClient`, 11 métodos → endpoints `sinpapel-drf`, `AbortController`, `buildTransitionRequest`/`buildDocumentoUpload`. |
| `sinpapel-vue-components` | 9 widgets (`SeguimientoPanel`…, `RequisitosPanel`/`DocumentosPanel`), props/emits, a11y, firma polimórfica en `TransitionDialog`. |
| `sinpapel-vue-store` | Store Pinia `useSeguimientoStore`, composables `useTransition`/`useSpLabels`, loading granular, `cancel()`. |
| `sinpapel-testing` | `FakeBackend`, fixture RSA keypair, settings de test, `WorkflowRegistry.unregister()`. |

## Generar las variantes por proveedor

Requisitos: Python ≥3.10 y PyYAML.

```bash
pip install -e .
python build_skills.py
# o:
make skills
```

Verificar idempotencia:

```bash
python build_skills.py --verify
```

Limpiar:

```bash
make clean
```

## Instalar en cada proveedor

### Claude Code

**Global (todas tus sesiones):**

```bash
mkdir -p ~/.claude/skills
cp -R dist/claude/skills/* ~/.claude/skills/
# o:
make install-claude
```

**Por proyecto:**

```bash
mkdir -p .claude/skills
cp -R dist/claude/skills/* .claude/skills/
```

Las skills se activan por `description` (Claude las inyecta cuando aplica).

### Cursor

Copia las reglas al proyecto donde uses sinpapel:

```bash
mkdir -p .cursor/rules
cp -R dist/cursor/.cursor/rules/* .cursor/rules/
# o, desde el directorio del proyecto target:
make -C /ruta/a/sinpapel-skills install-cursor
```

Los `.mdc` usan `alwaysApply: false` y se activan por `description` (modo
*Agent Requested*). Las skills que añaden `applies_to` en el frontmatter
canónico también se activan por `globs` (modo *Auto Attached*).

### OpenCode

OpenCode soporta el formato de Claude:

```bash
mkdir -p .opencode/skills
cp -R dist/opencode/.opencode/skills/* .opencode/skills/
```

Adicionalmente, `dist/AGENTS.md` puede colocarse en la raíz del proyecto
como índice cross-tool legible por múltiples agentes.

## Editar las skills

1. Edita `skills/<nombre>/SKILL.md` (o sus `references/`, `scripts/`, `assets/`).
2. Ejecuta `python build_skills.py`.
3. Re-instala en los proveedores que uses.

**Nunca edites archivos dentro de `dist/`:** el generador los sobrescribe.

## Convenciones de las skills

- **Idioma:** español, consistente con el framework.
- **`name`**: kebab-case `sinpapel-<dominio>`.
- **`description`**: tercera persona, empieza con "Usar siempre que…" o
  similar, lista disparadores concretos (nombres del framework, archivos,
  síntomas) para evitar sub-activación.
- **Ejemplos**: verificados contra el código real de los repos
  (`/Users/jadrians/aprendo/sinpapel/`, etc.). No inventar nombres.
- **Anti-patrones**: cada skill enumera explícitamente qué NO hacer.
- **Versión**: cada skill anota `tested_against:` con las versiones contra
  las que se verificó.

## Limitaciones y notas

- `sinpapel` está en **0.x (beta)**: la API es estable pero pueden ocurrir
  breaking changes hasta 1.0. Fija `~=0.8.4` (o el tag/commit que uses) en
  tus dependencias.
- **Usuario custom:** `AUTH_USER_MODEL` distinto de `auth.User` requiere
  `sinpapel>=0.8.3` y `sinpapel-webhooks>=0.2.4`. En versiones previas el
  system check de Django falla con `fields.E301`.
- `i18n` del framework está parcialmente en español (verbose_names, mensajes
  de error). Las skills están en español por consistencia.
- `WorkflowService` **no existe**: el motor real es `WorkflowEngine` en
  `sinpapel.services.workflow_engine`. Si ves código legado que lo
  referencia, hay que migrarlo.

## Licencia

GPL-3.0-or-later (igual que sinpapel).
