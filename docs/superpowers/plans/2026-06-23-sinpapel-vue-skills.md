# sinpapel-vue Skills Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Añadir 4 skills finos (`sinpapel-vue-setup`, `-client`, `-components`, `-store`) que documentan cómo usar la librería Vue 3 `@aprendomx/sinpapel-vue`, y enrutarlos desde `sinpapel-overview` y el `README`.

**Architecture:** Cada skill se escribe una sola vez en `skills/<nombre>/SKILL.md` (fuente canónica). El generador `build_skills.py` escanea `skills/` (sin lista hardcodeada) y produce `dist/` para Claude/OpenCode/Cursor + `AGENTS.md`. No se edita `dist/` a mano.

**Tech Stack:** Markdown + frontmatter YAML; `build_skills.py` (Python ≥3.10, PyYAML). Conocimiento verificado contra `../sinpapel-vue` (`@aprendomx/sinpapel-vue@0.1.0`) y `sinpapel-drf==0.2.1`.

## Global Constraints

- **Idioma:** español en todo el contenido de las skills.
- **`name`:** kebab-case `sinpapel-vue-<capa>`.
- **`description`:** tercera persona, empieza con "Usar siempre que…", lista disparadores concretos (símbolos del código, archivos, síntomas).
- **`tested_against`:** incluir `sinpapel-vue@0.1.0` y `sinpapel-drf==0.2.1` en cada skill nuevo.
- **Ejemplos verificados contra el código real** de `../sinpapel-vue` — NO inventar nombres. Anclas: body snake_case (`target_state`, `monto_aprobado`, `condiciones`); FIEL server-side = `multipart/form-data` con claves `signature.<campo>`; resto = JSON con bloque `signature`; `axios` vive como closure const fuera del estado del store; `createSinpapelClient` lanza si falta `axios` o `resource`.
- **Cada skill enumera anti-patrones explícitos.**
- **Nunca editar `dist/`** — se regenera con `python build_skills.py`.
- Encabezados de `description` no exceden lo razonable; seguir el estilo de los skills existentes (`sinpapel-designer`, `sinpapel-drf`).

---

### Task 1: Skill `sinpapel-vue-setup`

**Files:**
- Create: `skills/sinpapel-vue-setup/SKILL.md`
- Reference (solo lectura, para verificar nombres): `../sinpapel-vue/README.md`, `../sinpapel-vue/src/index.js`, `../sinpapel-vue/src/styles/tokens.css`, `../sinpapel-vue/src/composables/useSpLabels.js`, `../sinpapel-vue/package.json`

**Interfaces:**
- Consumes: nada (primer task).
- Produces: el nombre de skill `sinpapel-vue-setup` (referenciado por `sinpapel-overview` en Task 5 y por los anti-patrones cruzados de otros skills). Símbolos cubiertos: `SeguimientoPanel` (mount), prop `locale`, variables `--sp-*`, import `@aprendomx/sinpapel-vue/style.css`.

- [ ] **Step 1: Verificar nombres reales contra el código**

Run: `cat ../sinpapel-vue/src/index.js ../sinpapel-vue/package.json && grep -n "^  --sp" ../sinpapel-vue/src/styles/tokens.css | head`
Expected: confirma exports (`createSinpapelClient`, `SeguimientoPanel`, etc.), `peerDependencies` (`vue`/`pinia`/`quasar`), export `./style.css`, y prefijos `--sp-*`. Anota cualquier discrepancia con el spec antes de escribir.

- [ ] **Step 2: Escribir `skills/sinpapel-vue-setup/SKILL.md`**

Crear el archivo con este contenido (ajustar variables `--sp-*` exactas si Step 1 reveló nombres distintos):

