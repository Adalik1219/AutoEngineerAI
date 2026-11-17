# AutoEngineerAI – Mapping Engine (Agent B)
#
# Vlastněné soubory: src/Chassis/mapping_engine.py, src/Chassis/mapping/**,
# docs/MAPPING.md. READ-ONLY mimo ně (zvlášť src/Optimizer/** – wiring dělá
# agent D). Pravidla: docs/AGENT-RULES.md. Česky; identifikátory anglicky;
# Python 3 stdlib; žádné git operace.
"""Mapování VehicleConfig → A-Chassis Tune klíče nad katalogem parameters.json.

Zmrazené API (neměnit):
    map_config(vehicle_config, catalog_path, adapter_id) -> dict
    build_search_space(catalog_path, backend_caps) -> list[str]

Katalogový záznam (19 polí, zdroj: zadání FÁZE 4.2, katalog Agenta A):
    id, tune_key, category, config_path, value, unit, value_type, min, max,
    default, function, physical_effect, used_in, depends_on, conflicts,
    change_method, source, confidence, verification_status.
Kategorie: MUTABLE_TUNE | SCRIPT_CONTROLLED | STRUCTURE_CONTROLLED |
    READ_ONLY | UNKNOWN.

Pravidla mapování (žádná tichá ignorace – každý vstupní list končí buď
v `tune_changes`, nebo v `rejected` s důvodem):
  - bez katalogového záznamu (neznámý `config_path`) → rejected;
  - kategorie jiná než MUTABLE_TUNE → rejected (read-only/script/unknown);
  - číselná hodnota mimo ověřený rozsah [min, max] → rejected;
  - nesplněná závislost `depends_on` → rejected;
  - konflikt `conflicts` s již aplikovaným parametrem → rejected
    (vítězí abecedně první config_path – deterministicky);
  - `verification_status` jiný než "verified" → varování, jinak se mapuje;
  - hodnota None (např. `geometry_overrides: null`) = není požadavek
    na změnu, přeskočí se bez záznamu (povinné schémaové null);
  - `engine.peak_power_kw` se NIKDY nerovná `engine.horsepower` bez
    definovaného převodu – bez katalogového záznamu je to prostě rejected.

`build_search_space` vrací seřazené Tune klíče, které splňují všech 5 filtrů:
ověřené (verification_status == "verified") + měnitelné
(MUTABLE_TUNE) + s rozsahem (číselné min < max) + se vztahem k měření
(neprázdné used_in) + podporované backendem (tune_key ∈ backend_caps).
"""

from __future__ import annotations

import json
import os
import sys
import tempfile

CATEGORIES = (
    "MUTABLE_TUNE",
    "SCRIPT_CONTROLLED",
    "STRUCTURE_CONTROLLED",
    "READ_ONLY",
    "UNKNOWN",
)

VERIFIED_STATUS = "PASS"  # sjednocení s katalogem Agenta A (loader.py: VERIFICATION = ("PASS", "PENDING"); PASS = ověřeno auditem/kódem [F]). "verified" = starší název ze zadání FÁZE 4.2, akceptován zpětně ve VERIFIED_STATUSES (selftest Agenta B).
VERIFIED_STATUSES = ("PASS", "verified")  # oba tvary = "ověřeno"; kanonický je PASS

__all__ = ["map_config", "build_search_space", "run_selftest"]


# --------------------------------------------------------------------------
# Katalog
# --------------------------------------------------------------------------

def _load_catalog(catalog_path: str) -> list[dict]:
    """Načte katalog; přijímá list i obálku {"parameters": [...]}."""
    with open(catalog_path, "r", encoding="utf-8") as fh:
        doc = json.load(fh)
    if isinstance(doc, dict) and isinstance(doc.get("parameters"), list):
        records = doc["parameters"]
    elif isinstance(doc, list):
        records = doc
    else:
        raise ValueError(
            "katalog %r: očekáván list záznamů nebo "
            "{'parameters': [...]}" % (catalog_path,)
        )
    if not all(isinstance(r, dict) for r in records):
        raise ValueError("katalog %r: každý záznam musí být objekt" % (catalog_path,))
    return records


