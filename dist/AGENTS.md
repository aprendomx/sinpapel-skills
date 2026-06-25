# AGENTS.md — sinpapel skills

Índice cross-tool de skills para el framework sinpapel.
Este archivo se **genera** desde `skills/` — no editar a mano.
Para detalles, abre el `SKILL.md` correspondiente.

## Skills disponibles

### sinpapel-audit-trail

Usar siempre que el usuario configure auditoría, use Trazable, HistoricalRecords o django-simple-history, consulte el historial de un modelo o de SeguimientoWorkflow, mencione HistoryRequestMiddleware o history_user nulo en jobs/background, o pregunte cómo persistir quién y cuándo cambió qué en sinpapel.

Fuente: `skills/sinpapel-audit-trail/SKILL.md`

### sinpapel-designer

Usar siempre que el usuario diseñe visualmente un flujo sinpapel, instale o ejecute sinpapel-designer (Vue 3 + Quasar + Vue Flow), exporte / importe JSON v0.2, integre el designer con un backend Django vía sinpapel_export_flujo / sinpapel_import_flujo, configure el generador IA (Anthropic / OpenAI / OpenCode), o pregunte cómo embeber el designer en otra app (S27.9). Cubre que es una SPA standalone, NO un paquete Django.

Fuente: `skills/sinpapel-designer/SKILL.md`

### sinpapel-drf

Usar siempre que el usuario exponga flujos sinpapel por API REST con Django REST Framework, instale sinpapel-drf, use expose_endpoints=True / endpoint_slug en @workflow_enabled, monte SinpapelRouter, llame los endpoints available-transitions / transition / history / preview-transition / metadatos / sla-status, exporte / importe flujos por HTTP, o configure permisos sobre transiciones. Cubre el dispatch polimórfico de firma y el mapeo de errores.

Fuente: `skills/sinpapel-drf/SKILL.md`

### sinpapel-metadata

Usar siempre que el usuario capture metadatos estructurados por instancia, defina SCHEMA_METADATOS con CampoMetadato, herede de MetadatosCapturables, genere formularios o serializers DRF con MetaFormFactory, acceda a instance.meta, o pregunte cómo validar y serializar datos arbitrarios sin crear columnas físicas en el modelo.

Fuente: `skills/sinpapel-metadata/SKILL.md`

### sinpapel-migrations-seeding

Usar siempre que el usuario siembre datos iniciales de Estado, Etapa, VersionFlujo o ConfiguracionTransicion vía data migrations; importe o exporte flujos con sinpapel_export_flujo / sinpapel_import_flujo (JSON schema v0.2); diseñe migraciones reversibles para catálogos del framework, o pregunte por requisitos documentales (RequisitoEstadoDocumento).

Fuente: `skills/sinpapel-migrations-seeding/SKILL.md`

### sinpapel-overview

Usar siempre que el usuario mencione el framework sinpapel, sinpapel-drf, sinpapel-webhooks o sinpapel-designer; necesite decidir qué skill cargar; pregunte qué hace el framework, su arquitectura, qué versión usar, o cómo se relacionan sus paquetes; o cuando aparezcan términos como @workflow_enabled, VersionFlujo, ConfiguracionTransicion, SeguimientoWorkflow, FielBackend, RegistroFirma, CondicionTransicion, SLAConfiguracion o MetadatosCapturables sin un contexto más específico.

Fuente: `skills/sinpapel-overview/SKILL.md`

### sinpapel-predicates

Usar siempre que el usuario defina reglas de negocio que bloqueen una transición (montos, fechas, validaciones cruzadas), use CondicionTransicion, PredicateEngine, los backends python_path / json_logic / django_orm, o vea el signal predicate_failed. Cubre cómo configurar SINPAPEL_PREDICATE_MODULES como whitelist de seguridad y el JSON Logic restringido del framework.

Fuente: `skills/sinpapel-predicates/SKILL.md`

### sinpapel-project-setup

Usar siempre que el usuario instale sinpapel en un proyecto Django nuevo o existente, configure INSTALLED_APPS, MIDDLEWARE o cualquier setting con prefijo SINPAPEL_*; mencione errores como "Estado no resuelto" / "history_user is None" / "AppRegistryNotReady"; o pregunte por dependencias (django-simple-history, cryptography), versiones soportadas o el orden correcto de las apps. Cubre el primer migrate, la instalación desde git@v0.5.1 y la verificación post-setup.

Fuente: `skills/sinpapel-project-setup/SKILL.md`

### sinpapel-side-effects

Usar siempre que el usuario quiera ejecutar lógica adicional tras una transición de sinpapel (notificaciones, generación de oficios, integración con sistemas externos, llamadas a otros servicios), use el decorador register_side_effect, registre handlers en AppConfig.ready(), o pregunte qué pasa si un handler falla, cuándo se ejecuta y cómo afecta a la atomicidad de la transición.