```markdown
---
name: sinpapel-vue-setup
description: Usar siempre que el usuario instale o integre la librería @aprendomx/sinpapel-vue (widgets Vue 3 de seguimiento de flujos), configure sus peer deps (vue/pinia/quasar), importe @aprendomx/sinpapel-vue/style.css, monte SeguimientoPanel, sobrescriba la tematización --sp-*, cambie el locale (es/en), o pregunte qué es la librería frente a sinpapel-designer. Cubre que CONSUME sinpapel-drf y NO es un backend.
tested_against:
  - sinpapel-vue@0.1.0
  - sinpapel-drf==0.2.1
applies_to:
  - "**/sinpapel-vue/**"
  - "**/quasar*.{js,ts,conf,config}"
---

# sinpapel-vue — instalación y arranque

## Qué es (y qué NO es)

- **Es**: biblioteca de componentes **Vue 3** (`@aprendomx/sinpapel-vue`)
  para *seguir/operar* una instancia de flujo consumiendo la API REST de
  `sinpapel-drf`. Widgets `q-*` reutilizan **Quasar**.
- **No es**: un backend, ni `sinpapel-designer`. `sinpapel-designer` *diseña*
  flujos (SPA standalone); esta librería *opera* una instancia existente.
- **No** auto-descubre el `resource` slug (v1): el consumidor lo pasa.

## Instalación

\`\`\`bash
npm install @aprendomx/sinpapel-vue
# peer deps OBLIGATORIAS:
npm install vue pinia quasar
\`\`\`

Peer deps: `vue ^3.5`, `pinia ^3`, `quasar ^2.16`. Quasar no es opcional:
los widgets usan `q-dialog`, `q-icon`, etc.

## Estilos

Importa el CSS una vez (p.ej. en el entry de la app):

\`\`\`js
import '@aprendomx/sinpapel-vue/style.css'
\`\`\`

## Quick-start

\`\`\`vue
<script setup>
import axios from 'axios'
import { SeguimientoPanel } from '@aprendomx/sinpapel-vue'
import '@aprendomx/sinpapel-vue/style.css'

const http = axios.create({ withCredentials: true })
</script>

<template>
  <SeguimientoPanel
    :axios="http"
    base-path="/sinpapel/api"
    resource="solicitudes"
    :pk="42"
    current-state="EN_REVISION"
  />
</template>
\`\`\`

- `resource` = `effective_slug` del modelo decorado con `@workflow_enabled`
  (ver `sinpapel-drf`). No hay auto-descubrimiento.
- Si `pk`/`resource` cambian dinámicamente, pasa `:key="pk"` para forzar
  remount (el panel crea su store desde las props iniciales).

## Exports

Desde `@aprendomx/sinpapel-vue` (ver `src/index.js`): `createSinpapelClient`,
`buildTransitionRequest`, `useTransition`, `buildSignaturePayload`,
`useSeguimientoStore`, y los componentes `StateBadge`, `HistoryTimeline`,
`TransitionDialog`, `PreviewTransitionPanel`, `MetadatosForm`,
`SlaStatusPanel`, `SeguimientoPanel`.

Detalle por capa: `sinpapel-vue-client`, `sinpapel-vue-components`,
`sinpapel-vue-store`.

## Tematización

Sobrescribe variables `--sp-*` en tu scope (ver `src/styles/tokens.css`):

\`\`\`css
:root {
  --sp-color-primary: #3a4a5c;
  --sp-surface: #ffffff;
  --sp-border: #dfe3e8;
}
\`\`\`

## i18n

`locale` acepta `es` (default) y `en`, sin deps externas:

\`\`\`vue
<SeguimientoPanel ... locale="en" />
\`\`\`

Nuevo idioma: archivo en `src/locales/` + registro en `useSpLabels.js`.

## Anti-patrones

- ❌ Olvidar `import '@aprendomx/sinpapel-vue/style.css'` → widgets sin estilo.
- ❌ Omitir Quasar como peer dep → componentes `q-*` rotos.
- ❌ Esperar que la librería descubra el `resource` slug sola.
- ❌ Cambiar `pk`/`resource` sin `:key` → el store no se reinicia.
- ❌ Confundirla con `sinpapel-designer` (diseña flujos, no los opera).
```

- [ ] **Step 3: Verificar que el frontmatter parsea**

Run: `python build_skills.py && ls dist/claude/skills/sinpapel-vue-setup/SKILL.md`
Expected: build sin errores y el archivo existe en `dist/`.

- [ ] **Step 4: Commit**

```bash
git add skills/sinpapel-vue-setup/ dist/
git commit -m "feat(skills): sinpapel-vue-setup (instalación y arranque)"
```

---

### Task 2: Skill `sinpapel-vue-client`

**Files:**
- Create: `skills/sinpapel-vue-client/SKILL.md`
- Reference: `../sinpapel-vue/src/client/sinpapelClient.js`