def _norm_entry(raw: dict) -> dict:
    """Doplní chybějící volitelná pole katalogového záznamu výchozími hodnotami."""
    e = dict(raw)
    e.setdefault("tune_key", None)
    e.setdefault("category", "UNKNOWN")
    e.setdefault("config_path", None)
    e.setdefault("unit", "")
    e.setdefault("value_type", "number")
    e.setdefault("min", None)
    e.setdefault("max", None)
    e.setdefault("default", None)
    e.setdefault("function", "")
    e.setdefault("physical_effect", "")
    e.setdefault("used_in", [])
    e.setdefault("depends_on", [])
    e.setdefault("conflicts", [])
    e.setdefault("change_method", "")
    e.setdefault("source", "")
    e.setdefault("confidence", 0.0)
    e.setdefault("verification_status", "unverified")
    if e["category"] not in CATEGORIES:
        e["category"] = "UNKNOWN"
    for key in ("depends_on", "conflicts", "used_in"):
        if e[key] is None:
            e[key] = []
    return e


def _resolve_entry(entries: list[dict], token: str) -> dict | None:
    """Najde záznam podle id, tune_key nebo config_path."""
    for e in entries:
        if token in (e.get("id"), e.get("tune_key"), e.get("config_path")):
            return e
    return None


def _adapter_warning(adapter_id: str) -> str | None:
    """Ověří adapter_id proti registru (best-effort; registr je READ-ONLY)."""
    try:
        from src.Chassis.registry import is_ready, list_adapters
    except ImportError:
        # Přímé spuštění jako skript: repo root na sys.path (soubor leží
        # v src/Chassis, tj. 3× dirname z cesty k souboru).
        root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if root not in sys.path:
            sys.path.insert(0, root)
        try:
            from src.Chassis.registry import is_ready, list_adapters  # noqa: E402
        except Exception as exc:
            return "registr adaptérů nedostupný (%s); adapter_id %r neověřen" % (
                exc, adapter_id)
    try:
        known = {a["id"]: a.get("status") for a in list_adapters()}
    except Exception as exc:
        return "registr adaptérů nečitelný (%s); adapter_id %r neověřen" % (
            exc, adapter_id)
    if adapter_id not in known:
        return ("neznámý adaptér %r (známé: %s); mapováno dle katalogu, "
                "bez záruky platnosti pro tento adaptér"
                % (adapter_id, sorted(known)))
    if not is_ready(adapter_id):
        return ("adaptér %r je rezervován, ale neimplementován; mapování dle "
                "katalogu, aplikaci musí potvrdit implementace adaptéru"
                % (adapter_id,))
    return None


# --------------------------------------------------------------------------
# Pomocné funkce
# --------------------------------------------------------------------------

def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _flatten(params: dict, prefix: str = "") -> list[tuple[str, object]]:
    """Zploští vnořený dict parameters na [(tečková cesta, list)] seřazeně."""
    out: list[tuple[str, object]] = []
    for key in sorted(params):
        path = "%s.%s" % (prefix, key) if prefix else str(key)
        value = params[key]
        if isinstance(value, dict):
            out.extend(_flatten(value, path))
        else:
            out.append((path, value))
    return out


def _check_depends(dep: object, requested: dict, entries: list[dict]) -> str | None:
    """Vrátí None = splněno, jinak popis nesplněné podmínky (strukturovaně)."""
    if isinstance(dep, str):
        target = _resolve_entry(entries, dep)
        if target is None:
            return "závislost %r nemá katalogový záznam" % (dep,)
        if target.get("category") != "MUTABLE_TUNE":
            return ("závislost %r není měnitelná (kategorie %s)"
                    % (dep, target.get("category")))
        return None
    if isinstance(dep, dict):
        param = dep.get("param")
        if not param:
            return "závislost bez 'param': %r" % (dep,)
        target = _resolve_entry(entries, param)
        if target is None:
            return "závislost %r nemá katalogový záznam" % (param,)
        if param in requested:
            actual = requested[param]
        else:
            actual = target.get("default")
        if actual is None:
            return "závislost %r: bez hodnoty (ani požadavek, ani default)" % (param,)
        for bound in ("min", "max"):
            if bound in dep and dep[bound] is not None and _is_number(actual):
                if bound == "min" and actual < dep[bound]:
                    return ("závislost %r: hodnota %s < požadované minimum %s (%s)"
                            % (param, actual, dep[bound], dep.get("reason", "")))
                if bound == "max" and actual > dep[bound]:
                    return ("závislost %r: hodnota %s > požadované maximum %s (%s)"
                            % (param, actual, dep[bound], dep.get("reason", "")))
        if "equals" in dep and dep["equals"] is not None and actual != dep["equals"]:
            return ("závislost %r: hodnota %s != požadováno %s (%s)"
                    % (param, actual, dep["equals"], dep.get("reason", "")))
        return None
    return "nepodporovaný tvar závislosti: %r" % (dep,)


