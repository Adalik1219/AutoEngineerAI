"""Vicekriterialni akceptacni pravidlo A1–A5 (TESTING-OPTIMIZATION §5.3).

Kandidat C je prijat jako novy best prave tehdy, kdy plati VSECHNY podminky.
Skore: nizsi = lepsi. Chranene metriky (lower-better) se hlidaji vuci best;
higher-better metriky (V-max) maji samostatnou straz proti poklesu, protoze
limity Agenta F (src/Telemetry/evaluate.py HARD_LIMITS_DEFAULT) kryji jen
lower-better metriky. A5: v SIM rezimu vzdy pass s flagem UNCONFIRMED_RUNTIME
(SIM neni dukaz pro Roblox, §6.4) – runtime brana patri Agentu QA/valiidaci.
Pouze stdlib.
"""

from .statistics import mann_whitney_less, mean, means_separated, stdev_sample

ALPHA = 0.05
# Prakticky prah zlepseni (absolutne v jednotkach TotalScore; ~1 % bezneho
# rozsahu). Statisticky vyznamne, ale prakticky nulove zlepseni se neprijima.
PRACTICAL_GAIN_ABS = 0.02
# Maximalni z horseni scenare rychlé matice nad best (relativne, §5.5 bod 3).
SCENARIO_TOL_REL = 0.03
# Straze higher-better metrik: pokles V-max nad 2 % = zamitnuti (A2 rozsireni).
HIGHER_BETTER_GUARD = {
    "v_max_kmh": 0.02,
    "v_max_mps": 0.02,
}
HIGHER_BETTER = set(HIGHER_BETTER_GUARD) | {"mean_decel_mps2", "a_lat_max_mps2"}


def _standardized_pool(cand, best):
    """Sloucene standardizovane totaly pres scenare (odstraneni meritka).

    Kazdy scenar se standardizuje prumerem/smerodatnou odchylkou best-behu
    (z = (t - mu_b) / sd_b; pri sd_b == 0 je z = 0 pri shode, jinak
    +/-velke). Scenar bez jakekoli variace (vsechny behy obou stran shodne
    na 1e-9 – kandidat scenar deterministicky neovlivnuje) se preskakuje:
    nenese zadnou informaci a jeho shody by jen ředily silu testu.
    Vraci (z_cand, z_best, skipped).
    """
    z_cand, z_best, skipped = [], [], []
    for scen, totals_c in (cand.get("scenario_rep_totals") or {}).items():
        totals_b = (best.get("scenario_rep_totals") or {}).get(scen)
        if not totals_b:
            continue
        vals_c = [float(v) for v in totals_c]
        vals_b = [float(v) for v in totals_b]
        if len(vals_c) == len(vals_b):
            scale = max(1.0, max(abs(v) for v in vals_c + vals_b))
            if all(abs(a - b) < 1e-9 * scale
                   for a, b in zip(vals_c, vals_b)):
                skipped.append(scen)
                continue
        mu_b = mean([float(v) for v in totals_b])
        sd_b = stdev_sample([float(v) for v in totals_b])
        for v in totals_b:
            z_best.append(0.0 if sd_b < 1e-12 else (float(v) - mu_b) / sd_b)
        for v in totals_c:
            if sd_b < 1e-12:
                z_cand.append(0.0 if abs(float(v) - mu_b) < 1e-9
                              else (10.0 if float(v) < mu_b else -10.0))
            else:
                z_cand.append((float(v) - mu_b) / sd_b)
    return z_cand, z_best, skipped


def _med(agg, metric):
    """Median metriky z prvniho scenare, kde je pritomna (pak zalozni pool)."""
    for scen_meds in (agg.get("scenario_metric_medians") or {}).values():
        if metric in scen_meds and scen_meds[metric] is not None:
            return scen_meds[metric]
    return (agg.get("metric_medians") or {}).get(metric)


def _stat_margin(cand, best):
    """Statisticky okraj: prumer pres scenare z 0.5*(SE_cand + SE_best).

    Pocita se po scenarih (kazdy scenar ma vlastni meritko); poolovani
    pres scenare by nafouklo rozptyl rozdilem meritka, ne sumem.
    """
    import math
    margins = []
    for scen, totals_c in (cand.get("scenario_rep_totals") or {}).items():
        totals_b = (best.get("scenario_rep_totals") or {}).get(scen)
        if not totals_b:
            continue
        se = 0.0
        for totals in (totals_c, totals_b):
            n = len(totals)
            if n >= 2:
                se += stdev_sample([float(v) for v in totals]) / math.sqrt(n)
        margins.append(0.5 * se)
    if margins:
        return sum(margins) / len(margins)
    # Zalozni chodnik bez scenarovych behu: poolovane totaly.
    return _pooled_margin(cand.get("rep_totals", []), best.get("rep_totals", []))


def _pooled_margin(totals_c, totals_b):
    import math
    se = 0.0
    for totals in (totals_c, totals_b):
        n = len(totals)
        if n >= 2:
            se += stdev_sample([float(v) for v in totals]) / math.sqrt(n)
    return 0.5 * se