**Interfaces:**
- Consumes: nombre `sinpapel-vue-setup` (cross-link en cuerpo).
- Produces: nombre `sinpapel-vue-client`. Símbolos cubiertos: `createSinpapelClient({axios, basePath, resource, pk, signal})`, `buildTransitionRequest(payload)`, métodos `availableTransitions/history/previewTransition/getMetadatos/patchMetadatos/slaStatus/transition`.

- [ ] **Step 1: Verificar firmas reales**

Run: `cat ../sinpapel-vue/src/client/sinpapelClient.js`
Expected: confirma defaults (`basePath='/sinpapel/api'`, `pk=null`), que lanza si falta `axios`/`resource`, el body `{ target_state }` en preview, el `page_size` en history, y el branch multipart de `buildTransitionRequest`.

- [ ] **Step 2: Escribir `skills/sinpapel-vue-client/SKILL.md`**

```markdown
---
name: sinpapel-vue-client
description: Usar siempre que el usuario cree o use el cliente REST JS de sinpapel-vue (createSinpapelClient), llame uno de sus 7 métodos (availableTransitions, history, previewTransition, getMetadatos, patchMetadatos, slaStatus, transition), mapee llamadas a los endpoints de sinpapel-drf, cancele requests con AbortController/signal, o use buildTransitionRequest para codificar el payload de transición (JSON vs multipart FIEL). 
tested_against:
  - sinpapel-vue@0.1.0
  - sinpapel-drf==0.2.1
applies_to:
  - "**/sinpapel-vue/**"
  - "**/client/sinpapelClient.js"
---

# sinpapel-vue — cliente REST

## Crear el cliente

\`\`\`js
import { createSinpapelClient } from '@aprendomx/sinpapel-vue'

const client = createSinpapelClient({
  axios: http,                 // requerido (lanza si falta)
  basePath: '/sinpapel/api',   // default
  resource: 'solicitudes',     // requerido (lanza si falta)
  pk: 42,                      // mutable: client.pk = 7
  signal,                      // opcional: AbortController.signal
})
\`\`\`

`createSinpapelClient` lanza `Error` si falta `axios` o `resource`. La URL
base se calcula en cada llamada: `{basePath}/{resource}/{pk}` (lee
`client.resource`/`client.pk` en vivo).

## Métodos → endpoints sinpapel-drf

| Método | HTTP | Ruta | Body / params |
|---|---|---|---|
| `availableTransitions()` | GET | `…/available-transitions/` | — |
| `history({page, pageSize})` | GET | `…/history/` | params `page`, `page_size` |
| `previewTransition(targetState, {signal})` | POST | `…/preview-transition/` | `{ target_state }` |
| `getMetadatos()` | GET | `…/metadatos/` | — |
| `patchMetadatos(values)` | PATCH | `…/metadatos/` | `values` |
| `slaStatus()` | POST | `…/sla-status/` | `null` |
| `transition(payload)` | POST | `…/transition/` | JSON o multipart |

Cada método retorna `data` de axios. Todos propagan `signal` si se pasó al
crear el cliente.

## Payload de transición — `buildTransitionRequest`

El body usa **snake_case**: `target_state`, `comentarios`, `monto_aprobado`,
`condiciones`, y opcional `signature`.

- **FIEL server-side** (`signature.backend==='fiel'` y
  `signature.mode==='server-side'`) → `multipart/form-data` con claves DRF
  punteadas: `signature.backend`, `signature.mode`, `signature.cer_file`,
  `signature.key_file`, `signature.password`.
- **Todo lo demás** → JSON con el bloque `signature` anidado.

\`\`\`js
// JSON (fake/manual/fiel client-side o sin firma):
await client.transition({
  target_state: 'APROBADA',
  comentarios: 'OK',
  signature: { backend: 'fake' },
})
\`\`\`

`buildTransitionRequest(payload)` devuelve `{ body, config }`; normalmente no
lo llamas tú directo — `transition()` lo usa internamente. La forma del
bloque `signature` la produce `buildSignaturePayload` (ver
`sinpapel-vue-store`).

## Cancelación

Pasa `signal` (de un `AbortController`) al crear el cliente y se propaga a
cada request. El store (`sinpapel-vue-store`) ya gestiona esto con
`cancel()`; usa el cliente crudo con `signal` solo si manejas axios a mano.

## Errores

El cliente **no normaliza** errores: deja propagar el error de axios. Lee
`e.response?.data` (o `{ detail: e.message }` como fallback). La
normalización vive en el store/composable.

## Anti-patrones

- ❌ Enviar camelCase al backend (`targetState`, `montoAprobado`). Usa
  snake_case.
- ❌ Armar el `FormData` multipart a mano: pasa `signature` y deja que
  `buildTransitionRequest` decida JSON vs multipart.
- ❌ Asumir que `history()` siempre pagina: puede venir array plano o
  `{results, count}` (lo normaliza el store).
- ❌ Crear el cliente sin `axios`/`resource` (lanza en construcción).
```

