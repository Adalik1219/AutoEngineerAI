"""Telemetrie a vyhodnoceni – metriky z RAW CSV.

Vlastneny modul: src/Telemetry/*.py (Agent F).
Format CSV je FIXNI – 30 sloupcu, souradnice x vpřed / y vlevo / z vzhuru, SI.
Cte se pouze stdlib (csv, math). Vypocty dle docs/TESTING-OPTIMIZATION.md §4.2.
"""

import csv
import math

TELEMETRY_COLUMNS = (
    "time_s", "x_m", "y_m", "v_mps", "a_long_mps2", "a_lat_mps2",
    "yaw_rad", "yaw_rate_radps", "steer_rad", "throttle", "brake",
    "gear", "engine_rpm", "engine_torque_nm",
    "omega_FL", "omega_FR", "omega_RL", "omega_RR",
    "slip_FL", "slip_FR", "slip_RL", "slip_RR",
    "fz_FL", "fz_FR", "fz_RL", "fz_RR",
    "travel_FL", "travel_FR", "travel_RL", "travel_RR",
)

WHEELS = ("FL", "FR", "RL", "RR")

V_60 = 60.0 / 3.6    # 16.6667 m/s
V_100 = 100.0 / 3.6  # 27.7778 m/s

# §4.5 bod 6: rotace mimo manevr – yaw_rate nad 120 °/s = nestabilita.
YAW_UNSTABLE_RPS = 120.0 * math.pi / 180.0

# §6.3 sanity meze (podezrele mereni, ne super-vysledek).
SANITY_T_0_100 = (1.0, 60.0)        # s
SANITY_VMAX_KMH = (20.0, 400.0)      # km/h
SANITY_BRAKE_M = (10.0, 300.0)       # m


