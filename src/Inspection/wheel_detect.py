# wheel_detect.py — identifikace 4 kol A-Chassis (M2.2, kostra po spike M2.1).
#
# ROZHODOVACI PRAVIDLO (docs/IMPLEMENTATION_ROADMAP.md §M2, poradi zavazne):
#   kandidat je kolo, jen pokud SOUCASNE
#     (a) lezi v Model:Wheels,
#     (b) nese oznaceni FL/FR/RL/RR,
#     (c) ma tvar Ball.
#   Ball-tvar mimo Model:Wheels se kolem NIKDY nestane.
#   4-tier klasifikace (classify_candidate):
#     VALID_WHEEL = (a)+(b)+(c); KNOWN_NON_WHEEL = Part ve Wheels
#       se jmenem z CHASSIS_PART_ALLOWLIST (legitimni podvozek:
#       NEBLOKUJE, zustava evidovan); UNKNOWN_CANDIDATE = nezname
#       ve Wheels -> BLOCKED; INVALID_WHEEL = narokuje oznaceni kola,
#       ale porusuje (a)/(c) -> BLOCKED (uvnitr Wheels).
#
# BLOCKED (analyza se zastavi):
#   - chybejici Model:Wheels,
#   - pocet identifikovanych kol != 4 (vcetne duplicitniho oznaceni),
#   - jakykoli UNKNOWN_CANDIDATE / INVALID_WHEEL uvnitr Wheels,
#   - poskozena parent hierarchie: cyklus (duvod parent_cycle) nebo
#     odkaz na neexistujici parent ID — takovou hierarchii nelze
#     klasifikovat jako validni, vysledek je vzdy BLOCKED,
#   - nekonzistentni meritko z >=2 rozmeru (M2.9/M2.10 — kontrola mimo
#     tento modul; vysledek se pripojuje pres blocked_reasons).
#
# VSTUPY: synteticke fixture / pozdeji zaznamy z RBXM parseru (C05/C06).
#   Instance = dict{id, name, class_name, shape, parent_id}.
#   shape: "Ball" | jiny PartType retezec | None (nezname).
# VYSTUPY: structured dict, zadny odhad — pri nejasnosti UNKNOWN/BLOCKED.
# JEDNOTKY: bezrozmerne identifikatory, zadne fyzikalni jednotky.
# LIMITY: tento modul nemeri rozmery ani meritko, jen identitu kol.

"""Identifikace kol v Model:Wheels konjunkci (a)+(b)+(c); 4-tier VALID_WHEEL / KNOWN_NON_WHEEL / UNKNOWN_CANDIDATE / INVALID_WHEEL, jinak BLOCKED."""

from __future__ import annotations

import math

# Oznaceni korenoveho modelu kol (audit: 2:Model:Wheels -> FL/FR/RL/RR).
WHEELS_MODEL_NAME = "Wheels"
# Povolena oznaceni kol (audit: Drive tabulka ridi kola dle jmena).
WHEEL_DESIGNATIONS = ("FL", "FR", "RL", "RR")
# Ocekavany tvar dilu kola (audit §10: kola = koule, shape=Ball).
WHEEL_SHAPE = "Ball"

# Model-specificky allowlist: 11 nazvu dilu podvozku, kazdy 4x
# (FL/FR/RL/RR instance) = 44 Partu uvnitr Model:Wheels.
# Overeno na realne kopii chasis-work-copy.rbxm
# (sha256 dc8747e0...fefdf, read-only, pred/po shodne):
#   SpringBottom/CLower/CUpper/SpringTop/LowerArmB/LowerArmF/Hub/
#   LowerArm/UpperArmF/UpperArmB/UpperArm x 4, vse Part/Block.
# Plati JEN uvnitr Model:Wheels (kontext modelu je soucasti pravidla);
# stejny nazev mimo Wheels neni KNOWN_NON_WHEEL.
CHASSIS_PART_ALLOWLIST = frozenset({
    "SpringBottom", "CLower", "CUpper", "SpringTop",
    "LowerArmB", "LowerArmF", "Hub", "LowerArm",
    "UpperArmF", "UpperArmB", "UpperArm",
})

