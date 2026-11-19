"""Kalibrace měřítka studs/m z referenčních rozměrů (M2.9/M2.10).

Vstup: referenční rozměry v SI (z profilu M1) + měření v studs
(z inspection_report M2). Výstup: scale_calibration.json dle
reports/M2-M3-CONTRACTS-FREEZE-v1.md (tvar závazný).

Klíčové pravidlo příkazu: rozchod ani průměr pneu NEJSOU automaticky
přesná reference — každá reference nese zdroj + status + nejistotu a
pro kalibraci se počítají jen NEZÁVISLÉ rodiny parametrů:

    wheelbase              -> rodina "wheelbase"
    track_f / track_r      -> rodina "track"          (společná rodina!)
    tire_d_f / tire_d_r    -> rodina "tire_diameter"  (společná rodina!)

Důvod: track_f + track_r jsou dvě měření téže věci (šířka náprav
z jednoho výkresu), stejně tak oba průměry pneu (nominální výpočet
z designace). Dva závislé údaje = 1 nezávislá reference.

BLOCKED podmínky (pořadí závazné):
  1. měření zcela chybí (prázdné / všechna None) -> UNKNOWN
     (není co kalibrovat; není to výrok o měřítku).
  2. < 2 nezávislé použitelné rodiny -> BLOCKED.
  3. relativní rozptyl odhadů > 5 % -> BLOCKED (nekonzistence, M2.10).

Jinak: vše použité VERIFIED a max |odchylka| <= 2 % -> VERIFIED,
jinak ESTIMATED. Neověřené měřítko (cokoli kromě VERIFIED) se nesmí
dostat do M3 — hlídá usable_for_m3() / require_verified_for_m3().

Pouze stdlib. Čistá funkce — deterministická (řazení + pevné pořadí
součtů), žádná náhoda, žádný čas.
"""

from __future__ import annotations

import math

VEHICLE_ID_DEFAULT = "ford-mustang-gt-2024-eu-manual-standard"

#: Mapování parametru -> rodina nezávislosti (viz modulový docstring).
PARAM_FAMILY = {
    "wheelbase": "wheelbase",
    "track_f": "track",
    "track_r": "track",
    "tire_d_f": "tire_diameter",
    "tire_d_r": "tire_diameter",
}

#: Vše VERIFIED a odchylky do této meze -> VERIFIED.
VERIFIED_MAX_DEV_PCT = 2.0
#: Rozptyl odhadů nad touto mezí -> BLOCKED (nekonzistence).
CONSISTENCY_MAX_SPREAD_PCT = 5.0

VALID_REF_STATUSES = ("VERIFIED", "ESTIMATED", "UNKNOWN")


class CalibrationError(ValueError):
    """Chybný vstup kalibrace (neplatná hodnota, neznámý parametr, …)."""


class CalibrationBlockedError(CalibrationError):
    """Měřítko je BLOCKED / neověřené a nesmí do M3."""


def _finite(value: float, name: str) -> float:
    v = float(value)
    if not math.isfinite(v):
        raise CalibrationError(f"{name} musí být konečné číslo, je {value!r}")
    return v


def _positive_si(value: float, name: str) -> float:
    v = _finite(value, name)
    if v <= 0:
        raise CalibrationError(f"{name} musí být > 0 (SI), je {value!r}")
    return v


def default_references() -> list:
    """Výchozí sada referencí Mustangu GT 2024 EU (M1 profil, SI metry).

    Rozvor + rozchody: VERIFIED (tovární údaj [1b], rozvor navíc [3]).
    Průměry pneu: ESTIMATED (nominální výpočet z designace, tolerance
    dezénu ±5 mm) — nejsou automaticky přesná reference.
    """
    base = ("[1b] Ford EU tech specs (mirror, overeno 2026-11-19) + "
            "[3] ADAC Autokatalog (overeno 2026-11-19)")
    return [
        {"param": "wheelbase", "value_si": 2.719, "unit": "m",
         "uncertainty_si": 0.003,
         "source": base + " — Wheelbase 2719 mm, [1b] i [3] shodne",
         "status": "VERIFIED"},
        {"param": "track_f", "value_si": 1.585, "unit": "m",
         "uncertainty_si": 0.003,
         "source": ("[1b] Ford EU tech specs (mirror, overeno 2026-11-19) — "
                    "Track width front 1585 (sloupec Mustang GT)"),
         "status": "VERIFIED"},
        {"param": "track_r", "value_si": 1.642, "unit": "m",
         "uncertainty_si": 0.003,
         "source": ("[1b] Ford EU tech specs (mirror, overeno 2026-11-19) — "
                    "Track width rear 1642 (sloupec Mustang GT)"),
         "status": "VERIFIED"},
        {"param": "tire_d_f", "value_si": 0.6866, "unit": "m",
         "uncertainty_si": 0.005,
         "source": ("vypocet z designace 255/40 R19 (profil M1, "
                    "VEHICLE-SPECIFICATIONS.md §2): "
                    "D = 19x25,4 + 2x255x40/100 = 686,6 mm"),
         "status": "ESTIMATED"},
        {"param": "tire_d_r", "value_si": 0.7026, "unit": "m",
         "uncertainty_si": 0.005,
         "source": ("vypocet z designace 275/40 R19 (profil M1, "
                    "VEHICLE-SPECIFICATIONS.md §2): "
                    "D = 19x25,4 + 2x275x40/100 = 702,6 mm"),
         "status": "ESTIMATED"},
    ]


