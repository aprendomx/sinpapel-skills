# Verificación HMAC de webhooks — ejemplos por lenguaje

Algoritmo (Stripe-compatible):

```
signature = HMAC-SHA256(secret, f"{timestamp}.".encode() + raw_body)
```

Header outbound:

```
X-Sinpapel-Signature: t=<unix-ts>,v1=<sha256-hex>
```

Tolerancia recomendada para replay protection: 300 segundos (5 min).

## Test vector

```
payload:   b'{"event":"test","data":{"x":1}}'
secret:    "demo-secret"
timestamp: 1714492800
signature: 42740cbdf2a28e4c8c81742f20936d35a6895352d2395818f04a28d4e2030e11
```

## Python

```python
import hmac
import hashlib
import time

def verify_sinpapel_signature(raw_body: bytes, header_value: str, secret: str,
                              tolerance_seconds: int = 300) -> None:
    parts = dict(p.split("=", 1) for p in header_value.split(","))
    t = int(parts["t"])
    if abs(time.time() - t) > tolerance_seconds:
        raise ValueError("timestamp out of tolerance")
    expected = hmac.new(
        secret.encode(),
        f"{t}.".encode() + raw_body,
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected, parts["v1"]):
        raise ValueError("bad signature")
```

## Node.js

```javascript
const crypto = require("crypto");

function verifySinpapelSignature(rawBody, headerValue, secret, toleranceSeconds = 300) {
  const parts = Object.fromEntries(
    headerValue.split(",").map((p) => p.split("="))
  );
  const t = parseInt(parts.t, 10);
  if (Math.abs(Date.now() / 1000 - t) > toleranceSeconds) {
    throw new Error("timestamp out of tolerance");
  }
  const hmac = crypto.createHmac("sha256", secret);
  hmac.update(`${t}.`);
  hmac.update(rawBody);                  // Buffer crudo, NO JSON.stringify(JSON.parse(body))
  const expected = hmac.digest("hex");
  if (!crypto.timingSafeEqual(Buffer.from(expected), Buffer.from(parts.v1))) {
    throw new Error("bad signature");
  }
}
```

## Ruby

```ruby
require "openssl"

def verify_sinpapel_signature(raw_body, header_value, secret, tolerance_seconds: 300)
  parts = Hash[header_value.split(",").map { |p| p.split("=", 2) }]
  t = parts["t"].to_i
  raise "timestamp out of tolerance" if (Time.now.to_i - t).abs > tolerance_seconds

  expected = OpenSSL::HMAC.hexdigest("SHA256", secret, "#{t}.#{raw_body}")
  raise "bad signature" unless Rack::Utils.secure_compare(expected, parts["v1"])
end
```

## Go

```go
package webhook

import (
    "crypto/hmac"
    "crypto/sha256"
    "encoding/hex"
    "errors"
    "fmt"
    "strconv"
    "strings"
    "time"
)

func VerifySinpapelSignature(rawBody []byte, headerValue, secret string, tolerance time.Duration) error {
    parts := map[string]string{}
    for _, p := range strings.Split(headerValue, ",") {
        kv := strings.SplitN(p, "=", 2)
        if len(kv) == 2 {
            parts[kv[0]] = kv[1]
        }
    }
    t, err := strconv.ParseInt(parts["t"], 10, 64)
    if err != nil {
        return fmt.Errorf("bad timestamp: %w", err)
    }
    if d := time.Since(time.Unix(t, 0)); d > tolerance || d < -tolerance {
        return errors.New("timestamp out of tolerance")
    }
    mac := hmac.New(sha256.New, []byte(secret))
    mac.Write([]byte(fmt.Sprintf("%d.", t)))
    mac.Write(rawBody)
    expected := hex.EncodeToString(mac.Sum(nil))
    if !hmac.Equal([]byte(expected), []byte(parts["v1"])) {
        return errors.New("bad signature")
    }
    return nil
}
```

## Trampas comunes

- **Usar el body parseado**: si tu framework parsea JSON antes del
  handler, debes acceder al body **crudo** (`request.body` en Django,
  `req.rawBody` en Express con un middleware adecuado). Re-serializar
  cambia espacios y orden de keys → la firma no verifica.
- **`time.time()` desincronizado**: usa NTP en el servidor. Una deriva
  de >5 min rechaza todos los eventos válidos.
- **Comparación con `==`**: usa funciones de comparación
  constante-tiempo (`hmac.compare_digest`, `crypto.timingSafeEqual`,
  `hmac.Equal`) para evitar timing attacks.
- **Secreto débil**: 32 bytes hex desde `secrets.token_hex(32)` o
  `crypto.randomBytes(32).toString("hex")`.
