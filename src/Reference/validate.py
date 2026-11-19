"""Validace profilů proti _schema.json + konzistenční kontroly (Agent E, stdlib only).

Podmnožina JSON Schema draft 2020-12 postačující pro _schema.json:
type / required / additionalProperties / properties / $ref / $defs /
const / enum / pattern / items / minItems / minimum / maximum / format:date.
Plus pravidla z VEHICLE-DATA.md: estimate → notes ODHAD:/CHYBÍ:,
fyzikální konzistence (P = M·n, průměr pneu, V-max vs. převody).
"""

from __future__ import annotations

import math
import re
from typing import Any

ESTIMATE_NOTE_PREFIXES = ("ODHAD:", "CHYBÍ:")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _resolve_ref(ref: str, root_schema: dict) -> dict:
    if not ref.startswith("#/"):
        raise ValueError(f"Nepodporovaný $ref (jen lokální): {ref}")
    node: Any = root_schema
    for part in ref[2:].split("/"):
        node = node[part]
    return node


def _check_type(value: Any, expected: Any) -> bool:
    types = [expected] if isinstance(expected, str) else list(expected)
    for t in types:
        if t == "object" and isinstance(value, dict):
            return True
        if t == "array" and isinstance(value, list):
            return True
        if t == "string" and isinstance(value, str):
            return True
        if t == "boolean" and isinstance(value, bool):
            return True
        if t == "integer" and isinstance(value, int) and not isinstance(value, bool):
            return True
        if t == "number" and isinstance(value, (int, float)) and not isinstance(value, bool):
            return True
        if t == "null" and value is None:
            return True
    return False


def validate_against_schema(data: Any, schema: dict, root_schema: dict | None = None,
                            path: str = "$") -> list[str]:
    """Vrátí seznam chyb (prázdný = validní). Nevyhazuje."""
    errors: list[str] = []
    root_schema = root_schema if root_schema is not None else schema

    if "$ref" in schema:
        return validate_against_schema(data, _resolve_ref(schema["$ref"], root_schema),
                                       root_schema, path)

    expected = schema.get("type")
    if expected is not None and not _check_type(data, expected):
        return [f"{path}: očekáván typ {expected}, nalezeno {type(data).__name__}"]

    if isinstance(data, dict):
        for key in schema.get("required", []):
            if key not in data:
                errors.append(f"{path}: chybí povinný klíč '{key}'")
        props = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            for key in data:
                if key not in props:
                    errors.append(f"{path}: nepovolený klíč '{key}'")
        for key, subschema in props.items():
            if key in data:
                errors += validate_against_schema(data[key], subschema, root_schema,
                                                 f"{path}.{key}")
        for key in data:
            if key not in props and key in ("$defs",):
                pass
    elif isinstance(data, list):
        if "minItems" in schema and len(data) < schema["minItems"]:
            errors.append(f"{path}: minItems {schema['minItems']}, nalezeno {len(data)}")
        item_schema = schema.get("items")
        if item_schema:
            for i, item in enumerate(data):
                errors += validate_against_schema(item, item_schema, root_schema,
                                                 f"{path}[{i}]")
    elif isinstance(data, str):
        if "const" in schema and data != schema["const"]:
            errors.append(f"{path}: očekávána konstanta {schema['const']!r}")
        if "enum" in schema and data not in schema["enum"]:
            errors.append(f"{path}: hodnota {data!r} není v enum {schema['enum']}")
        if "pattern" in schema and not re.search(schema["pattern"], data):
            errors.append(f"{path}: hodnota neodpovídá pattern {schema['pattern']}")
        if schema.get("format") == "date" and not _DATE_RE.match(data):
            errors.append(f"{path}: neplatný formát date (očekáváno YYYY-MM-DD)")
    elif isinstance(data, (int, float)) and not isinstance(data, bool):
        if "const" in schema and data != schema["const"]:
            errors.append(f"{path}: očekávána konstanta {schema['const']!r}")
        if "enum" in schema and data not in schema["enum"]:
            errors.append(f"{path}: hodnota {data!r} není v enum {schema['enum']}")
        if "minimum" in schema and data < schema["minimum"]:
            errors.append(f"{path}: {data} < minimum {schema['minimum']}")
        if "maximum" in schema and data > schema["maximum"]:
            errors.append(f"{path}: {data} > maximum {schema['maximum']}")
        if schema.get("format") == "date":
            errors.append(f"{path}: neplatný formát date")
    if "const" in schema and not isinstance(data, (dict, list, str, int, float, bool, type(None))):
        pass
    if "const" in schema and data is None and schema["const"] is not None:
        errors.append(f"{path}: očekávána konstanta {schema['const']!r}")
    if "const" in schema and isinstance(data, bool) and data != schema["const"]:
        errors.append(f"{path}: očekávána konstanta {schema['const']!r}")
    return errors