def _check_references(references: list) -> dict:
    """Validace seznamu referencí -> {param: ref}. Chyba = výjimka."""
    if not isinstance(references, list) or not references:
        raise CalibrationError("references musí být neprázdný seznam")
    by_param = {}
    for ref in references:
        if not isinstance(ref, dict):
            raise CalibrationError(f"reference musí být dict, je {ref!r}")
        param = ref.get("param")
        if param not in PARAM_FAMILY:
            raise CalibrationError(f"neznámý parametr reference: {param!r}")
        if param in by_param:
            raise CalibrationError(f"duplicitní reference: {param!r}")
        status = ref.get("status")
        if status not in VALID_REF_STATUSES:
            raise CalibrationError(
                f"status reference {param!r} musí být {VALID_REF_STATUSES}, "
                f"je {status!r}")
        unit = ref.get("unit")
        if unit != "m":
            raise CalibrationError(
                f"value_si reference {param!r} musí mít unit 'm' (SI), "
                f"je {unit!r}")
        if not ref.get("source"):
            raise CalibrationError(
                f"reference {param!r} musí mít zdroj (source)")
        value_si = ref.get("value_si")
        if value_si is None:
            if status != "UNKNOWN":
                raise CalibrationError(
                    f"reference {param!r} má value_si null, "
                    f"status pak musí být UNKNOWN (je {status!r})")
        else:
            _positive_si(value_si, f"value_si[{param}]")
        u_si = ref.get("uncertainty_si")
        if u_si is not None:
            u_si = _finite(u_si, f"uncertainty_si[{param}]")
            if u_si < 0:
                raise CalibrationError(
                    f"uncertainty_si[{param}] nesmí být záporná")
        by_param[param] = {
            "param": param,
            "value_si": (None if value_si is None else float(value_si)),
            "unit": "m",
            "uncertainty_si": u_si,
            "source": ref["source"],
            "status": status,
        }
    return by_param


def _check_measurements(measurements_studs: dict) -> dict:
    """Validace měření -> {param: float|None}. Nula/zápor = výjimka."""
    if not isinstance(measurements_studs, dict):
        raise CalibrationError("measurements_studs musí být dict")
    out = {}
    for param in sorted(PARAM_FAMILY):
        if param in measurements_studs:
            m = measurements_studs[param]
            if m is None:
                out[param] = None
            else:
                v = _finite(m, f"measurements_studs[{param}]")
                if v <= 0:
                    raise CalibrationError(
                        f"measurements_studs[{param}] musí být > 0 "
                        f"nebo null, je {m!r}")
                out[param] = v
        else:
            out[param] = None
    unknown_keys = sorted(set(measurements_studs) - set(PARAM_FAMILY))
    if unknown_keys:
        raise CalibrationError(
            f"neznámé parametry měření: {unknown_keys}")
    return out


