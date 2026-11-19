"""Loader referenčních profilů vozidel (Agent E).

Načítá JSON profily z vehicle-data/references/. Nevymýšlí si žádná data —
pouze čte soubory a vrací dict + cestu. NEMĚNÍ example-vehicle.json (MX-5 ND).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

#: Povinná trojice profilů pro selftest (MX-5 ND se nemění, 2 nové koncepce).
REFERENCE_FILENAMES = (
    "example-vehicle.json",  # Mazda MX-5 ND 2.0 184 6MT (RWD roadster) — REFERENCE, NEMĚNIT
    "honda-civic-fk8-20-vtec-turbo-6mt-eu.json",  # FWD hot-hatch
    "toyota-gr86-zn8-24-d4s-6mt-eu.json",  # RWD kupé 2+2
)


def project_root() -> Path:
    """Kořen AutoEngineerAI (env přepíše default odvozený z loader.py)."""
    override = os.environ.get("AUTOENGINEERAI_ROOT")
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[2]


def references_dir() -> Path:
    return project_root() / "vehicle-data" / "references"


def schema_path() -> Path:
    return references_dir() / "_schema.json"


def load_profile(path: str | Path) -> dict:
    """Načte jeden JSON profil. Vyhazuje FileNotFoundError / json.JSONDecodeError."""
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"Profil {path}: kořen musí být objekt.")
    return data


def load_all(directory: str | Path | None = None) -> dict[str, dict]:
    """Načte všechny 3 povinné profily. Vrátí {vehicle_id: profil}.

    Vyhazuje FileNotFoundError, pokud některý povinný soubor chybí.
    """
    directory = Path(directory) if directory else references_dir()
    profiles: dict[str, dict] = {}
    for filename in REFERENCE_FILENAMES:
        data = load_profile(directory / filename)
        vehicle_id = data.get("vehicle_id", filename)
        profiles[vehicle_id] = data
    return profiles


def load_schema(path: str | Path | None = None) -> dict:
    """Načte _schema.json."""
    with open(Path(path) if path else schema_path(), encoding="utf-8") as fh:
        return json.load(fh)
