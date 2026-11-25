"""La versión es la misma en todos los lugares donde vive.

pyproject.toml, `applyops.__version__` (que también publica FastAPI y /health),
el badge, la tabla y el pie del README y la sección más reciente del CHANGELOG.
Un desfase se ve en el PR, no al pushear el tag.

Refactor: Nicolás Cano Leal / Fecha: 2026-11-25
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

from applyops import __version__

RAIZ = Path(__file__).resolve().parents[1]


def _version_pyproject() -> str:
    datos = tomllib.loads((RAIZ / "pyproject.toml").read_text(encoding="utf-8"))
    return str(datos["project"]["version"])


def test_paquete_igual_a_pyproject() -> None:
    assert __version__ == _version_pyproject()


def test_readme_badge_tabla_y_pie() -> None:
    readme = (RAIZ / "README.md").read_text(encoding="utf-8")
    assert f"versi%C3%B3n-{__version__}-blue" in readme, "badge desfasado"
    assert f"| **Versión** | {__version__} |" in readme, "tabla desfasada"
    assert f"ApplyOps v{__version__} ·" in readme.strip().splitlines()[-1], "pie desfasado"


def test_changelog_tiene_la_version_como_la_mas_reciente() -> None:
    changelog = (RAIZ / "CHANGELOG.md").read_text(encoding="utf-8")
    versiones = re.findall(r"^## \[(\d+\.\d+\.\d+[^\]]*)\]", changelog, flags=re.MULTILINE)
    assert versiones, "CHANGELOG sin secciones de versión"
    assert versiones[0] == __version__