- [ ] **Step 3: Build**

Run: `python build_skills.py && ls dist/claude/skills/sinpapel-vue-client/SKILL.md`
Expected: build OK, archivo presente.

- [ ] **Step 4: Commit**

```bash
git add skills/sinpapel-vue-client/ dist/
git commit -m "feat(skills): sinpapel-vue-client (cliente REST y endpoints)"
```

---

### Task 3: Skill `sinpapel-vue-components`

**Files:**
- Create: `skills/sinpapel-vue-components/SKILL.md`
- Reference: `../sinpapel-vue/README.md` (sección Componentes), `../sinpapel-vue/src/components/*.vue`

**Interfaces:**
- Consumes: nombres `sinpapel-vue-setup`, `sinpapel-vue-store`, `sinpapel-signing` (cross-links).
- Produces: nombre `sinpapel-vue-components`. Símbolos cubiertos: `SeguimientoPanel`, `StateBadge`, `HistoryTimeline`, `TransitionDialog`, `PreviewTransitionPanel`, `MetadatosForm`, `SlaStatusPanel` con sus props/emits.

- [ ] **Step 1: Verificar props/emits reales**

Run: `grep -nE "defineProps|defineEmits|emit\(|props\." ../sinpapel-vue/src/components/*.vue`
Expected: confirma las props y emits documentados (p.ej. `HistoryTimeline` emite `prev`/`next`; `TransitionDialog` emite `update:modelValue` y `transitioned`; `MetadatosForm` emite `saved`). Corregir la tabla si difiere.

- [ ] **Step 2: Escribir `skills/sinpapel-vue-components/SKILL.md`**

```markdown
---
name: sinpapel-vue-components
description: Usar siempre que el usuario use o parametrice los componentes Vue de sinpapel-vue (SeguimientoPanel, StateBadge, HistoryTimeline, TransitionDialog, PreviewTransitionPanel, MetadatosForm, SlaStatusPanel), sus props/emits, la composición de pestañas del panel, el remount con :key, la accesibilidad del diálogo, o la UI de firma polimórfica (FIEL client/server-side, manual, fake) en TransitionDialog.
tested_against:
  - sinpapel-vue@0.1.0
  - sinpapel-drf==0.2.1
applies_to:
  - "**/sinpapel-vue/**"
  - "**/*.vue"
---

# sinpapel-vue — componentes

## SeguimientoPanel (compuesto)

Widget principal: badge de estado + pestañas (Historial / Previsualizar /
Metadatos / SLA) + diálogo de transición. Crea su propio store desde props.

| Prop | Tipo | Req | Default |
|---|---|---|---|
| `axios` | Object | Sí | — |
| `basePath` | string | No | `/sinpapel/api` |
| `resource` | string | Sí | — |
| `pk` | number\|string | Sí | — |
| `currentState` | string | No | `''` |
| `canEvaluateSla` | boolean | No | `false` |
| `locale` | string | No | `'es'` |

Emits: ninguno (todo vía el store interno). Remount con `:key="pk"` si
cambian `pk`/`resource`.

## Componentes hoja

### StateBadge
Props: `estado` (req), `color`, `label`. Humaniza el estado
(`EN_REVISION` → `EN REVISION`). Con `color`, usa `color-mix` para el fondo.

### HistoryTimeline
Props: `entries` (`[]`), `page` (`1`), `pageSize` (`0` = sin paginación),
`count` (`0`). Emits: `prev`, `next`.

### TransitionDialog
Props: `modelValue` (`false`), `client` (req), `currentState` (`''`),
`estados` (`[]`). Emits: `update:modelValue`, `transitioned(result)`.
Selector de estado destino, comentarios, monto aprobado, condiciones y
**firma polimórfica**. Validación: estado destino obligatorio; monto > 0 si
se da; FIEL server-side exige `.cer`/`.key`/contraseña. La lógica del form
vive en `useTransition` (ver `sinpapel-vue-store`).

### PreviewTransitionPanel
Props: `client` (req), `targetState` (`''`). Debounce 300ms sobre
`targetState`.

### MetadatosForm
Props: `client` (req). Emits: `saved(values)`. Formulario generado desde el
schema de metadatos del backend.

### SlaStatusPanel
Props: `client` (req). Evalúa SLAs (admin only).

## Firma polimórfica (en TransitionDialog)

Cuatro backends, ligados al backend `sinpapel-signing`:

- **FIEL client-side**: `firma_b64`, `certificado_cer_b64`.
- **FIEL server-side**: archivos `.cer`/`.key` + contraseña → la librería
  manda multipart (ver `sinpapel-vue-client`).
- **manual**: `scanned_image_path`, `witness_name`.
- **fake**: sin campos (tests/demo).

La forma del payload la arma `buildSignaturePayload` (ver
`sinpapel-vue-store`).

## Accesibilidad y ciclo de vida

- Diálogos: `role="dialog"`, `aria-modal`, `aria-live`, focus-trap.
- Cleanup automático al desmontar (`onUnmounted` + `cancel()` del store).

## Anti-patrones

- ❌ Mutar props directamente (usa emits / el store).
- ❌ No pasar `:key="pk"` cuando cambia la instancia.
- ❌ Reimplementar la validación del form: ya la hace `useTransition`.
- ❌ Construir el multipart de firma en el componente: pásalo por el
  `client`/store.
```

