---
description: Genera la app del trámite a partir de spec/flujos/, copiando la vertical slice canónica.
argument-hint: [clave del trámite, p. ej. permiso_construccion]
---

Vas a generar la app de un trámite ya especificado en `spec/flujos/`.

Trámite:

$ARGUMENTS

## La regla que gobierna este comando

**Copia `apps/tramite_ejemplo/` completa y adáptala.** No armes la estructura
desde cero.

La slice canónica conecta piezas que no fallan de forma visible cuando faltan:
un side effect que no se registró en `AppConfig.ready()` simplemente no ocurre,
un `requiere_firma` que no se sembró deja pasar la aprobación sin firmar, un
requisito documental ausente no bloquea nada. Reconstruirla a mano garantiza
olvidar alguna, y ninguna de esas omisiones rompe un test que no exista.

## Antes de empezar

1. Lee `CLAUDE.md` entero.
2. Lee el JSON del flujo en `spec/flujos/`: es la fuente de verdad y no se
   toca desde aquí.
3. `make verify` tiene que estar en verde **antes** de empezar. Si no lo está,
   arregla eso primero: no sabrás qué rompiste tú.

## Qué generas

**Backend** — copia de `apps/tramite_ejemplo/`, con:

- `models.py`: el modelo decorado con `@workflow_enabled`. Hereda `Trazable`
  —el decorador lo exige— y `MetadatosCapturables` si captura datos.
- `apps.py`: `ready()` importando los módulos de side effects y reportes. Sin
  ese import los handlers no existen para el motor.
- `side_effects.py`: handlers idempotentes. Corren **post-commit**: un fallo no
  revierte la transición, así que lo que deba bloquear va en un predicado.
- `migrations/0002_seed_flujo.py`: siembra el flujo leyendo el JSON con
  `deserialize_flujo`. Pásale `activo=` explícito — ignora la clave del payload.
- `api.py`: el CRUD de dominio, acotado por rol y adscripción. `sinpapel-drf`
  genera las acciones de workflow, no la bandeja ni el alta.
- `webhooks.py` y `reportes.py` si el trámite los necesita.

**Frontend** — rutas y pantallas, reutilizando `SeguimientoPanel`. La página de
seguimiento existente ya resuelve dos cosas que cuestan encontrar: mantener
`current-state` al día tras una transición, y el `:key` para remontar al
cambiar de instancia.

**Tests** — el trámite nuevo necesita los suyos. El gate `coverage` exige 85 %
sobre la app, y `api-roles` que cada endpoint responda 200/403 por rol.

## Qué NO haces

- **No toques `spec/flujos/*.json`.** Si al generar descubres que el flujo está
  mal, dilo y vuelve a `/sinpapel:especificar`. Cambiar el JSON aquí es cambiar
  la especificación a espaldas de quien la aprobó.
- **No declares estados ni transiciones en Python.** Se siembran leyendo el JSON.
- **No inventes APIs del framework.** Si no la has usado ya en este repositorio,
  ábrela en `backend/.venv/lib/python3.12/site-packages/sinpapel*` y confirma la
  firma. Si no existe, dilo y detente.
- **No edites `.claude/skills/`.** Es contenido vendorizado.

## Al terminar

Corre `/sinpapel:verificar`. Mientras `parity` no esté en verde, lo sembrado y
lo declarado no coinciden y el trabajo no está hecho.
