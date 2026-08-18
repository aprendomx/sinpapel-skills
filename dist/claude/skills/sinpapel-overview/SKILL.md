---
name: sinpapel-overview
description: Usar siempre que el usuario mencione el framework sinpapel, sinpapel-drf, sinpapel-webhooks, sinpapel-reports o sinpapel-designer; necesite decidir qué skill cargar; pregunte qué hace el framework, su arquitectura, qué versión usar, o cómo se relacionan sus paquetes; o cuando aparezcan términos como @workflow_enabled, VersionFlujo, ConfiguracionTransicion, SeguimientoWorkflow, FielBackend, RegistroFirma, CondicionTransicion, SLAConfiguracion o MetadatosCapturables sin un contexto más específico.
tested_against:
  - sinpapel==0.8.2
  - sinpapel-drf==0.4.5
  - sinpapel-webhooks==0.2.3
  - sinpapel-reports==0.2.3
  - sinpapel-designer@S27.8
  - sinpapel-vue@0.4.0
applies_to:
  - "**/models.py"
  - "**/services/*.py"
  - "**/apps.py"
---

# sinpapel — visión general y enrutado de skills

## Qué es sinpapel

Framework Django (Python ≥3.10, Django ≥5.0, GPL-3.0) para construir
sistemas de trámites con cinco pilares:

1. **Motor de workflow versionado** — `Estado`, `VersionFlujo`,
   `ConfiguracionTransicion`. Las transiciones son datos en BD, no código.
2. **Audit trail inmutable** — `SeguimientoWorkflow` + `django-simple-history`
   (mixin `Trazable` inlined).
3. **Firma electrónica pluggable** — patrón Port/Adapter: `FielBackend`
   (SAT México), `ManualBackend`, `FakeBackend`.
4. **Predicados de transición** — `CondicionTransicion` + `PredicateEngine`
   (`python_path`, `json_logic`, `django_orm`).
5. **SLA timers con acciones** — `SLAConfiguracion` + `SLAEngine`
   (`notificar`, `escalar`, `rechazar`, `alertar`). Desde 0.8.0 las
   acciones ejecutan de verdad (transición automática, handler de
   notificación, bandera persistida); el plazo mide tiempo-en-estado.

Adicionalmente: captura de metadatos estructurados
(`MetadatosCapturables`/`CampoMetadato`), signals de dominio
(`predicate_failed`, `sla_breached`, `sla_action_executed`,
`transition_preview_requested`), cache transparente con invalidación en
cascada (0.8.0: keys versionadas con `sinpapel:cache_version`; mutar un
`Estado` bumpea la versión post-commit), y export/import portable JSON
v0.2 (`sinpapel_export_flujo` / `sinpapel_import_flujo`).

## Paquetes del ecosistema

| Paquete | Qué añade | Versión |
|---|---|---|
| `sinpapel` | Núcleo: workflow + audit + signing + predicates + SLA + metadata. | 0.8.1 |
| `sinpapel-drf` | API REST DRF: 8 acciones por modelo (incluye `documentos`/`requisitos`) + CRUD admin + portabilidad. | 0.4.5 |
| `sinpapel-webhooks` | Outbound (signals→outbox→worker, HMAC) + inbound (`@webhook_receiver`). | 0.2.3 |
| `sinpapel-reports` | Generación de documentos por plantilla (PDF overlay + DOCX) sobre `Documento`/`InstanciaDocumento`. Capa DRF opcional. | 0.2.3 |
| `sinpapel-designer` | SPA Vue 3 + Quasar standalone para diseñar flujos. Round-trip JSON v0.2. | S27.8+ |
| `sinpapel-vue` | Widgets Vue 3 que consumen `sinpapel-drf` para seguir flujos en el frontend (incluye carga documental). | 0.4.0 |

## Qué skill usar para qué tarea