def acceptance_decision(cand, best, hard_limits, alpha=ALPHA,
                         practical_gain=PRACTICAL_GAIN_ABS,
                         scenario_tol_rel=SCENARIO_TOL_REL,
                         runtime_required=False):
    """Rozhodnuti o kandidatovi.

    cand/best: {"S", "rep_totals", "scenario_medians", "metric_medians",
                "unstable", "suspect"}.
    hard_limits: {"metrika": {"rel": f} | {"abs": d}} pro lower-better metriky.
    Vraci {"accept", "failed_condition", "summary", "stats"}.
    """
    stats = {
        "S_cand": cand["S"],
        "S_best": best["S"],
        "n_cand": len(cand["rep_totals"]),
        "n_best": len(best["rep_totals"]),
    }

    # --- A1: celkove skore s margínem. ---
    margin = max(_stat_margin(cand, best), 0.005 * abs(best["S"]))
    stats["margin"] = margin
    stats["gain"] = best["S"] - cand["S"]
    if not (cand["S"] < best["S"] - margin):
        return _reject("A1_TOTAL_SCORE", stats,
                       "S_cand=%.4f neni pod S_best=%.4f - margin=%.4f"
                       % (cand["S"], best["S"], margin))

    # --- A2: chranene lower-better metriky (limity Agenta F + vlastni). ---
    for metric, lim in (hard_limits or {}).items():
        cv = _med(cand, metric)
        bv = _med(best, metric)
        if cv is None or bv is None:
            continue  # metrika v teto matici nepritomna -> n/a
        if "abs" in lim:
            allowed = bv + lim["abs"]
        else:
            allowed = bv * (1.0 + lim["rel"]) if bv >= 0 else bv
        if not (cv <= allowed):
            return _reject("A2_HARD_LIMIT:" + metric, stats,
                           "%s median %.4f nad limitem %.4f (best %.4f)"
                           % (metric, cv, allowed, bv))
    # --- A2b: higher-better metriky nesmi klesnout nad straze. ---
    for metric, rel in HIGHER_BETTER_GUARD.items():
        cv = _med(cand, metric)
        bv = _med(best, metric)
        if cv is None or bv is None:
            continue
        floor = bv * (1.0 - rel)
        if not (cv >= floor):
            return _reject("A2_HARD_LIMIT:" + metric, stats,
                           "%s median %.4f pod prahem %.4f (best %.4f)"
                           % (metric, cv, floor, bv))

    # --- A3: stabilita (zadny UNSTABLE beh, zadne podezrele mereni,
    #         zadny novy abort). ---
    if cand.get("unstable", 0) > 0:
        return _reject("A3_STABILITY", stats,
                       "kandidat ma %d UNSTABLE behu" % cand["unstable"])
    if cand.get("suspect", 0) > 0:
        return _reject("A3_STABILITY", stats,
                       "kandidat ma %d podezrelych (SUSPECT) behu" % cand["suspect"])
    if cand.get("aborts", 0) > best.get("aborts", 0):
        return _reject("A3_STABILITY", stats, "vice abortu nez best")

    # --- A4: vyznamnost zlepseni na sloucene standardizovane matici
    #         (Mann-Whitney pri n>=4, jinak prumer+-rozptyl), dale prakticky
    #         prah a konzistence scenaru (zadny scenar nesmi regresovat). ---
    z_cand, z_best, skipped = _standardized_pool(cand, best)
    stats["skipped_scenarios"] = skipped
    if z_cand and z_best:
        nc, nb = len(z_cand), len(z_best)
        if nc >= 4 and nb >= 4:
            _, p_val = mann_whitney_less(z_cand, z_best)
            stats["mann_whitney_p"] = p_val
            stats["mann_whitney_method"] = "exact_or_normal_pooled_z"
            if not (p_val < alpha):
                return _reject("A4_STATISTICS", stats,
                               "Mann-Whitney (pooled z) p=%.4f >= %.2f"
                               % (p_val, alpha))
        else:
            separated, gap = means_separated(z_cand, z_best)
            stats["means_gap"] = gap
            stats["mann_whitney_method"] = "mean_std_small_n_pooled_z"
            if not separated:
                return _reject("A4_STATISTICS", stats,
                               "pooled z: pasma mean+-std se prekryvaji (gap=%.4f)"
                               % gap)
    else:
        return _reject("A4_STATISTICS", stats,
                       "prazdna srovnavaci matice")
    if not (stats["gain"] >= practical_gain):
        return _reject("A4_PRACTICAL_GAIN", stats,
                       "zisk %.4f pod praktickym prahem %.4f"
                       % (stats["gain"], practical_gain))
    for scen, med_c in cand["scenario_medians"].items():
        med_b = best["scenario_medians"].get(scen)
        if med_b is None:
            continue
        tol = scenario_tol_rel * max(1.0, abs(med_b))
        if med_c - med_b > tol:
            return _reject("A4_SCENARIO_REGRESSION", stats,
                           "scenar %s regres: %.4f vs best %.4f (tol %.4f)"
                           % (scen, med_c, med_b, tol))

    # --- A5: runtime brana (SIM -> odklad s flagem, ne zamitnuti). ---
    stats["runtime_gate"] = "UNCONFIRMED_RUNTIME" if not runtime_required else "passed"
    if runtime_required:
        return _reject("A5_RUNTIME", stats,
                       "runtime brana vyzadovana, SIM nestaci")
    p_info = stats.get("mann_whitney_p", stats.get("means_gap"))
    if isinstance(p_info, dict):
        p_info = {k: round(v, 4) for k, v in p_info.items()}
    elif isinstance(p_info, float):
        p_info = round(p_info, 4)
    return {"accept": True, "failed_condition": None,
            "summary": "gain=%.4f stat=%s gate=UNCONFIRMED_RUNTIME" % (
                stats["gain"], p_info),
            "stats": stats}


def _reject(condition, stats, summary):
    return {"accept": False, "failed_condition": condition,
            "summary": summary, "stats": stats}