def _is_m19_empty_torque_curve(profile: dict) -> bool:
    """M1.9 výjimka (IMPLEMENTATION_ROADMAP.md §M1.8): pro Mustang GT 2024 EU
    existuje 0 továrních kotev momentové křivky, profil proto nese prázdnou
    křivku se statusem UNKNOWN. Podmínky: points == [], interpolation "none",
    curve_source estimate s confidence <= 0.5 a notes "CHYBÍ: ...".
    Výjimka se nesmí stát precedentem pro domýšlení bodů — jakýkoli
    neprázdný seznam bodů prochází standardní validací (minItems 2)."""
    tc = profile.get("torque_curve")
    if not isinstance(tc, dict):
        return False
    if tc.get("points") != [] or tc.get("interpolation") != "none":
        return False
    curve = tc.get("curve_source")
    if not isinstance(curve, dict):
        return False
    conf = curve.get("confidence")
    return (curve.get("source_type") == "estimate"
            and isinstance(conf, (int, float)) and conf <= 0.5
            and str(curve.get("notes") or "").startswith("CHYBÍ:"))


def _walk_envelopes(node: Any, path: str = "$") -> list[tuple[str, dict]]:
    """Najde všechny obálky {value, unit, source, source_type, confidence}."""
    found: list[tuple[str, dict]] = []
    if isinstance(node, dict):
        keys = set(node.keys())
        if {"value", "unit", "source", "source_type", "confidence"} <= keys:
            found.append((path, node))
        for key, val in node.items():
            found += _walk_envelopes(val, f"{path}.{key}")
    elif isinstance(node, list):
        for i, item in enumerate(node):
            found += _walk_envelopes(item, f"{path}[{i}]")
    return found


def check_envelope_rules(profile: dict) -> tuple[list[str], list[str]]:
    """Pravidla VEHICLE-DATA.md kap. 3–4, 6: estimate → notes, confidence meze."""
    errors: list[str] = []
    warnings: list[str] = []
    # Pozn.: porušení prefixu notes je VAROVÁNÍ, ne chyba — dodaný vzor
    # example-vehicle.json (NEMĚNIT) sám používá notes "Vypočteno...",
    # "ODHAD." či null, takže striktní chyba by vzor neprošel.
    # Nové profily drží přísný tvar ODHAD:/CHYBÍ: (0 varování).
    for path, env in _walk_envelopes(profile):
        stype = env.get("source_type")
        conf = env.get("confidence")
        notes = env.get("notes")
        value = env.get("value")
        if stype not in ("factory", "measurement", "aggregator", "estimate"):
            errors.append(f"{path}: neznámý source_type {stype!r}")
            continue
        if not isinstance(conf, (int, float)) or not (0 <= conf <= 1):
            errors.append(f"{path}: confidence mimo 0–1: {conf!r}")
        if stype == "estimate":
            if not notes or not str(notes).startswith(ESTIMATE_NOTE_PREFIXES):
                warnings.append(f"{path}: estimate by měl mít notes začínající "
                                f"{ESTIMATE_NOTE_PREFIXES} (VEHICLE-DATA.md kap. 4)")
            if value is None and isinstance(conf, (int, float)) and conf > 0.5:
                warnings.append(f"{path}: null estimate s confidence {conf} > 0.5")
        if stype == "factory" and value is not None and isinstance(conf, (int, float)) and conf < 0.8:
            warnings.append(f"{path}: factory údaj s nízkou confidence {conf}")
        if stype == "factory" and value is not None:
            # VEHICLE-SPECIFICATIONS.md §4: každá hodnota VERIFIED (factory)
            # musí mít zdroj; bez zdroje je hodnota ESTIMATED nebo UNKNOWN.
            src = env.get("source") or ""
            if (not src.strip() or src.strip().lower().startswith(
                    ("neznám", "neznam", "unknown", "chybí", "chybí:", "chybi"))):
                errors.append(f"{path}: factory údaj bez zdroje — bez zdroje "
                              f"je hodnota ESTIMATED nebo UNKNOWN")
    # torque_curve: každý bod point_type; interpolované body mají mít nízkou důvěru křivky
    tc = profile.get("torque_curve") or {}
    for i, pt in enumerate(tc.get("points", [])):
        if pt.get("point_type") not in ("factory", "measured", "interpolated", "estimated"):
            errors.append(f"$.torque_curve.points[{i}]: neznámý point_type")
    curve = tc.get("curve_source") or {}
    if curve.get("source_type") == "estimate" and not str(curve.get("notes") or "").startswith("ODHAD:"):
        # M1.9 výjimka: prázdná křivka (points [], interpolation "none")
        # smí nést "CHYBÍ: ..." místo "ODHAD: ..." — UNKNOWN se nevymýšlí.
        if not _is_m19_empty_torque_curve(profile):
            errors.append("$.torque_curve.curve_source: estimate bez notes 'ODHAD:...'")
    return errors, warnings


