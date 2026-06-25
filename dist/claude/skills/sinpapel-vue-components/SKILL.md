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
