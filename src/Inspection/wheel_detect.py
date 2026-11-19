# wheel_detect.py — identifikace 4 kol A-Chassis (M2.2, kostra po spike M2.1).
#
# ROZHODOVACI PRAVIDLO (docs/IMPLEMENTATION_ROADMAP.md §M2, poradi zavazne):
#   kandidat je kolo, jen pokud SOUCASNE
#     (a) lezi v Model:Wheels,
#     (b) nese oznaceni FL/FR/RL/RR,
#     (c) ma tvar Ball.
#   Ball-tvar mimo Model:Wheels se kolem NIKDY nestane.
#   Pri poruseni libovolne podminky: kandidat -> UNKNOWN se zaznamem,
#   ktery bod selhal.
#
# BLOCKED (analyza se zastavi):
#   - chybejici Model:Wheels,
#   - pocet identifikovanych kol != 4 (vcetne duplicitniho oznaceni),
#   - jakekoli UNKNOWN u kola,
#   - nekonzistentni meritko z >=2 rozmeru (M2.9/M2.10 — kontrola mimo
#     tento modul; vysledek se pripojuje pres blocked_reasons).
#
# VSTUPY: synteticke fixture / pozdeji zaznamy z RBXM parseru (C05/C06).
#   Instance = dict{id, name, class_name, shape, parent_id}.
#   shape: "Ball" | jiny PartType retezec | None (nezname).
# VYSTUPY: structured dict, zadny odhad — pri nejasnosti UNKNOWN/BLOCKED.
# JEDNOTKY: bezrozmerne identifikatory, zadne fyzikalni jednotky.
# LIMITY: tento modul nemeri rozmery ani meritko, jen identitu kol.

"""Identifikace kol v Model:Wheels konjunkci (a)+(b)+(c); jinak UNKNOWN/BLOCKED."""

from __future__ import annotations

# Oznaceni korenoveho modelu kol (audit: 2:Model:Wheels -> FL/FR/RL/RR).
WHEELS_MODEL_NAME = "Wheels"
# Povolena oznaceni kol (audit: Drive tabulka ridi kola dle jmena).
WHEEL_DESIGNATIONS = ("FL", "FR", "RL", "RR")
# Ocekavany tvar dilu kola (audit §10: kola = koule, shape=Ball).
WHEEL_SHAPE = "Ball"

# Navrh tvaru inspection_report.json (M2 vystup). Jednotky: studs, pokud
# neni uvedeno jinak; kazda hodnota pozdeji ponese unit + zdroj.
INSPECTION_REPORT_SCHEMA = {
    "$schema": "inspection_report (navrh, M2 spike)",
    "type": "object",
    "required": ["vehicle_id", "rbxm_sha256", "status", "wheels",
                 "scale", "blocked_reasons"],
    "properties": {
        "vehicle_id": {"type": "string"},
        "rbxm_sha256": {"type": "string",
                        "description": "SHA-256 pracovni kopie pred/po (G-01)"},
        "status": {"enum": ["OK", "BLOCKED"]},
        "wheels": {
            "type": "object",
            "description": "FL/FR/RL/RR -> zaznam kola, nebo UNKNOWN",
            "patternProperties": {
                "^(FL|FR|RL|RR)$": {
                    "type": "object",
                    "required": ["status", "instance_id", "failed_checks"],
                    "properties": {
                        "status": {"enum": ["WHEEL", "UNKNOWN"]},
                        "instance_id": {"type": ["integer", "null"]},
                        "shape": {"type": ["string", "null"]},
                        "failed_checks": {"type": "array", "items": {
                            "enum": ["not_in_wheels", "bad_designation",
                                     "bad_shape", "duplicate_designation"]}},
                    },
                },
            },
        },
        "unidentified": {"type": "array",
                         "description": "UNKNOWN kandidati se zaznamem"},
        "scale": {
            "type": "object",
            "required": ["studs_per_meter", "unit", "status"],
            "properties": {
                "studs_per_meter": {"type": ["number", "null"]},
                "unit": {"type": "string", "const": "studs/m"},
                "status": {"enum": ["OK", "UNKNOWN", "BLOCKED"]},
            },
        },
        "blocked_reasons": {"type": "array", "items": {"type": "string"}},
    },
}


def _by_id(instances):
    """Index instanci dle id (duplicitni id = poskozeny vstup)."""
    index = {}
    for inst in instances:
        iid = inst.get("id")
        if iid in index:
            raise ValueError("duplicate instance id: %r" % (iid,))
        index[iid] = inst
    return index