Fuente: `skills/sinpapel-side-effects/SKILL.md`

### sinpapel-signing

Usar siempre que el usuario implemente firma electrónica con sinpapel, configure SINPAPEL_SIGNATURE_BACKEND, use FielBackend (FIEL/SAT México) en modo client-side o server-side, ManualBackend o FakeBackend, escriba un backend custom que implemente el Protocol SignatureBackend, persista RegistroFirma, llame get_signature_backend(), pase firma_payload a transition(), o vea SignatureValidationError / SignatureBackendNotConfiguredError. Cubre los dos modos del FIEL y el contrato del Port/Adapter.

Fuente: `skills/sinpapel-signing/SKILL.md`

### sinpapel-sla

Usar siempre que el usuario defina tiempos máximos por estado, escalamiento o alertas de vencimiento; use SLAConfiguracion, SLAEngine, las acciones notificar / escalar / rechazar / alertar, el comando sinpapel_verificar_slas, o los signals sla_breached y sla_action_executed. Cubre cómo configurar el cron, el dry-run y la integración con webhooks/notificaciones.

Fuente: `skills/sinpapel-sla/SKILL.md`

### sinpapel-testing

Usar siempre que el usuario escriba tests de un proyecto que use sinpapel, configure pytest / pytest-django, use FakeBackend en lugar de FielBackend real, genere un keypair RSA en fixtures, limpie el cache del framework entre tests, use WorkflowRegistry.unregister, mockee transiciones o verifique history_user en tests sin request. Cubre los settings de test y los patrones de aislamiento.

Fuente: `skills/sinpapel-testing/SKILL.md`

### sinpapel-transitions

Usar siempre que el usuario ejecute una transición de estado, llame transition() / available_transitions() / can_transition_to() / preview_transition(), maneje PermissionError o ValueError al transicionar, o use WorkflowEngine directamente. Cubre payload de firma (firma_payload), kwargs (comentarios, monto_aprobado, condiciones, ip_address) y la consulta del audit log SeguimientoWorkflow.

Fuente: `skills/sinpapel-transitions/SKILL.md`

### sinpapel-vue-client

Usar siempre que el usuario cree o use el cliente REST JS de sinpapel-vue (createSinpapelClient), llame uno de sus 7 métodos (availableTransitions, history, previewTransition, getMetadatos, patchMetadatos, slaStatus, transition), mapee llamadas a los endpoints de sinpapel-drf, cancele requests con AbortController/signal, o use buildTransitionRequest para codificar el payload de transición (JSON vs multipart FIEL).

Fuente: `skills/sinpapel-vue-client/SKILL.md`

### sinpapel-vue-components

Usar siempre que el usuario use o parametrice los componentes Vue de sinpapel-vue (SeguimientoPanel, StateBadge, HistoryTimeline, TransitionDialog, PreviewTransitionPanel, MetadatosForm, SlaStatusPanel), sus props/emits, la composición de pestañas del panel, el remount con :key, la accesibilidad del diálogo, o la UI de firma polimórfica (FIEL client/server-side, manual, fake) en TransitionDialog.

Fuente: `skills/sinpapel-vue-components/SKILL.md`

### sinpapel-vue-setup

Usar siempre que el usuario instale o integre la librería @aprendomx/sinpapel-vue (widgets Vue 3 de seguimiento de flujos), configure sus peer deps (vue/pinia/quasar), importe @aprendomx/sinpapel-vue/style.css, monte SeguimientoPanel, sobrescriba la tematización --sp-*, cambie el locale (es/en), o pregunte qué es la librería frente a sinpapel-designer. Cubre que CONSUME sinpapel-drf y NO es un backend.

Fuente: `skills/sinpapel-vue-setup/SKILL.md`

### sinpapel-webhooks

Usar siempre que el usuario emita o consuma webhooks con sinpapel-webhooks; configure WebhookSubscription / WebhookEvent / WebhookDelivery / InboundWebhookEvent; use el decorador @webhook_receiver, los backends de entrega inline / outbox / celery, HMAC-SHA256 con X-Sinpapel-Signature, política de reintentos con backoff y dead letter, idempotencia inbound, o el Admin REST API. Cubre el cron del worker y la verificación de firmas desde cliente.

Fuente: `skills/sinpapel-webhooks/SKILL.md`

### sinpapel-workflow-modeling

Usar siempre que el usuario decore un modelo Django con @workflow_enabled, defina Estado / VersionFlujo / ConfiguracionTransicion, implemente resolve_workflow_version(), consulte el WorkflowRegistry, o pregunte cómo modelar máquinas de estado en sinpapel. Cubre también nombres de campos requeridos (state_field, workflow_key, version_field, expose_endpoints, endpoint_slug) y errores como WorkflowConfigurationError o WorkflowDuplicateKeyError.

Fuente: `skills/sinpapel-workflow-modeling/SKILL.md`
