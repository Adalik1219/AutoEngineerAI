"""Porovnání simulačních metrik s referenčním profilem (Agent E, stdlib only).

compare(sim_metrics, reference, tolerances=None) → dict odchylek vs. tolerance.
Každá metrika: reference (hodnota + obálka) vs. simulace → abs/rel odchylka,
status pass / fail / unknown (+ příznak, že reference je jen odhad).
"""

from __future__ import annotations

from typing import Any

#: Mapování metriky → cesta v profilu (tečková cesta do obálky {value,...}).
REFERENCE_METRICS: dict[str, str] = {
    "vmax_kmh": "performance.vmax",
    "accel_0_100_s": "performance.accel_0_100",
    "accel_0_60mph_s": "performance.accel_0_60mph",
    "braking_100_0_m": "performance.braking_100_0",
    "max_power_kw": "engine.max_power",
    "max_torque_nm": "engine.max_torque",
    "curb_weight_kg": "mass.curb_weight",
}

#: Výchozí tolerance: rel = relativní zlomek, abs = absolutní v jednotkách metriky.
#: Zvítězí přísnější z obou, je-li zadáno obojí.
DEFAULT_TOLERANCES: dict[str, dict[str, float]] = {
    "vmax_kmh": {"rel": 0.03},            # ±3 % (odpor vzduchu / převody)
    "accel_0_100_s": {"abs": 0.5},        # ±0.5 s (rozptyl měření, launch)
    "accel_0_60mph_s": {"abs": 0.5},
    "braking_100_0_m": {"rel": 0.10},     # ±10 % (povrch, pneu, teplota)
    "max_power_kw": {"rel": 0.03},        # ±3 % (tovární údaj)
    "max_torque_nm": {"rel": 0.03},
    "curb_weight_kg": {"rel": 0.03},      # ±3 % (výbava/trh)
}


def _envelope_at(reference: dict, dotted: str) -> dict | None:
    node: Any = reference
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node if isinstance(node, dict) and "value" in node else None


def _sim_value(metric: str, sim_metrics: dict) -> float | None:
    raw = sim_metrics.get(metric)
    if isinstance(raw, dict):
        raw = raw.get("value")
    return raw if isinstance(raw, (int, float)) else None


def compare(sim_metrics: dict, reference: dict,
            tolerances: dict[str, dict[str, float]] | None = None) -> dict:
    """Porovná simulační metriky s referencí.

    sim_metrics: {metrika: číslo | {"value": číslo, ...}} v kanonických jednotkách.
    reference: načtený profil. tolerances: volitelně vlastní meze.
    Vrací {"vehicle_id": ..., "metrics": {metrika: {...}}, "verdict": ...}.
    verdict: "pass" (vše v toleranci), "fail" (≥1 mimo), "unknown" (nic k porovnání).
    """
    tolerances = tolerances if tolerances is not None else DEFAULT_TOLERANCES
    out_metrics: dict[str, dict] = {}
    n_compared = 0
    n_failed = 0

    for metric, dotted in REFERENCE_METRICS.items():
        env = _envelope_at(reference, dotted)
        sim = _sim_value(metric, sim_metrics)
        ref_val = env.get("value") if env else None
        tol = tolerances.get(metric, {})

        entry: dict[str, Any] = {
            "reference": ref_val,
            "reference_source_type": (env or {}).get("source_type"),
            "reference_confidence": (env or {}).get("confidence"),
            "simulated": sim,
            "tolerance": tol,
            "abs_dev": None,
            "rel_dev": None,
            "status": "unknown",
            "note": None,
        }
        if ref_val is None or sim is None:
            reasons = []
            if ref_val is None:
                reasons.append("reference chybí (null/není v profilu)")
            if sim is None:
                reasons.append("simulace metriku nedodala")
            entry["note"] = "; ".join(reasons)
        else:
            n_compared += 1
            abs_dev = sim - ref_val
            rel_dev = abs_dev / ref_val if ref_val != 0 else None
            entry["abs_dev"] = abs_dev
            entry["rel_dev"] = rel_dev
            ok = True
            if "rel" in tol and rel_dev is not None:
                ok = ok and abs(rel_dev) <= tol["rel"]
            if "abs" in tol:
                ok = ok and abs(abs_dev) <= tol["abs"]
            entry["status"] = "pass" if ok else "fail"
            if not ok:
                n_failed += 1
            if (env or {}).get("source_type") == "estimate":
                entry["note"] = "varování: reference je pouze odhad — selhání vážit níže"
        out_metrics[metric] = entry

    verdict = "unknown" if n_compared == 0 else ("fail" if n_failed else "pass")
    return {
        "vehicle_id": reference.get("vehicle_id"),
        "metrics": out_metrics,
        "compared": n_compared,
        "failed": n_failed,
        "verdict": verdict,
    }
