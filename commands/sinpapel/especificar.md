---
description: Traduce una descripción en lenguaje natural a spec/sistema.yaml y spec/flujos/<tramite>.json, sin escribir código todavía.
argument-hint: [descripción del trámite en lenguaje natural]
---

Vas a especificar un trámite para este template. **Todavía no escribes código.**
La salida de este comando son dos archivos de `spec/`, que es de donde deriva
todo lo demás.

Descripción del usuario:

$ARGUMENTS

## Antes de empezar

Lee `CLAUDE.md`. Contiene las reglas duras del repositorio y las trampas
verificadas del framework, varias de las cuales condicionan cómo se puede
modelar un flujo.

Lee también `spec/flujos/solicitud_constancia.json`: es un flujo real y
completo, y el formato exacto que tienes que producir.

## Qué tienes que averiguar

Una descripción en lenguaje natural casi nunca trae todo. Pregunta lo que falte
en vez de inventarlo, y pregunta **junto**, no de una en una:

1. **Estados y transiciones.** Qué estados atraviesa, quién ejecuta cada paso.
   Convención: `MAYÚSCULAS_GUION_BAJO`.
2. **Roles.** Quién presenta, quién recibe, quién resuelve, quién firma. Si el
   trámite reutiliza los cinco roles del sistema, dilo; si necesita otros,
   decláralos.
3. **Requisitos documentales.** Qué documentos exige y en qué estado. Ojo: el
   motor enforca los requisitos del estado **actual** al avanzar, no los del
   destino.
4. **Firma electrónica.** Qué transición la exige. Si el trámite emite un acto
   administrativo, casi siempre la resolución favorable.
5. **Plazos.** Cuántos días puede permanecer en cada estado y qué pasa al
   vencer.
6. **Datos capturables.** Qué se captura por instancia y cuáles son
   obligatorios desde el alta.

## Restricciones que condicionan el modelado

No son preferencias: son límites del framework, verificados.

- **JSON Logic solo ve** `instance.pk`, `meta.<clave>`, `user.id` y
  `user.username`. Una condición sobre cualquier otro campo del modelo necesita
  el backend `django_orm`, no `json_logic`.
- **Un campo de metadatos `requerido=True` se exige en CADA guardado**, incluido
  el que hace el motor al transicionar. Un dato que solo se conoce al final del
  trámite —el motivo de un rechazo, por ejemplo— **no puede** ser requerido: su
  obligatoriedad se modela con un predicado sobre la transición.
- **`requerido` y `default` juntos son redundantes**: con default, el campo
  nunca se ve vacío.
- Un requisito documental con `auto_carga=True` no bloquea: es para lo que
  genera el sistema.

## Qué produces

**`spec/flujos/<clave>.json`** — JSON v0.2, con la misma estructura que el
flujo de ejemplo: `catalogos` (etapas, estados, grupos, tipos de documento) y
`flujo` (transiciones con sus `grupos_permitidos`, `requiere_firma` y
`condiciones`, más `requisitos`). Los SLA van dentro del estado que los tiene.

**`spec/sistema.yaml`** — añade el trámite a la lista, y los roles nuevos si los
hay.

## Antes de terminar

- Recorre el flujo mentalmente con cada rol y comprueba que alguien puede
  ejecutar cada transición.
- Comprueba que no hay estados sin salida que no sean terminales, ni estados
  inalcanzables.
- Un estado que no aparece en ninguna transición **no viaja en el JSON**: el
  export lo omitiría y el gate `parity` no lo cubriría.

Enseña al usuario el flujo resultante en prosa —no el JSON crudo— y pídele
confirmación antes de dar por buena la especificación. Después dile que el
siguiente paso es `/sinpapel:generar`.
