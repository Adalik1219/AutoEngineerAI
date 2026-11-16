"""Hlavni smycka optimalizatoru (TESTING-OPTIMIZATION §5.2–§5.8).

propose(history) ve smyslu kontraktu §5.2: cte celou historii (nikdy jen
posledni vysledek), drzi best_config_id, konci pri target_score /
max_iterations; neuspesna vetev = rollback (pointer zustava, auditni zaznam).
Strategie: koordinatni sondy +-krok (interpretabilita) -> grid kombinace
2 parametru (pruzkum). Bezpecnostni filtr pred testem (meze, max_step).
Pouze stdlib.
"""

import copy

from .acceptance import acceptance_decision
from .search_space import CORE_ORDER, PARAM_DEFS, get_param, set_param
from .statistics import mean

MIN_STEP_SCALE = 0.25  # pod touto urovni: 2 halvings bez uspechu -> CONVERGED


def _cfg_id(counter):
    return "cfg_%04d" % counter


def _initial_counter(initial_config):
    """Startovni citac bez kolize s ID zakladni konfigurace.

    Kdyby best mela tvar cfg_NNNN (napr. cfg_0001 z drivejsi kampane),
    zacina citac na N+1, aby prvni kandidat neprepsal/duplikoval best ID.
    Jinak (cfg_selftest_base, cfg_input_base, ...) se zacina od 1.
    """
    import re
    start = 1
    seen = set()
    node = initial_config
    while isinstance(node, dict) and node.get("config_id"):
        cid = node.get("config_id")
        seen.add(cid)
        m = re.fullmatch(r"cfg_(\d+)", str(cid))
        if m:
            start = max(start, int(m.group(1)) + 1)
        node = node.get("parent_config_id")
        if not isinstance(node, dict):
            break
    while _cfg_id(start) in seen:
        start += 1
    return start


def safety_filter(candidate_diff, best_config, space, step_scale=1.0):
    """Kontrola kandidata pred testem: meze + max_step. Vraci (ok, duvod).

    candidate_diff: {param: {"from": .., "to": ..}} (tvar z _diff_params).
    """
    by_name = {entry["name"]: entry for entry in space}
    for name, change in candidate_diff.items():
        value = change["to"] if isinstance(change, dict) else change
        entry = by_name.get(name)
        if entry is None:
            continue  # parametr mimo prostor: optimizer ho nemenil
        if not (entry["min"] <= value <= entry["max"]):
            return False, "SAFETY_FILTER: %s=%.4g mimo [%.4g, %.4g]" % (
                name, value, entry["min"], entry["max"])
        try:
            current = get_param(best_config, name)
        except KeyError:
            return False, "SAFETY_FILTER: %s v best chybi" % name
        max_step = 2.0 * entry["step"] * step_scale + 1e-9
        if abs(value - current) > max_step:
            return False, "SAFETY_FILTER: %s krok %.4g nad max %.4g" % (
                name, abs(value - current), max_step)
    return True, ""


def _round_value(name, value):
    entry = PARAM_DEFS[name]
    span = entry["max"] - entry["min"]
    decimals = 4
    step = entry["step"]
    while step < 1.0 and decimals < 6:
        step *= 10.0
        decimals += 1
    value = min(entry["max"], max(entry["min"], value))
    return round(value + 1e-9, decimals)


def _candidate(best_config, changes, counter, rationale):
    config = copy.deepcopy(best_config)
    for name, value in changes.items():
        set_param(config, name, value)
    config["parent_config_id"] = best_config["config_id"]
    config["config_id"] = _cfg_id(counter)
    config["rationale"] = rationale
    return config


