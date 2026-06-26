# FIEL — Modo A (client-side) vs Modo B (server-side)

`FielBackend` soporta dos modos de firma. La elección tiene
implicaciones de seguridad y legales (ADR-012). Léelos completos antes de
habilitar Modo B en producción.

## Modo A — client-side (default, recomendado)

El cliente firma localmente con su `.key` y solo envía:

- `firma_b64` — firma RSA-SHA256 codificada en base64.
- `certificado_cer_b64` — certificado X.509 DER en base64.

**El servidor solo verifica.** La clave privada **nunca cruza la red**.

Pros:

- No-repudio sólido: la clave privada nunca sale del dispositivo del
  firmante.
- Reduce superficie de ataque del servidor (sin keys en memoria).
- Cumple expectativas de auditoría más estrictas.

Contras:

- Requiere que el cliente tenga capacidad de firmar (browser con
  crypto-libs o app nativa).
- Más complejidad en el frontend.

Setting: `SINPAPEL_ALLOW_SERVER_SIGNING = False` (default).

## Modo B — server-side (opt-in)

El cliente sube `.cer` + `.key` + `password`. El servidor:

1. Descifra la `.key` en memoria con `password`.
2. Firma RSA-SHA256 sobre el `content` canónico.
3. **Descarta** key y password (`_with_secure_key_buffer` + `gc.collect()`).
4. Persiste `RegistroFirma` con `backend_metadata.mode = "server-side"`.

Pros:

- UX más simple para usuarios no técnicos.
- Sin dependencias crypto en el navegador.

Contras:

- La clave privada existe en RAM del servidor durante la firma.
- Implica responsabilidad legal sobre el manejo de la clave.
- Aumenta requisitos de revisión legal y seguridad.

Settings:

```python
SINPAPEL_ALLOW_SERVER_SIGNING = True
```

Sin este flag, el dispatcher de `sinpapel-drf` rechaza con `400`.

## Checklist de seguridad para Modo B

ADR-012 lista (extracto):

- [ ] `SINPAPEL_ALLOW_SERVER_SIGNING` controlado por env var, no
      hardcoded.
- [ ] `key_file` y `password` marcados `write_only=True` en serializer
      (no leakean en responses). Verificado en `sinpapel-drf` v0.3.0.
- [ ] Liberación explícita de memoria: `_with_secure_key_buffer` borra
      buffers + `gc.collect()` en `finally`.
- [ ] Logging conservador: no logear key, password, ni `.key` decodificada.
      Tests con `caplog` que verifican que no hay leak.
- [ ] `RegistroFirma.backend_metadata.mode = "server-side"` queda
      registrado para forensics.
- [ ] HTTPS-only enforcement en producción (responsabilidad del consumer).
- [ ] Rate limiting opt-in (`UserRateThrottle` u otro) — `sinpapel-drf`
      v0.3.0 no lo trae built-in.
- [ ] Revisión legal de uso de FIEL del SAT para firma electrónica
      avanzada (Código Civil Federal Art. 1803, NOM-151, ley FECEM si
      aplica).

## Verificación de la firma

Ambas modas persisten `RegistroFirma` con el mismo schema. `verify()` del
backend re-valida cualquier `RegistroFirma`:

```python
from sinpapel.signing import get_signature_backend

backend = get_signature_backend()
result = backend.verify(registro)
assert result.valid
```

`VerificationResult` (DTO en `sinpapel/signing/dto.py`):

- `valid` (bool)
- `subject` (`x509.Name` del certificado)
- `not_valid_before`, `not_valid_after`
- `rfc_firmante`, `numero_serie_cer`
- `errors` (lista de strings, vacío si válido)

## Errores típicos

| Error | Causa | Diagnóstico |
|---|---|---|
| `SignatureValidationError: signature does not verify` | El `firma_b64` no coincide con `content` + `cert.public_key`. | Re-canonizar `content`, verificar codificación base64 sin padding extra. |
| `SignatureValidationError: certificate expired` | `cert.not_valid_after < now`. | El firmante debe renovar su FIEL. |
| `SignatureValidationError: certificate not yet valid` | `cert.not_valid_before > now`. | Reloj del servidor mal sincronizado, o cert futuro. |
| `SignatureBackendNotConfiguredError` | `SINPAPEL_SIGNATURE_BACKEND` dotted path roto. | Verificar import path; tras cambio en runtime, `reset_backend_cache()`. |
| `ValueError: server-side signing not allowed` (en sinpapel-drf) | `SINPAPEL_ALLOW_SERVER_SIGNING=False`. | Habilitar el flag o usar Modo A. |
