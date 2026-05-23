# sinpapel-drf — referencia de endpoints

Detalle exacto de payloads y responses. Para entender el flujo completo,
empieza por la skill principal `sinpapel-drf`. Verificado contra
v0.2.1.

## `GET /<slug>/<pk>/available-transitions/`

Devuelve estados destino válidos (sin filtrar por permisos).

**Response 200:**

```json
[
  {"id": 5, "nombre": "EN_REVISION", "color": "#FFA500"},
  {"id": 7, "nombre": "RECHAZADA", "color": "#D32F2F"}
]
```

## `POST /<slug>/<pk>/preview-transition/`

**Request:**

```json
{ "target_state": "APROBADA" }
```

**Response 200:**

```json
{
  "permitido": false,
  "razones_bloqueo": [
    {"tipo": "predicado", "mensaje": "Monto < $100,000"}
  ],
  "documentos_faltantes": [
    {"tipo_documento": "RFC", "porcentaje": 100}
  ],
  "predicados_fallidos": [...],
  "aprobadores_requeridos": [...],
  "side_effects": ["APROBADA"],
  "historial_reciente": [...]
}
```

`historial_reciente` típicamente incluye las últimas N transiciones del
`SeguimientoWorkflow`. Si `SINPAPEL_EMIT_PREVIEW_EVENTS=True`, este
endpoint además dispara el signal `transition_preview_requested`.

## `POST /<slug>/<pk>/transition/`

**Request mínimo (sin firma):**

```json
{
  "target_state": "EN_REVISION",
  "comentarios": "Pasa a revisión"
}
```

**Campos del request:**

| Campo | Tipo | Notas |
|---|---|---|
| `target_state` | string | **Obligatorio.** Nombre del estado destino. |
| `comentarios` | string | Default `""`. |
| `monto_aprobado` | string (decimal) | Opcional. |
| `condiciones` | string \| null | Opcional. |
| `signature` | object \| null | Ver dispatch polimórfico abajo. |

**Response 201:**

```json
{
  "success": true,
  "instance_id": 42,
  "estado_anterior": "CAPTURA",
  "estado_nuevo": "EN_REVISION",
  "seguimiento_id": 1834
}
```

**Errores:**

- `400` — `target_state` inválido, predicado fallido, requisito faltante,
  firma inválida.
- `403` — usuario no autorizado por `grupos_permitidos`.

### Dispatch polimórfico de `signature`

#### FIEL — client-side (recomendado)

```json
{
  "signature": {
    "backend": "fiel",
    "mode": "client-side",
    "firma_b64": "...",
    "certificado_cer_b64": "..."
  }
}
```

El servidor verifica RSA-SHA256 sobre el `content` canónico
(`{instance_id, target_state, user_id}` json-canónico, separadores
compactos, keys ordenadas). La clave privada nunca cruza la red.

#### FIEL — server-side (gated)

`multipart/form-data`. Requiere `SINPAPEL_ALLOW_SERVER_SIGNING=True`.

```bash
curl -X POST -H "Authorization: Token <t>" \
  -F "target_state=APROBADA" \
  -F "signature[backend]=fiel" \
  -F "signature[mode]=server-side" \
  -F "signature[cer_file]=@firma.cer" \
  -F "signature[key_file]=@firma.key" \
  -F "signature[password]=••••" \
  https://host/sinpapel/api/solicitudes/42/transition/
```

#### Manual

```json
{
  "signature": {
    "backend": "manual",
    "scanned_image_path": "/uploads/escaneo.pdf",
    "witness_name": "María López"
  }
}
```

#### Fake (solo tests)

```json
{ "signature": { "backend": "fake" } }
```

## `GET /<slug>/<pk>/history/`

Paginado (10/página, máximo 100). Devuelve entradas de
`HistoricalRecords` **del modelo decorado** (no `SeguimientoWorkflow`).

**Response:**

```json
{
  "count": 12,
  "next": "?page=2",
  "previous": null,
  "results": [
    {
      "history_id": 1834,
      "history_type": "~",
      "history_date": "2026-05-22T...",
      "history_user": "alice",
      "history_change_reason": null
    }
  ]
}
```

`history_type`: `+` creado, `~` modificado, `-` borrado. `history_user`
puede ser `null` si el cambio ocurrió fuera de un request.

## `GET /<slug>/<pk>/metadatos/`

```json
{
  "schema": [
    {
      "nombre": "rfc",
      "tipo": "str",
      "requerido": true,
      "default": null,
      "choices": null,
      "etiqueta": "RFC",
      "ayuda": "13 caracteres alfanuméricos."
    }
  ],
  "values": {"rfc": "ABCD010101ABC"}
}
```

## `PATCH /<slug>/<pk>/metadatos/`

**Request:**

```json
{ "rfc": "ABCD010101ABC" }
```

Validación: rechaza keys fuera de `SCHEMA_METADATOS` con 400.

**Response 200:** valores actualizados.

## `POST /<slug>/<pk>/sla-status/`

Permiso `IsAdminUser`. Evalúa SLAs para la instancia (puede mutar estado
si la acción es `alertar` u otra mutativa).

**Response:**

```json
["notificar", "escalar"]
```

## Admin — `/condiciones/`

ModelViewSet completo. Filtros `?transicion=<id>`, `?activo=true|false`.

**POST:**

```json
{
  "transicion": 7,
  "tipo": "json_logic",
  "configuracion": {"rule": {">": [{"var": "instance.monto"}, 0]}},
  "mensaje_error": "El monto debe ser positivo",
  "orden": 1,
  "activo": true
}
```

## Admin — `/slas/`

ModelViewSet. Filtros `?estado=<id>`, `?activo=true|false`. Maneja
`IntegrityError` (unique_together) → `400`.

**POST:**

```json
{
  "estado": 3,
  "dias_maximos": 7,
  "accion_vencimiento": "notificar",
  "configuracion_accion": {"grupo_id": 1, "template": "expiration.html"},
  "activo": true
}
```

## Admin — `POST /slas/verificar/`

Evaluación masiva de SLAs (equivalente a
`python manage.py sinpapel_verificar_slas`).

**Response:**

```json
{
  "ejecutadas": {
    "notificar": 3,
    "escalar": 1
  }
}
```

## Portabilidad — `GET /flujos/<pk>/export/`

Descarga JSON v0.2 como adjunto.

```
Content-Type: application/json
Content-Disposition: attachment; filename=flujo_solicitudes_20260522.json
```

## Portabilidad — `POST /flujos/import/`

Body: JSON v0.2.

Query params:

- `?dry_run=true` — valida sin persistir.
- `?activo=true` — override del default seguro `activo=False`.

**Response 201 (normal) / 200 (dry_run):**

```json
{
  "id": 42,
  "nombre": "solicitudes",
  "activo": false,
  "transiciones_count": 5,
  "requisitos_count": 3
}
```

`ValueError` (referencias faltantes a estados/grupos/tipos doc) → 400.