| Tarea del usuario | Skill |
|---|---|
| Arrancar un proyecto nuevo con sinpapel. | `sinpapel-project-setup` |
| Decorar un modelo, modelar estados y transiciones. | `sinpapel-workflow-modeling` |
| Ejecutar una transición, previsualizarla, manejar errores. | `sinpapel-transitions` |
| Disparar lógica post-transición (notificaciones, oficios). | `sinpapel-side-effects` |
| Reglas que bloquean una transición (montos, fechas, ORM). | `sinpapel-predicates` |
| Vencimientos de estado, escalamiento, alertas. | `sinpapel-sla` |
| Capturar y validar metadatos estructurados por instancia. | `sinpapel-metadata` |
| Implementar firma FIEL, manual o un backend propio. | `sinpapel-signing` |
| Auditoría de cambios, `history_user`, simple-history. | `sinpapel-audit-trail` |
| Sembrar flujos vía data migrations o importar JSON v0.2. | `sinpapel-migrations-seeding` |
| Exponer flujos por API REST. | `sinpapel-drf` |
| Emitir/consumir webhooks de transición. | `sinpapel-webhooks` |
| Generar PDFs/DOCX por plantilla (overlay, ZIP, fuentes de datos). | `sinpapel-reports` |
| Diseñar flujos visualmente. | `sinpapel-designer` |
| Escribir tests sin tocar FIEL real ni red. | `sinpapel-testing` |
| Instalar/montar la UI de seguimiento (Vue). | `sinpapel-vue-setup` |
| Consumir la API REST desde JS (cliente). | `sinpapel-vue-client` |
| Usar los widgets Vue (panel, diálogo, timeline). | `sinpapel-vue-components` |
| Store Pinia y composables de seguimiento. | `sinpapel-vue-store` |

## Glosario

- **Estado**: nodo del workflow. Catálogo (`sinpapel.Estado`) con `nombre`,
  `activo`, `etapa`, `permite_expediente`, etc. Desde 0.8.0 `nombre` es
  único (constraint `sin_estado_nombre_uniq`).
- **VersionFlujo**: versión inmutable de un workflow. Desde 0.8.0 la BD
  garantiza una sola activa por nombre (constraint condicional
  `sin_versionflujo_activa_uniq`).
- **ConfiguracionTransicion**: arista del grafo. Define `(flujo,
  estado_origen, estado_destino, grupos_permitidos)` y, desde 0.8.0,
  `requiere_firma` (exige `firma_payload` en la transición).
- **SeguimientoWorkflow**: registro inmutable por transición ejecutada
  (`target` vía GenericForeignKey, `usuario_accion`, `fecha_accion`,
  `firma_registro`, etc.).
- **RegistroFirma**: registro de firma electrónica, persistido por un
  `SignatureBackend`.
- **`@workflow_enabled`**: decorador que inyecta `transition()`,
  `available_transitions()`, `can_transition_to()` y `preview_transition()`
  en el modelo de dominio.
- **WorkflowEngine**: servicio en `sinpapel.services.workflow_engine`.
  Transición atómica (`SELECT ... FOR UPDATE` + revalidación desde 0.7.1),
  ejecuta predicados y firma; los side effects corren **después** del
  commit de la transacción del motor.
- **PredicateEngine**: evalúa condiciones de transición.
- **SLAEngine**: evalúa vencimientos y dispara acciones.
- **`SINPAPEL_*`**: prefijo común de los settings del framework (ver
  `sinpapel-project-setup`). 0.8.x añade cuatro opcionales:
  `SINPAPEL_FIEL_TRUSTED_CA_BUNDLE` (ACs de confianza FIEL),
  `SINPAPEL_SLA_SYSTEM_USER` (username para transiciones automáticas SLA),
  `SINPAPEL_SLA_NOTIFY_HANDLER` (handler de notificación SLA) y
  `SINPAPEL_ENFORCE_ESTADO_ACTIVO` (bloquear destinos inactivos,
  default `False`).

## Trampas a recordar (válidas para todas las skills)

- **`WorkflowService` no existe**. El motor es `WorkflowEngine`. Si ves
  código que importa `WorkflowService`, hay que migrarlo.
- **`trazable` no está en PyPI**. Está inlined en `sinpapel/mixins.py`.
  Solo necesitas instalar `django-simple-history`.
- **`history_user` puede ser `None`** fuera de un request (management
  commands, tareas en background, signals sin middleware). Es esperado.
- **i18n hardcoded en español**: verbose_names, mensajes de error y de
  validación están en español. Override en formularios/serializers si
  necesitas otro idioma.
