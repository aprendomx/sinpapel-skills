---
name: sinpapel-vue-store
description: Usar siempre que el usuario use el store Pinia useSeguimientoStore de sinpapel-vue o sus composables useTransition/useSpLabels, gestione loading granular (estados/historial/metadatos/transicion/documentos/requisitos), cancele requests con cancel(), cargue o suba documentos (cargarDocumentos/cargarRequisitos/subirDocumento/eliminarDocumento), construya el payload de transición/firma (buildPayload/buildSignaturePayload), valide el formulario de transición, o normalice el historial paginado del backend.
tested_against:
  - sinpapel-vue@0.2.0
  - sinpapel-drf==0.3.0
applies_to:
  - "**/sinpapel-vue/**"
  - "**/stores/useSeguimientoStore.js"
  - "**/composables/use*.js"
---

# sinpapel-vue — store y composables

## useSeguimientoStore

Factory de setup-store de Pinia, keyed por `(resource, pk)`:

```js
import { useSeguimientoStore } from '@aprendomx/sinpapel-vue'

const store = useSeguimientoStore({ axios: http, resource: 'solicitudes', pk: 42 })
```

`id` interno: `seguimiento-<resource>-<pk>`. **`axios` vive como closure
const, fuera del estado reactivo** (no es serializable; no debe entrar al
estado del store — aunque el objeto `client` generado por `makeClient()` sí
se retorna como parte de la API pública). Por eso instancias distintas por
`pk` tienen stores distintos — remount con `:key` en el componente.

### Estado
`estados`, `historial`, `historialCount`, `metadatos` (`{schema, values}`),
`preview`, `slaActions`, `documentos`, `requisitos`, `error`, y `loading`
granular: `{ estados, historial, metadatos, transicion, documentos,
requisitos }`.

### Acciones
- `cargarEstados()` → `availableTransitions()`.
- `cargarHistorial(page=1)` → normaliza array plano o `{results, count}`.
- `ejecutarTransicion(payload)` → `transition()` y luego recarga
  `cargarEstados()` + `cargarHistorial()`.
- `cargarMetadatos()` / `guardarMetadatos(values)`.
- `cargarDocumentos()` → `listDocumentos()` (loading `documentos`).
- `cargarRequisitos()` → `requisitos()` (loading `requisitos`).
- `subirDocumento(payload)` / `eliminarDocumento(docId)` → suben/borran y
  luego refrescan **lista + requisitos** (`cargarDocumentos()` +
  `cargarRequisitos()`); ambas marcan loading `documentos`.
- `cargarPreview(targetState)` / `evaluarSla()`.
  > `cargarPreview` y `evaluarSla` no pasan por el wrapper interno: no marcan `loading` ni setean `error.value` en fallo (sólo limpian su cliente).
- `cancel()` → aborta todas las requests en vuelo (un `AbortController` por
  request en vuelo, rastreado en un Set `inFlight` compartido).

Las acciones de documentos requieren `sinpapel-drf >= 0.3.0`.

### Cancelación
Los errores de cancelación (`AbortError`, `CanceledError`, `ERR_CANCELED`)
se re-lanzan **sin** setear `error.value`. Cualquier otro error setea
`error.value = e.response?.data ?? { detail: e.message }`.

## useTransition(client)

Estado y lógica del formulario de transición:

```js
const tx = useTransition(client)
tx.targetState.value = 'APROBADA'
tx.comentarios.value = 'Aprobado por comité'
await tx.submit()  // valida, arma payload, envía, resetea en éxito
```

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
