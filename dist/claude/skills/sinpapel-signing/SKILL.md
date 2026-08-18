---
name: sinpapel-signing
description: Usar siempre que el usuario implemente firma electrónica con sinpapel, configure SINPAPEL_SIGNATURE_BACKEND, use FielBackend (FIEL/SAT México) en modo client-side o server-side, ManualBackend o FakeBackend, escriba un backend custom que implemente el Protocol SignatureBackend, persista RegistroFirma, llame get_signature_backend(), pase firma_payload a transition(), o vea SignatureValidationError / SignatureBackendNotConfiguredError. Cubre los dos modos del FIEL y el contrato del Port/Adapter.
tested_against:
  - sinpapel==0.8.2
applies_to:
  - "**/signing/**/*.py"
  - "**/backends/*.py"
---

# Firma electrónica con sinpapel

## Arquitectura Port/Adapter

- **Port**: `sinpapel.signing.ports.SignatureBackend` (Protocol). Define
  `request_signature`, `verify`, `revoke`.
- **Adapters incluidos**: `FielBackend`, `ManualBackend`, `FakeBackend`.
- **Factory**: `sinpapel.signing.get_signature_backend()` — lee
  `SINPAPEL_SIGNATURE_BACKEND` y cachea con `lru_cache`.

```
WorkflowEngine.cambiar_estado()
   ├── enforce requiere_firma (0.8.0): sin firma_payload → PermissionError
   ├── lee firma_payload (kwarg)
   ├── get_signature_backend()           ← factory (respeta SINPAPEL_SIGNATURE_BACKEND)
   └── backend.request_signature(...)    ← retorna RegistroFirma
```

Desde 0.8.0 el motor resuelve el backend **vía la factory** — ya no
instancia `FielBackend` hardcodeado. Cualquier backend configurado (manual,
fake, custom) recibe el payload de la transición.

## El Protocol `SignatureBackend`

```python
from typing import ClassVar, Protocol, runtime_checkable
from sinpapel.signing.dto import VerificationResult
from sinpapel.models import RegistroFirma

@runtime_checkable
class SignatureBackend(Protocol):
    name: ClassVar[str]   # identificador (ej. "fiel", "manual", "fake")

    def request_signature(self, content: bytes, signer, **kwargs) -> RegistroFirma: ...
    def verify(self, registro: RegistroFirma) -> VerificationResult: ...
    def revoke(self, registro: RegistroFirma, reason: str) -> None: ...
```

`RegistroFirma` se persiste en BD con `backend_name`, `signer`,
`content_hash`, `signature_payload`, `verification_result` y
`backend_metadata` (JSONField específico del backend).

## Backends incluidos

### `FakeBackend` — solo tests

- `name = "fake"`
- No requiere cryptography ni keypair.
- `content_hash = sha256(content).hexdigest()`.
- `verification_result` siempre `"VALIDA"`.
- `backend_metadata = {"fake": True}`.

Configurar en `settings/test.py`:

```python
SINPAPEL_SIGNATURE_BACKEND = "sinpapel.signing.backends.fake.FakeBackend"
```

**Nunca lo dejes activo en producción.**

### `ManualBackend` — escaneo + sello

- `name = "manual"`
- Para procesos donde la firma se captura en papel y se digitaliza.
- No usa cryptography.
- `kwargs` esperados: `scanned_image_path`, `witness_name`, `is_required`.
- `backend_metadata` incluye `scanned_image_path`, `witness_name`,
  `timestamp`.

### `FielBackend` — FIEL/SAT México (RSA-SHA256 + X.509)

- `name = "fiel"`
- **Modo A — client-side (default y recomendado).** El cliente firma
  localmente con su `.key` y envía `firma_b64` + `certificado_cer_b64`. El
  servidor solo verifica. La clave privada **nunca cruza la red**.

  ```python
  registro = FielBackend().request_signature(
      content=canonical_bytes,
      signer=user,
      firma_b64="...",
      certificado_cer_b64="...",
      is_required=True,
  )
  ```