- **API 0.x (pre-1.0)**: los paquetes se instalan desde **PyPI**
  (`pip install sinpapel`); ya no se recomienda instalar desde git+ssh con
  tags. Los minors PUEDEN romper: pinea `sinpapel~=0.8.1`. Los breaking
  changes por versión están en `docs/development/upgrading.md` y la
  superficie pública en `docs/development/api-publica.md` (repo sinpapel).
- **0.6.0 enforca requisitos documentales** (`RequisitoEstadoDocumento`) en
  las transiciones — antes solo se sembraban/exportaban. Cambio
  potencialmente breaking al actualizar desde 0.5.x: transiciones con
  requisitos configurados pueden lanzar `PermissionError` hasta satisfacerlos.
  Detalle en `sinpapel-transitions` y `sinpapel-project-setup`.
- **0.7.0 elimina `monto_aprobado`** (campo residual de dominio) de
  `SeguimientoWorkflow`, `transition()` / `cambiar_estado()` y del paso a
  side-effects (migración `0006`). Breaking: usa metadatos o
  `condiciones`/`comentarios`. `sinpapel-drf` (≥0.4.0) y `sinpapel-vue 0.3.0`
  alinean este cambio; `sinpapel-drf` además enriquece `/requisitos/`
  con `tipo_documento_id` + `documentos_disponibles` para selects dependientes.
- **0.8.0: `Estado.nombre` es único** (`sin_estado_nombre_uniq`). Seeds o
  fixtures que creaban dos estados homónimos fallarán al migrar.
- **0.8.0: solo UNA `VersionFlujo` activa por nombre** (constraint
  condicional `sin_versionflujo_activa_uniq`). Desactiva la vieja antes de
  activar la nueva.
- **0.8.0: autoría con `SET_NULL`**: `Trazable.autor`/`modificador` pasaron
  de CASCADE a SET_NULL — borrar un `User` ya no borra en cascada sus
  registros (quedan con autoría nula). Además hay PROTECT en
  `Documento.tipo_documento`, `InstanciaDocumento.documento` y
  `SeguimientoWorkflow.firma_registro`.
- **0.8.0: `SeguimientoWorkflow` y `RegistroFirma` son append-only a nivel
  ORM**: `save()` de un registro existente y `delete()` lanzan `ValueError`
  (`RegistroFirma` se revoca vía `backend.revoke()`). Salvedad: los
  `queryset.update()` / `queryset.delete()` masivos NO pasan por estos
  hooks.
- **0.8.0: `VALIDA_SIN_CADENA`**: sin `SINPAPEL_FIEL_TRUSTED_CA_BUNDLE`, la
  firma FIEL íntegra se persiste como `VALIDA_SIN_CADENA` (identidad del
  emisor no verificada), no como `VALIDA`. Compara contra
  `RegistroFirma.RESULTADOS_VALIDOS`, nunca contra el string `"VALIDA"`.
- **0.8.0: `ConfiguracionTransicion.requiere_firma`** (default `False`): con
  `True`, `transition()` sin `firma_payload` lanza `PermissionError` y
  `preview_transition()` incluye la key `firma_requerida`.
- **0.8.0: `@workflow_enabled` valida el contrato Trazable en decoración**:
  si el modelo no tiene campo `actualizado`, lanza
  `WorkflowConfigurationError` al importar — ya no falla en runtime en la
  primera transición.
- **Algunas tablas usan prefijo legado**: la tabla SQL puede no coincidir
  con el nombre del modelo (`db_table` override). No asumas el nombre de
  la tabla; consúltalo en `migrations/0001_initial.py`.

## Versiones contra las que se verificó este conjunto de skills

Instalación desde PyPI (pineando con `~=`; los minors pre-1.0 pueden
romper):

```
sinpapel~=0.8.1
sinpapel-drf~=0.4.3
sinpapel-webhooks~=0.2.3
sinpapel-reports~=0.2.2
sinpapel-designer @ rama main (S27.8+)
sinpapel-vue @ npm @aprendomx/sinpapel-vue@0.4.0
```

## Referencias canónicas

- Núcleo: <https://github.com/aprendomx/sinpapel>
- REST: <https://github.com/aprendomx/sinpapel-drf>
- Webhooks: <https://github.com/aprendomx/sinpapel-webhooks>
- Reports: <https://github.com/aprendomx/sinpapel-reports>
- Designer: <https://github.com/aprendomx/sinpapel-designer>
- Vue widgets: <https://github.com/aprendomx/sinpapel-vue>
