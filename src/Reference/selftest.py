"""Selftest Agent E (stdlib only). Spuštění: python3 src/Reference/selftest.py

1. Načte všechny 3 profily (MX-5 ND + 2 nové).
2. Každý validuje schématem _schema.json + pravidly obálek + konzistencí.
3. Ukázkové compare nad syntetickými metrikami (schválně mimo toleranci).
4. Tiskne RAW JSON výstup + seznam zdrojů. Exit 0 jen při plném úspěchu.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.Reference.compare import compare
from src.Reference.loader import REFERENCE_FILENAMES, load_profile, references_dir
from src.Reference.loader import load_schema
from src.Reference.validate import validate_profile


def collect_sources(profiles: dict[str, dict]) -> list[str]:
    """Unikátní seznam zdrojů ze všech obálek (seznam zdrojů pro akceptaci)."""
    sources: set[str] = set()

    def walk(node):
        if isinstance(node, dict):
            if {"source", "source_type", "confidence"} <= set(node.keys()):
                sources.add(f"[{node['source_type']}] {node['source']}")
            for val in node.values():
                walk(val)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    for profile in profiles.values():
        walk(profile)
    return sorted(sources)


def main() -> int:
    refdir = references_dir()
    print(f"# Agent E selftest — adresář: {refdir}")
    schema = load_schema()
    profiles: dict[str, dict] = {}
    report: dict = {"profiles": {}, "compare_demo": {}, "sources": []}
    failed = False

    # 1+2) načtení + validace všech 3 profilů
    for filename in REFERENCE_FILENAMES:
        entry: dict = {"file": filename, "errors": [], "warnings": []}
        try:
            profile = load_profile(refdir / filename)
        except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
            entry["errors"].append(f"načtení selhalo: {exc}")
            report["profiles"][filename] = entry
            failed = True
            continue
        vehicle_id = profile.get("vehicle_id", filename)
        entry["vehicle_id"] = vehicle_id
        errors, warnings = validate_profile(profile, schema)
        entry["errors"] = errors
        entry["warnings"] = warnings
        if errors:
            failed = True
        else:
            profiles[vehicle_id] = profile
        report["profiles"][filename] = entry
        print(f"## {filename} → {vehicle_id}: "
              f"{len(errors)} chyb, {len(warnings)} varování")

    # 3) ukázkové compare nad syntetickými metrikami (záměrně mimo toleranci)
    synthetic = {
        "mazda-mx5-nd-20-184-softtop-6mt-eu": {
            "vmax_kmh": 215, "accel_0_100_s": 6.9, "braking_100_0_m": 38,
            "max_power_kw": 135, "max_torque_nm": 205, "curb_weight_kg": 1075,
        },
        "honda-civic-fk8-20-vtec-turbo-6mt-eu": {
            "vmax_kmh": 265, "accel_0_100_s": 6.4, "braking_100_0_m": None,
            "max_power_kw": 235, "max_torque_nm": 400, "curb_weight_kg": 1410,
        },
        "toyota-gr86-zn8-24-d4s-6mt-eu": {
            "vmax_kmh": 226, "accel_0_100_s": 6.3, "braking_100_0_m": None,
            "max_power_kw": 165, "max_torque_nm": 250, "curb_weight_kg": 1280,
        },
    }
    for vehicle_id, sim in synthetic.items():
        profile = profiles.get(vehicle_id)
        if profile is None:
            report["compare_demo"][vehicle_id] = {"error": "profil neprošel validací"}
            failed = True
            continue
        result = compare({k: v for k, v in sim.items() if v is not None}, profile)
        report["compare_demo"][vehicle_id] = result
        print(f"## compare {vehicle_id}: verdict={result['verdict']} "
              f"(porovnáno {result['compared']}, mimo toleranci {result['failed']})")

    # 4) seznam zdrojů + RAW výstup
    report["sources"] = collect_sources(profiles)
    print(f"## zdrojů celkem: {len(report['sources'])}")
    print("# RAW OUTPUT (JSON) >>>")
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    print("<<< KONEC RAW OUTPUT")
    print(f"# selftest: {'OK' if not failed else 'SELHAL'}")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