def find_wheels_models(instances):
    """Vsechny instance tridy Model se jmenem Wheels."""
    return [i for i in instances
            if i.get("class_name") == "Model"
            and i.get("name") == WHEELS_MODEL_NAME]


def is_in_wheels(instance, wheels_id, index):
    """Ancestor-walk: lezi instance v podstrome Model:Wheels?"""
    seen = set()
    node = instance
    while node is not None:
        if node.get("id") in seen:
            return False  # cyklus v rodicich -> povazuj za mimo
        seen.add(node.get("id"))
        if node.get("id") == wheels_id:
            return True
        node = index.get(node.get("parent_id"))
    return False


def classify_candidate(instance, in_wheels):
    """Jedna kandidatni instance -> (status, failed_checks).

    Podminky (a)+(b)+(c) jako konjunkce; Ball mimo Wheels nikdy kolo.
    """
    failed = []
    if not in_wheels:
        failed.append("not_in_wheels")
    if instance.get("name") not in WHEEL_DESIGNATIONS:
        failed.append("bad_designation")
    if instance.get("shape") != WHEEL_SHAPE:
        failed.append("bad_shape")
    if failed:
        return "UNKNOWN", failed
    return "WHEEL", []


def detect_wheels(instances):
    """Identifikace kol ze seznamu instanci.

    Vraci dict: {wheels, unidentified, blocked, blocked_reasons, status}.
    Deterministicke: stejny vstup = stejny vystup.
    """
    index = _by_id(instances)
    result = {"wheels": {}, "unidentified": [],
              "blocked": False, "blocked_reasons": [], "status": "OK"}

    def block(reason):
        if reason not in result["blocked_reasons"]:
            result["blocked_reasons"].append(reason)
        result["blocked"] = True
        result["status"] = "BLOCKED"

    wheels_models = find_wheels_models(instances)
    if not wheels_models:
        block("missing Model:Wheels")
        return result
    if len(wheels_models) > 1:
        block("ambiguous Model:Wheels: found %d" % len(wheels_models))
        return result
    wheels_id = wheels_models[0].get("id")

    hits = {des: [] for des in WHEEL_DESIGNATIONS}
    for inst in instances:
        if inst.get("id") == wheels_id:
            continue
        if inst.get("class_name") != "Part":
            # Kandidatem je jen Part (tvar Ball maji jen Part dily;
            # Modely/Constrainty/Attachmenty uvnitr Wheels nejsou kola
            # ani UNKNOWN — jen by otravily vysledek).
            continue
        in_w = is_in_wheels(inst, wheels_id, index)
        status, failed = classify_candidate(inst, in_w)
        if status == "WHEEL":
            hits[inst.get("name")].append(inst)
        elif in_w:
            # UNKNOWN uvnitr Wheels se eviduje; Ball mimo Wheels je
            # ocekavana ne-kola (ochrana pred zamenou) -> bez zaznamu.
            result["unidentified"].append({
                "instance_id": inst.get("id"),
                "name": inst.get("name"),
                "shape": inst.get("shape"),
                "failed_checks": failed,
            })

    for des in WHEEL_DESIGNATIONS:
        if len(hits[des]) == 1:
            inst = hits[des][0]
            result["wheels"][des] = {
                "status": "WHEEL",
                "instance_id": inst.get("id"),
                "shape": inst.get("shape"),
                "failed_checks": [],
            }
        elif len(hits[des]) == 0:
            result["wheels"][des] = {
                "status": "UNKNOWN",
                "instance_id": None,
                "shape": None,
                "failed_checks": ["missing_wheel"],
            }
            block("wheel %s not identified (count != 4)" % des)
        else:
            result["wheels"][des] = {
                "status": "UNKNOWN",
                "instance_id": None,
                "shape": None,
                "failed_checks": ["duplicate_designation"],
            }
            block("duplicate designation %s: %d candidates"
                  % (des, len(hits[des])))

    if result["unidentified"]:
        block("UNKNOWN candidate(s) inside Model:Wheels: %d"
              % len(result["unidentified"]))
    n_wheels = sum(1 for w in result["wheels"].values()
                   if w["status"] == "WHEEL")
    if n_wheels != 4:
        block("identified wheels != 4 (got %d)" % n_wheels)
    return result


def is_blocked(detection_result):
    """True, pokud analyza nesmi pokracovat (BLOCKED podminky M2)."""
    return bool(detection_result.get("blocked"))