- [ ] **Step 3: Build**

Run: `python build_skills.py && ls dist/claude/skills/sinpapel-vue-components/SKILL.md`
Expected: build OK, archivo presente.

- [ ] **Step 4: Commit**

```bash
git add skills/sinpapel-vue-components/ dist/
git commit -m "feat(skills): sinpapel-vue-components (7 widgets, props/emits, firma)"
```

---

### Task 4: Skill `sinpapel-vue-store`

**Files:**
- Create: `skills/sinpapel-vue-store/SKILL.md`
- Reference: `../sinpapel-vue/src/stores/useSeguimientoStore.js`, `../sinpapel-vue/src/composables/useTransition.js`, `../sinpapel-vue/src/composables/useSpLabels.js`

**Interfaces:**
- Consumes: nombres `sinpapel-vue-client`, `sinpapel-vue-components`.
- Produces: nombre `sinpapel-vue-store`. Símbolos cubiertos: `useSeguimientoStore`, `useTransition`, `useSpLabels`, `buildSignaturePayload`, acciones `cargarEstados/Historial/Metadatos/Preview`, `guardarMetadatos`, `ejecutarTransicion`, `evaluarSla`, `cancel`.

- [ ] **Step 1: Verificar API real del store y composables**

Run: `cat ../sinpapel-vue/src/stores/useSeguimientoStore.js ../sinpapel-vue/src/composables/useTransition.js`
Expected: confirma el `id` del store (`seguimiento-<resource>-<pk>`), el set de `loading` (`estados/historial/metadatos/transicion`), la detección de cancelación (`AbortError`/`CanceledError`/`ERR_CANCELED`), y los retornos de `buildSignaturePayload` por backend×mode.

- [ ] **Step 2: Escribir `skills/sinpapel-vue-store/SKILL.md`**

