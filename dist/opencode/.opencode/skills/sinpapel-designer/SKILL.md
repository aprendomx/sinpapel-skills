---
name: sinpapel-designer
description: Usar siempre que el usuario diseñe visualmente un flujo sinpapel, instale o ejecute sinpapel-designer (Vue 3 + Quasar + Vue Flow), exporte / importe JSON v0.2, integre el designer con un backend Django vía sinpapel_export_flujo / sinpapel_import_flujo, configure el generador IA (Anthropic / OpenAI / OpenCode), o pregunte cómo embeber el designer en otra app (S27.9). Cubre que es una SPA standalone, NO un paquete Django.
tested_against:
  - sinpapel-designer@S27.8
  - sinpapel==0.5.1
applies_to:
  - "**/sinpapel-designer/**"
  - "**/quasar.config.*"
---

# sinpapel-designer

## Qué es (y qué NO es)

- **Es**: SPA standalone Vue 3 + Quasar + Vue Flow para diseñar flujos.
  Persistencia en `localStorage`. Sin backend propio, sin autenticación.
  Round-trip JSON v0.2 con el núcleo.
- **No es**: un paquete Django reusable. No se instala con `pip`. No tiene
  modelos ni vistas Django. No se importa desde Python.

## Modelo de integración con sinpapel

```
sinpapel-designer (browser, localStorage)
        │  exporta JSON v0.2
        ▼
   archivo .json
        │
        ▼
  python manage.py sinpapel_import_flujo flujo.json
        │  (o POST /flujos/import/ vía sinpapel-drf)
        ▼
  VersionFlujo + ConfiguracionTransicion + RequisitoEstadoDocumento
```

Y al revés: `python manage.py sinpapel_export_flujo <id> --inline-catalogs > flujo.json`
→ cargar el archivo en el designer (drop area en `/workflows`).

## Stack

- Vue 3.5 (Composition API)
- Quasar 2.16
- Pinia 3
- Vue Router 4.6
- Vue Flow 1.48 (`@vue-flow/core` + background + controls + minimap)
- Vitest 2.1 (jsdom) para tests
- Node ≥ 22

## Arrancar

```bash
cd sinpapel-designer
npm install
npm run dev        # http://localhost:5173
```

Scripts:

| Script | Acción |
|---|---|
| `npm run dev` | Servidor Vite con HMR. |
| `npm run build` | Build producción a `dist/spa/`. |
| `npm run test` | Vitest (44 tests). |
| `npm run lint` | ESLint. |
| `npm run format` | Prettier. |

## Rutas

| Ruta | Página | Uso |
|---|---|---|
| `/` | `IndexPage.vue` | Landing. |
| `/workflows` | `WorkflowListPage.vue` | Listar, importar (drag-drop), crear. |
| `/workflow/:id` | `WorkflowCanvasPage.vue` | Canvas visual (drag-drop estados, conectar). |
| `/catalogos` | `CatalogosPage.vue` | CRUD de Estados/Etapas/Grupos/Tipos doc. |
| `/ai-generator` | `AiGeneratorPage.vue` | Generador IA. |

## Schema v0.2 (round-trip)

`src/data/schema-v0_2.js` define `serializeV0_2`, `parseV0_2`,
`parseV0_1` (migración), `validateSchema`.

```json
{
  "schema_version": "0.2",
  "exported_at": "2026-05-22T...",
  "catalogos": {
    "estados": [{"nombre": "CAPTURA", "color": "#4DEFE2", ...}],
    "etapas": [...],
    "grupos": [{"name": "operadores"}],
    "tipos_documento": [...]
  },
  "flujo": {
    "nombre": "solicitudes",
    "activo": true,
    "metadatos": {"positions": {"<hash>": {"x": 100, "y": 80}}},
    "transiciones": [
      {
        "estado_origen": "CAPTURA",
        "estado_destino": "EN_REVISION",
        "grupos_permitidos": ["operadores"],
        "condiciones": [...]
      }
    ],
    "requisitos": [
      {"estado": "EN_REVISION", "tipo_documento": "RFC", "porcentaje": 100, "auto_carga": false}
    ]
  }
}
```

## Almacenamiento (localStorage)

- `sinpapel-designer/workflow-index` — array de IDs.
- `sinpapel-designer/workflow/{id}` — JSON v0.2 serializado.
- `sinpapel-designer/ai-settings` — provider, model, API keys (sin cifrar).

Cuota típica del navegador: 5–10 MB. Si se llena, el store dispara
backup automático (descarga).

## Generador IA (S27.8+)

`/ai-generator`. Despacha a un adapter (`anthropic`, `openai`, `opencode`)
configurado en `AiSettingsDialog`. El system prompt vive en
`src/services/llmPrompts/workflowGenerator.js`.

API keys se piden por UI y se guardan en `localStorage` **sin cifrar** —
no usar credenciales sensibles compartidas; idealmente, generar una key
dedicada con scope acotado para esta SPA.

## Flujos de trabajo

### Crear flujo desde cero

1. `/workflows` → "Nuevo".
2. Define nombre.
3. Navega al canvas.
4. Arrastra estados desde el panel lateral, conéctalos.
5. Edita transiciones (grupos, condiciones, requisitos) en el panel derecho.
6. Ctrl+S autosave; "Exportar" descarga el JSON.

### Importar JSON de un backend

1. Backend: `python manage.py sinpapel_export_flujo <id> --inline-catalogs > flujo.json`
2. Designer `/workflows` → drag-drop `flujo.json`.
3. Editar en canvas.
4. Exportar JSON modificado.
5. Backend: `python manage.py sinpapel_import_flujo flujo.json` (o vía
   `sinpapel-drf` `POST /flujos/import/?dry_run=true` para validar primero).

### Atajos de teclado

- `Ctrl/Cmd + Z` / `Ctrl/Cmd + Shift + Z` — undo / redo (hasta 50).
- `Delete` — borrar nodo o arista seleccionada.

## Embed (S27.9, pendiente)

`syncService.js` tiene stubs para sincronizar contra un backend
(`sinpapel-drf`). En S27.9 se planea embebido vía `<iframe>` con
postMessage. Hasta entonces, la integración es manual vía JSON.

## Anti-patrones

- **No** trates al designer como autoridad: la **fuente de verdad** son
  las migraciones del backend (`VersionFlujo` activa). El designer es
  una herramienta de edición.
- **No** dependas del designer para validar reglas de negocio complejas:
  el motor (`PredicateEngine`, `WorkflowEngine`) las valida en runtime.
- **No** confundas `grupos[].name` (designer) con `grupos_permitidos[].name`
  (núcleo): el designer usa `name`, el núcleo Django usa `Group.name`.
  Coinciden si los nombras igual.
- **No** edites JSON exportado a mano sin re-validar con `validateSchema`:
  el importer del backend rechaza referencias faltantes.
- **No** uses el generador IA con keys de producción compartidas — vive
  en `localStorage` sin cifrar.
- **No** intentes "instalar" el designer en `INSTALLED_APPS`: no es una
  app Django.

## Limitaciones conocidas

- Embed `<iframe>` aún no implementado (S27.9 roadmap).
- TypeScript no migrado (S28.x roadmap).
- API keys en `localStorage` sin cifrar.
- Sin auth (admin-only por convención de despliegue).
- Sin sync backend automático (stubs en `syncService.js`).

## Siguiente paso

- Para importar el resultado a Django: `sinpapel-migrations-seeding`.
- Para sincronizar vía API: `sinpapel-drf` (`POST /flujos/import/`).