# 4-tier klasifikace kandidata (vraci classify_candidate):
#   VALID_WHEEL      — (a)+(b)+(c) splneno; jediny stav, ktery je kolem.
#   KNOWN_NON_WHEEL — Part uvnitr Wheels se jmenem z allowlistu;
#                     legitimni podvozek, NEBLOKUJE, zustava evidovan
#                     v result["known_non_wheels"].
#   UNKNOWN_CANDIDATE — uvnitr Wheels, neni kolo ani allowlist -> BLOCKED.
#   INVALID_WHEEL    — kandidat si narokuje oznaceni kola (FL/FR/RL/RR),
#                     ale porusuje (a) nebo (c) -> BLOCKED.
# INVALID_WHEEL mimo Wheels se ignoruje (ochrana pred zamenou, viz
# test_ball_outside_wheels_never_wheel); blokuje jen uvnitr Wheels.

# Skutecny souradnicovy ramec podvozku (empiricky, Studio ground-truth
# reports/STUDIO_GROUND_TRUTH.md §3 + parser na pracovni kopii
# chasis-work-copy.rbxm, sha256 dc8747e0...fefdf):
#   FL=(-45.1878, 23.6221, -203.2503), FR=(-51.1785, 23.6221, -203.2503),
#   RL=(-45.1878, 23.6221, -213.7731), RR=(-51.1785, 23.6221, -213.7731).
#   x: FL.x != FR.x (|dx|=5.9907 = rozchod) -> lateral (left/right).
#   y: konstantni 23.622142791748047 na vsech 4 kolech -> up (vyska).
#   z: FL.z != RL.z (|dz|=10.5228 = rozvor) -> longitudinal (front/rear).
# ROZPOR S PRIKAZEM: navrhovana konvence "X=vpřed / Y=vlevo / Z=vzhůru"
# na datech NEPLATI (X se lisi lateralne, nikoli vpřed; Y je vyska,
# nikoli vlevo). Implementovano je SKUTECNE mapovani (Roblox Y-up:
# x=lateral, y=up, z=longitudinal), rozpor je explicitne zdokumentovan
# zde a v reports/M2/WHEEL-GEOMETRY-REPORT.md. Slepe prevzeti navrhu
# by prohodilo rozchod/rozvor a vysku.
#   Predni naprava = vetsi Z (FL.z=FR.z=-203.25 > RL.z=RR.z=-213.77),
#   leva strana = vetsi X (FL.x=RL.x=-45.19 > FR.x=RR.x=-51.18);
#   pri doprednem +Z a +Y nahoru je +X leva (prave system Y-up).
COORDINATE_FRAME_ACTUAL = {
    "x": "lateral: left/right (osa rozchodu; L = vetsi X, R = mensi X)",
    "y": "up: vyska (konstantni 23.622142791748047 na vsech kolech)",
    "z": "longitudinal: front/rear (osa rozvoru; F = vetsi Z, R = mensi Z)",
    "verified_in_studio": True,
}

# Tolerance krizovych kontrol geometrie (zrcadli assess_wheel_geometry
# v rbxm_parser.py, ktery se NEMENI; tento modul ho jen cte/assessuje):
# koule max-min <= 1 % maxima, vysky Y spread <= 0.05, roh mrize 0.06.
GEOMETRY_SPHERICAL_TOL = 0.01
GEOMETRY_HEIGHT_TOL = 0.05
GEOMETRY_CORNER_TOL = 0.06
# Minimalni rozestup shluku, aby mel rohove zarazeni smysl
# (rozchod/rozvor v radech jednotek studu >> float32 sum).
GEOMETRY_MIN_CLUSTER_GAP = 1.0

# Tvar inspection_report.json dle ZAVAZNEHO kontraktu
# reports/M2-M3-CONTRACTS-FREEZE-v1.md §inspection_report.json
# (stary "navrh M2 spike" schema je nahrazen timto tvarem).