def propose_candidates(best_config, space, step_scale=1.0, start_counter=1,
                       order=None):
    """Jedno kolo kandidatu: sondy +-krok v poradi, pak grid 2 parametru.

    `order`: volitelne poradi dle citlivosti (jinak CORE_ORDER / plan).
    Vraci (kandidati, dalsi_counter). Kandidati jsou VehicleConfig dicts
    (schema-compatible: plna kopie parameters + nove config_id + rationale).
    """
    names = [e["name"] for e in space]
    if order:
        names = [n for n in order if n in names] + \
                [n for n in names if n not in order]
    else:
        names = [n for n in CORE_ORDER if n in names] + \
                [n for n in names if n not in CORE_ORDER]
    by_name = {e["name"]: e for e in space}
    candidates = []
    counter = start_counter
    seen = set()

    def emit(changes, rationale):
        nonlocal counter
        key = tuple(sorted(changes.items()))
        if key in seen:
            return
        seen.add(key)
        candidates.append(_candidate(best_config, changes, counter, rationale))
        counter += 1

    # 1. Jednoparametrove sondy (koordinatni sestup).
    for name in names:
        entry = by_name[name]
        try:
            current = get_param(best_config, name)
        except KeyError:
            continue
        for direction in (-1, +1):
            value = _round_value(name, current + direction * entry["step"] * step_scale)
            if value == current:
                continue
            emit({name: value},
                 "sonda %s %s%.4g (krok %.4g, skala %.2f)" % (
                     name, "+" if direction > 0 else "", value,
                     entry["step"], step_scale))
    # 2. Grid kombinace prvnich 2 parametru (4 kombinace +-).
    if len(names) >= 2:
        pair = names[:2]
        currents = {}
        ok = True
        for name in pair:
            try:
                currents[name] = get_param(best_config, name)
            except KeyError:
                ok = False
        if ok:
            for d0 in (-1, +1):
                for d1 in (-1, +1):
                    changes = {
                        pair[0]: _round_value(
                            pair[0], currents[pair[0]]
                            + d0 * by_name[pair[0]]["step"] * step_scale),
                        pair[1]: _round_value(
                            pair[1], currents[pair[1]]
                            + d1 * by_name[pair[1]]["step"] * step_scale),
                    }
                    if changes[pair[0]] == currents[pair[0]] \
                            and changes[pair[1]] == currents[pair[1]]:
                        continue
                    emit(changes, "grid %s%+d & %s%+d (skala %.2f)" % (
                        pair[0], d0, pair[1], d1, step_scale))
    return candidates, counter


def estimate_sensitivities(records, baseline_stats, space):
    """Jednorozmerne citlivosti S_p = dS/dp_norm z jednosondovych zaznamu kola.

    Vraci poradi parametru (nejvetsi |S_p| prvni) pro dalsi kolo.
    """
    by_name = {e["name"]: e for e in space}
    sens = {}
    for rec in records:
        diff = rec.get("param_diff") or {}
        if len(diff) != 1:
            continue
        name = next(iter(diff))
        entry = by_name.get(name)
        if not entry or entry["max"] == entry["min"]:
            continue
        delta_norm = (diff[name]["to"] - diff[name]["from"]) / (entry["max"] - entry["min"])
        if abs(delta_norm) < 1e-12:
            continue
        dec = (rec.get("decision") or {})
        stats = dec.get("stats") or {}
        s_cand = stats.get("S_cand")
        if s_cand is None or baseline_stats is None:
            continue
        sens[name] = (s_cand - baseline_stats["S"]) / delta_norm
    return sorted(sens, key=lambda n: -abs(sens[n]))


def _deviations(metric_medians, targets):
    """Normalizovane odchylky (znaminko: zaporna = lepsi nez cil)."""
    devs = {}
    for spec in targets:
        name = spec["metric"]
        value = metric_medians.get(name)
        if value is None:
            continue
        tol = spec["tolerance"] if spec["tolerance"] > 0 else 1.0
        from .backend import HIGHER_BETTER
        if name in HIGHER_BETTER:
            devs[name] = (spec["target"] - value) / tol
        else:
            devs[name] = (value - spec["target"]) / tol
    return devs


