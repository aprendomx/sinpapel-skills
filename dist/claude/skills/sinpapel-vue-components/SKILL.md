---
name: sinpapel-vue-components
description: Usar siempre que el usuario use o parametrice los componentes Vue de sinpapel-vue (SeguimientoPanel, StateBadge, HistoryTimeline, TransitionDialog, PreviewTransitionPanel, MetadatosForm, SlaStatusPanel, RequisitosPanel, DocumentosPanel), sus props/emits, la composición de pestañas del panel, el remount con :key, la accesibilidad del diálogo, la UI de cumplimiento/carga documental, o la UI de firma polimórfica (FIEL client/server-side, manual, fake) en TransitionDialog.
tested_against:
  - sinpapel-vue@0.3.0
  - sinpapel-drf==0.4.0
applies_to:
  - "**/sinpapel-vue/**"
  - "**/*.vue"
---

# sinpapel-vue — componentes

## SeguimientoPanel (compuesto)

Widget principal: badge de estado + pestañas (Historial / Requisitos /
Documentos / Previsualizar / Metadatos / SLA) + diálogo de transición. Crea
su propio store desde props. Las pestañas **Requisitos** y **Documentos**
(0.2.0) requieren `sinpapel-drf >= 0.3.0`; la pestaña SLA solo aparece con
`canEvaluateSla`.

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
Selector de estado destino, comentarios, condiciones y **firma polimórfica**.
Validación: estado destino obligatorio; FIEL server-side exige
`.cer`/`.key`/contraseña. La lógica del form vive en `useTransition` (ver
`sinpapel-vue-store`). *(sinpapel-vue 0.3.0 eliminó el campo monto aprobado,
alineado con sinpapel 0.7.0.)*

### PreviewTransitionPanel
Props: `client` (req), `targetState` (`''`). Debounce 300ms sobre
`targetState`.

### MetadatosForm
Props: `client` (req). Emits: `saved(values)`. Formulario generado desde el
schema de metadatos del backend.

### SlaStatusPanel
Props: `client` (req). Evalúa SLAs (admin only).

### RequisitosPanel (0.2.0)
Props: `client` (req). Checklist **read-only** del cumplimiento documental
del estado actual (`client.requisitos()`). Pinta ✓/○ por requisito con
`porcentaje_actual / porcentaje_requerido` y mensaje. Carga al montar;
`defineExpose({ load, items })` para refrescar desde fuera.

### DocumentosPanel (0.2.0; selects dependientes en 0.3.0)
Props: `client` (req). Emits: `changed`. Lista las `InstanciaDocumento` del
trámite + formulario de carga y borrado. Sube vía `client.uploadDocumento` y
borra vía `client.deleteDocumento`. Emite `changed` tras subir/borrar para que
el contenedor refresque requisitos. Usa el `client` directo (no toca el store).

**Carga con selects dependientes (sinpapel-vue 0.3.0, requiere
`sinpapel-drf >= 0.4.0`):** el formulario ya no pide `documento`/`tipo_documento`
como inputs numéricos ni `porcentaje`. En su lugar:
- Llama `client.requisitos()` al montar (`loadRequisitos`) y filtra los items
  `nivel === 'requisito_documento'` con `tipo_documento_id`.
- `<select>` de **tipo** (los tipos exigidos por el estado) y `<select>`
  **dependiente** de documento poblado desde `documentos_disponibles`
  (`[{id, nombre}]`, ej. "Identificación" → "Pasaporte"/"INE"). Si el tipo trae
  una sola opción, se autoselecciona.
- Sube solo `{ archivo, documento: documentoId }`; el `porcentaje` lo define la
  config del requisito en el backend.
- Si el estado no exige documentos (sin tipos), muestra un aviso en vez del
  formulario. `defineExpose` añade `tipos`, `selectedTipoId`, `documentoId`,
  `loadRequisitos`.

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