# --------------------------------------------------------------------------
# Zmrazené API
# --------------------------------------------------------------------------

def map_config(vehicle_config: dict, catalog_path: str, adapter_id: str) -> dict:
    """Namapuje VehicleConfig na Tune změny dle katalogu.

    Vrací {"tune_changes": [{tune_key, value, unit, reason}],
            "rejected": [{param, reason}], "warnings": [str]}.
    """
    warnings: list[str] = []
    tune_changes: list[dict] = []
    rejected: list[dict] = []

    note = _adapter_warning(adapter_id)
    if note:
        warnings.append(note)

    entries = [_norm_entry(r) for r in _load_catalog(catalog_path)]
    by_path = {e["config_path"]: e for e in entries if e.get("config_path")}

    params = vehicle_config.get("parameters") if isinstance(vehicle_config, dict) else None
    if not isinstance(params, dict):
        warnings.append(
            "vehicle_config nemá dict 'parameters' – nic k mapování")
        return {"tune_changes": tune_changes, "rejected": rejected,
                "warnings": warnings}

    requested = {p: v for p, v in _flatten(params) if v is not None}
    if len(requested) < len(_flatten(params)):
        pass  # None = není požadavek (např. geometry_overrides: null)
    if not requested:
        warnings.append("žádné mapovatelné listy v 'parameters' – nic neaplikováno")
        return {"tune_changes": tune_changes, "rejected": rejected,
                "warnings": warnings}

    applied_paths: set[str] = set()
    for path in sorted(requested):
        value = requested[path]
        entry = by_path.get(path)
        if entry is None:
            rejected.append({
                "param": path,
                "reason": ("neznámý parametr: katalog neobsahuje záznam "
                           "s config_path %r – bez záznamu se nemapuje "
                           "(nikdy se nevymýšlí)" % (path,)),
            })
            continue
        cat = entry.get("category")
        if cat != "MUTABLE_TUNE":
            rejected.append({
                "param": path,
                "reason": ("kategorie %s: %s -> %s se nemapuje "
                           "(change_method=%s; zdroj=%s)" % (
                               cat, path, entry.get("tune_key"),
                               entry.get("change_method") or "–",
                               entry.get("source") or "–")),
            })
            continue
        if _is_number(value) and _is_number(entry.get("min")) \
                and _is_number(entry.get("max")):
            if not (entry["min"] <= value <= entry["max"]):
                rejected.append({
                    "param": path,
                    "reason": ("hodnota %s mimo ověřený rozsah [%s, %s] – "
                               "odmítnuto, nezapisuji" % (
                                   value, entry["min"], entry["max"])),
                })
                continue
        dep_problem = None
        for dep in entry.get("depends_on") or []:
            problem = _check_depends(dep, requested, entries)
            if problem is not None:
                dep_problem = problem
                break
        if dep_problem is not None:
            rejected.append({
                "param": path,
                "reason": "nesplněná závislost: %s" % dep_problem,
            })
            continue
        clash = None
        for token in entry.get("conflicts") or []:
            target = _resolve_entry(entries, token) if isinstance(token, str) else None
            other = target.get("config_path") if target else token
            if other in applied_paths:
                clash = other
                break
        if clash is not None:
            rejected.append({
                "param": path,
                "reason": ("konflikt s %r: současná změna obou je "
                           "nejednoznačná – vítězí abecedně první (%s)"
                           % (clash, clash)),
            })
            continue
        if entry.get("verification_status") not in VERIFIED_STATUSES:
            warnings.append(
                "parametr %r mapován s výhradou (verification_status=%r, "
                "zdroj=%s)" % (path, entry.get("verification_status"),
                               entry.get("source") or "–"))
        tune_key = entry.get("tune_key")
        function = entry.get("function") or "mapování dle katalogu"
        source = entry.get("source") or "–"
        tune_changes.append({
            "tune_key": tune_key,
            "value": value,
            "unit": entry.get("unit", ""),
            "reason": "%s -> %s: %s [%s]" % (path, tune_key, function, source),
        })
        applied_paths.add(path)

    return {"tune_changes": tune_changes, "rejected": rejected,
            "warnings": warnings}