def run_optimization(initial_config, space, evaluate_config, store,
                     targets, hard_limits, max_evaluations=60,
                     stop_on_target=True, seed_offset=0):
    """Plna kampan: baseline -> kola sond -> A1–A5 -> best/rollback.

    evaluate_config(config, seed_offset, baseline_metrics) dodava backend.
    Vraci {"best_config", "best_stats", "stop_reason", "evaluations"}.
    """
    from .backend import GROUP_WEIGHTS  # jen pro manifest, ne pro skore
    _ = GROUP_WEIGHTS
    best_config = copy.deepcopy(initial_config)
    best_stats = evaluate_config(best_config, seed_offset=seed_offset,
                                 baseline_metrics=None)
    store.append({
        "event": "attempt",
        "attempt": 0,
        "config_id": best_config["config_id"],
        "parent_config_id": best_config.get("parent_config_id"),
        "param_diff": {},
        "S": best_stats["S"],
        "scenario_medians": best_stats.get("scenario_medians"),
        "scenario_rep_totals": best_stats.get("scenario_rep_totals"),
        "scenario_metric_medians": best_stats.get("scenario_metric_medians"),
        "metric_medians": best_stats.get("metric_medians"),
        "decision": {"accept": True, "failed_condition": None,
                     "summary": "BASELINE (re-baseline na aktualnich tratich)",
                     "stats": {"S_cand": best_stats["S"], "S_best": best_stats["S"]}},
        "rationale": best_config.get("rationale", ""),
        "level": "SIM",
    })
    store.set_best(best_config, best_stats)

    counter = _initial_counter(initial_config)
    evaluations = 0
    attempt_no = 0
    step_scale = 1.0
    rejected_rounds = 0
    order = None
    stop_reason = "BUDGET_OUT"
    unstable_total = best_stats.get("unstable", 0)
    total_runs = len(best_stats.get("rep_totals", []))

    while evaluations < max_evaluations:
        candidates, counter = propose_candidates(
            best_config, space, step_scale, counter, order)
        accepted = False
        round_records = []
        for cand in candidates:
            if evaluations >= max_evaluations:
                break
            changes = _diff_params(best_config, cand)
            ok, reason = safety_filter(changes, best_config, space, step_scale)
            attempt_no += 1
            if not ok:
                rec = _record(cand, changes, None,
                              {"accept": False, "failed_condition": reason,
                               "summary": reason, "stats": {}}, best_config,
                              attempt_no)
                store.append(rec)
                round_records.append(rec)
                continue
            stats = evaluate_config(
                cand, seed_offset=seed_offset,
                baseline_metrics=best_stats["metric_medians"])
            evaluations += 1
            unstable_total += stats.get("unstable", 0)
            total_runs += len(stats.get("rep_totals", []))
            decision = acceptance_decision(stats, best_stats, hard_limits)
            rec = _record(cand, changes, stats, decision, best_config, attempt_no)
            store.append(rec)
            round_records.append(rec)
            if decision["accept"]:
                best_config = cand
                best_stats = stats
                store.set_best(cand, stats)
                accepted = True
                break
            store.log_rollback(best_config["config_id"], cand["config_id"],
                               decision["failed_condition"])
        if accepted:
            step_scale = min(1.0, step_scale * 1.2)
            rejected_rounds = 0
            order = None  # krajina se zmenila -> re-sonda
        else:
            rejected_rounds += 1
            order = estimate_sensitivities(round_records, best_stats, space) \
                or None
            step_scale *= 0.5
            if rejected_rounds >= 2 or step_scale < MIN_STEP_SCALE:
                stop_reason = "CONVERGED"
                break
        if stop_on_target and _target_met(best_stats, targets):
            stop_reason = "TARGET_MET"
            break
        if total_runs > 0 and unstable_total / total_runs > 0.20:
            stop_reason = "UNSTABLE_STOP"
            break
    return {"best_config": best_config, "best_stats": best_stats,
            "stop_reason": stop_reason, "evaluations": evaluations}


def _diff_params(best_config, cand_config):
    diff = {}
    for name in PARAM_DEFS:
        try:
            old = get_param(best_config, name)
            new = get_param(cand_config, name)
        except KeyError:
            continue
        if new != old:
            diff[name] = {"from": old, "to": new}
    return diff


def _record(cand, changes, stats, decision, best_config, attempt_no):
    return {
        "event": "attempt",
        "attempt": attempt_no,
        "config_id": cand["config_id"],
        "parent_config_id": cand.get("parent_config_id"),
        "param_diff": changes,
        "S": (stats or {}).get("S"),
        "scenario_medians": (stats or {}).get("scenario_medians"),
        "scenario_rep_totals": (stats or {}).get("scenario_rep_totals"),
        "metric_medians": (stats or {}).get("metric_medians"),
        "decision": decision,
        "rationale": cand.get("rationale", ""),
        "level": "SIM",
        "rollback_to": None if decision.get("accept") else best_config["config_id"],
    }


def _target_met(best_stats, targets):
    """TARGET_MET: vsechny bodovane metriky v toleranci (|dev| <= 1)."""
    devs = _deviations(best_stats.get("metric_medians", {}), targets)
    if not devs:
        return False
    return all(abs(d) <= 1.0 for d in devs.values())
