#!/usr/bin/env python3
"""Genera skills por proveedor desde la fuente canónica en skills/.

Idempotente: borra y regenera dist/ completo. La fuente está en skills/<nombre>/SKILL.md
con frontmatter YAML; los archivos en dist/ NO deben editarse a mano.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
SKILLS_DIR = ROOT / "skills"
DIST = ROOT / "dist"


def parse_skill(skill_md: Path) -> tuple[dict, str]:
    """Devuelve (frontmatter_dict, body_str) de un SKILL.md."""
    text = skill_md.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"Falta frontmatter en {skill_md}")
    _, fm, body = text.split("---\n", 2)
    data = yaml.safe_load(fm) or {}
    if "name" not in data or "description" not in data:
        raise ValueError(f"{skill_md} debe tener `name` y `description` en frontmatter")
    return data, body.lstrip("\n")


def copy_skill_tree(src: Path, dst: Path) -> None:
    """Copia el árbol de la skill canónica al destino (1:1)."""
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def _quote_yaml_scalar(s: str) -> str:
    """Cita una cadena como YAML double-quoted scalar single-line."""
    escaped = s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")
    return f'"{escaped}"'


def write_cursor_rule(meta: dict, body: str, out_file: Path) -> None:
    """Genera un .mdc de Cursor a partir del frontmatter canónico."""
    description = meta["description"]
    globs = meta.get("applies_to", [])
    always_apply = bool(meta.get("always_apply", False))
    fm_lines = ["---", f"description: {_quote_yaml_scalar(description)}"]
    if globs:
        items = ", ".join(_quote_yaml_scalar(g) for g in globs)
        fm_lines.append(f"globs: [{items}]")
    fm_lines.append(f"alwaysApply: {'true' if always_apply else 'false'}")
    fm_lines.append("---")
    fm_lines.append("")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text("\n".join(fm_lines) + body, encoding="utf-8")


def build_agents_md(skills: list[tuple[dict, Path]], out_file: Path) -> None:
    """Índice cross-tool con descripción y enlaces a la fuente canónica."""
    lines = [
        "# AGENTS.md — sinpapel skills",
        "",
        "Índice cross-tool de skills para el framework sinpapel.",
        "Este archivo se **genera** desde `skills/` — no editar a mano.",
        "Para detalles, abre el `SKILL.md` correspondiente.",
        "",
        "## Skills disponibles",
        "",
    ]
    for meta, path in skills:
        name = meta["name"]
        desc = meta["description"].strip().replace("\n", " ")
        lines.append(f"### {name}")
        lines.append("")
        lines.append(desc)
        lines.append("")
        lines.append(f"Fuente: `skills/{path.parent.name}/SKILL.md`")
        lines.append("")
    out_file.write_text("\n".join(lines), encoding="utf-8")


def build(verify: bool = False) -> int:
    if not SKILLS_DIR.exists():
        print(f"ERROR: no existe {SKILLS_DIR}", file=sys.stderr)
        return 1

    skill_dirs = sorted(p for p in SKILLS_DIR.iterdir() if p.is_dir())
    if not skill_dirs:
        print(f"ERROR: no hay skills en {SKILLS_DIR}", file=sys.stderr)
        return 1

    if DIST.exists():
        shutil.rmtree(DIST)

    claude_root = DIST / "claude" / "skills"
    opencode_root = DIST / "opencode" / ".opencode" / "skills"
    cursor_root = DIST / "cursor" / ".cursor" / "rules"
    claude_root.mkdir(parents=True, exist_ok=True)
    opencode_root.mkdir(parents=True, exist_ok=True)
    cursor_root.mkdir(parents=True, exist_ok=True)

    parsed: list[tuple[dict, Path]] = []
    for sk in skill_dirs:
        skill_md = sk / "SKILL.md"
        if not skill_md.exists():
            print(f"AVISO: {sk} no tiene SKILL.md — se omite", file=sys.stderr)
            continue
        meta, body = parse_skill(skill_md)
        parsed.append((meta, skill_md))

        # Claude (identity)
        copy_skill_tree(sk, claude_root / sk.name)
        # OpenCode (identity, compatible con formato Claude)
        copy_skill_tree(sk, opencode_root / sk.name)
        # Cursor (.mdc)
        write_cursor_rule(meta, body, cursor_root / f"{sk.name}.mdc")
        print(f"  ✓ {sk.name}")

    build_agents_md(parsed, DIST / "AGENTS.md")
    print(f"\nGenerado: {len(parsed)} skills → {DIST}")

    if verify:
        # Re-ejecuta y comprueba que no cambia nada (idempotencia)
        snapshot = {p: p.read_bytes() for p in DIST.rglob("*") if p.is_file()}
        build(verify=False)
        for p, content in snapshot.items():
            if not p.exists() or p.read_bytes() != content:
                print(f"FALLO idempotencia: {p}", file=sys.stderr)
                return 2
        print("Idempotencia OK")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Genera skills por proveedor.")
    parser.add_argument("--verify", action="store_true", help="Verifica idempotencia.")
    args = parser.parse_args()
    return build(verify=args.verify)


if __name__ == "__main__":
    sys.exit(main())
