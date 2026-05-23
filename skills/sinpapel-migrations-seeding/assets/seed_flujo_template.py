"""Plantilla de data migration para sembrar un flujo de sinpapel.

Adapta los nombres `<TU_APP>`, los estados y las aristas. Copia este
archivo a `<tu_app>/migrations/000X_seed_flujo_<nombre>.py`.

Reglas:
- Usa `apps.get_model("sinpapel", "...")`, NO imports directos.
- `get_or_create` (no `create`) para idempotencia.
- `reverse_code` = `migrations.RunPython.noop` para data migrations
  críticas en producción (no destruir catálogos al revertir).
"""

from django.db import migrations


def seed(apps, schema_editor):
    Etapa = apps.get_model("sinpapel", "Etapa")
    Estado = apps.get_model("sinpapel", "Estado")
    VersionFlujo = apps.get_model("sinpapel", "VersionFlujo")
    ConfiguracionTransicion = apps.get_model("sinpapel", "ConfiguracionTransicion")

    # 1. Etapas
    etapa_inicial, _ = Etapa.objects.get_or_create(
        nombre="Inicial",
        defaults={"activo": True, "orden": 1},
    )
    etapa_final, _ = Etapa.objects.get_or_create(
        nombre="Final",
        defaults={"activo": True, "orden": 2},
    )

    # 2. Estados
    estados_def = [
        ("CAPTURA", etapa_inicial, 1, "#4DEFE2"),
        ("EN_REVISION", etapa_inicial, 2, "#FFA500"),
        ("APROBADA", etapa_final, 3, "#00C853"),
        ("RECHAZADA", etapa_final, 4, "#D32F2F"),
    ]
    estados = {}
    for nombre, etapa, orden, color in estados_def:
        obj, _ = Estado.objects.get_or_create(
            nombre=nombre,
            defaults={"activo": True, "etapa": etapa, "orden": orden, "color": color},
        )
        estados[nombre] = obj

    # 3. Versión del flujo
    flujo, _ = VersionFlujo.objects.get_or_create(
        nombre="<NOMBRE_FLUJO>",
        defaults={"activo": True, "descripcion": "Flujo estándar v1"},
    )

    # 4. Transiciones
    aristas = [
        ("CAPTURA", "EN_REVISION"),
        ("EN_REVISION", "APROBADA"),
        ("EN_REVISION", "RECHAZADA"),
    ]
    for origen, destino in aristas:
        ConfiguracionTransicion.objects.get_or_create(
            flujo=flujo,
            estado_origen=estados[origen],
            estado_destino=estados[destino],
        )


class Migration(migrations.Migration):
    dependencies = [
        ("sinpapel", "0001_initial"),
        # ("<TU_APP>", "0001_initial"),
    ]
    operations = [
        # Para data migrations críticas en prod, deja noop:
        migrations.RunPython(seed, reverse_code=migrations.RunPython.noop),
    ]