# Schema inspection_report.json dle ZAVAZNEHO kontraktu
# reports/M2-M3-CONTRACTS-FREEZE-v1.md §inspection_report.json.
# Vse studs; status povinny u kazdeho mereni.
INSPECTION_REPORT_SCHEMA = {
    "$schema": "inspection_report (kontrakt M2-M3-CONTRACTS-FREEZE-v1)",
    "type": "object",
    "required": ["report_id", "vehicle_id", "source_file",
                 "source_sha256", "parser_version", "code_version",
                 "wheels", "axles", "wheelbase_studs",
                 "tire_diameters_studs", "coordinate_frame",
                 "method", "warnings", "overall_status"],
    # "known_non_wheels" je NADSTAVBA tohoto modulu (evidovane legitimni
    # dily podvozku, viz CHASSIS_PART_ALLOWLIST): volitelny klic, povinne
    # klice kontraktu se NEMENI.
    "properties": {
        "known_non_wheels": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["instance_id", "name", "shape", "tier"],
            },
        },
        "report_id": {"type": "string"},
        "vehicle_id": {"type": "string"},
        "source_file": {"type": "string"},
        "source_sha256": {"type": "string"},
        "parser_version": {"type": "string"},
        "code_version": {"type": "string"},
        "wheels": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["designation", "instance_id", "class_name",
                             "center_studs", "size_studs", "shape",
                             "status", "reason"],
            },
        },
        "axles": {
            "type": "object",
            "required": ["front", "rear"],
        },
        "wheelbase_studs": {"type": ["number", "null"]},
        "tire_diameters_studs": {"type": "object"},
        "coordinate_frame": {
            "type": "object",
            "required": ["x", "y", "z", "verified_in_studio"],
        },
        "method": {"type": "string"},
        "warnings": {"type": "array"},
        "overall_status": {"enum": ["GEOMETRY_OK", "UNKNOWN", "BLOCKED"]},
    },
}


class HierarchyError(ValueError):
    """Poskozena parent hierarchie — nelze klasifikovat jako validni."""


class ParentCycleError(HierarchyError):
    """Cyklus v parent retezci (duvod parent_cycle -> vzdy BLOCKED)."""


class MissingParentError(HierarchyError):
    """Odkaz na neexistujici parent ID (vzdy BLOCKED)."""


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


def _ancestor_ids(instance, index):
    """Id predku od primeho rodice ke koreni (poradi vystupu).

    Sleduje navstivena id: pri opakovani hlasi ParentCycleError
    s duvodem parent_cycle, pri odkazu mimo index MissingParentError.
    Cyklus se nikdy tise nepreskakuje — poskozena hierarchie nesmi
    projit jako validni.
    """
    chain = []
    seen = {instance.get("id")}
    parent_id = instance.get("parent_id")
    if parent_id is None:
        return chain
    node = index.get(parent_id)
    if node is None:
        raise MissingParentError(
            "missing parent id: instance %r odkazuje na neexistujici "
            "parent %r" % (instance.get("id"), parent_id))
    while node is not None:
        nid = node.get("id")
        if nid in seen:
            raise ParentCycleError(
                "parent_cycle: cyklus v parent hierarchii u instance "
                "%r (retezec %r)" % (instance.get("id"), chain + [nid]))
        seen.add(nid)
        chain.append(nid)
        parent_id = node.get("parent_id")
        if parent_id is None:
            break
        node = index.get(parent_id)
        if node is None:
            raise MissingParentError(
                "missing parent id: instance %r odkazuje na neexistujici "
                "parent %r" % (nid, parent_id))
    return chain


def is_in_wheels(instance, wheels_id, index):
    """Ancestor-walk: lezi instance v podstrome Model:Wheels?

    Pri cyklu nebo chybejicim parent ID vyhodi ParentCycleError /
    MissingParentError — volajici musi vysledek oznacit BLOCKED.
    """
    if instance.get("id") == wheels_id:
        return True
    return wheels_id in _ancestor_ids(instance, index)


def classify_candidate(instance, in_wheels):
    """Jedna kandidatni instance -> (tier, failed_checks).

    4-tier: VALID_WHEEL | KNOWN_NON_WHEEL | UNKNOWN_CANDIDATE |
    INVALID_WHEEL (vyznam viz komentar u CHASSIS_PART_ALLOWLIST).
    failed_checks nese konkretni porusene podminky
    (not_in_wheels / bad_designation / bad_shape).
    """
    failed = []
    if not in_wheels:
        failed.append("not_in_wheels")
    name = instance.get("name")
    if name not in WHEEL_DESIGNATIONS:
        failed.append("bad_designation")
    if instance.get("shape") != WHEEL_SHAPE:
        failed.append("bad_shape")
    if not failed:
        return "VALID_WHEEL", []
    if (in_wheels and instance.get("class_name") == "Part"
            and name in CHASSIS_PART_ALLOWLIST):
        # Legitimni dil podvozku ve Wheels: evidovat, neblokovat.
        # failed_checks se zahazuji (dil je znamy cely, ne "skoro kolo").
        return "KNOWN_NON_WHEEL", []
    if name in WHEEL_DESIGNATIONS:
        # Narokuje oznaceni kola, ale porusuje (a) nebo (c).
        return "INVALID_WHEEL", failed
    return "UNKNOWN_CANDIDATE", failed


