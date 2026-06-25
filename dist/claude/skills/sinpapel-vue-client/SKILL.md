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

```js
import { createSinpapelClient } from '@aprendomx/sinpapel-vue'

const client = createSinpapelClient({
  axios: http,                 // requerido (lanza si falta)
  basePath: '/sinpapel/api',   // default
  resource: 'solicitudes',     // requerido (lanza si falta)
  pk: 42,                      // mutable: client.pk = 7
  signal,                      // opcional: AbortController.signal
})
```

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

```js
// JSON (fake/manual/fiel client-side o sin firma):
await client.transition({
  target_state: 'APROBADA',
  comentarios: 'OK',
  signature: { backend: 'fake' },
})
```

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
