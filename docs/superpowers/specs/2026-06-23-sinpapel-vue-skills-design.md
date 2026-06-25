# Diseño: skills para `sinpapel-vue`

**Fecha:** 2026-06-23
**Estado:** aprobado para implementación
**Repo objetivo del conocimiento:** `../sinpapel-vue` (`@aprendomx/sinpapel-vue@0.1.0`)

## Objetivo

Extender `sinpapel-skills` para cubrir `sinpapel-vue`: la biblioteca de
componentes **Vue 3** que consume la API REST de `sinpapel-drf` para
*workflow tracking* en el frontend. Las skills encapsulan cómo **usar** la
biblioteca; no reimplementan sus componentes.

`sinpapel-vue` es distinto de `sinpapel-designer` (skill ya existente): el
designer es un SPA standalone para *diseñar* flujos; `sinpapel-vue` es una
**librería de widgets** para *operar/seguir* una instancia ya existente
contra `sinpapel-drf`.

## Decisión de alcance

- **Granularidad:** varios skills finos (no uno solo, no extender skills
  existentes).
- **Descomposición:** 4 skills por capa, espejo de `src/` y de la carpeta
  de tests.

## Los 4 skills nuevos

Cada skill se crea en `skills/<nombre>/SKILL.md` (fuente canónica). Todos en
español, con frontmatter `name` (kebab-case) + `description` (tercera
persona, "Usar siempre que…", disparadores concretos), `tested_against` y
`applies_to`. Cada skill enumera anti-patrones explícitos.

### `sinpapel-vue-setup`

- **Qué es / qué NO es:** librería Vue 3 que consume `sinpapel-drf`; NO es
  backend, NO descubre el `resource` slug solo (v1).
- Instalación: `npm install @aprendomx/sinpapel-vue`; peer deps
  obligatorias `vue ^3.5`, `pinia ^3`, `quasar ^2.16`.
- Import de estilos: `import '@aprendomx/sinpapel-vue/style.css'`.
- Exports de `src/index.js` (qué se exporta y desde dónde).
- Quick-start: montar `SeguimientoPanel` con `:axios`, `base-path`,
  `resource` (= `effective_slug` del modelo `@workflow_enabled`), `pk`,
  `current-state`; usar `:key="pk"` si `pk`/`resource` cambian.
- Tematización: variables `--sp-*` (`src/styles/tokens.css`), override en
  `:root`/scope.
- i18n: `locale` `es`/`en`, sin deps externas; cómo añadir un idioma
  (`src/locales/` + registro en `useSpLabels.js`).
- **Disparadores:** instalar la librería, peer deps Quasar/Pinia, montar
  `SeguimientoPanel`, temas `--sp-*`, locale.
- **Anti-patrones:** olvidar el `style.css`; omitir Quasar como peer dep;
  esperar auto-descubrimiento de `resource`; no remountar con `:key` al
  cambiar `pk`.

### `sinpapel-vue-client`

- `createSinpapelClient({ axios, basePath='/sinpapel/api', resource, pk, signal })`
  — lanza si falta `axios` o `resource`.
- Los 7 métodos y su mapeo 1:1 a endpoints `sinpapel-drf`:
  - `availableTransitions()` → GET `…/available-transitions/`
  - `history({page, pageSize})` → GET `…/history/` (param `page_size`)
  - `previewTransition(targetState)` → POST `…/preview-transition/`
    (body `{ target_state }`)
  - `getMetadatos()` → GET `…/metadatos/`
  - `patchMetadatos(values)` → PATCH `…/metadatos/`
  - `slaStatus()` → POST `…/sla-status/`
  - `transition(payload)` → POST `…/transition/`
- `buildTransitionRequest(payload)`: FIEL server-side → `multipart/form-data`
  con claves DRF `signature.<campo>` (`cer_file`/`key_file`/`password`); el
  resto → JSON con bloque `signature`. Body usa snake_case
  (`target_state`, `monto_aprobado`, `condiciones`).
- Cancelación: `signal` (AbortController) propagado a cada llamada axios.
- Forma del error: el consumidor lee `e.response?.data` (no normaliza
  aquí; eso vive en store/composable).
- **Disparadores:** crear el cliente, llamar uno de los 7 métodos, mapear a
  endpoints `sinpapel-drf`, cancelar requests.
- **Anti-patrones:** mandar camelCase al backend; armar el multipart a mano
  en vez de pasar `signature` por `buildTransitionRequest`; asumir que
  `history()` siempre pagina.

### `sinpapel-vue-components`

- Los 7 widgets con props/emits exactos:
  - `SeguimientoPanel` (compuesto: badge + pestañas Historial/Preview/
    Metadatos/SLA + diálogo de transición; crea su propio store desde props).
  - `StateBadge` (`estado`, `color`, `label`; humaniza `EN_REVISION`).
  - `HistoryTimeline` (`entries`, `page`, `pageSize`, `count`; emits
    `prev`/`next`).
  - `TransitionDialog` (`modelValue`, `client`, `currentState`, `estados`;
    emits `update:modelValue`, `transitioned`; validación; firma
    polimórfica FIEL client/server, manual, fake).
  - `PreviewTransitionPanel` (`client`, `targetState`; debounce 300ms).
  - `MetadatosForm` (`client`; emit `saved`).
  - `SlaStatusPanel` (`client`; admin only).
