"""Parametricky prostor optimalizace (ARCHITECTURE §5.2, TESTING-OPTIMIZATION §5.1).

search_space(config, plan) -> explicitni rozsahy parametru.
Meze jsou tvrde (bezpecnostni filtr kandidaty mimo meze zamita bez testu).
Dynamika FÁZE 4 (Agent D): prostor se odviji od katalogu pres
build_search_space (jen overene MUTABLE_TUNE s rozsahem a vztahem
k mereni) protnuteho s backend_caps Simu; engine.peak_torque_nm nema
Tune protejsek (MAPPING.md §6, polozka 1), a proto v prostoru neni.
Pouze stdlib.
"""

import os as _os
import sys as _sys

try:
    from src.Chassis.mapping_engine import build_search_space
except ImportError:  # prime spousteni jako skript: koren projektu na sys.path
    _ROOT_FALLBACK = _os.path.dirname(
        _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
    if _ROOT_FALLBACK not in _sys.path:
        _sys.path.insert(0, _ROOT_FALLBACK)
    from src.Chassis.mapping_engine import build_search_space

# Koren projektu (= adresar nad src/) a vychozi cesta ke katalogu Agenta A.
_PROJECT_ROOT = _os.path.dirname(
    _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
CATALOG_PATH = _os.path.join(_PROJECT_ROOT, "src", "Chassis", "catalog",
                             "parameters.json")

# Kanonicky zdroj backend_caps: Sim backend (vyhodnocovaci vetev).
# Mnozina config_path, ktere Sim skutecne cte pri behu:
#  - fallback_sim._params: engine.peak_torque_nm, engine.peak_power_kw,
#    transmission.gears/final_drive/shift_rpm/shift_time_s,
#    tires.grip_long, brakes.bias_front;
#  - src/Sim/vehicle.py (externi Sim): navic engine.idle_rpm/redline_rpm,
#    transmission.efficiency/drive, brakes.torque_Nm,
#    tires.grip_lat/mu_road (krok, brzdy, pneumatiky).
# backend_caps = tune_key tech katalogovych zaznamu, jejichz config_path
# je v teto mnozine (podpora backendu; overenost resi build_search_space).
SIM_SUPPORTED_CONFIG_PATHS = frozenset({
    "engine.peak_torque_nm", "engine.peak_power_kw",
    "engine.idle_rpm", "engine.redline_rpm", "engine.shift_rpm",
    "transmission.gears", "transmission.final_drive",
    "transmission.efficiency", "transmission.drive",
    "transmission.shift_time_s",
    "tires.grip_long", "tires.grip_lat", "tires.mu_road",
    "brakes.bias_front", "brakes.torque_Nm",
})


def backend_caps(catalog_path=None):
    """Tune klice podporovane Sim backendem (kanonicky zdroj pro build_search_space).

    Odvozeni: config_path podpora Simu (SIM_SUPPORTED_CONFIG_PATHS)
    -> tune_key mnozina pres katalog. Bez ohledu na verification_status
    (tu filtruje build_search_space); jen MUTABLE_TUNE se svym tune_key.
    """
    import json
    path = catalog_path or CATALOG_PATH
    with open(path, "r", encoding="utf-8") as fh:
        doc = json.load(fh)
    records = (doc.get("parameters") if isinstance(doc, dict) else doc) or []
    caps = set()
    for raw in records:
        if not isinstance(raw, dict):
            continue
        if raw.get("config_path") in SIM_SUPPORTED_CONFIG_PATHS \
                and raw.get("category") == "MUTABLE_TUNE" \
                and isinstance(raw.get("tune_key"), str) and raw["tune_key"]:
            caps.add(raw["tune_key"])
    return sorted(caps)


def _dynamic_specs(catalog_path=None):
    """{config_path: {min, max, step, unit, label}} z katalogu.

    Prostor = build_search_space(katalog, backend_caps()) prevedeny
    tune_key -> config_path. Meze min/max vzdy z katalogu (overeny zdroj);
    krok/jednotka/popisek z PARAM_DEFS, je-li knob Optimizeru znam
    (safety_filter/_round_value/_diff_params v optimizer.py nad
    PARAM_DEFS pracuji). Knoby mimo PARAM_DEFS se zatim neladi
    (wiring F4.3), do prostoru nevstupuji.
    """
    import json
    path = catalog_path or CATALOG_PATH
    tune_keys = build_search_space(path, backend_caps(path))
    with open(path, "r", encoding="utf-8") as fh:
        doc = json.load(fh)
    records = (doc.get("parameters") if isinstance(doc, dict) else doc) or []
    by_tune = {r["tune_key"]: r for r in records
               if isinstance(r, dict) and r.get("tune_key")}
    specs = {}
    for key in tune_keys:
        rec = by_tune.get(key)
        if not rec or not rec.get("config_path"):
            continue
        name = rec["config_path"]
        if name not in PARAM_DEFS:
            continue  # wiring F4.3: Optimizer novy knob zatim neumi
        known = PARAM_DEFS[name]
        specs[name] = {
            "min": rec["min"], "max": rec["max"],
            "step": known["step"], "unit": known["unit"],
            "label": known.get("label", name),
        }
    return specs

# Tvrde meze + diskretizacni krok. Kalibrace SIM (Agent G, vlna 1):
# final_drive [2.5, 4.2] pokrýva tovarni 2.866 i degradovane okraje;
# nad ~4.0 si model vynuti 4. rychlostni stupen do 100 km/h a vazi V-max
# prevodem (interierove optimum), pod ~2.6 chyba sila na kolech.
# engine.peak_torque_nm zde NENI (zamerne): nema Tune protejsek
# (MAPPING.md §6, polozka 1) ani katalogovy zaznam, dynamicky prostor
# pres build_search_space ho proto nikdy nevydá; mrtva statika by jen
# matla safety_filter/_round_value/_diff_params.
PARAM_DEFS = {
    "transmission.final_drive": {
        "min": 2.5, "max": 4.2, "step": 0.15, "unit": "-",
        "label": "staly prevod",
    },
    "brakes.bias_front": {
        "min": 0.55, "max": 0.70, "step": 0.01, "unit": "-",
        "label": "brzdny bias na predni napravu",
    },
}

# Poradi sond (koordinatni sestup). final_drive prvni: primarni paka
# pro selftest se zhorsenym stalym prevodem. engine.peak_torque_nm
# zamerne chybi (nema Tune protejsek, viz PARAM_DEFS vyse).
CORE_ORDER = [
    "transmission.final_drive",
    "brakes.bias_front",
]


def get_param(config, name):
    """Hodnota teckovane cesty v config['parameters'] (napr. 'transmission.final_drive')."""
    node = config["parameters"]
    for part in name.split("."):
        if not isinstance(node, dict) or part not in node:
            raise KeyError("parametr %r v konfiguraci chybi" % name)
        node = node[part]
    return node


def set_param(config, name, value):
    """Nastavi teckvanou cestu v config['parameters'] (in-place, volat na kopii)."""
    parts = name.split(".")
    node = config["parameters"]
    for part in parts[:-1]:
        if not isinstance(node.get(part), dict):
            raise KeyError("cesta %r v konfiguraci chybi" % name)
        node = node[part]
    node[parts[-1]] = value


def _plan_priority(plan):
    """Poradi parametru podle plan.priorities, pokud odkazuji na zname parametry."""
    if not isinstance(plan, dict):
        return []
    prios = plan.get("priorities") or []
    area_to_param = {
        "transmission": "transmission.final_drive",
        "powertrain": "transmission.final_drive",
        "brakes": "brakes.bias_front",
        "braking": "brakes.bias_front",
    }
    ordered = []
    for area in prios:
        param = area_to_param.get(str(area).lower())
        if param and param not in ordered:
            ordered.append(param)
    return ordered


def search_space(config, plan=None):
    """Vrati list explicitnich rozsahu: [{name, min, max, step, unit, current}].

    Prostor je dynamicky: _dynamic_specs() z katalogu pres build_search_space
    (overene MUTABLE_TUNE s rozsahem + podpora Sim backendu). `plan`
    (ChangePlan) muze urcit poradi priorit; kroky planu mimo tento prostor
    se ignoruji (optimizer na ne nesaha). engine.peak_torque_nm v prostoru
    neni (nema Tune protejsek, MAPPING.md §6 polozka 1).
    """
    specs = _dynamic_specs()
    ordered = [n for n in _plan_priority(plan) if n in specs]
    for name in sorted(specs):
        if name not in ordered:
            ordered.append(name)
    space = []
    for name in ordered:
        spec = specs[name]
        try:
            current = get_param(config, name)
        except KeyError:
            current = None
        space.append({
            "name": name,
            "min": spec["min"],
            "max": spec["max"],
            "step": spec["step"],
            "unit": spec["unit"],
            "current": current,
        })
    return space