def load_telemetry(path):
    """Nacte RAW CSV, overi FIXNI hlavicku, vrati list radku (floaty)."""
    with open(path, "r", newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        header = tuple(reader.fieldnames or ())
        if set(header) != set(TELEMETRY_COLUMNS):
            missing = set(TELEMETRY_COLUMNS) - set(header)
            extra = set(header) - set(TELEMETRY_COLUMNS)
            raise ValueError(
                "spatna hlavicka CSV: chybi %s, prebyva %s"
                % (sorted(missing), sorted(extra))
            )
        rows = []
        for i, raw in enumerate(reader, start=2):
            row = {}
            for col in TELEMETRY_COLUMNS:
                try:
                    row[col] = float(raw[col])
                except (TypeError, ValueError):
                    raise ValueError("radek %d: sloupec %s neni cislo" % (i, col))
            rows.append(row)
    if len(rows) < 2:
        raise ValueError("CSV ma mene nez 2 vzorky")
    # Seradit podle casu (obrona proti prehazene telemetrii).
    rows.sort(key=lambda r: r["time_s"])
    return rows


def _crossing_time(t0, v0, t1, v1, threshold):
    """Linearni interpolace okamziku prekroceni prahu mezi dvema vzorky."""
    if v1 == v0:
        return t1
    frac = (threshold - v0) / (v1 - v0)
    frac = min(1.0, max(0.0, frac))
    return t0 + frac * (t1 - t0)


def _first_crossing(rows, threshold, start_idx=0, column="v_mps"):
    """Prvni cas, kdy sloupec dosahne prahu (od indexu). Jinak None."""
    for i in range(start_idx, len(rows) - 1):
        if rows[i][column] < threshold <= rows[i + 1][column]:
            return _crossing_time(
                rows[i]["time_s"], rows[i][column],
                rows[i + 1]["time_s"], rows[i + 1][column], threshold,
            )
    return None


def _trapezoid_distance(rows, i_from, i_to):
    """Draha integralem rychlosti (lichobeznik), §4.2."""
    s = 0.0
    for i in range(i_from, i_to):
        dt = rows[i + 1]["time_s"] - rows[i]["time_s"]
        s += 0.5 * (rows[i]["v_mps"] + rows[i + 1]["v_mps"]) * dt
    return s


def _mean(values):
    return sum(values) / len(values) if values else 0.0


def _variance(values):
    """Populacni rozptyl (stabilita yaw-rate)."""
    if not values:
        return 0.0
    m = _mean(values)
    return sum((v - m) ** 2 for v in values) / len(values)


def _std(values):
    return math.sqrt(_variance(values))


def compute_metrics(rows, travel_limit_m=0.12):
    """Spocita vsechny metriky z radku telemetrie. Nedostupne = None + flag."""
    n = len(rows)
    metrics = {}
    flags = []

    # --- Akcelerace: casy od povele plneho plynu (§4.2). ---
    throttle_start = next(
        (i for i, r in enumerate(rows) if r["throttle"] >= 0.95), 0
    )
    metrics["t_0_60_s"] = _first_crossing(rows, V_60, throttle_start)
    metrics["t_0_100_s"] = _first_crossing(rows, V_100, throttle_start)
    if metrics["t_0_100_s"] is None:
        flags.append("t_0_100_not_reached")

    # --- Brzdeni 100–0: od povele brzdy do v < 0.1 m/s (§4.2). ---
    brake_start = next(
        (i for i, r in enumerate(rows)
         if r["brake"] >= 0.9 and r["v_mps"] >= 15.0),
        None,
    )
    if brake_start is None:
        metrics["brake_distance_100_0_m"] = None
        metrics["mean_decel_mps2"] = None
        metrics["stopping_time_s"] = None
        flags.append("brake_phase_not_found")
    else:
        v0 = rows[brake_start]["v_mps"]
        stop_idx = next(
            (i for i in range(brake_start, n) if rows[i]["v_mps"] < 0.1),
            None,
        )
        if stop_idx is None:
            metrics["brake_distance_100_0_m"] = None
            metrics["mean_decel_mps2"] = None
            metrics["stopping_time_s"] = None
            flags.append("no_full_stop")
        else:
            dist = _trapezoid_distance(rows, brake_start, stop_idx)
            t_stop = rows[stop_idx]["time_s"] - rows[brake_start]["time_s"]
            metrics["brake_distance_100_0_m"] = dist
            metrics["stopping_time_s"] = t_stop
            # Korekce na skutecnou vstupni rychlost: mean_decel = v0^2 / (2*s).
            metrics["mean_decel_mps2"] = (v0 ** 2) / (2.0 * dist) if dist > 0 else None

    # --- V-max: prumer poslednich 5 s, pokud std < 0.5 m/s (§4.2). ---
    t_end = rows[-1]["time_s"]
    window = [r["v_mps"] for r in rows if r["time_s"] >= t_end - 5.0]
    if len(window) >= 2 and _std(window) < 0.5:
        v_max = _mean(window)
        settled = True
    else:
        v_max = max(r["v_mps"] for r in rows)
        settled = False
        flags.append("vmax_not_settled")
    metrics["v_max_mps"] = v_max
    metrics["v_max_kmh"] = v_max * 3.6
    metrics["v_max_settled"] = settled

    # --- Bocni zrychleni: maximum |a_lat|. ---
    metrics["a_lat_max_mps2"] = max(abs(r["a_lat_mps2"]) for r in rows)

    # --- Understeer gradient K_us = d(delta)/d(a_lat), regrese v linearni zone. ---
    a_max = metrics["a_lat_max_mps2"]
    pairs = [
        (r["a_lat_mps2"], r["steer_rad"]) for r in rows
        if 0.5 <= abs(r["a_lat_mps2"]) <= min(6.0, 0.8 * a_max)
    ]
    if len(pairs) >= 10:
        ma = _mean([p[0] for p in pairs])
        md = _mean([p[1] for p in pairs])
        denom = sum((p[0] - ma) ** 2 for p in pairs)
        if denom > 1e-9:
            slope = sum((p[0] - ma) * (p[1] - md) for p in pairs) / denom
            metrics["understeer_gradient"] = slope  # >0 nedotacivost, <0 pretacivost
            metrics["understeer_valid"] = True
        else:
            metrics["understeer_gradient"] = None
            metrics["understeer_valid"] = False
            flags.append("understeer_no_variance")
    else:
        metrics["understeer_gradient"] = None
        metrics["understeer_valid"] = False
        flags.append("understeer_invalid")
    # (K_us vyzaduje min. 3 platne kroky S4 – v jedne stope se hlasi validita.)

    # --- Stabilita: rozptyl a maximum yaw-rate. ---
    yaw_rates = [r["yaw_rate_radps"] for r in rows]
    metrics["yaw_rate_variance"] = _variance(yaw_rates)
    metrics["yaw_rate_max_abs"] = max(abs(y) for y in yaw_rates)

    # --- Prokluz: max |slip| pres vsechna kola + cas nad |kappa| > 0.2. ---
    slip_cols = ["slip_%s" % w for w in WHEELS]
    metrics["slip_max_abs"] = max(
        abs(r[c]) for r in rows for c in slip_cols
    )
    dt_med = (rows[-1]["time_s"] - rows[0]["time_s"]) / max(n - 1, 1)
    metrics["slip_time_over_02_s"] = sum(
        1 for r in rows
        if any(abs(r[c]) > 0.2 for c in slip_cols)
    ) * dt_med

    # --- Odpruzeni: max travel + pocet dosednuti na dorazy (§4.2). ---
    travel_cols = ["travel_%s" % w for w in WHEELS]
    metrics["susp_travel_max_m"] = max(r[c] for r in rows for c in travel_cols)
    metrics["susp_bottoming_count"] = sum(
        1 for r in rows
        if any(r[c] >= travel_limit_m - 0.002 for c in travel_cols)
    )

    # --- Nestabilita behu (§4.5, mapovano na dostupne kanaly). ---
    unstable_reasons = []
    for r in rows:
        for col in TELEMETRY_COLUMNS:
            if math.isnan(r[col]) or math.isinf(r[col]):
                unstable_reasons.append("nan_inf")
                break
        else:
            continue
        break
    for i in range(n - 1):
        dt = rows[i + 1]["time_s"] - rows[i]["time_s"]
        dx = rows[i + 1]["x_m"] - rows[i]["x_m"]
        dy = rows[i + 1]["y_m"] - rows[i]["y_m"]
        step = math.hypot(dx, dy)
        if step > rows[i]["v_mps"] * dt * 5.0 + 1.0:
            unstable_reasons.append("teleport")
            break
    if metrics["yaw_rate_max_abs"] > YAW_UNSTABLE_RPS:
        unstable_reasons.append("yaw_rate_over_120dps")
    metrics["unstable"] = len(unstable_reasons) > 0
    metrics["unstable_reasons"] = unstable_reasons

    # --- Sanity (§6.3): mimo rad = podezrele mereni. ---
    suspect = []
    t100 = metrics["t_0_100_s"]
    if t100 is not None and not (SANITY_T_0_100[0] < t100 < SANITY_T_0_100[1]):
        suspect.append("t_0_100_out_of_range")
    if not (SANITY_VMAX_KMH[0] < metrics["v_max_kmh"] < SANITY_VMAX_KMH[1]):
        suspect.append("vmax_out_of_range")
    bd = metrics["brake_distance_100_0_m"]
    if bd is not None and not (SANITY_BRAKE_M[0] < bd < SANITY_BRAKE_M[1]):
        suspect.append("brake_distance_out_of_range")
    metrics["suspect"] = suspect
    metrics["flags"] = flags

    return metrics