def detect_wheels(instances):
    """Identifikace kol ze seznamu instanci.

    Vraci dict: {wheels, known_non_wheels, unidentified, blocked,
      blocked_reasons, status}.
    known_non_wheels: evidovane legitimni dily podvozku (allowlist),
      NEBLOKUJI. unidentified: UNKNOWN_CANDIDATE / INVALID_WHEEL
      uvnitr Wheels (kazdy zaznam nese tier) -> vzdy BLOCKED.
    Deterministicke: stejny vstup = stejny vystup.
    Poskozena hierarchie (duplicitni id, cyklus, chybejici parent)
    vzdy BLOCKED — nikdy se neklasifikuje jako validni.
    """
    result = {"wheels": {}, "known_non_wheels": [], "unidentified": [],
              "blocked": False, "blocked_reasons": [], "status": "OK"}

    def block(reason):
        if reason not in result["blocked_reasons"]:
            result["blocked_reasons"].append(reason)
        result["blocked"] = True
        result["status"] = "BLOCKED"

    try:
        index = _by_id(instances)
    except ValueError as exc:
        block("duplicate instance id: %s" % exc)
        return result

    wheels_models = find_wheels_models(instances)
    if not wheels_models:
        block("missing Model:Wheels")
        return result
    if len(wheels_models) > 1:
        block("ambiguous Model:Wheels: found %d" % len(wheels_models))
        return result
    wheels_id = wheels_models[0].get("id")
    # Retez samotneho Model:Wheels musi byt zdravy — cyklus zasahujici
    # primo Wheels (i cyklus jinde, kudy prochazi jeho retez) blokuje.
    try:
        _ancestor_ids(wheels_models[0], index)
    except HierarchyError as exc:
        block(str(exc))
        return result

    # Les (vice korenu) neni strom M2 drahy kol: explicitni politika
    # BLOCKED (format-audit §3/F2), nikdy tichy pruchod.
    roots = [i for i in instances if i.get("parent_id") is None]
    if len(roots) != 1:
        block("forest: ocekavan prave 1 koren, nalezeno %d" % len(roots))
        return result

    hits = {des: [] for des in WHEEL_DESIGNATIONS}
    for inst in instances:
        if inst.get("id") == wheels_id:
            continue
        if inst.get("class_name") != "Part":
            # Kandidatem je jen Part (tvar Ball maji jen Part dily;
            # Modely/Constrainty/Attachmenty uvnitr Wheels nejsou kola
            # ani UNKNOWN — jen by otravily vysledek).
            continue
        try:
            in_w = is_in_wheels(inst, wheels_id, index)
        except ParentCycleError as exc:
            # Poskozeny retez: kandidat je UNKNOWN_CANDIDATE, analyza BLOCKED.
            result["unidentified"].append({
                "instance_id": inst.get("id"),
                "name": inst.get("name"),
                "shape": inst.get("shape"),
                "tier": "UNKNOWN_CANDIDATE",
                "failed_checks": ["parent_cycle"],
            })
            block(str(exc))
            continue
        except MissingParentError as exc:
            result["unidentified"].append({
                "instance_id": inst.get("id"),
                "name": inst.get("name"),
                "shape": inst.get("shape"),
                "tier": "UNKNOWN_CANDIDATE",
                "failed_checks": ["missing_parent"],
            })
            block(str(exc))
            continue
        tier, failed = classify_candidate(inst, in_w)
        if tier == "VALID_WHEEL":
            hits[inst.get("name")].append(inst)
        elif tier == "KNOWN_NON_WHEEL":
            # Legitimni podvozek: evidovat, NEBLOKOVAT.
            result["known_non_wheels"].append({
                "instance_id": inst.get("id"),
                "name": inst.get("name"),
                "shape": inst.get("shape"),
                "tier": tier,
            })
        elif in_w:
            # UNKNOWN_CANDIDATE / INVALID_WHEEL uvnitr Wheels se eviduje
            # a blokuje; Ball mimo Wheels je ocekavana ne-kola
            # (ochrana pred zamenou) -> bez zaznamu, bez bloku.
            result["unidentified"].append({
                "instance_id": inst.get("id"),
                "name": inst.get("name"),
                "shape": inst.get("shape"),
                "tier": tier,
                "failed_checks": failed,
            })

    for des in WHEEL_DESIGNATIONS:
        if len(hits[des]) == 1:
            inst = hits[des][0]
            result["wheels"][des] = {
                "tier": "VALID_WHEEL",
                "status": "WHEEL",
                "instance_id": inst.get("id"),
                "shape": inst.get("shape"),
                "failed_checks": [],
            }
        elif len(hits[des]) == 0:
            result["wheels"][des] = {
                "tier": "UNKNOWN_CANDIDATE",
                "status": "UNKNOWN",
                "instance_id": None,
                "shape": None,
                "failed_checks": ["missing_wheel"],
            }
            block("wheel %s not identified (count != 4)" % des)
        else:
            result["wheels"][des] = {
                "tier": "INVALID_WHEEL",
                "status": "UNKNOWN",
                "instance_id": None,
                "shape": None,
                "failed_checks": ["duplicate_designation"],
            }
            block("duplicate designation %s: %d candidates"
                  % (des, len(hits[des])))

    if result["unidentified"]:
        tiers = sorted({u.get("tier", "?") for u in result["unidentified"]})
        block("UNKNOWN candidate(s) inside Model:Wheels: %d [tiers: %s]"
              % (len(result["unidentified"]), ",".join(tiers)))
    n_wheels = sum(1 for w in result["wheels"].values()
                   if w["tier"] == "VALID_WHEEL")
    if n_wheels != 4:
        block("identified wheels != 4 (got %d)" % n_wheels)
    return result