- **Modo B — server-side (opt-in).** El cliente sube `.cer` + `.key` + `password`.
  El servidor descifra in-memory, firma RSA-SHA256, descarta la key. Gated
  por `SINPAPEL_ALLOW_SERVER_SIGNING=True` (default `False`). Implica
  responsabilidad legal (ver `references/fiel-modes.md`).

  ```python
  registro = FielBackend().sign_server_side(
      content=canonical_bytes,
      signer=user,
      cer_bytes=...,
      key_bytes=...,
      password="...",
      is_required=True,
  )
  ```

#### Cadena de confianza (0.8.0)

`SINPAPEL_FIEL_TRUSTED_CA_BUNDLE` (path a un PEM, o lista de paths, con
las ACs del SAT) controla si se verifica la identidad del emisor del
certificado:

- **Con bundle**: si el cert NO fue emitido por una AC del bundle →
  `SignatureValidationError`. Si sí → `verification_result="VALIDA"` y
  `backend_metadata.cadena_verificada=True`.
- **Sin bundle** (default): la firma íntegra criptográficamente se
  persiste como **`VALIDA_SIN_CADENA`** — la identidad del emisor NO se
  verificó. Antes de 0.8.0 estos casos decían `"VALIDA"`.

Para decidir si una firma es válida usa
`RegistroFirma.RESULTADOS_VALIDOS` (frozenset
`{"VALIDA", "VALIDA_SIN_CADENA"}`), nunca la comparación con el string
`"VALIDA"`.

## Configurar el backend activo

```python
# settings/prod.py
SINPAPEL_SIGNATURE_BACKEND = "sinpapel.signing.backends.fiel.FielBackend"
SINPAPEL_ALLOW_SERVER_SIGNING = False   # mantenlo False salvo necesidad real
# 0.8.0 — ACs de confianza del SAT (path PEM o lista de paths).
# Sin él, las firmas FIEL quedan como VALIDA_SIN_CADENA.
SINPAPEL_FIEL_TRUSTED_CA_BUNDLE = "/etc/sinpapel/sat-ca-bundle.pem"

# settings/test.py
SINPAPEL_SIGNATURE_BACKEND = "sinpapel.signing.backends.fake.FakeBackend"
```

Tras un cambio del setting en runtime (típico en tests), invalida el
cache:

```python
from sinpapel.signing.factory import reset_backend_cache
reset_backend_cache()
```

## Pasar firma a una transición

El motor acepta `firma_payload` en `transition(**kwargs)`. Dos formas:

**Forma A — `RegistroFirma` ya creado por el caller:**

```python
instance.transition("APROBADA", user, firma_payload={"registro_firma_id": registro.id})
```

Desde 0.8.0 el motor **valida** el registro antes de vincularlo, y cada
violación lanza `PermissionError`:

- el registro debe existir;
- su firmante debe ser el usuario que ejecuta la transición
  (`signer == user`);
- su `verification_result` debe estar en
  `RegistroFirma.RESULTADOS_VALIDOS`;
- NO puede estar ya vinculado a otro `SeguimientoWorkflow`
  (una firma no se reutiliza).

**Forma B — el motor invoca al backend configurado:**

```python
instance.transition(
    "APROBADA",
    user,
    firma_payload={
        "contenido": canonical_bytes,
        "firma_b64": "...",
        "certificado_cer_b64": "...",
    },
)
```

Desde 0.8.0 el motor resuelve el backend con `get_signature_backend()`
(respeta `SINPAPEL_SIGNATURE_BACKEND`); los kwargs extra del payload
(todo menos `contenido`) se pasan tal cual al backend.

El `RegistroFirma` queda asociado al `SeguimientoWorkflow` vía OneToOne
(`firma_registro`).

### Exigir firma en la configuración (0.8.0)

`ConfiguracionTransicion.requiere_firma` (default `False`): con `True`,
llamar `transition()` sin `firma_payload` lanza `PermissionError` — la
exigencia vive en la configuración de la transición, no en la buena fe del
caller. `preview_transition()` incluye la key `firma_requerida: bool` para
que la UI sepa pedir la firma por adelantado.

