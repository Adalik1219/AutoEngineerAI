#!/usr/bin/env python3
"""Validátor kontraktů AutoEngineerAI — pouze stdlib, chyby česky.

Použití:
  python tools/validate_contracts.py
      Selftest všech schémat (ke každému 1 validní + 1 nevalidní příklad),
      kontrola vzorových artefaktů contracts/examples/*.valid.json
      a kontrola vehicle-data/references/*.json proti
      vehicle-data/references/_schema.json. Exit 0 = vše prošlo.

  python tools/validate_contracts.py --schema <jméno> <soubor...>
      Zkontroluje dané soubory proti schématu <jméno>
      (vehicle_profile | reference_profile | vehicle_config | change_plan |
       test_result | diagnosis | chassis_info | scenario | manifest).
      Exit 0 = všechny platné, 1 = jakákoli chyba.

  python tools/validate_contracts.py --list
      Vypíše dostupná schémata.

Podporovaná podmnožina JSON Schema draft 2020-12: type (včetně seznamů
typů), const, enum, required, properties, additionalProperties, pattern,
minimum/maximum, exclusiveMinimum/exclusiveMaximum, min/maxItems,
min/maxLength, min/maxProperties, items, anyOf/oneOf/allOf, $ref na
lokální #/$defs, format: date.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "contracts"
EXAMPLES = CONTRACTS / "examples"
VEHICLE_DATA_SCHEMA = ROOT / "vehicle-data" / "references" / "_schema.json"
VEHICLE_DATA_DIR = ROOT / "vehicle-data" / "references"

SCHEMA_FILES = {
    "vehicle_profile": "vehicle_profile.schema.json",
    "reference_profile": "reference_profile.schema.json",
    "vehicle_config": "vehicle_config.schema.json",
    "change_plan": "change_plan.schema.json",
    "test_result": "test_result.schema.json",
    "diagnosis": "diagnosis.schema.json",
    "chassis_info": "chassis_info.schema.json",
    "scenario": "scenario.schema.json",
    "manifest": "manifest.schema.json",
}

EXAMPLE_FOR_SCHEMA = {
    "vehicle_profile": "vehicle_profile.valid.json",
    "reference_profile": "reference_profile.valid.json",
    "vehicle_config": "vehicle_config.valid.json",
    "change_plan": "change_plan.valid.json",
    "test_result": "test_result.valid.json",
    "diagnosis": "diagnosis.valid.json",
    "chassis_info": "chassis_info.valid.json",
    "scenario": "scenario.valid.json",
    "manifest": "manifest.valid.json",
}

# Značka v contracts/reference_profile.schema.json ($defs/proven, $comment):
# ARCH §3.2 — value:null (chybějící údaj) ⇒ confidence:0.
_PROVEN_NULL_CONFIDENCE_COMMENT = (
    "proven-null-confidence-0: ARCH §3.2 — value:null (chybějící údaj) ⇒ confidence:0."
)

# Ke každému schématu 1 nevalidní příklad (musí selhat aspoň 1 chybou).
INVALID_SAMPLES = {
    "vehicle_profile": {
        "schema_version": "1.0.0",
        "profile_id": "spatne-id-bez-prefixu",
        "source_model_hash": "není-hash",
        "chassis": {},
        "hierarchy": {"root": "Chassis", "wheels": []},
        "dimensions": {"wheelbase_m": -2.7, "track_f_m": 1.55, "track_r_m": 1.55},
        "mass": {"total_kg": 1400, "center_of_mass": [0, 0.55]},
        "wheels": [],
        "powertrain": {"drive_type": "4WD"},
        "brakes": {"bias_front": 1.5},
    },
    "reference_profile": {
        "schema_version": "1.0.0",
        "vehicle": {"make": "Mazda", "model": "MX-5", "year": 2020},
        "specs": {
            "power_kw": {"value": 135, "confidence": 1.0},
            "mass_kg": {"value": 1075, "source": "odhad", "confidence": 1.5},
        },
        "target_metrics": [],
    },
    "vehicle_config": {
        "schema_version": "1.0.0",
        "config_id": "cfg_0042",
        "vehicle_profile_id": "vp_2026_mx5_demo",
        "chassis_adapter": "achassis-v1",
        "parameters": {
            "engine": {},
            "transmission": {},
            "tires": {},
            "suspension": {},
            "steering": {},
            "brakes": {},
        },
        "rationale": "chybí geometry_overrides",
    },
    "change_plan": {
        "schema_version": "1.0.0",
        "plan_id": "plan_0012",
        "diagnosis_ref": "dg_0007",
        "steps": [{"area": "motor"}],
        "chassis_decision": "rewrite",
        "priorities": ["tires"],
        "stop_conditions": {"max_iterations": 0},
    },
    "test_result": {
        "schema_version": "1.0.0",
        "result_id": "tr_0100",
        "config_id": "cfg_0042",
        "scenario_id": "straight_brake_100_0",
        "environment": {"mode": "studio", "seed": 1234},
        "metrics": {},
        "deviations_vs_target": {},
        "score": 1.5,
        "reproduced_runs": 0,
        "raw_telemetry_ref": "telemetry/tr_0100.csv",
    },
    "diagnosis": {
        "schema_version": "1.0.0",
        "diagnosis_id": "dg_0007",
        "profile_id": "vp_2026_mx5_demo",
        "items": [{"area": "tires", "symptom": "smyk"}],
    },
    "chassis_info": {
        "schema_version": "1.0.0",
        "chassis_id": "a-chassis-ac6c-demo",
        "adapter_id": "achassis-v1",
        "detection_confidence": 2.0,
        "limits": "měl být seznam",
    },
    "scenario": {
        "schema_version": "1.0.0",
        "scenario_id": "drag_race",
        "kind": "drag_race",
        "seed": "hodně",
    },
    "manifest": {
        "schema_version": "1.0.0",
        "run_id": "spatny-tvar",
        "seed": 1,
        "scenario_versions": {},
        "artifacts": [{"kind": "test_result"}],
    },
}


def _is_int(v: object) -> bool:
    if isinstance(v, bool):
        return False
    if isinstance(v, int):
        return True
    return isinstance(v, float) and v.is_integer()


def _is_num(v: object) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


_TYPE_NAMES = {
    "object": "objekt",
    "array": "pole",
    "string": "řetězec",
    "number": "číslo",
    "integer": "celé číslo",
    "boolean": "logická hodnota",
    "null": "null",
}


def _check_type(value: object, want: str) -> bool:
    if want == "object":
        return isinstance(value, dict)
    if want == "array":
        return isinstance(value, list)
    if want == "string":
        return isinstance(value, str)
    if want == "number":
        return _is_num(value)
    if want == "integer":
        return _is_int(value)
    if want == "boolean":
        return isinstance(value, bool)
    if want == "null":
        return value is None
    return False


def _resolve_ref(ref: str, root: dict) -> dict:
    if not ref.startswith("#/"):
        raise ValueError(f"podporovány jsou jen lokální reference (#/...), je {ref!r}")
    node: object = root
    for part in ref[2:].split("/"):
        part = part.replace("~1", "/").replace("~0", "~")
        if not isinstance(node, dict) or part not in node:
            raise ValueError(f"reference {ref!r} neexistuje ve schématu")
        node = node[part]
    if not isinstance(node, dict):
        raise ValueError(f"reference {ref!r} neukazuje na objekt schématu")
    return node


def _validate(value: object, schema: dict, root: dict, path: str) -> list[str]:
    errs: list[str] = []
    if "$ref" in schema:
        try:
            target = _resolve_ref(schema["$ref"], root)
        except ValueError as exc:
            return [f"{path or '$'}: poškozené schéma ({exc})"]
        errs.extend(_validate(value, target, root, path))
        schema = {k: v for k, v in schema.items() if k != "$ref"}

    if (
        isinstance(value, dict)
        and schema.get("$comment") == _PROVEN_NULL_CONFIDENCE_COMMENT
        and "value" in value
        and value["value"] is None
        and "confidence" in value
        and value["confidence"] != 0
    ):
        errs.append(
            f"{path or '$'}: je-li value null (chybějící údaj), "
            f"confidence musí být 0 (ARCH §3.2), je {value['confidence']!r}"
        )

    want = schema.get("type")
    if want is not None:
        wants = [want] if isinstance(want, str) else list(want)
        if not any(_check_type(value, w) for w in wants):
            names = " nebo ".join(_TYPE_NAMES.get(w, w) for w in wants)
            return [f"{path or '$'}: očekáván {names}, je {type(value).__name__}"]

    if "const" in schema and value != schema["const"]:
        errs.append(f"{path or '$'}: musí být přesně {schema['const']!r}")

    if "enum" in schema and value not in schema["enum"]:
        errs.append(
            f"{path or '$'}: hodnota {value!r} není mezi povolenými {schema['enum']!r}"
        )

    if isinstance(value, dict):
        for req in schema.get("required", []):
            if req not in value:
                errs.append(f"{path or '$'}: chybí povinné pole '{req}'")
        props = schema.get("properties", {})
        for key, sub in props.items():
            if key in value:
                errs.extend(_validate(value[key], sub, root, f"{path}/{key}"))
        add = schema.get("additionalProperties", True)
        if add is False:
            for key in value:
                if key not in props:
                    errs.append(f"{path or '$'}: neznámé pole '{key}'")
        elif isinstance(add, dict):
            for key in value:
                if key not in props:
                    errs.extend(_validate(value[key], add, root, f"{path}/{key}"))
        for kw in ("minProperties", "maxProperties"):
            if kw in schema:
                n = len(value)
                limit = schema[kw]
                if kw == "minProperties" and n < limit:
                    errs.append(f"{path or '$'}: málo položek ({n} < {limit})")
                if kw == "maxProperties" and n > limit:
                    errs.append(f"{path or '$'}: příliš mnoho položek ({n} > {limit})")

    if isinstance(value, list):
        for kw in ("minItems", "maxItems"):
            if kw in schema:
                n = len(value)
                limit = schema[kw]
                if kw == "minItems" and n < limit:
                    errs.append(f"{path or '$'}: pole je příliš krátké ({n} < {limit})")
                if kw == "maxItems" and n > limit:
                    errs.append(f"{path or '$'}: pole je příliš dlouhé ({n} > {limit})")
        items = schema.get("items")
        if isinstance(items, dict):
            for i, el in enumerate(value):
                errs.extend(_validate(el, items, root, f"{path}[{i}]"))

    if isinstance(value, str):
        if "pattern" in schema and re.search(schema["pattern"], value) is None:
            errs.append(
                f"{path or '$'}: hodnota {value!r} neodpovídá vzoru {schema['pattern']!r}"
            )
        for kw in ("minLength", "maxLength"):
            if kw in schema:
                n = len(value)
                limit = schema[kw]
                if kw == "minLength" and n < limit:
                    errs.append(f"{path or '$'}: řetězec je příliš krátký ({n} < {limit})")
                if kw == "maxLength" and n > limit:
                    errs.append(f"{path or '$'}: řetězec je příliš dlouhý ({n} > {limit})")
        if schema.get("format") == "date":
            try:
                date.fromisoformat(value)
            except ValueError:
                errs.append(f"{path or '$'}: není platné datum (očekáván formát RRRR-MM-DD)")

    if _is_num(value):
        for kw in ("minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum"):
            if kw in schema:
                limit = schema[kw]
                bad = (
                    (kw == "minimum" and value < limit)
                    or (kw == "maximum" and value > limit)
                    or (kw == "exclusiveMinimum" and value <= limit)
                    or (kw == "exclusiveMaximum" and value >= limit)
                )
                if bad:
                    errs.append(f"{path or '$'}: hodnota {value!r} porušuje mez {kw}={limit!r}")

    for kw in ("allOf", "anyOf", "oneOf"):
        if kw in schema:
            branches = schema[kw]
            results = [_validate(value, b, root, path) for b in branches]
            if kw == "allOf":
                for r in results:
                    errs.extend(r)
            elif kw == "anyOf":
                if all(r for r in results):
                    errs.append(
                        f"{path or '$'}: neodpovídá žádné povolené variantě "
                        f"({len(results)} možností)"
                    )
            elif kw == "oneOf":
                if sum(1 for r in results if not r) != 1:
                    errs.append(f"{path or '$'}: musí odpovídat právě jedné variantě")

    return errs


def load_json(path: Path) -> tuple[object, str | None]:
    """Načte JSON; vrátí (data, chyba-česky nebo None)."""
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except FileNotFoundError:
        return None, f"soubor neexistuje: {path}"
    except json.JSONDecodeError as exc:
        return None, f"soubor {path} není platný JSON: {exc}"
    except OSError as exc:
        return None, f"soubor {path} nelze přečíst: {exc}"


def validate_against_schema(data: object, schema: dict) -> list[str]:
    """Zkontroluje data proti schématu; vrátí seznam českých chyb (prázdný = OK)."""
    if not isinstance(schema, dict):
        return ["$: poškozené schéma (kořen není objekt)"]
    return _validate(data, schema, schema, "$")


def check_file(data_path: Path, schema_path: Path) -> list[str]:
    """Zkontroluje jeden soubor; vrátí seznam českých chyb."""
    data, err = load_json(data_path)
    if err is not None:
        return [err]
    schema, err = load_json(schema_path)
    if err is not None:
        return [err]
    if not isinstance(schema, dict):
        return [f"schéma {schema_path} nemá kořenový objekt"]
    return [f"{data_path}: {e}" for e in validate_against_schema(data, schema)]


def run_selftest() -> tuple[int, int, list[str]]:
    """Selftest: ke každému schématu 1 validní + 1 nevalidní příklad,
    plus kontrola ARCH §3.2 (reference_profile: null⇒confidence 0).

    Vrací (počet_kontrol, počet_chyb, výstupní_řádky).
    """
    lines: list[str] = []
    checks = 0
    failures = 0
    for name, schema_file in SCHEMA_FILES.items():
        schema_path = CONTRACTS / schema_file
        schema, err = load_json(schema_path)
        if err is not None or not isinstance(schema, dict):
            lines.append(f"[CHYBA] schéma {name}: {err or 'kořen není objekt'}")
            failures += 1
            continue

        # 1) validní příklad ze souboru
        valid_path = EXAMPLES / EXAMPLE_FOR_SCHEMA[name]
        data, err = load_json(valid_path)
        checks += 1
        if err is not None:
            lines.append(f"[CHYBA] {name}: validní příklad nelze načíst: {err}")
            failures += 1
        else:
            errs = validate_against_schema(data, schema)
            if errs:
                lines.append(f"[CHYBA] {name}: validní příklad neprošel ({len(errs)} chyb):")
                lines.extend(f"    {e}" for e in errs[:5])
                failures += 1
            else:
                lines.append(f"[OK] {name}: validní příklad prošel ({valid_path.name})")

        # 2) nevalidní příklad musí selhat
        checks += 1
        errs = validate_against_schema(INVALID_SAMPLES[name], schema)
        if not errs:
            lines.append(f"[CHYBA] {name}: nevalidní příklad prošel, ačkoli měl selhat")
            failures += 1
        else:
            lines.append(f"[OK] {name}: nevalidní příklad správně zamítnut ({len(errs)} chyb)")

    # 3) ARCH §3.2: value:null (chybějící údaj) ⇒ confidence:0 (reference_profile).
    ref_schema, err = load_json(CONTRACTS / SCHEMA_FILES["reference_profile"])
    if err is not None or not isinstance(ref_schema, dict):
        lines.append(f"[CHYBA] reference_profile: schéma nelze načíst pro kontrolu null⇒0: {err}")
        failures += 1
    else:
        base_doc = {
            "schema_version": "1.0.0",
            "vehicle": {"make": "Mazda", "model": "MX-5", "year": 2020},
            "specs": {},
            "target_metrics": [
                {"metric": "brake_100_0_m", "target": 37.0, "tolerance": 2.0, "weight": 0.9}
            ],
        }

        # 3a) null + confidence 0.5 musí být INVALID
        checks += 1
        bad_doc = dict(base_doc)
        bad_doc["specs"] = {
            "brake_100_0_m": {
                "value": None,
                "source": "neznámé — tovární údaj neexistuje",
                "confidence": 0.5,
            }
        }
        errs = validate_against_schema(bad_doc, ref_schema)
        if not errs:
            lines.append(
                "[CHYBA] reference_profile: null+0.5 prošel, "
                "ačkoli ARCH §3.2 vyžaduje confidence 0"
            )
            failures += 1
        else:
            lines.append(
                f"[OK] reference_profile: null+0.5 správně zamítnut ({len(errs)} chyb)"
            )

        # 3b) null + confidence 0 musí být VALID
        checks += 1
        good_doc = dict(base_doc)
        good_doc["specs"] = {
            "brake_100_0_m": {
                "value": None,
                "source": "neznámé — tovární údaj neexistuje",
                "confidence": 0,
            }
        }
        errs = validate_against_schema(good_doc, ref_schema)
        if errs:
            lines.append(
                f"[CHYBA] reference_profile: null+0 neprošel ({len(errs)} chyb):"
            )
            lines.extend(f"    {e}" for e in errs[:5])
            failures += 1
        else:
            lines.append("[OK] reference_profile: null+0 prošel (chybějící údaj)")

    return checks, failures, lines


def check_vehicle_data() -> tuple[int, int, list[str]]:
    """Zkontroluje vehicle-data/references/*.json proti _schema.json."""
    lines: list[str] = []
    checks = 0
    failures = 0
    schema, err = load_json(VEHICLE_DATA_SCHEMA)
    if err is not None or not isinstance(schema, dict):
        return 0, 1, [f"[CHYBA] schéma vehicle-data: {err or 'kořen není objekt'}"]
    for path in sorted(VEHICLE_DATA_DIR.glob("*.json")):
        if path.name.startswith("_"):
            continue
        checks += 1
        errs = check_file(path, VEHICLE_DATA_SCHEMA)
        if errs:
            lines.append(f"[CHYBA] {path.name}: neprošel ({len(errs)} chyb):")
            lines.extend(f"    {e}" for e in errs[:5])
            failures += 1
        else:
            lines.append(f"[OK] vehicle-data: {path.name} prošel")
    if checks == 0:
        lines.append("[INFO] vehicle-data: žádné profily ke kontrole")
    return checks, failures, lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validátor kontraktů AutoEngineerAI (pouze stdlib)."
    )
    parser.add_argument("--schema", choices=sorted(SCHEMA_FILES), help="jméno schématu")
    parser.add_argument("--list", action="store_true", help="vypsat dostupná schémata")
    parser.add_argument("files", nargs="*", help="kontrolované JSON soubory")
    args = parser.parse_args(argv)

    if args.list:
        for name in sorted(SCHEMA_FILES):
            print(f"{name}: {SCHEMA_FILES[name]}")
        return 0

    if args.schema is not None:
        if not args.files:
            print("Chyba: --schema vyžaduje aspoň jeden soubor.", file=sys.stderr)
            return 1
        schema_path = CONTRACTS / SCHEMA_FILES[args.schema]
        failures = 0
        for f in args.files:
            errs = check_file(Path(f), schema_path)
            if errs:
                failures += 1
                print(f"NEPLATNÝ: {f}")
                for e in errs[:20]:
                    print(f"  {e}")
            else:
                print(f"PLATNÝ: {f}")
        return 1 if failures else 0

    if args.files:
        print("Chyba: bez --schema nelze určit schéma; spusť bez argumentů pro selftest.",
              file=sys.stderr)
        return 1

    total_checks = 0
    total_failures = 0
    print("== Selftest schémat (1 validní + 1 nevalidní příklad ke každému + null⇒0) ==")
    checks, failures, lines = run_selftest()
    total_checks += checks
    total_failures += failures
    for line in lines:
        print(line)
    print("== Vzorové artefakty + example-vehicle.json ==")
    checks, failures, lines = check_vehicle_data()
    total_checks += checks
    total_failures += failures
    for line in lines:
        print(line)
    print(f"-- Celkem kontrol: {total_checks}, chyb: {total_failures}")
    if total_failures:
        print("VÝSLEDEK: NEÚSPĚCH — oprav výše uvedené chyby.")
        return 1
    print("VÝSLEDEK: ÚSPĚCH — všechny kontrakty a vzory jsou platné.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