```markdown
---
name: sinpapel-vue-store
description: Usar siempre que el usuario use el store Pinia useSeguimientoStore de sinpapel-vue o sus composables useTransition/useSpLabels, gestione loading granular (estados/historial/metadatos/transicion), cancele requests con cancel(), construya el payload de transición/firma (buildPayload/buildSignaturePayload), valide el formulario de transición, o normalice el historial paginado del backend.
tested_against:
  - sinpapel-vue@0.1.0
  - sinpapel-drf==0.2.1
applies_to:
  - "**/sinpapel-vue/**"
  - "**/stores/useSeguimientoStore.js"
  - "**/composables/use*.js"
---

# sinpapel-vue — store y composables

## useSeguimientoStore

Factory de setup-store de Pinia, keyed por `(resource, pk)`:

\`\`\`js
import { useSeguimientoStore } from '@aprendomx/sinpapel-vue'

const store = useSeguimientoStore({ axios: http, resource: 'solicitudes', pk: 42 })
\`\`\`

`id` interno: `seguimiento-<resource>-<pk>`. **`axios` vive como closure
const, fuera del estado reactivo** (no es serializable; no debe entrar al
store). Por eso instancias distintas por `pk` tienen stores distintos —
remount con `:key` en el componente.

### Estado
`estados`, `historial`, `historialCount`, `metadatos` (`{schema, values}`),
`preview`, `slaActions`, `error`, y `loading` granular:
`{ estados, historial, metadatos, transicion }`.

### Acciones
- `cargarEstados()` → `availableTransitions()`.
- `cargarHistorial(page=1)` → normaliza array plano o `{results, count}`.
- `ejecutarTransicion(payload)` → `transition()` y luego recarga
  `cargarEstados()` + `cargarHistorial()`.
- `cargarMetadatos()` / `guardarMetadatos(values)`.
- `cargarPreview(targetState)` / `evaluarSla()`.
- `cancel()` → aborta todas las requests en vuelo (`AbortController` por
  acción).

### Cancelación
Los errores de cancelación (`AbortError`, `CanceledError`, `ERR_CANCELED`)
se re-lanzan **sin** setear `error.value`. Cualquier otro error setea
`error.value = e.response?.data ?? { detail: e.message }`.

## useTransition(client)

Estado y lógica del formulario de transición:

\`\`\`js
const tx = useTransition(client)
tx.targetState.value = 'APROBADA'
tx.comentarios.value = 'Aprobado por comité'
await tx.submit()  // valida, arma payload, envía, resetea en éxito
\`\`\`

Expone: `targetState`, `comentarios`, `montoAprobado`, `condiciones`,
`signatureBackend`, `signatureMode`, `signatureFields`, `signaturePayload`
(computed), `loading`, `error`, `errors`, `buildPayload`, `submit`,
`reset`, `validate`.

### Validación (`validate()`)
- Estado destino obligatorio.
- `montoAprobado` > 0 si se proporciona.
- FIEL server-side: `.cer`, `.key` y contraseña obligatorios.

### buildSignaturePayload(backend, mode, fields)
Función pura (espeja `SignatureRequestSerializer`):
- `fiel` + `server-side` → `{ backend, mode, cer_file, key_file, password }`.
- `fiel` (client-side) → `{ backend, mode:'client-side', firma_b64, certificado_cer_b64 }`.
- `manual` → `{ backend, scanned_image_path, witness_name }`.
- `fake` → `{ backend: 'fake' }`.
- `null`/desconocido → `null`.

`buildPayload()` arma `{ target_state, comentarios?, monto_aprobado?,
condiciones?, signature? }` en snake_case.

## useSpLabels()

Devuelve las etiquetas localizadas (`es`/`en`). Se usa automáticamente
dentro de los hijos de `SeguimientoPanel`; llámalo directo solo si compones
componentes a mano.

## Anti-patrones

- ❌ Meter `axios` en el estado reactivo del store.
- ❌ Tratar un `AbortError`/`CanceledError` como error real de la API.
- ❌ Reusar un store entre `pk` distintos sin remount (`:key`).
- ❌ Construir el bloque `signature` a mano en vez de
  `buildSignaturePayload`/`useTransition`.
- ❌ Enviar el payload en camelCase (usa `buildPayload`, que es snake_case).
```

- [ ] **Step 3: Build**

Run: `python build_skills.py && ls dist/claude/skills/sinpapel-vue-store/SKILL.md`
Expected: build OK, archivo presente.

- [ ] **Step 4: Commit**

```bash
git add skills/sinpapel-vue-store/ dist/
git commit -m "feat(skills): sinpapel-vue-store (store Pinia y composables)"
```

---

### Task 5: Enrutado en `sinpapel-overview` y catálogo en `README`