def build_search_space(catalog_path: str, backend_caps: list[str]) -> list[str]:
    """Vrátí seřazené Tune klíče pro optimalizaci (5 filtrů, viz modulový docstring)."""
    if not isinstance(backend_caps, list):
        raise TypeError("backend_caps musí být list[str], mám %r"
                        % type(backend_caps).__name__)
    caps = set(backend_caps)
    space: list[str] = []
    for raw in _load_catalog(catalog_path):
        e = _norm_entry(raw)
        if e.get("category") != "MUTABLE_TUNE":
            continue
        if e.get("verification_status") not in VERIFIED_STATUSES:
            continue
        if not (isinstance(e.get("tune_key"), str) and e["tune_key"]):
            continue
        if not (_is_number(e.get("min")) and _is_number(e.get("max"))
                and e["min"] < e["max"]):
            continue
        if not (isinstance(e.get("used_in"), list) and e["used_in"]):
            continue
        if e["tune_key"] not in caps:
            continue
        space.append(e["tune_key"])
    return sorted(space)


# --------------------------------------------------------------------------
# Selftest (akceptace Agenta B)
# --------------------------------------------------------------------------

def _sample_catalog() -> list[dict]:
    """Ukázkový katalog ve formátu parameters.json (Agent A ještě nedodal)."""
    def rec(rid, tune_key, category, config_path, value, unit, vtype,
            vmin, vmax, default, function, effect, used_in, depends,
            conflicts, method, source, conf, status):
        return {
            "id": rid, "tune_key": tune_key, "category": category,
            "config_path": config_path, "value": value, "unit": unit,
            "value_type": vtype, "min": vmin, "max": vmax, "default": default,
            "function": function, "physical_effect": effect,
            "used_in": used_in, "depends_on": depends, "conflicts": conflicts,
            "change_method": method, "source": source, "confidence": conf,
            "verification_status": status,
        }

    return [
        rec("engine.horsepower", "Horsepower", "MUTABLE_TUNE",
            "engine.horsepower", 200, "hp", "number", 50, 1000, 200,
            "škálování výkonové křivky motoru",
            "vyšší maximální výkon → vyšší V-max a rychlejší akcelerace",
            ["straight_accel"], [], [], "tune", "A-CHASSIS-AUDIT.md §5",
            1.0, "verified"),
        rec("transmission.final_drive", "FinalDrive", "MUTABLE_TUNE",
            "transmission.final_drive", 3.545, "-", "number", 2.5, 4.2, 3.545,
            "stálý převod",
            "nižší hodnota → vyšší V-max, horší akcelerace",
            ["straight_accel"], [], ["transmission.final_drive_mult"],
            "tune", "A-CHASSIS-AUDIT.md §6", 1.0, "verified"),
        rec("transmission.final_drive_mult", "FDMult", "MUTABLE_TUNE",
            "transmission.final_drive_mult", 1.1, "-", "number", 0.5, 2.0, 1.1,
            "multiplikativní škálování stálého převodu",
            "FDMult != 1 rozhodí Gauges max-rychlosti (jen vizuálně)",
            ["straight_accel"], [], ["transmission.final_drive"],
            "tune", "A-CHASSIS-AUDIT.md §6", 1.0, "verified"),
        rec("brakes.bias_front", "Bias", "MUTABLE_TUNE",
            "brakes.bias_front", 0.6, "0-1", "number", 0, 1, 0.6,
            "rozložení brzdné síly předek/zadek",
            "vyšší bias → stabilnější brzdy, delší dráha; extrémy rizikové",
            ["straight_brake_100_0"], [], [], "tune",
            "A-CHASSIS-AUDIT.md §12", 1.0, "verified"),
        rec("engine.turbo.count", "Turbochargers", "MUTABLE_TUNE",
            "engine.turbo.count", 2, "ks", "number", 0, 4, 2,
            "počet turbodmychadel",
            "více stupňů → vyšší plnicí tlak ve vysokých otáčkách",
            ["straight_accel"], [], [], "tune", "A-CHASSIS-AUDIT.md §5",
            1.0, "verified"),
        rec("engine.turbo.boost", "T_Boost", "MUTABLE_TUNE",
            "engine.turbo.boost", 7, "-", "number", 0, 20, 7,
            "plnicí tlak turba",
            "vyšší boost → vyšší moment ve středních/vysokých otáčkách",
            ["straight_accel"],
            [{"param": "engine.turbo.count", "min": 1,
              "reason": "plnicí tlak bez turbodmychadla nemá účinek"}],
            [], "tune", "A-CHASSIS-AUDIT.md §5", 1.0, "verified"),
        rec("aero.drag", None, "SCRIPT_CONTROLLED",
            "aero.drag_coeff", 0.34, "-", "number", 0, 1.0, 0.34,
            "součinitel odporu vzduchu",
            "vyšší odpor → nižší V-max (v kitu se navíc neaplikuje, chyba kódu)",
            ["straight_accel"], [], [], "script",
            "A-CHASSIS-AUDIT.md §13", 1.0, "verified"),
        rec("engine.compression_ratio", "CompressionRatio", "UNKNOWN",
            "engine.compression_ratio", None, "-", "number",
            None, None, None,
            "kompresní poměr (vstup vzorce turba)",
            "vyšší poměr → vyšší příspěvek turba k výkonu",
            [], [], [], "unknown", "A-CHASSIS-AUDIT.md §5",
            0.0, "unverified"),
        rec("suspension.stiffness", "Stiffness", "MUTABLE_TUNE",
            "suspension.spring_f_Npm", 20000, "N/m", "number",
            None, None, 20000,
            "tuhost pružin podvozku",
            "měkčí → dosedání; tvrdší → ztráta kontaktu na nerovnosti",
            ["bump_section"], [], [], "tune", "A-CHASSIS-AUDIT.md §8",
            0.6, "verified"),
    ]


