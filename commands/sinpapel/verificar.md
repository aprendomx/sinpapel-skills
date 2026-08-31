---
description: Corre todos los gates e interpreta los fallos, incluidos los dos que no entran en make verify.
---

Vas a verificar el estado del repositorio y a interpretar lo que falle.

## Qué correr

```bash
make db && make verify
```

Y, cuando el cambio toque el frontend o la parametrización, los dos gates que
`make verify` no incluye porque tardan minutos:

```bash
make up && make seed && make e2e
make rename-check
```

## Cómo leer cada fallo

No reportes «falló el gate X». Cada uno significa algo concreto:

**`parity`** — la base de datos y `spec/flujos/*.json` divergieron. Es el gate
que impide la deriva, así que **casi nunca se arregla tocando el JSON**. Lo
normal es que falte la data migration que siembra el cambio, o que alguien haya
editado el flujo por el admin. El mensaje enumera las rutas concretas que
difieren.

Si el cambio del JSON es el intencional, siembra la versión nueva con una
migración. Nunca al revés: reescribir el JSON para que coincida con la base
convierte al gate en un sello de goma.

**`roundtrip`** — el ciclo export→import pierde datos. Suele ser una regresión
del framework, no del proyecto. Compruébalo contra el JSON del repositorio, que
es la única referencia que no pasa por el serializador.

**`api-roles`** — un endpoint responde algo distinto de lo esperado para algún
rol. Recuerda que casi todo bloqueo del motor llega como **403**, incluidos el
estado destino inexistente y la arista inexistente: `transition()` no lanza
`ValueError` en la práctica.

**`coverage`** — menos del 85 % en la slice. Cubre las **ramas de error**: el
side effect que no encuentra su plantilla, el webhook con payload incompleto,
el requisito a medias. Son las que importan y las que nadie escribe.

**`migrations`** — hay cambios de modelo sin migración generada.

**`audit`** — o hay una vulnerabilidad conocida, o los pines del ecosistema se
movieron. Comprueba lo declarado y lo realmente instalado, más el tag del
designer. Si un pin cambió a propósito, actualiza también
`ops/ci/check-pins.sh` y deja un ADR.

Si se queja del bundle del designer, basta con `make designer`.

**`e2e`** — es el único que ejercita frontend, proxy, sesión, CSRF, motor,
firma y side effects a la vez. Un fallo aquí suele estar en las costuras, no en
las piezas.

Playwright guarda la traza, la captura y el vídeo del fallo en
`e2e/test-results/`; el informe HTML solo se genera en CI, donde además se sube
como artefacto. Ábrelos antes de tocar código: casi siempre el fallo se ve.

```bash
cd e2e && npx playwright show-trace test-results/*/trace.zip
```

**`rename-check`** — el template deja de funcionar al renombrarse. Comprueba
también que el renombrado no se llevó por delante el nombre del **framework**,
que es la forma en que un reemplazo demasiado amplio lo destruye todo.

## Antes de dar nada por terminado

- ¿`make verify` está entero en verde? No hay «verde salvo un test».
- ¿Los tests nuevos **fallan** si deshaces el cambio que prueban? Un test que
  nunca se ha visto fallar no prueba nada.
- ¿Queda código muerto, TODOs o `pass` de relleno? Lo que no se implementó, no
  existe todavía.
- ¿Alguna API que usaste está confirmada contra `site-packages`, y no contra la
  memoria o contra una skill?

## Cómo reportar

Di qué pasó y qué no. Si un gate está en rojo, dilo con su salida: no lo
resumas como «hay un detalle pendiente». Si algo quedó fuera del alcance,
nómbralo explícitamente en vez de dejar que se descubra después.