def is_blocked(detection_result):
    """True, pokud analyza nesmi pokracovat (BLOCKED podminky M2)."""
    return bool(detection_result.get("blocked"))


# --- Writer inspection_report.json (kontrakt M2-M3-CONTRACTS-FREEZE-v1) ---
#
# Vstupem jsou hotove zaznamy kol (identita z detect_wheels +
# geometrie z assess_wheel_geometry v rbxm_parser.py, ktery se NEMENI);
# writer jen sklade kontraktni JSON, nic neodhaduje. Chybejici hodnota
# = None + status UNKNOWN/BLOCKED, nikdy vymysl.

def _as_xyz(value):
    """Mapovani {x,y,z} / (x,y,z) -> (x,y,z) float, jinak None.

    Nevlastni labely (krome nekonecna/nenumericnosti) nerozlisuje —
    volajici kazi zaznam jako UNKNOWN s duvodem, writer pocita jen
    s konecnymi trojicemi.
    """
    if isinstance(value, dict):
        try:
            value = (value["x"], value["y"], value["z"])
        except KeyError:
            return None
    if not (isinstance(value, (tuple, list)) and len(value) == 3):
        return None
    try:
        xyz = (float(value[0]), float(value[1]), float(value[2]))
    except (TypeError, ValueError):
        return None
    if not all(math.isfinite(v) for v in xyz):
        return None
    return xyz


def _tire_diameter(size):
    """Prumer pneumatiky ze size (koule) — priemer slozek, jinak None.

    Koule: vsechny slozky > 0 a max-min <= 1 % maxima (tolerance
    assess_wheel_geometry). Nesfericke/neuplne size -> None (UNKNOWN),
    nikdy odhad.
    """
    xyz = _as_xyz(size)
    if xyz is None or not all(v > 0 for v in xyz):
        return None
    if max(xyz) - min(xyz) > GEOMETRY_SPHERICAL_TOL * max(xyz):
        return None
    return sum(xyz) / 3.0


def _expected_corner(designation):
    """Ocekavany roh dle skutecneho ramce: F = vetsi Z, L = vetsi X."""
    return {"FL": (1, 1), "FR": (0, 1),
            "RL": (1, 0), "RR": (0, 0)}[designation]