- Composición de `SeguimientoPanel` y por qué `:key="pk"` para remount.
- a11y: `role="dialog"`, `aria-modal`, `aria-live`, focus-trap; cleanup
  `onUnmounted` + `cancel()`.
- **Firma polimórfica** vive aquí (UI de `TransitionDialog`), ligada a
  `sinpapel-signing` (backend) y a `useTransition` (lógica, en
  `sinpapel-vue-store`).
- **Disparadores:** usar/parametrizar cualquiera de los 7 componentes,
  props/emits, a11y del diálogo, UI de firma.
- **Anti-patrones:** mutar props; no pasar `:key`; reimplementar la
  validación que ya hace `useTransition`.

### `sinpapel-vue-store`

- `useSeguimientoStore({ axios, resource, pk })`: setup-store factory de
  Pinia, `id` = `seguimiento-<resource>-<pk>`; `axios` vive como closure
  const (fuera del estado reactivo → no serializable fuera).
- Estado: `estados`, `historial`, `historialCount`, `metadatos`,
  `preview`, `slaActions`; `loading` granular
  (`{estados, historial, metadatos, transicion}`); `error`.
- Acciones: `cargarEstados/Historial/Metadatos/Preview`, `guardarMetadatos`,
  `ejecutarTransicion` (recarga estados+historial al terminar), `evaluarSla`,
  `cancel()` (aborta todo lo en vuelo).
- Normalización: `history()` → `results`/`count` o array plano; errores de
  cancelación se distinguen (`AbortError`/`CanceledError`/`ERR_CANCELED`) y
  no setean `error`.
- Composables: `useTransition(client)` (estado del form, `buildPayload`,
  `validate`, `submit`, `reset`, `signaturePayload`) y `useSpLabels()`.
  Funciones puras `buildSignaturePayload(backend, mode, fields)` y
  `buildPayload()`.
- Reglas de validación reales: estado destino obligatorio; monto > 0 si se
  da; FIEL server-side exige `.cer`/`.key`/password.
- **Disparadores:** usar el store o los composables, loading granular,
  cancelación, construir el payload de transición/firma.
- **Anti-patrones:** meter `axios` en el estado reactivo; tratar un
  `AbortError` como error real; reusar un store entre `pk` distintos sin
  remount.

## Frontmatter (convención del repo)

```yaml
tested_against:
  - sinpapel-vue@0.1.0
  - sinpapel-drf==0.2.1
applies_to:
  - "**/sinpapel-vue/**"          # los 4
  - "**/*.vue"                    # solo sinpapel-vue-components
```

`applies_to` exacto se afina por skill (p.ej. el de store puede apuntar a
`**/stores/*.js` y `**/composables/*.js`).

## Actualizaciones a archivos existentes

### `skills/sinpapel-overview/SKILL.md`
- Fila nueva en "Paquetes del ecosistema": `sinpapel-vue` — widgets Vue 3
  que consumen `sinpapel-drf`. Versión `0.1.0`.
- 4 filas en "Qué skill usar para qué tarea":
  - Instalar/montar la UI de seguimiento → `sinpapel-vue-setup`
  - Cliente REST JS contra sinpapel-drf → `sinpapel-vue-client`
  - Widgets Vue (panel, diálogo, timeline) → `sinpapel-vue-components`
  - Store Pinia / composables de seguimiento → `sinpapel-vue-store`
- Añadir `sinpapel-vue@0.1.0` a "Versiones contra las que se verificó".
- Referencia canónica: <https://github.com/aprendomx/sinpapel-vue>.

### `README.md`
- 4 filas nuevas en el catálogo de skills.
- Versión objetivo `sinpapel-vue==0.1.0` en el encabezado de versiones.

## Build y verificación

1. `python build_skills.py` — regenera `dist/` (claude/opencode/cursor/
   AGENTS.md). El generador escanea `skills/` (sin lista hardcodeada), así
   que los 4 directorios nuevos se recogen solos.
2. `python build_skills.py --verify` — idempotencia.
3. Sanity check: los nuevos `dist/claude/skills/sinpapel-vue-*` existen y
   `dist/AGENTS.md` los lista.

## Anclas de precisión (verificadas contra el código)

- Body en snake_case: `target_state`, `monto_aprobado`, `condiciones`.
- FIEL server-side = multipart con `signature.cer_file/key_file/password`;
  resto = JSON con `signature`.
- `buildSignaturePayload`: `fiel/server-side` → `{cer_file,key_file,password}`;
  `fiel/client-side` → `{firma_b64, certificado_cer_b64}`;
  `manual` → `{scanned_image_path, witness_name}`; `fake` → `{backend:'fake'}`.
- Store: `axios` como closure const; cancelación distingue
  `AbortError`/`CanceledError`/`ERR_CANCELED`.
- `history()` soporta paginado (`results`/`count`) y array plano.
- `createSinpapelClient` lanza si falta `axios` o `resource`.

## Fuera de alcance (YAGNI)

- No reimplementar componentes ni añadir features a `sinpapel-vue`.
- No documentar internals de Quasar.
- No auto-descubrimiento de `resource` (no existe en v1).
- No scripts/assets nuevos salvo que un ejemplo lo exija.