**Files:**
- Modify: `skills/sinpapel-overview/SKILL.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: los 4 nombres de skill (`sinpapel-vue-setup`, `-client`, `-components`, `-store`) de Tasks 1-4.
- Produces: nada (último task de contenido).

- [ ] **Step 1: Añadir `sinpapel-vue` a la tabla "Paquetes del ecosistema" de `sinpapel-overview/SKILL.md`**

En la tabla que termina en la fila `sinpapel-designer`, añadir tras ella:

```markdown
| `sinpapel-vue` | Widgets Vue 3 que consumen `sinpapel-drf` para seguir flujos en el frontend. | 0.1.0 |
```

- [ ] **Step 2: Añadir 4 filas a la tabla "Qué skill usar para qué tarea"**

Tras la fila `| Escribir tests sin tocar FIEL real ni red. | sinpapel-testing |`, añadir:

```markdown
| Instalar/montar la UI de seguimiento (Vue). | `sinpapel-vue-setup` |
| Consumir la API REST desde JS (cliente). | `sinpapel-vue-client` |
| Usar los widgets Vue (panel, diálogo, timeline). | `sinpapel-vue-components` |
| Store Pinia y composables de seguimiento. | `sinpapel-vue-store` |
```

- [ ] **Step 3: Añadir la versión verificada en `sinpapel-overview/SKILL.md`**

En el bloque "Versiones contra las que se verificó este conjunto de skills", tras la línea `sinpapel-designer @ rama main (S27.8+)`, añadir:

```
sinpapel-vue @ npm @aprendomx/sinpapel-vue@0.1.0
```

Y en "Referencias canónicas", tras la línea del Designer, añadir:

```markdown
- Vue widgets: <https://github.com/aprendomx/sinpapel-vue>
```

- [ ] **Step 4: Añadir 4 filas al catálogo del `README.md`**

En la tabla "Catálogo de skills", tras la fila `sinpapel-designer`, añadir:

```markdown
| `sinpapel-vue-setup` | Instalación de `@aprendomx/sinpapel-vue`, peer deps, `style.css`, temas `--sp-*`, i18n, quick-start. |
| `sinpapel-vue-client` | `createSinpapelClient`, 7 métodos → endpoints `sinpapel-drf`, `AbortController`, `buildTransitionRequest`. |
| `sinpapel-vue-components` | 7 widgets (`SeguimientoPanel`…), props/emits, a11y, firma polimórfica en `TransitionDialog`. |
| `sinpapel-vue-store` | Store Pinia `useSeguimientoStore`, composables `useTransition`/`useSpLabels`, loading granular, `cancel()`. |
```

- [ ] **Step 5: Añadir la versión objetivo en el encabezado del `README.md`**

En el párrafo "**Versiones objetivo:**", añadir al final de la lista:
`, sinpapel-vue@0.1.0`.

- [ ] **Step 6: Regenerar y verificar idempotencia**

Run: `python build_skills.py && python build_skills.py --verify`
Expected: regenera sin errores; `--verify` confirma idempotencia (sin diffs). `dist/AGENTS.md` lista los 4 skills nuevos.

- [ ] **Step 7: Sanity check del dist**

Run: `ls dist/claude/skills/ | grep sinpapel-vue && grep -c "sinpapel-vue" dist/AGENTS.md`
Expected: los 4 directorios `sinpapel-vue-*` y al menos 4 menciones en `AGENTS.md`.

- [ ] **Step 8: Commit**

```bash
git add skills/sinpapel-overview/ README.md dist/
git commit -m "docs(skills): enrutar sinpapel-vue desde overview y README"
```

---

## Self-Review

**1. Spec coverage:**
- 4 skills (setup/client/components/store) → Tasks 1-4. ✓
- Frontmatter `tested_against`/`applies_to` → cada task Step 2. ✓
- Anti-patrones por skill → incluidos en cada SKILL.md. ✓
- Actualizar `sinpapel-overview` (misma tabla de paquetes, confirmado por el usuario) → Task 5 Steps 1-3. ✓
- Actualizar `README` (catálogo + versión) → Task 5 Steps 4-5. ✓
- Build + `--verify` → Task 5 Steps 6-7 (y build por task). ✓
- Anclas de precisión (snake_case, multipart FIEL, closure axios, cancelación) → incorporadas en el contenido de Tasks 2-4. ✓

**2. Placeholder scan:** Sin TBD/TODO; cada SKILL.md está escrito completo. Step 1 de cada task verifica nombres contra el código y permite corregir antes de escribir (no es un placeholder, es validación). ✓

**3. Type consistency:** Nombres de símbolos consistentes entre tasks: `createSinpapelClient`, `buildTransitionRequest`, `buildSignaturePayload`, `buildPayload`, `useSeguimientoStore`, `useTransition`, `useSpLabels`, y los 7 componentes — coinciden con `../sinpapel-vue/src/index.js`. Los 4 nombres de skill referenciados en Task 5 coinciden con los creados en Tasks 1-4. ✓