def calibrate(vehicle_id: str = VEHICLE_ID_DEFAULT,
              inspection_ref=None,
              references: list | None = None,
              measurements_studs: dict | None = None,
              u_studs: float = 0.05) -> dict:
    """Spočti měřítko studs/m. Vrací dict ve tvaru scale_calibration.json.

    u_studs: nejistota měření v RBXM ve studs (symetrická, 1σ).
    """
    refs = _check_references(
        list(references) if references is not None else default_references())
    meas = _check_measurements(dict(measurements_studs or {}))
    u_studs = _finite(u_studs, "u_studs")
    if u_studs < 0:
        raise CalibrationError("u_studs nesmí být záporná")

    ref_out = [
        {"param": p, "value_si": refs[p]["value_si"], "unit": "m",
         "source": refs[p]["source"], "status": refs[p]["status"]}
        for p in sorted(refs)
    ]
    meas_out = {p: meas[p] for p in sorted(PARAM_FAMILY)}

    def blocked(reason: str) -> dict:
        return {
            "vehicle_id": vehicle_id, "inspection_ref": inspection_ref,
            "references": ref_out, "measurements_studs": meas_out,
            "estimates": [], "deviations_pct": {},
            "uncertainty": {"combined_studs_per_meter": None,
                            "rel_pct": None,
                            "method": ("inverse-variance z nejistot referenci "
                                       "a mereni + polovicni rozpyl odhadu")},
            "overall_status": "BLOCKED", "blocked_reason": reason,
        }

    # 1) Žádná měření -> UNKNOWN (není co kalibrovat).
    if all(meas[p] is None for p in meas):
        return {
            "vehicle_id": vehicle_id, "inspection_ref": inspection_ref,
            "references": ref_out, "measurements_studs": meas_out,
            "estimates": [], "deviations_pct": {},
            "uncertainty": {"combined_studs_per_meter": None,
                            "rel_pct": None,
                            "method": ("inverse-variance z nejistot referenci "
                                       "a mereni + polovicni rozpyl odhadu")},
            "overall_status": "UNKNOWN", "blocked_reason": None,
        }

    # 2) Odhady pro použitelné páry (ref + měření, status != UNKNOWN).
    per_param = {}  # param -> (estimate, rel_var, status)
    for param in sorted(PARAM_FAMILY):
        ref = refs.get(param)
        m = meas[param]
        if ref is None or m is None:
            continue
        if ref["status"] == "UNKNOWN" or ref["value_si"] is None:
            continue
        est = m / ref["value_si"]
        rel_var = 0.0
        if ref["uncertainty_si"]:
            rel_var += (ref["uncertainty_si"] / ref["value_si"]) ** 2
        if u_studs:
            rel_var += (u_studs / m) ** 2
        per_param[param] = (est, rel_var, ref["status"])

    families = {PARAM_FAMILY[p] for p in per_param}
    if len(families) < 2:
        return blocked(
            f"méně než 2 nezávislé reference (použitelné rodiny: "
            f"{sorted(families) or ['žádná']}); "
            f"rozchod/pneu ze stejné rodiny se nepočítají dvakrát")

    # 3) Konzistence rozptylu (M2.10).
    ests = sorted(e for e, _, _ in per_param.values())
    spread_pct = (ests[-1] - ests[0]) / (sum(ests) / len(ests)) * 100.0
    if spread_pct > CONSISTENCY_MAX_SPREAD_PCT:
        return blocked(
            f"nekonzistentní měřítko: rozptyl odhadů {spread_pct:.2f} % "
            f"> {CONSISTENCY_MAX_SPREAD_PCT:.0f} %; měření/model je "
            f"deformovaný, kalibrace se nesmí použít")

    # 4) Kombinovaný odhad (inverse-variance, deterministické pořadí).
    weights = {}
    for param, (est, rel_var, _st) in per_param.items():
        weights[param] = 1.0 / rel_var if rel_var > 0 else 1.0
    w_sum = sum(weights[p] for p in sorted(weights))
    combined = sum(weights[p] * per_param[p][0]
                   for p in sorted(weights)) / w_sum
    stat_rel = math.sqrt(1.0 / w_sum) if w_sum > 0 else 0.0
    half_range_rel = ((ests[-1] - ests[0]) / 2.0 / combined
                      if len(ests) >= 2 and combined > 0 else 0.0)
    combined_rel = math.sqrt(stat_rel ** 2 + half_range_rel ** 2)

    estimates = [{"param": p, "studs_per_meter": per_param[p][0]}
                 for p in sorted(per_param)]
    deviations = {p: (per_param[p][0] - combined) / combined * 100.0
                  for p in sorted(per_param)}

    all_verified = all(st == "VERIFIED"
                       for _, _, st in per_param.values())
    max_dev = max(abs(v) for v in deviations.values())
    status = ("VERIFIED" if (all_verified and max_dev <= VERIFIED_MAX_DEV_PCT)
              else "ESTIMATED")

    return {
        "vehicle_id": vehicle_id, "inspection_ref": inspection_ref,
        "references": ref_out, "measurements_studs": meas_out,
        "estimates": estimates, "deviations_pct": deviations,
        "uncertainty": {"combined_studs_per_meter": combined,
                        "rel_pct": combined_rel * 100.0,
                        "method": ("inverse-variance z nejistot referenci "
                                   "a mereni + polovicni rozpyl odhadu")},
        "overall_status": status, "blocked_reason": None,
    }


def usable_for_m3(result: dict) -> bool:
    """Smí výsledek do M3? Jen VERIFIED — cokoli jiného je neověřené."""
    if not isinstance(result, dict):
        return False
    return result.get("overall_status") == "VERIFIED"


def require_verified_for_m3(result: dict) -> dict:
    """Vrať result, je-li VERIFIED; jinak zvedni CalibrationBlockedError."""
    if not usable_for_m3(result):
        status = (result.get("overall_status")
                  if isinstance(result, dict) else None)
        reason = (result.get("blocked_reason")
                  if isinstance(result, dict) else None)
        raise CalibrationBlockedError(
            f"měřítko {status!r} se nesmí dostat do M3 "
            f"(vyžadováno VERIFIED){': ' + reason if reason else ''}")
    return result