## Contenido canónico para firmar

Cuando el cliente firma localmente, **ambos** lados (cliente y servidor)
deben producir el mismo `content` bytes. `sinpapel-drf` usa este patrón
(`_canonicalize_for_signing`):

```python
import json

def canonical(target_state: str, instance_id: int, user_id: int) -> bytes:
    return json.dumps(
        {"instance_id": instance_id, "target_state": target_state, "user_id": user_id},
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
```

## Escribir un backend custom

Implementa el Protocol y registra el dotted path en `SINPAPEL_SIGNATURE_BACKEND`.

```python
# tu_app/signing.py
from typing import ClassVar
from sinpapel.signing.dto import VerificationResult
from sinpapel.models import RegistroFirma

class MiBackend:
    name: ClassVar[str] = "mi_backend"

    def request_signature(self, content: bytes, signer, **kwargs) -> RegistroFirma:
        # 1) verificar firma (HMAC, OTP, otro proveedor PKI...)
        # 2) crear y persistir RegistroFirma
        return RegistroFirma.objects.create(
            backend_name=self.name,
            signer=signer,
            content_hash=...,
            signature_payload=...,
            verification_result="VALIDA",
            backend_metadata={...},
        )

    def verify(self, registro: RegistroFirma) -> VerificationResult:
        # Idempotente: re-verifica una firma persistida.
        return VerificationResult(valid=True, ...)

    def revoke(self, registro: RegistroFirma, reason: str) -> None:
        # Opcional: marca revocada o no-op.
        pass
```

```python
# settings.py
SINPAPEL_SIGNATURE_BACKEND = "tu_app.signing.MiBackend"
```

## Excepciones

| Excepción | Cuándo |
|---|---|
| `SignatureValidationError` | Firma RSA inválida, certificado expirado/inválido, hash no coincide, o (0.8.0) cert no emitido por una AC de `SINPAPEL_FIEL_TRUSTED_CA_BUNDLE`. |
| `SignatureBackendNotConfiguredError` | `SINPAPEL_SIGNATURE_BACKEND` apunta a algo no importable. |
| `PermissionError` (del motor) | Transición con `requiere_firma=True` sin `firma_payload`, o `registro_firma_id` inválido (no existe, firmante distinto, resultado no válido, ya vinculado). |

Mapeo HTTP típico: `SignatureValidationError → 400`,
`SignatureBackendNotConfiguredError → 500`. `sinpapel-drf` ya lo hace.

## Anti-patrones

- **No** uses `FakeBackend` en producción.
- **No** subas `.key` por la red en producción sin Modo B opt-in y
  revisión legal.
- **No** dejes `SINPAPEL_ALLOW_SERVER_SIGNING=True` como default global.
- **No** persistas `password` ni `.key` en BD, logs o
  `RegistroFirma.backend_metadata` — el backend canónico los descarta
  inmediatamente.
- **No** uses un `content` no determinista (timestamps, orden variable de
  keys): el verify fallará intermitentemente.
- **No** modifiques ni borres `RegistroFirma` después de creado: desde
  0.8.0 el ORM lo enforca — `delete()` lanza `ValueError`. Para revocar,
  usa `backend.revoke()`. Ojo: `queryset.update()/delete()` masivos NO
  pasan por estos hooks.
- **No** compares `verification_result == "VALIDA"`: sin bundle de ACs la
  firma FIEL íntegra se persiste como `VALIDA_SIN_CADENA`. Usa
  `RegistroFirma.RESULTADOS_VALIDOS`.
- **No** despliegues FIEL en producción sin
  `SINPAPEL_FIEL_TRUSTED_CA_BUNDLE`: sin él la identidad del emisor del
  certificado no se verifica.

## Referencia detallada

`references/fiel-modes.md` — comparación detallada de Modos A/B,
implicaciones legales, checklist de seguridad (ADR-012).

## Siguiente paso

- Para probar firmas sin sandbox FIEL: `sinpapel-testing`.
- Para exponer la firma vía API REST: `sinpapel-drf`.
