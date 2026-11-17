# AutoEngineerAI – katalog parametrů A-Chassis (Agent A, FÁZE 4.1)
"""Dotazy nad `parameters.json` (zmrazené rozhraní 19 polí).

Použití::
    from src.Chassis.catalog import loader
    recs = loader.load()
    loader.get_by_id(recs, "horsepower")
    loader.by_category(recs, "MUTABLE_TUNE")
    loader.by_config_path(recs, "engine.horsepower")

Selftest (akceptace: exit 0 + raw výstup)::
    python3 src/Chassis/catalog/loader.py --selftest
"""
from __future__ import annotations

import json
import os
import sys

FIELDS = ("id", "tune_key", "category", "config_path", "value", "unit",
          "value_type", "min", "max", "default", "function",
          "physical_effect", "used_in", "depends_on", "conflicts",
          "change_method", "source", "confidence", "verification_status")

CATEGORIES = ("MUTABLE_TUNE", "SCRIPT_CONTROLLED", "STRUCTURE_CONTROLLED",
              "READ_ONLY", "UNKNOWN")

VERIFICATION = ("PASS", "PENDING")

VALUE_TYPES = ("boolean", "integer", "number", "string", "array",
               "object", "null")

EXPECTED_COUNT = 138  # = počet položek achassis_v1 po F4.3 live-rekonciliaci (Agent R)

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "parameters.json")


def load(path: str = DATA_FILE) -> list[dict]:
    """Načte katalog a validuje ho. Vrací seznam záznamů."""
    with open(path, encoding="utf-8") as f:
        recs = json.load(f)
    validate(recs)
    return recs


def validate(recs: list[dict]) -> None:
    """Validace zmrazeného rozhraní. Chyba = ValueError s důvodem."""
    if not isinstance(recs, list) or not recs:
        raise ValueError("katalog musí být neprázdný seznam záznamů")
    seen_ids: set[str] = set()
    seen_paths: set[str] = set()
    cats: set[str] = set()
    for i, r in enumerate(recs):
        if set(r.keys()) != set(FIELDS):
            raise ValueError(
                f"záznam {i}: pole {sorted(r.keys())} != {sorted(FIELDS)}")
        if r["id"] in seen_ids:
            raise ValueError(f"duplicitní id: {r['id']!r}")
        seen_ids.add(r["id"])
        cats.add(r["category"])
        if r["category"] not in CATEGORIES:
            raise ValueError(f"{r['id']}: neznámá category {r['category']!r}")
        if r["category"] == "MUTABLE_TUNE" and not r["tune_key"]:
            raise ValueError(
                f"{r['id']}: MUTABLE_TUNE bez ověřeného tune_key")
        if r["config_path"]:
            if r["config_path"] in seen_paths:
                raise ValueError(
                    f"duplicitní config_path: {r['config_path']!r}")
            seen_paths.add(r["config_path"])
        if r["value_type"] not in VALUE_TYPES:
            raise ValueError(f"{r['id']}: neznámé value_type")
        if not isinstance(r["confidence"], (int, float)) or not (
                0 <= r["confidence"] <= 1):
            raise ValueError(f"{r['id']}: confidence mimo 0..1")
        if r["verification_status"] not in VERIFICATION:
            raise ValueError(f"{r['id']}: neznámý verification_status")
        for k in ("used_in", "depends_on", "conflicts"):
            if not isinstance(r[k], list):
                raise ValueError(f"{r['id']}: {k} musí být seznam")
    missing = set(CATEGORIES) - cats
    if missing:
        raise ValueError(f"chybí kategorie: {sorted(missing)}")


def get_by_id(recs: list[dict], record_id: str) -> dict | None:
    """Jeden záznam podle `id`, nebo None."""
    for r in recs:
        if r["id"] == record_id:
            return r
    return None


def by_category(recs: list[dict], category: str) -> list[dict]:
    """Všechny záznamy dané kategorie."""
    if category not in CATEGORIES:
        raise ValueError(f"neznámá category {category!r}")
    return [r for r in recs if r["category"] == category]


def by_config_path(recs: list[dict], config_path: str) -> dict | None:
    """Jeden záznam podle `config_path`, nebo None."""
    for r in recs:
        if r["config_path"] == config_path:
            return r
    return None


def run_selftest(path: str = DATA_FILE) -> dict:
    """Akceptační selftest: načtení všech záznamů, každá kategorie
    zastoupena, žádný MUTABLE_TUNE bez ověřeného tune_key. Vrací report."""
    recs = load(path)
    if len(recs) != EXPECTED_COUNT:
        raise ValueError(
            f"očekáváno {EXPECTED_COUNT} záznamů (= achassis_v1), mám {len(recs)}")
    counts = {c: len(by_category(recs, c)) for c in CATEGORIES}
    if any(v == 0 for v in counts.values()):
        raise ValueError(f"nezastoupená kategorie: {counts}")
    if any(not r["tune_key"] for r in by_category(recs, "MUTABLE_TUNE")):
        raise ValueError("MUTABLE_TUNE bez ověřeného tune_key")
    pend = sorted(r["id"] for r in recs
                  if r["verification_status"] == "PENDING")
    return {
        "selftest": "OK",
        "n_records": len(recs),
        "category_counts": counts,
        "n_pending_studio": len(pend),
        "pending_studio": pend,
        "sample": get_by_id(recs, "horsepower"),
    }


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] not in ("--selftest",):
        print(f"neznámý argument {sys.argv[1]!r}; povolen: --selftest",
              file=sys.stderr)
        sys.exit(2)
    result = run_selftest()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("SELFTEST OK")