def _cfg(parameters: dict) -> dict:
    return {
        "schema_version": "1.0.0",
        "config_id": "cfg_selftest_b",
        "parent_config_id": None,
        "vehicle_profile_id": "vp_selftest_b",
        "chassis_adapter": "achassis-v1",
        "parameters": parameters,
        "rationale": "selftest mapping_engine",
    }


def run_selftest() -> dict:
    """Akceptační selftest: mapování 3 vlastností vč. motoru + 4 druhy
    odmítnutí + prostor jen z MUTABLE_TUNE s rozsahem. Deterministický."""
    tmpdir = tempfile.mkdtemp(prefix="mapping_selftest_")
    catalog_path = os.path.join(tmpdir, "parameters.json")
    with open(catalog_path, "w", encoding="utf-8") as fh:
        json.dump(_sample_catalog(), fh, ensure_ascii=False, indent=2)

    # (A) Mapování 3 vlastností včetně motoru.
    r3 = map_config(_cfg({"engine": {"horsepower": 210},
                          "transmission": {"final_drive": 3.2},
                          "brakes": {"bias_front": 0.62}}),
                    catalog_path, "achassis-v1")
    assert len(r3["tune_changes"]) == 3, r3
    assert {c["tune_key"] for c in r3["tune_changes"]} == {
        "Horsepower", "FinalDrive", "Bias"}, r3
    assert r3["rejected"] == [], r3
    hp = next(c for c in r3["tune_changes"] if c["tune_key"] == "Horsepower")
    assert hp["value"] == 210 and hp["unit"] == "hp" and hp["reason"], r3

    # (B) Odmítnutí: neznámý parametr.
    r_unk = map_config(_cfg({"engine": {"warp_drive": 5}}),
                       catalog_path, "achassis-v1")
    assert r_unk["tune_changes"] == [] and len(r_unk["rejected"]) == 1, r_unk
    assert r_unk["rejected"][0]["param"] == "engine.warp_drive", r_unk

    # (C) Odmítnutí: read-only (script-controlled).
    r_ro = map_config(_cfg({"aero": {"drag_coeff": 0.5}}),
                      catalog_path, "achassis-v1")
    assert r_ro["tune_changes"] == [] and len(r_ro["rejected"]) == 1, r_ro
    assert "SCRIPT_CONTROLLED" in r_ro["rejected"][0]["reason"], r_ro

    # (D) Odmítnutí: mimo rozsah.
    r_range = map_config(_cfg({"engine": {"horsepower": 5000}}),
                         catalog_path, "achassis-v1")
    assert r_range["tune_changes"] == [] and len(r_range["rejected"]) == 1, r_range
    assert "rozsah" in r_range["rejected"][0]["reason"], r_range

    # (E) Odmítnutí: konflikt (vítězí abecedně první).
    r_conf = map_config(_cfg({"transmission": {"final_drive": 3.2,
                                               "final_drive_mult": 1.5}}),
                        catalog_path, "achassis-v1")
    assert len(r_conf["tune_changes"]) == 1, r_conf
    assert r_conf["tune_changes"][0]["tune_key"] == "FinalDrive", r_conf
    assert len(r_conf["rejected"]) == 1, r_conf
    assert "konflikt" in r_conf["rejected"][0]["reason"], r_conf

    # (F) Závislost: boost bez turba odmítnut, s turbem aplikován.
    r_dep = map_config(_cfg({"engine": {"turbo": {"count": 0, "boost": 10}}}),
                       catalog_path, "achassis-v1")
    keys_dep = {c["tune_key"] for c in r_dep["tune_changes"]}
    assert keys_dep == {"Turbochargers"}, r_dep
    assert any(d["param"] == "engine.turbo.boost" for d in r_dep["rejected"]), r_dep
    r_dep_ok = map_config(_cfg({"engine": {"turbo": {"count": 2, "boost": 10}}}),
                          catalog_path, "achassis-v1")
    assert {c["tune_key"] for c in r_dep_ok["tune_changes"]} == {
        "Turbochargers", "T_Boost"}, r_dep_ok

    # (G) peak_power_kw ≠ horsepower: bez převodu se nemapuje, odmítne se.
    r_kw = map_config(_cfg({"engine": {"peak_power_kw": 135.0}}),
                      catalog_path, "achassis-v1")
    assert r_kw["tune_changes"] == [] and len(r_kw["rejected"]) == 1, r_kw

    # (H) Prostor: jen MUTABLE_TUNE + verified + rozsah + used_in + backend.
    full_caps = ["Horsepower", "FinalDrive", "FDMult", "Bias", "T_Boost",
                 "Turbochargers", "Stiffness"]
    space = build_search_space(catalog_path, full_caps)
    assert space == ["Bias", "FDMult", "FinalDrive", "Horsepower",
                     "T_Boost", "Turbochargers"], space
    assert "Stiffness" not in space  # MUTABLE_TUNE, ale bez rozsahu

    # (I) Filtr backendu.
    assert build_search_space(catalog_path, ["Horsepower"]) == ["Horsepower"]
    assert build_search_space(catalog_path, []) == []

    # (J) Determinismus.
    again = map_config(_cfg({"engine": {"horsepower": 210},
                             "transmission": {"final_drive": 3.2},
                             "brakes": {"bias_front": 0.62}}),
                       catalog_path, "achassis-v1")
    assert json.dumps(again, sort_keys=True) == json.dumps(r3, sort_keys=True)
    assert build_search_space(catalog_path, full_caps) == space

    return {
        "selftest": "OK",
        "catalog_records": len(_sample_catalog()),
        "map_3_props": r3,
        "reject_unknown": r_unk,
        "reject_readonly": r_ro,
        "reject_out_of_range": r_range,
        "reject_conflict": r_conf,
        "depends_rejected": r_dep,
        "depends_applied": r_dep_ok,
        "reject_kw_not_hp": r_kw,
        "search_space": space,
    }


if __name__ == "__main__":
    result = run_selftest()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("SELFTEST OK")