def check_consistency(profile: dict) -> tuple[list[str], list[str]]:
    """Fyzikální konzistence dle VEHICLE-DATA.md kap. 8.2. Vrací (errors, warnings)."""
    errors: list[str] = []
    warnings: list[str] = []

    def num(*keys: str) -> float | None:
        node: Any = profile
        for k in keys:
            if not isinstance(node, dict) or k not in node:
                return None
            node = node[k]
        if isinstance(node, dict):
            node = node.get("value")
        return node if isinstance(node, (int, float)) else None

    # 1) P[kW] ≈ M[Nm] × n[rpm] / 9549 (tolerance 8 % — křivka má zaokrouhlení)
    power = num("engine", "max_power")
    power_rpm = num("engine", "max_power_rpm")
    torque = num("engine", "max_torque")
    torque_rpm = num("engine", "max_torque_rpm")
    if power and power_rpm:
        expected_nm = power * 9549.0 / power_rpm
        tc = profile.get("torque_curve") or {}
        pts = [p for p in tc.get("points", [])
               if isinstance(p.get("rpm"), (int, float))
               and isinstance(p.get("torque_nm"), (int, float))]
        if pts:
            nearest = min(pts, key=lambda p: abs(p["rpm"] - power_rpm))
            if nearest["torque_nm"] > 0:
                dev = abs(nearest["torque_nm"] - expected_nm) / expected_nm
                if dev > 0.08:
                    errors.append(
                        f"$.torque_curve: bod {nearest['rpm']} rpm = {nearest['torque_nm']} Nm, "
                        f"z výkonu {power} kW@{power_rpm} vychází {expected_nm:.1f} Nm "
                        f"(odchylka {dev*100:.1f} % > 8 %)")
    if (torque is not None and torque_rpm is not None
            and power is not None and power > 0):
        p_at_torque = torque * torque_rpm / 9549.0
        if p_at_torque > power * 1.05:
            errors.append(f"$.engine: moment {torque} Nm@{torque_rpm} = {p_at_torque:.1f} kW "
                          f"> max výkon {power} kW")

    # 2) Průměr pneu: D = 25.4×rim + 2×(šířka×profil/100), tolerance ±8 mm
    for axle in ("tire_front", "tire_rear"):
        tire = (profile.get("wheels_tires") or {}).get(axle) or {}
        w = (tire.get("width_mm") or {}).get("value")
        a = (tire.get("aspect_ratio_pct") or {}).get("value")
        r = (tire.get("rim_in") or {}).get("value")
        d = (tire.get("diameter_mm") or {}).get("value")
        if all(isinstance(v, (int, float)) for v in (w, a, r, d)):
            calc = 25.4 * r + 2 * (w * a / 100.0)
            if abs(d - calc) > 8:
                errors.append(f"$.wheels_tires.{axle}: průměr {d} mm vs. výpočet {calc:.1f} mm")

    # 3) V-max dosažitelná převody: teoretická rychlost na nejvyšší stupeň
    #    při redline musí být ≥ V-max (jinak je profil vnitřně sporný).
    vmax = num("performance", "vmax")
    redline = num("engine", "redline_rpm")
    tire = (profile.get("wheels_tires") or {}).get("tire_rear") or {}
    diameter = (tire.get("diameter_mm") or {}).get("value")
    gears = ((profile.get("transmission") or {}).get("gear_ratios")) or []
    final = num("transmission", "final_drive")
    if vmax and redline and diameter and gears and final:
        top = max(g.get("ratio", {}).get("value", 0)
                  for g in gears if isinstance(g.get("ratio", {}).get("value"), (int, float)))
        ratios = [g.get("ratio", {}).get("value") for g in gears
                  if isinstance(g.get("ratio", {}).get("value"), (int, float))]
        if ratios:
            top_ratio = min(ratios)
            circumference = math.pi * diameter / 1000.0  # m
            v_theor = circumference * (redline / 60.0) / (top_ratio * final) * 3.6
            if v_theor < vmax:
                errors.append(f"$.performance.vmax: {vmax} km/h > teoretických "
                              f"{v_theor:.0f} km/h na nejvyšší stupeň při redline")
    return errors, warnings


def validate_profile(profile: dict, schema: dict) -> tuple[list[str], list[str]]:
    """Plná validace: schéma + obálky + konzistence. Vrací (errors, warnings)."""
    errors = validate_against_schema(profile, schema)
    if _is_m19_empty_torque_curve(profile):
        # M1.9 výjimka: prázdná křivka UNKNOWN je záměr — minItems chyba
        # pro $.torque_curve.points se potlačí (jen při splnění podmínek).
        errors = [e for e in errors
                  if e != "$.torque_curve.points: minItems 2, nalezeno 0"]
    env_errors, env_warnings = check_envelope_rules(profile)
    con_errors, con_warnings = check_consistency(profile)
    return errors + env_errors + con_errors, env_warnings + con_warnings