def build_inspection_report(vehicle_id, source_file, source_sha256, wheels,
                            parser_version, code_version,
                            method=("identity (a) v Model:Wheels + (b) FL/FR/RL/RR "
                                    "+ (c) Ball; geometrie stredu/rozmeru; "
                                    "ramec x=lateral, y=up, z=longitudinal"),
                            warnings=None, unidentified=None,
                            known_non_wheels=None,
                            coordinate_frame=None, report_id=None,
                            assess_blocked_reasons=None):
    """Slozi inspection_report.json dle kontraktu M2-M3-CONTRACTS-FREEZE-v1.

    wheels: {FL,FR,RL,RR} -> {instance_id, class_name, center_studs,
      size_studs, shape, status, reason}; status kola GEOMETRY_OK |
      UNKNOWN | BLOCKED, reason retezec popisujici selhani (None = OK).
      center/size jako {x,y,z} nebo (x,y,z); chybejici = None.
    unidentified: [{instance_id, name, reason}, ...] — UNKNOWN_CANDIDATE /
      INVALID_WHEEL uvnitr Model:Wheels. Kazdy zaznam = BLOCKED
      (pravidlo identity: neznamemu kandidatu ve Wheels nelze verit).
    known_non_wheels: [{instance_id, name, shape}, ...] — evidovane
      legitimni dily podvozku (CHASSIS_PART_ALLOWLIST). NEBLOKUJI,
      zustavaji v reportu pod klicem "known_non_wheels" (nadstavba
      nad kontrakt; povinne klice kontraktu nedotcena).
    coordinate_frame: default COORDINATE_FRAME_ACTUAL (Studio-overeno);
      pri verified_in_studio=False je strop UNKNOWN (bez overeni ramce
      nelze prohlasit GEOMETRY_OK).
    assess_blocked_reasons: [(str)] — duvody BLOCKED z assess_vrstvy
      (assess_wheel_geometry v rbxm_parser.py). Kazdy duvod se prida mezi
      blockujici duvody -> overall_status je vzdy BLOCKED, kdykoli je
      assess BLOCKED (I-1: zeleny report na BLOCKED datech je nebezpecny,
      report se krmi do kalibrace/M3). Per-kolo GEOMETRY_OK zaznamy
      v tele reportu zustavaji nedotceny.
    Deterministicke: zadne casy, zadny nahodny obsah; report_id default
    vehicle_id@sha256[:12].
    """
    if coordinate_frame is None:
        coordinate_frame = dict(COORDINATE_FRAME_ACTUAL)
    warn = list(warnings) if warnings else []
    unidentified = list(unidentified) if unidentified else []
    known = list(known_non_wheels) if known_non_wheels else []
    if known:
        warn.append("%d known chassis part(s) documented "
                    "(allowlist, not wheels, not blocking)"
                    % len(known))
    if report_id is None:
        report_id = "%s@%s" % (vehicle_id, (source_sha256 or "")[:12])

    entries = {}
    for des in WHEEL_DESIGNATIONS:
        rec = (wheels or {}).get(des)
        if rec is None:
            entries[des] = {
                "designation": des, "instance_id": None,
                "class_name": None, "center_studs": None,
                "size_studs": None, "shape": None,
                "status": "UNKNOWN", "reason": "missing_wheel",
            }
            continue
        center = _as_xyz(rec.get("center_studs"))
        size = _as_xyz(rec.get("size_studs"))
        entries[des] = {
            "designation": des,
            "instance_id": rec.get("instance_id"),
            "class_name": rec.get("class_name"),
            "center_studs": ({"x": center[0], "y": center[1], "z": center[2]}
                             if center is not None else None),
            "size_studs": ({"x": size[0], "y": size[1], "z": size[2]}
                           if size is not None else None),
            "shape": rec.get("shape"),
            "status": rec.get("status", "UNKNOWN"),
            "reason": rec.get("reason"),
        }

    blocked = []
    unknown = []
    for des in WHEEL_DESIGNATIONS:
        entry = entries[des]
        if entry["status"] == "BLOCKED":
            blocked.append("%s: %s" % (des, entry["reason"] or "blocked"))
        elif entry["reason"] == "missing_wheel":
            # Pocet identifikovanych kol != 4 -> vzdy BLOCKED
            # (pravidlo identity, zadny tichy UNKNOWN).
            blocked.append("%s: missing_wheel" % des)
        elif entry["status"] != "GEOMETRY_OK":
            unknown.append("%s: %s" % (des, entry["reason"] or "unknown"))
        if entry["center_studs"] is None or entry["size_studs"] is None:
            if entry["status"] == "GEOMETRY_OK":
                entry["status"] = "UNKNOWN"
                entry["reason"] = "missing_geometry"
            unknown.append("%s: missing_geometry" % des)
    for item in unidentified:
        blocked.append("unidentified inside Wheels: id=%r name=%r (%s)"
                       % (item.get("instance_id"), item.get("name"),
                          item.get("reason") or "not_a_wheel"))
    for reason in assess_blocked_reasons or []:
        blocked.append("assess BLOCKED: %s" % (reason,))
    for des in WHEEL_DESIGNATIONS:
        if entries[des]["status"] == "UNKNOWN" and entries[des]["reason"] is None:
            entries[des]["reason"] = "unknown"

    centers = {des: ((e["center_studs"]["x"], e["center_studs"]["y"],
                      e["center_studs"]["z"]) if e["center_studs"] else None)
               for des, e in entries.items()}
    diameters = {des: _tire_diameter((e["size_studs"]["x"],
                                     e["size_studs"]["y"],
                                     e["size_studs"]["z"])
                                    if e["size_studs"] else None)
                 for des, e in entries.items()}

    def track(pair):
        a, b = centers[pair[0]], centers[pair[1]]
        if a is None or b is None:
            return None
        return abs(a[0] - b[0])

    track_f = track(("FL", "FR"))
    track_r = track(("RL", "RR"))

    wheelbase = None
    pairs = []
    if centers["FL"] and centers["RL"]:
        pairs.append(abs(centers["FL"][2] - centers["RL"][2]))
    if centers["FR"] and centers["RR"]:
        pairs.append(abs(centers["FR"][2] - centers["RR"][2]))
    if pairs:
        wheelbase = sum(pairs) / len(pairs)

    # Krizove kontroly (jen pri kompletnich stredech/prumerech).
    if all(centers[d] for d in WHEEL_DESIGNATIONS):
        ys = [centers[d][1] for d in WHEEL_DESIGNATIONS]
        if max(ys) - min(ys) > GEOMETRY_HEIGHT_TOL:
            blocked.append("height_asymmetry: Y spread %r > %s"
                           % (max(ys) - min(ys), GEOMETRY_HEIGHT_TOL))
            for des in WHEEL_DESIGNATIONS:
                entries[des]["status"] = "BLOCKED"
                entries[des]["reason"] = "height_asymmetry"
        xs = sorted(c[0] for c in centers.values())
        zs = sorted(c[2] for c in centers.values())
        x_gap = xs[-1] - xs[0]
        z_gap = zs[-1] - zs[0]
        if x_gap < GEOMETRY_MIN_CLUSTER_GAP \
                or z_gap < GEOMETRY_MIN_CLUSTER_GAP:
            blocked.append("wheel layout not rectangular: x=%r z=%r"
                           % (xs, zs))
        else:
            x_mid = (xs[0] + xs[-1]) / 2.0
            z_mid = (zs[0] + zs[-1]) / 2.0
            corners = {}
            for des in WHEEL_DESIGNATIONS:
                c = centers[des]
                corners[des] = (1 if c[0] >= x_mid else 0,
                                1 if c[2] >= z_mid else 0)
            if set(corners.values()) != {(0, 0), (0, 1), (1, 0), (1, 1)}:
                blocked.append("wheel layout not a 2x2 grid: %r" % corners)
            else:
                swapped = [des for des in WHEEL_DESIGNATIONS
                           if corners[des] != _expected_corner(des)]
                if swapped:
                    blocked.append(
                        "side_or_axle_swap: oznaceni neodpovida rohu "
                        "(F=vetsi Z, L=vetsi X): %s" % ",".join(swapped))
                    for des in swapped:
                        entries[des]["status"] = "BLOCKED"
                        entries[des]["reason"] = "side_or_axle_swap"
    if all(diameters[d] is not None for d in WHEEL_DESIGNATIONS):
        ref = sum(diameters.values()) / 4.0
        outliers = [d for d in WHEEL_DESIGNATIONS
                    if abs(diameters[d] - ref) > 0.01 * ref]
        if outliers:
            blocked.append("inconsistent tire diameters: %r"
                           % ({d: diameters[d]
                               for d in WHEEL_DESIGNATIONS},))
            for des in outliers:
                entries[des]["status"] = "BLOCKED"
                entries[des]["reason"] = "diameter_asymmetry"

    if blocked:
        overall = "BLOCKED"
    elif unknown or track_f is None or track_r is None or wheelbase is None \
            or any(v is None for v in diameters.values()):
        overall = "UNKNOWN"
    elif not coordinate_frame.get("verified_in_studio"):
        overall = "UNKNOWN"
        warn.append("coordinate frame not verified in Studio "
                    "(verified_in_studio=false) — strop UNKNOWN")
    else:
        overall = "GEOMETRY_OK"
    if blocked:
        warn.append("BLOCKED: " + "; ".join(blocked))

    return {
        "report_id": report_id,
        "vehicle_id": vehicle_id,
        "source_file": source_file,
        "source_sha256": source_sha256,
        "parser_version": parser_version,
        "code_version": code_version,
        "wheels": [entries[des] for des in WHEEL_DESIGNATIONS],
        "axles": {
            "front": {"wheel_L": "FL", "wheel_R": "FR",
                      "track_studs": track_f},
            "rear": {"wheel_L": "RL", "wheel_R": "RR",
                     "track_studs": track_r},
        },
        "wheelbase_studs": wheelbase,
        "tire_diameters_studs": diameters,
        "coordinate_frame": dict(coordinate_frame),
        "method": method,
        "warnings": warn,
        "known_non_wheels": [
            {"instance_id": k.get("instance_id"), "name": k.get("name"),
             "shape": k.get("shape"), "tier": "KNOWN_NON_WHEEL"}
            for k in known
        ],
        "overall_status": overall,
    }


