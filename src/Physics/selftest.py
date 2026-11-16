# selftest.py — akceptační test fyzikálního modelu (exit 0 = pass).
# Asertuje fyzikální invarianty + tiskne RAW hodnoty do hlášení.
"""Spustitelné: python selftest.py (nebo python -m src.Physics.selftest)."""

from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Physics import aero, brakes, diff, engine, gearbox, load_transfer, mass, steering, suspension, tires

RAW = []


def raw(name, value):
    RAW.append((name, value))
    return value


def check(cond, msg):
    if not cond:
        raise AssertionError(msg)


def main() -> int:
    g = 9.81
    # --- 1. Statika: ΣFz = m*g, symetrie L/R ---
    m, a, b, L, T, h = 1400.0, 1.35, 1.35, 2.7, 1.55, 0.5
    loads = load_transfer.compute_loads(m, a, b, h, L, T)
    s = raw("static_sum_N", loads["FL"] + loads["FR"] + loads["RL"] + loads["RR"])
    check(abs(s - m * g) / (m * g) < 0.005, f"ΣFz={s} != m*g={m*g}")
    check(load_transfer.check_load_sum(loads, m, g), "check_load_sum selhal ve statice")
    check(abs(loads["FL"] - loads["FR"]) < 1e-9 and abs(loads["RL"] - loads["RR"]) < 1e-9,
          "statika musi byt L/R symetricka")
    raw("static_FL_N", loads["FL"])
    check(abs(loads["FL"] - m * g / 4.0) < 1e-6, "symetricky vuz: kolo = m*g/4")

    # --- 2. Brzdění 5 m/s²: zadek odlehčen, předek přitížen, Σ zachováno ---
    lb = load_transfer.compute_loads(m, a, b, h, L, T, a_long_mps2=-5.0)
    raw("brake_FL_N", lb["FL"])
    check(lb["FL"] > loads["FL"] and lb["RL"] < loads["RL"], "pri brzděni roste predek")
    sb = lb["FL"] + lb["FR"] + lb["RL"] + lb["RR"]
    check(abs(sb - m * g) / (m * g) < 0.005, "ΣFz pri brzdeni bez liftu")

    # --- 3. Příčný přenos: aLat > 0 (vlevo) zatíží pravá kola ---
    lt = load_transfer.compute_loads(m, a, b, h, L, T, a_lat_mps2=5.0)
    raw("lat_FR_N", lt["FR"])
    check(lt["FR"] > lt["FL"] and lt["RR"] > lt["RL"], "lateral musi zatizit prava kola")
    check(abs((lt["FL"] + lt["FR"] + lt["RL"] + lt["RR"]) - m * g) / (m * g) < 0.005,
          "ΣFz pri lateralnim prenosu")

    # --- 4. Hmotnost/těžiště/setrvačnost: symetrie + kladnost ---
    ms = [700.0, 700.0]
    ps = [(-0.5, -0.4, 0.5), (-0.5, 0.4, 0.5)]
    com = raw("com", mass.center_of_mass(ms, ps))
    check(abs(com[1]) < 1e-12, "symetricka y-ova souradnice teziste = 0")
    ixx, iyy, izz = raw("inertia_cuboid", mass.inertia_cuboid(1400.0, 4.0, 1.8, 1.4))
    check(ixx > 0 and iyy > 0 and izz > 0, "setrvacnost kladna")
    check(abs(mass.weight_N(1400.0) - 1400.0 * g) < 1e-9, "tiha = m*g")
    it = mass.inertia_tensor_point_masses(ms, ps, com)
    check(abs(it[3]) < 1e-9, "symetricka konfigurace: Ixy = 0")  # −Σm·rx·ry se vyruší

    # --- 5. Motor: kladný moment i výkon, redline řez, interpolace monotónní ---
    curve = [(800, 120.0), (4000, 205.0), (7000, 184.0)]
    t_mid = raw("torque_2500_Nm", engine.torque_at_rpm(curve, 2500))
    check(120.0 < t_mid < 205.0, "interpolace mezi body")
    out = raw("engine_out", engine.engine_output(curve, 4000, 1.0, 7500))
    check(out["torque_nm"] > 0 and out["power_w"] > 0 and out["power_kw"] > 0,
          "kladny moment i vykon")
    check(abs(out["power_w"] - out["torque_nm"] * engine.rpm_to_rad_s(4000)) < 1e-6,
          "P = M*omega")
    cut = engine.engine_output(curve, 7600, 1.0, 7500)
    check(cut["torque_nm"] == 0.0 and cut["at_redline"], "redline rez")
    check(abs(engine.rad_s_to_rpm(engine.rpm_to_rad_s(3000)) - 3000) < 1e-9, "prevod rpm")

    # --- 6. Převodovka: neutrál, invariant energie, řazení ---
    gb = raw("gear_out", gearbox.gear_output(200.0, 300.0, 2, [3.2, 2.1, 1.5], 3.7))
    check(abs(gb["torque_out_nm"] * gb["omega_out_rads"] - 200.0 * 300.0 * 0.95) < 1e-6,
          "invariant M_out*w_out = M_in*w_in*eff")
    n0 = gearbox.gear_output(200.0, 300.0, 0, [3.2, 2.1], 3.7)
    check(n0["torque_out_nm"] == 0.0 and n0["omega_out_rads"] == 0.0, "neutral = (0,0)")
    up = gearbox.update_gear(2, 6500, 1.0, 30.0, [3.2, 2.1, 1.5], 6000, 3000)
    check(up == {"gear": 3, "shift_event": "up"}, "upshift nad prahem")
    dn = gearbox.update_gear(3, 2500, 0.2, 20.0, [3.2, 2.1, 1.5], 6000, 3000)
    check(dn["shift_event"] == "down", "downshift pod prahem")
    stay = gearbox.update_gear(2, 4500, 0.5, 25.0, [3.2, 2.1, 1.5], 6000, 3000)
    check(stay["shift_event"] is None, "hystereze: mezi prahy bez razeni")

    # --- 7. Diferenciál: součet, FWD/RWD nuly, symetrie, lock ---
    d_rwd = raw("diff_rwd", diff.distribute(1000.0, "RWD", omega=dict(FL=10, FR=10, RL=10, RR=10)))
    check(d_rwd["FL"] == 0.0 and d_rwd["FR"] == 0.0, "RWD: predek 0")
    check(abs(d_rwd["RL"] - d_rwd["RR"]) < 1e-9, "open: L/R symetrie")
    check(abs(sum(d_rwd.values()) - 1000.0 * 0.95) < 1e-9, "invariant Σ = T*eff")
    d_fwd = diff.distribute(1000.0, "FWD")
    check(d_fwd["RL"] == 0.0 and d_fwd["RR"] == 0.0, "FWD: zadek 0")
    d_lock = diff.distribute(1000.0, "RWD", lock_rear=1.0,
                             omega=dict(FL=0, FR=0, RL=5.0, RR=50.0))
    raw("diff_lock_RL", d_lock["RL"])
    check(d_lock["RL"] > d_lock["RR"], "lock: pomalejsi kolo dostane vic")
    d_awd = diff.distribute(1000.0, "AWD", front_bias=0.5)
    check(abs((d_awd["FL"] + d_awd["FR"]) - (d_awd["RL"] + d_awd["RR"])) < 1e-9,
          "AWD 50/50 symetrie pri stejnych otackach")

    # --- 8. Pneu: Fz<=0 → 0, friction circle, symetrie ---
    z0 = tires.compute_grip(0.1, 0.05, 0.0, 1.0)
    check(z0 == {"fx_N": 0.0, "fy_N": 0.0, "rho": 0.0}, "Fz<=0 → (0,0)")
    gg = raw("grip", tires.tire_forces(30.0, 0.31, 25.0, 0.5, 0.03, 4000.0, 1.0))
    check(math.hypot(gg["fx_N"], gg["fy_N"]) <= 1.0 * 4000.0 + 1e-9, "friction circle |F| ≤ μFz")
    sl = tires.compute_slip(30.0, 0.31, 25.0, 0.0, 0.0)
    check(abs(sl["alpha_rad"]) < 1e-12, "alpha = 0 pri vy=0, steer=0")
    mf = tires.magic_formula(0.0, 10.0, 1.9, 4000.0)
    check(mf == 0.0, "MF(0) = 0")

    # --- 9. Brzdy: split, součet, ABS ---
    bs = raw("brake_split", brakes.service_brake(1.0, 8000.0, 0.6))
    check(abs(bs["FL"] - bs["FR"]) < 1e-12 and abs(bs["RL"] - bs["RR"]) < 1e-12, "L/R symetrie")
    check(abs(sum(bs.values()) - 8000.0) < 1e-9, "soucet = pedal*Tmax")
    check(abs(bs["FL"] - 8000.0 * 0.6 / 2.0) < 1e-9, "bias predku")
    check(brakes.brake_slip(10.0, 0.3, 0.2) == 0.0, "|vx| < eps → 0")
    ab = raw("abs", brakes.abs_modulate(1000.0, 0.5))
    check(ab["abs_active"] and 0.0 < ab["torque_nm"] < 1000.0, "ABS skrti nad prahem")
    ab2 = brakes.abs_modulate(1000.0, 0.1)
    check(ab2 == {"torque_nm": 1000.0, "abs_active": False}, "ABS pod prahem propousti")

    # --- 10. Podvozek: motion ratio, symetrie, dorazy ---
    q = raw("quarter", suspension.quarter_force(30000.0, 0.05, 0.2, 3000.0, 4000.0, 1.0))
    check(abs(q["wheel_force_N"] - (30000.0 * 0.05 + 3000.0 * 0.2)) < 1e-9, "F = k*x + b*v")
    q2 = suspension.quarter_force(30000.0, 0.05, 0.2, 3000.0, 4000.0, 0.8)
    check(abs(q2["wheel_force_N"] - q["wheel_force_N"] * 0.64) < 1e-9, "motion ratio r²")
    check(suspension.damper_force(3000.0, 4000.0, 0.0) == 0.0, "tlumic pri v=0")
    tr = suspension.travel_check(0.12, 0.12)
    check(tr["bottomed_out"] and not tr["topped_out"], "doraz pri x=max")
    arb = suspension.anti_roll_bar(5000.0, 0.05, 0.02)
    check(abs(arb["left_N"] + arb["right_N"]) < 1e-12, "ARB antisymetrie L/R")

    # --- 11. Řízení: ořez, rate-limit, Ackermann inner > outer ---
    st = raw("steer", steering.compute(1.0, 0.0, 0.0, 0.1, 2.7, 1.55, 0.6))
    check(abs(st["delta"] - 0.3) < 1e-9, "rate-limit: 0 + 3.0*0.1 → 0.3")
    slow = steering.target_angle(1.0, 0.6, 0.0)
    fast = steering.target_angle(1.0, 0.6, 100.0)
    raw("steer_cut_ratio", fast / slow)
    check(abs(slow - 0.6) < 1e-12 and fast < slow / 10.0, "rychlostni orez")
    check(abs(st["delta_left"] - st["delta_right"]) > 0, "Ackermann L != R pri delta != 0")
    # δ > 0 = vlevo → levé (vnitřní) větší
    check(abs(st["delta_left"]) > abs(st["delta_right"]), "inner > outer")
    zero = steering.compute(0.0, 0.0, 10.0, 0.1, 2.7, 1.55, 0.6)
    check(zero["delta"] == 0.0 and zero["delta_left"] == 0.0, "nula zustava nulou")

    # --- 12. Aero: kvadratická závislost, symetrie splitu, nezápornost ---
    d1 = aero.drag_force(10.0)
    d2 = aero.drag_force(20.0)
    raw("drag_20_N", d2)
    check(abs(d2 / d1 - 4.0) < 1e-12, "odpor ~ v²")
    al = aero.aero_loads(30.0, ClA_m2=0.5, front_bias=0.5)
    raw("downforce_30_N", al["downforce_N"])
    check(abs(al["front_N"] - al["rear_N"]) < 1e-12, "symetricky split 50/50")
    check(al["power_loss_W"] >= 0 and al["drag_N"] >= 0, "nezapornost")
    check(aero.drag_force(0.0) == 0.0, "stani = nulovy odpor")

    print("SELFTEST PASS — vsechny invarianty drzi.")
    print("--- RAW vystup ---")
    for name, val in RAW:
        print(f"{name} = {val!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
