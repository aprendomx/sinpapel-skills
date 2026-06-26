---
name: sinpapel-overview
description: Usar siempre que el usuario mencione el framework sinpapel, sinpapel-drf, sinpapel-webhooks o sinpapel-designer; necesite decidir qué skill cargar; pregunte qué hace el framework, su arquitectura, qué versión usar, o cómo se relacionan sus paquetes; o cuando aparezcan términos como @workflow_enabled, VersionFlujo, ConfiguracionTransicion, SeguimientoWorkflow, FielBackend, RegistroFirma, CondicionTransicion, SLAConfiguracion o MetadatosCapturables sin un contexto más específico.
tested_against:
  - sinpapel==0.6.0
  - sinpapel-drf==0.2.1
  - sinpapel-webhooks==0.2.1
  - sinpapel-designer@S27.8
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
   (`notificar`, `escalar`, `rechazar`, `alertar`).

Adicionalmente: captura de metadatos estructurados
(`MetadatosCapturables`/`CampoMetadato`), signals de dominio
(`predicate_failed`, `sla_breached`, `sla_action_executed`,
`transition_preview_requested`), cache transparente con invalidación por
signals, y export/import portable JSON v0.2 (`sinpapel_export_flujo` /
`sinpapel_import_flujo`).

## Paquetes del ecosistema

| Paquete | Qué añade | Versión |
|---|---|---|
| `sinpapel` | Núcleo: workflow + audit + signing + predicates + SLA + metadata. | 0.6.0 |
| `sinpapel-drf` | API REST DRF: 6 acciones por modelo + CRUD admin + portabilidad. | 0.2.1 |
| `sinpapel-webhooks` | Outbound (signals→outbox→worker, HMAC) + inbound (`@webhook_receiver`). | 0.2.1 |
| `sinpapel-designer` | SPA Vue 3 + Quasar standalone para diseñar flujos. Round-trip JSON v0.2. | S27.8+ |
| `sinpapel-vue` | Widgets Vue 3 que consumen `sinpapel-drf` para seguir flujos en el frontend. | 0.1.0 |

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
| Diseñar flujos visualmente. | `sinpapel-designer` |
| Escribir tests sin tocar FIEL real ni red. | `sinpapel-testing` |
| Instalar/montar la UI de seguimiento (Vue). | `sinpapel-vue-setup` |
| Consumir la API REST desde JS (cliente). | `sinpapel-vue-client` |
| Usar los widgets Vue (panel, diálogo, timeline). | `sinpapel-vue-components` |
| Store Pinia y composables de seguimiento. | `sinpapel-vue-store` |

## Glosario

- **Estado**: nodo del workflow. Catálogo (`sinpapel.Estado`) con `nombre`,
  `activo`, `etapa`, `permite_expediente`, etc.
- **VersionFlujo**: versión inmutable de un workflow. Sólo una activa por
  `workflow_key` recomendada.
- **ConfiguracionTransicion**: arista del grafo. Define `(flujo,
  estado_origen, estado_destino, grupos_permitidos)`.
- **SeguimientoWorkflow**: registro inmutable por transición ejecutada
  (`target` vía GenericForeignKey, `usuario_accion`, `fecha_accion`,
  `firma_registro`, etc.).
- **RegistroFirma**: registro de firma electrónica, persistido por un
  `SignatureBackend`.
- **`@workflow_enabled`**: decorador que inyecta `transition()`,
  `available_transitions()`, `can_transition_to()` y `preview_transition()`
  en el modelo de dominio.
- **WorkflowEngine**: servicio en `sinpapel.services.workflow_engine`.
  Atómico, ejecuta predicados, side effects y firma.
- **PredicateEngine**: evalúa condiciones de transición.
- **SLAEngine**: evalúa vencimientos y dispara acciones.
- **`SINPAPEL_*`**: prefijo común de los settings del framework (ver
  `sinpapel-project-setup`).

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
- **API 0.x (beta)**: fija `@v0.6.0` (o el tag/commit exacto) en tus
  dependencias. No uses `>=0.6,<0.7` sin pinear el commit.
- **0.6.0 enforca requisitos documentales** (`RequisitoEstadoDocumento`) en
  las transiciones — antes solo se sembraban/exportaban. Cambio
  potencialmente breaking al actualizar desde 0.5.x: transiciones con
  requisitos configurados pueden lanzar `PermissionError` hasta satisfacerlos.
  Detalle en `sinpapel-transitions` y `sinpapel-project-setup`.
- **Algunas tablas usan prefijo legado**: la tabla SQL puede no coincidir
  con el nombre del modelo (`db_table` override). No asumas el nombre de
  la tabla; consúltalo en `migrations/0001_initial.py`.

## Versiones contra las que se verificó este conjunto de skills

```
sinpapel @ git+ssh://git@github.com/aprendomx/sinpapel.git@v0.6.0
sinpapel-drf @ git+ssh://git@github.com/aprendomx/sinpapel-drf.git@v0.2.1
sinpapel-webhooks @ git+ssh://git@github.com/aprendomx/sinpapel-webhooks.git@v0.2.1
sinpapel-designer @ rama main (S27.8+)
sinpapel-vue @ npm @aprendomx/sinpapel-vue@0.1.0
```

## Referencias canónicas

- Núcleo: <https://github.com/aprendomx/sinpapel>
- REST: <https://github.com/aprendomx/sinpapel-drf>
- Webhooks: <https://github.com/aprendomx/sinpapel-webhooks>
- Designer: <https://github.com/aprendomx/sinpapel-designer>
- Vue widgets: <https://github.com/aprendomx/sinpapel-vue>