def report_from_assess(vehicle_id, source_file, source_sha256, assess_result,
                       parser_version, code_version, **kwargs):
    """Prevod vystupu assess_wheel_geometry -> build_inspection_report.

    assess assessuje (r/bxm_parser.py, cizi modul — jen se cte):
    GEOMETRY_OK zaznamy nesou size/position; UNKNOWN nesou failed_checks
    jako reason. Hierarchicke/duplicitni chyby -> BLOCKED zaznam kola.
    Zaznamy unidentified se jmenem z CHASSIS_PART_ALLOWLIST se preklapi
    na known_non_wheels (evidovany legitimni podvozek, NEBLOKUJI);
    zbytek unidentified blokuje jako dosud.
    PROPAGACE I-1: je-li assess BLOCKED (blocked / status / blocked_reasons),
    preda se kazdy assess blocked_reason do build_inspection_report jako
    assess_blocked_reasons -> overall_status reportu je vzdy BLOCKED.
    Per-kolo GEOMETRY_OK zaznamy v tele reportu zustavaji nedotceny.
    """
    wheels = {}
    for des in WHEEL_DESIGNATIONS:
        rec = (assess_result.get("wheels") or {}).get(des)
        if rec is None:
            continue
        failed = list(rec.get("failed_checks") or [])
        if rec.get("status") == "GEOMETRY_OK":
            status, reason = "GEOMETRY_OK", None
        elif any(f in ("hierarchy", "duplicate_designation")
                 for f in failed):
            status, reason = "BLOCKED", ",".join(failed)
        else:
            status, reason = "UNKNOWN", ",".join(failed) or "unknown"
        wheels[des] = {
            "instance_id": rec.get("instance_id"),
            "class_name": "Part",
            "center_studs": rec.get("position"),
            "size_studs": rec.get("size"),
            "shape": rec.get("shape"),
            "status": status,
            "reason": reason,
        }
    unidentified = []
    known = list((assess_result.get("known_non_wheels") or []))
    for u in assess_result.get("unidentified") or []:
        if u.get("name") in CHASSIS_PART_ALLOWLIST:
            known.append(u)
        else:
            unidentified.append({
                "instance_id": u.get("instance_id"),
                "name": u.get("name"),
                "reason": ",".join(u.get("failed_checks") or [])})
    warn = list(kwargs.pop("warnings", []) or [])
    assess_reasons = list(assess_result.get("blocked_reasons") or [])
    assess_is_blocked = (bool(assess_result.get("blocked"))
                         or assess_result.get("status") == "BLOCKED"
                         or bool(assess_reasons))
    for reason in assess_reasons:
        warn.append("assess: " + reason)
    assess_blocked = list(assess_reasons)
    if assess_is_blocked and not assess_blocked:
        assess_blocked = ["assess reported BLOCKED without reasons"]
    return build_inspection_report(
        vehicle_id, source_file, source_sha256, wheels,
        parser_version, code_version,
        assess_blocked_reasons=assess_blocked,
        unidentified=unidentified + kwargs.pop("unidentified", []),
        known_non_wheels=known + kwargs.pop("known_non_wheels", []),
        warnings=warn, **kwargs)
