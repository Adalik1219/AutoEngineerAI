# AutoEngineerAI – adaptér achassis-v1 (A-Chassis 6C, Build 6C, v1.5 U2.1)
#
# Vlastník: Agent D. Rozsah: POUZE tento soubor + base.py + registry.py.
# Zdroje (čteno, nezapisováno):
#   C:/.DATA/AutoEngineerAI/docs/A-CHASSIS-AUDIT.md (celý; citace § u parametru)
#   C:/.DATA/AutoEngineerAI/docs/ARCHITECTURE.md (§3.3 VehicleConfig, §5.4)
#   C:/.DATA/AutoEngineerAI/docs/AGENT-RULES.md
# READ-ONLY: C:/Users/adamr/Downloads/chasis.rbxm (nesaháno).
#   Referenční čtení: C:/.DATA/AutoEngineerAI/assets/chassis-original/chasis-work-copy.rbxm
# Pravidla: česky; identifikátory anglicky; Python 3 stdlib; žádné git operace.
# Zásada: neúplné hodnoty = provenance "unknown", default None. NIC se nevymýšlí.
"""Adaptér `achassis-v1` – mapování Tune-parametrů z auditu na VehicleConfig.

Pokrytí: audit (§5–§13) explicitně jmenuje níže uvedené klíče Tune; zbytek
~150členné Tune-tabulky v auditu rozepsán není → takové klíče adaptér nezná
a `apply_config` je odmítne jako neznámé (důvod v reportu), nikdy netiše.
Hodnoty zakódované ve skriptech (Simulated._WHEELTUNE, Aerodynamics konstanty,
tvar křivky CurveN) jsou read-only.
"""
from __future__ import annotations

import copy
import json
import os
import sys

try:  # balíčkový import (běh z kořene projektu)
    from src.Chassis.base import ChassisAdapter, ParameterDef, PatchReport
except ImportError:  # přímé spuštění souboru jako skriptu (selftest)
    _ROOT = os.path.dirname(
        os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
    )
    if _ROOT not in sys.path:
        sys.path.insert(0, _ROOT)
    from src.Chassis.base import ChassisAdapter, ParameterDef, PatchReport


AUDIT = "A-CHASSIS-AUDIT.md"
WORK_COPY = (
    "C:/.DATA/AutoEngineerAI/assets/chassis-original/chasis-work-copy.rbxm"
)


def _m(name, tune_key, category, config_path, default, unit, source_ref,
       notes=""):
    """Tune-parametr ověřený auditem ([F]) – měnitelný."""
    return ParameterDef(
        name=name, tune_key=tune_key, category=category,
        config_path=config_path, provenance="measured", mutable=True,
        default=default, unit=unit, source_ref=f"{AUDIT} {source_ref}",
        notes=notes,
    )


def _s(name, tune_key, category, config_path, source_ref, reason, notes=""):
    """Hodnota zakódovaná ve skriptech (mimo Tune) – read-only."""
    return ParameterDef(
        name=name, tune_key=tune_key, category=category,
        config_path=config_path, provenance="script-coded", mutable=False,
        default=None, unit="", source_ref=f"{AUDIT} {source_ref}",
        notes=notes, read_only_reason=reason,
    )


def _u(name, tune_key, category, config_path, source_ref, reason, notes=""):
    """Neúplná/neověřená hodnota – read-only, default None, nic nevymyšleno."""
    return ParameterDef(
        name=name, tune_key=tune_key, category=category,
        config_path=config_path, provenance="unknown", mutable=False,
        default=None, unit="", source_ref=f"{AUDIT} {source_ref}",
        notes=notes, read_only_reason=reason,
    )


# NOTE: všechny názvy klíčů a hodnoty níže pocházejí výhradně z textu auditu.
PARAMETERS: list[ParameterDef] = [
    # --- motor (§5) ---
    _m("engine_enabled", "Engine", "engine", "engine.enabled", True, "bool", "§5",
       "Elektro-větev je mrtvá (Electric=false)."),
    _m("horsepower", "Horsepower", "engine", "engine.horsepower", 200, "hp", "§5", ""),
    _m("idle_rpm", "IdleRPM", "engine", "engine.idle_rpm", 950, "rpm", "§5", ""),
    _m("peak_rpm", "PeakRPM", "engine", "engine.peak_rpm", 6800, "rpm", "§5", ""),
    _m("redline_rpm", "Redline", "engine", "engine.redline_rpm", 8000, "rpm", "§5", ""),
    _m("peak_sharpness", "PeakSharpness", "engine", "engine.peak_sharpness", 20, "", "§5",
       "Extrémy → nerealistická špička/díra (jízdní nestabilita, ne simulační)."),
    _m("curve_mult", "CurveMult", "engine", "engine.curve_mult", 0.5, "~0–1", "§5",
       "CurveMult > ~1 → nerealistická křivka."),
    _m("eq_point", "EqPoint", "engine", "engine.eq_point", 5252, "", "§5",
       "Škálování HP↔lb-ft."),
    _m("turbo_count", "Turbochargers", "engine", "engine.turbo.count", 2, "ks", "§5", ""),
    _m("turbo_boost", "T_Boost", "engine", "engine.turbo.boost", 7, "", "§5",
       "HP_T z T_Boost × počet × CompressionRatio/10 / 7.5."),
    _m("turbo_boost_lag", "T_BoostLag", "engine", "engine.turbo.boost_lag", 125, "", "§5", ""),
    _m("turbo2_boost_lag", "T2_BoostLag", "engine", "engine.turbo.boost_lag_2", 250, "", "§5",
       "Druhý stupeň dvojitého turba."),
    _m("supercharger_count", "Superchargers", "engine", "engine.supercharger.count",
       0, "ks", "§5", ""),
    _u("supercharger_sensitivity", "S_Sensitivity", "engine",
       "engine.supercharger.sensitivity", "§5",
       "Hodnota v auditu neuvedena – nevymýšlím, nutno odečíst z Tune ve Studiu.",
       "_SBoost z otáček × S_Sensitivity."),
    _m("electric_enabled", "Electric", "engine", "engine.electric.enabled", False,
       "bool", "§5", "Elektro-větev mrtvá; Gauges názvy nesedí (viz limity)."),
    _u("electric_trans1", "E_Trans1", "engine", "engine.electric.trans1", "§5",
       "Hodnota v auditu neuvedena (Electric=false, mrtvá větev).",
       "Lichoběžník elektro-křivky."),
    _u("electric_trans2", "E_Trans2", "engine", "engine.electric.trans2", "§5",
       "Hodnota v auditu neuvedena; Gauges čte ElecTransition2 (mismatch, viz limity).",
       ""),
    _u("electric_redline", "E_Redline", "engine", "engine.electric.redline", "§5",
       "Hodnota v auditu neuvedena; Gauges čte ElecRedline (mismatch, viz limity).",
       ""),
    _u("electric_front_mult", "EH_FrontMult", "engine",
       "engine.electric.front_mult", "§5",
       "Hodnota v auditu neuvedena (mrtvá větev).", ""),
    _u("electric_end_mult", "EH_EndMult", "engine", "engine.electric.end_mult",
       "§5", "Hodnota v auditu neuvedena (mrtvá větev).", ""),
    _u("electric_end_percent", "EH_EndPercent", "engine",
       "engine.electric.end_percent", "§5",
       "Hodnota v auditu neuvedena (mrtvá větev).", ""),
    _u("electric_torque", "E_Torque", "engine", "engine.electric.torque", "§5",
       "Hodnota v auditu neuvedena (mrtvá větev).", ""),
    _u("electric_torque_end_mult", "ET_EndMult", "engine",
       "engine.electric.torque_end_mult", "§5",
       "Hodnota v auditu neuvedena (mrtvá větev).", ""),
    _u("electric_torque_end_percent", "ET_EndPercent", "engine",
       "engine.electric.torque_end_percent", "§5",
       "Hodnota v auditu neuvedena (mrtvá větev).", ""),
    _m("throttle_accel", "ThrotAccel", "engine", "engine.throttle_accel", 0.05, "", "§5", ""),
    _m("throttle_decel", "ThrotDecel", "engine", "engine.throttle_decel", 0.2, "", "§5", ""),
    _m("brake_accel", "BrakeAccel", "engine", "engine.brake_accel", 0.2, "", "§5", ""),
    _m("brake_decel", "BrakeDecel", "engine", "engine.brake_decel", 0.5, "", "§5", ""),
    _m("rev_accel", "RevAccel", "engine", "engine.rev_accel", 250, "", "§5", ""),
    _m("rev_decay", "RevDecay", "engine", "engine.rev_decay", 75, "", "§5", ""),
    _m("rev_bounce", "RevBounce", "engine", "engine.rev_bounce", 250, "", "§5",
       "Omezovač sráží RevBounce (plný/½ na posledním stupni)."),
    _m("idle_throttle", "IdleThrottle", "engine", "engine.idle_throttle", 3, "", "§5", ""),
    _m("flywheel", "Flywheel", "engine", "engine.flywheel", 500, "",
       "§5", "Vyšší = rychlejší reakce; Flywheel→0 = kmitání RPM [P]."),
    _m("incline_comp", "InclineComp", "engine", "engine.incline_comp", 1, "", "§5",
       "Násobič momentu do kopce; zpátečka invertována."),
    _u("compression_ratio", "CompressionRatio", "engine",
       "engine.compression_ratio", "§5",
       "Klíč v Tune auditem nepotvrzen (jen ve vzorci HP_T); hodnota neuvedena.",
       "Vstup vzorce turba: HP_T z T_Boost × počet × CompressionRatio/10 / 7.5."),
    _s("curve_shape_func", None, "engine", None, "§5",
       "Tvar křivky je kód (CurveN parabola kolem PeakRPM) – mění se skriptem, ne Tune.",
       "Skriptem: tvar křivky (CurveN…), přidání map (E85 apod.)."),
    # --- převodovka a spojka (§6) ---
    _m("gear_ratios", "Ratios", "transmission", "transmission.gears",
       {"R": 3.28, "N": 0, "1": 3.827, "2": 2.36, "3": 1.685, "4": 1.313,
        "5": 1.0, "6": 0.793}, "", "§6", ""),
    _m("final_drive", "FinalDrive", "transmission", "transmission.final_drive",
       3.545, "", "§6", ""),
    _m("final_drive_mult", "FDMult", "transmission",
       "transmission.final_drive_mult", 1.1, "", "§6",
       "FDMult≠1 rozhodí Gauges max-rychlosti jen vizuálně, fyziku ne."),
    _m("trans_modes", "TransModes", "transmission", "transmission.modes",
       ["Semi", "Manual", "Auto"], "", "§6", "První = výchozí."),
    _m("auto_shift_mode", "AutoShiftMode", "transmission",
       "transmission.auto_shift_mode", "Speed", "", "§6", ""),
    _m("auto_shift_type", "AutoShiftType", "transmission",
       "transmission.auto_shift_type", "DCT", "", "§6", ""),
    _m("shift_up_time", "ShiftUpTime", "transmission",
       "transmission.shift_up_time_s", 0.25, "s", "§6", ""),
    _m("shift_down_time", "ShiftDnTime", "transmission",
       "transmission.shift_down_time_s", 0.125, "s", "§6", ""),
    _m("auto_up_thresh", "AutoUpThresh", "transmission",
       "transmission.auto_up_thresh", -200, "rel. peak", "§6", ""),
    _m("auto_down_thresh", "AutoDownThresh", "transmission",
       "transmission.auto_down_thresh", 1400, "rpm", "§6", ""),
    _m("clutch_enabled", "Clutch", "transmission", "transmission.clutch.enabled",
       True, "bool", "§6",
       "Typ Clutch; alternativy TorqueConverter/CVT se volí stejným parametrem."),
    _m("clutch_engage", "ClutchEngage", "transmission",
       "transmission.clutch.engage", 10, "", "§6",
       "ClutchEngage→0 = rázy [P]."),
    _m("speed_engage", "SpeedEngage", "transmission",
       "transmission.clutch.speed_engage_sps", 20, "SPS", "§6", ""),
    _m("stall_enabled", "Stall", "transmission", "transmission.clutch.stall",
       True, "bool", "§6", "Chcípnutí; vyžaduje ignition plugin."),
    _m("clutch_kick", "ClutchKick", "transmission",
       "transmission.clutch.kick", False, "bool", "§6",
       "Launch control, standardně off."),
    _m("rpm_engage", "RPMEngage", "transmission",
       "transmission.clutch.rpm_engage", 3500, "rpm", "§6", ""),
    _u("tq_lock", "TQLock", "transmission", "transmission.clutch.tq_lock",
       "§6", "Hodnota v auditu neuvedena (parametr měniče).", ""),
    _s("shift_logic", None, "transmission", None, "§6",
       "Řadicí logika (Auto()) a Launch Control jsou kód – mění se skriptem.",
       ""),
    # --- pohon a diferenciály (§7) ---
    _m("drive_config", "Config", "drivetrain", "powertrain.drive_type", "AWD",
       "FWD|RWD|AWD", "§7",
       "Rozdělení F/R u AWD není středový dif – obě nápravy dostanou plné tq "
       "škálované jen TorqueVector biasem (zjednodušení)."),
    _m("torque_vector", "TorqueVector", "drivetrain",
       "powertrain.torque_vector", 0, "-1..1", "§7",
       "0 = 50:50; -1 = 100 % předek."),
    _m("differential_type", "DifferentialType", "drivetrain",
       "powertrain.differential_type", "New", "New|Old", "§7",
       "Nový dif: párové násobiče FR↔FL, RR↔RL kolem 1 (součet páru = 2)."),
    _m("front_diff_power", "FDiffPower", "drivetrain",
       "powertrain.diff.front_power", 20, "0–100", "§7", ""),
    _m("front_diff_coast", "FDiffCoast", "drivetrain",
       "powertrain.diff.front_coast", 20, "0–100", "§7", ""),
    _u("rear_diff_power", "RDiffPower?", "drivetrain",
       "powertrain.diff.rear_power", "§7",
       "Audit uvádí jen 'zadek 40/30' bez názvu klíče – název RDiffPower "
       "odvozen, nepotvrzen; hodnota 40 nepřevzata jako fakt.",
       "Bezpečné pásmo 0–100; vysoký Preload = nedotáčivost + odpor v rejdu."),
    _u("rear_diff_coast", "RDiffCoast?", "drivetrain",
       "powertrain.diff.rear_coast", "§7",
       "Audit uvádí jen 'zadek 40/30' bez názvu klíče – název RDiffCoast "
       "odvozen, nepotvrzen; hodnota 30 nepřevzata jako fakt.", ""),
    _m("diff_preload", "Preload", "drivetrain", "powertrain.diff.preload", 20,
       "0–100", "§7", "Vysoký Preload + uzamčené dify v rejdu = přetáčení simu [P]."),
    _u("slip_thresh_old", "SlipThres", "drivetrain",
       "powertrain.diff.slip_thresh_old", "§7",
       "Starý dif, při DifferentialType=New ignorován; hodnota neuvedena.", ""),
    _u("lock_thresh_old", "LockThres", "drivetrain",
       "powertrain.diff.lock_thresh_old", "§7",
       "Starý dif, při DifferentialType=New ignorován; hodnota neuvedena.", ""),
    _s("center_diff_logic", None, "drivetrain", None, "§7",
       "Skutečný středový dif / aktivní vektorování vyžaduje zásah skriptem.",
       ""),
    # --- odpružení (§8) ---
    _m("spring_stiffness", "Stiffness", "suspension",
       "suspension.spring_f_Npm", 20000, "", "§8",
       "F i R stejné; bezpečné cca 0.25–4×; < ~5000 = dosedání. "
       "POZOR: kandidátní dekód float-lane, symetrie kol nevychází – viz limity."),
    _m("damper", "Damping", "suspension", "suspension.damper_f_Nspm", 500, "",
       "§8", "Damping = 0 → houpání. Kandidátní dekód – viz limity."),
    _u("sus_length", "SusLength", "suspension", "suspension.length", "§8",
       "Audit dává jen odvozené délky (Free 2.7 / Max 3.2 / Min 2.35, kandidátní "
       "dekód); samotné SusLength neuvedeno.",
       "FreeLength=SusLength+PreCompress; Max=SusLength+ExtensionLim; "
       "Min=SusLength-CompressLim. Limity mimo FreeLength = trvalé dosednutí/propnutí."),
    _u("pre_compress", "PreCompress", "suspension", "suspension.pre_compress",
       "§8", "Hodnota v auditu neuvedena (jen vzorec FreeLength).", ""),
    _u("extension_lim", "ExtensionLim", "suspension", "suspension.extension_lim",
       "§8", "Hodnota v auditu neuvedena (jen vzorec MaxLength).", ""),
    _u("compress_lim", "CompressLim", "suspension", "suspension.compress_lim",
       "§8", "Hodnota v auditu neuvedena (jen vzorec MinLength).", ""),
    _m("sus_radius", "SusRadius", "suspension", "suspension.radius", 0.2, "", "§8",
       "Vzhled pružiny."),
    _m("front_gyro_dampening", "FGyroDampening", "suspension",
       "suspension.gyro_dampening_f", 50, "", "§8",
       "D tlumiče BodyGyro Stabilizer (MaxTorque 0,0,1)."),
    _m("rear_gyro_dampening", "RGyroDampening", "suspension",
       "suspension.gyro_dampening_r", 50, "", "§8", ""),
    _m("front_gyro_damp", "FGyroDamp", "suspension",
       "suspension.wheel_gyro_damp_f", 100, "", "§8",
       "Tlumení klopení kol (BodyGyro, MaxTorque 1,0,1)."),
    _m("rear_gyro_damp", "RGyroDamp", "suspension",
       "suspension.wheel_gyro_damp_r", 100, "", "§8", ""),
    _u("front_wishbone_len", "FWsBoneLen", "suspension",
       "suspension.wishbone_len_f", "§8",
       "Hodnota 4 patří procedurální (neaktivní) větvi; custom větev ji nepoužívá – "
       "hodnotu nepřebírám jako fakt pro tento kit.",
       "Bez SuspensionGeometry by skript stavěl procedurální wishbone – v tomto kitu neaktivní."),
    _u("rear_wishbone_len", "RWsBoneLen", "suspension",
       "suspension.wishbone_len_r", "§8",
       "Viz front_wishbone_len – neaktivní větev.", ""),
    _u("sus_angle", "SusAngle", "suspension", "suspension.angle", "§8",
       "Hodnota 80 patří neaktivní procedurální větvi – nepřebírána.", ""),
    _u("anchor_offset", "AnchorOffset", "suspension", "suspension.anchor_offset",
       "§8", "Hodnota v auditu neuvedena (jen neaktivní procedurální větev).", ""),
    _s("arm_kinematics", None, "suspension", "geometry_overrides", "§8, §16",
       "Kinematika ramen custom geometrie parametrem nelze – jen přestavbou dílů/kloubů.",
       "Test: průjezd nerovností – rozkmit, kontakt kol, náklon."),
    # --- řízení a geometrie (§9) ---
    _m("steering_type", "SteeringType", "steering", "steering.type", "New", "", "§9", ""),
    _m("lock_to_lock", "LockToLock", "steering", "steering.lock_to_lock", 2.6,
       "otáčky", "§9", "SteerOuter = LockToLock×180/SteerRatio = 31.2°."),
    _m("steer_ratio", "SteerRatio", "steering", "steering.ratio", 15, "", "§9", ""),
    _m("ackermann", "Ackerman", "steering", "steering.ackermann_ratio", 0.9, "", "§9",
       "SteerInner = min(Outer−(1−Ackerman)×Outer, 1.2×Outer)."),
    _m("steer_decay", "SteerDecay", "steering", "steering.decay_sps", 330, "SPS",
       "§9", "Nízký SteerDecay = přetáčivé ve vysoké rychlosti."),
    _m("min_steer", "MinSteer", "steering", "steering.min_steer_pct", 10, "%", "§9", ""),
    _m("steer_speed", "SteerSpeed", "steering", "steering.speed_per_tick", 0.05,
       "°/tick", "§9", ""),
    _m("return_speed", "ReturnSpeed", "steering", "steering.return_per_tick", 0.1,
       "°/tick", "§9", ""),
    _m("mouse_steer_exp", "MSteerExp", "steering", "steering.mouse_exp", 1, "", "§9", ""),
    _m("front_wheel_steer", "FWSteer", "steering", "steering.rear_steer", "None",
       "", "§9", "4WS off; zadní osa zamčena weldem."),
    _u("steer_axis_offset", "StAxisOffset", "steering", "steering.axis_offset",
       "§9",
       "Klíč v Tune CHYBÍ, ale Initialize:171 ho čte (CFrame.new(0, nil, 0) → "
       "podezření na runtime error). Nutno ověřit prvním spuštěním ve Studiu.",
       "Chyba kódu č. 1 – viz limits()."),
    _s("camber_caster_toe", None, "steering", None, "§9",
       "Camber/caster/toe (vše 0°) se aplikují jen natočením kola "
       "(CFrame.Angles), ne fyzikou závěsu – skutečný odklon/záklon jen geometrií.",
       "V Tune přiznáno ('Don't physically apply'); camber je vizuální."),
    # --- pneumatiky a trakce (§10) ---
    _m("front_wheel_density", "FWheelDensity", "tires", "tires.wheel_density_f",
       0.1, "", "§10", "Hmotnost kola = jediný 'parametr pneumatiky' v Tune."),
    _m("rear_wheel_density", "RWheelDensity", "tires", "tires.wheel_density_r",
       0.1, "", "§10", ""),
    _s("target_friction", None, "tires", "tires.grip_long", "§10",
       "Základ F/RTargetFriction=.7 + Heat a režimy skluzu žijí v Simulated "
       "(_WHEELTUNE, mimo Tune) – mění se skriptem, ne Tune.",
       "Grip = CustomPhysicalProperties kol, přepis každých wait() podle skluzu "
       "wheel/(0.774×speed). Kola = koule (Part.shape=0/Ball)."),
    _s("wheel_lock_ratio", None, "tires", None, "§10",
       "Režim lock (<8 % → ×WheelLockRatio) je v Simulated – mění se skriptem.", ""),
    _s("wheelspin_ratio", None, "tires", None, "§10",
       "Režim prokluz (>130 % → ×WheelspinRatio) je v Simulated – skriptem.", ""),
    _s("wear_speed", None, "tires", None, "§10",
       "Opotřebení WearSpeed=.4 / regenerace RegenSpeed=3.6 / elasticita .5 / "
       "váhy 1 – vše v Simulated, mimo Tune.",
       "Rozměr pneu = rozměr dílu kola (wDia z Size.x největšího hnacího kola)."),
    _u("legacy_wheel_density_f", "FWLgcyDensity", "tires",
       "tires.legacy_density_f", "§14, §17",
       "Legacy větev Simulated odkazuje neexistující klíč; větev je mrtvá "
       "(bez PGS Initialize skončí chybou). Hodnota neexistuje.",
       "Chyba kódu č. 4 – viz limits()."),
    _u("legacy_wheel_density_r", "RWLgcyDensity", "tires",
       "tires.legacy_density_r", "§14, §17",
       "Viz legacy_wheel_density_f – mrtvý kód.", ""),
    # --- hmotnost a těžiště (§11) ---
    _m("weight_lb", "Weight", "mass", "mass.total_kg", 3439, "lb", "§11",
       "Cílová hmotnost; hustota váhového kvádru dopočtena (cap-varování ≥2). "
       "Převod na kg řeší až runtime vrstva, nikdy úložiště (§3)."),
    _m("weight_dist_pct", "WeightDist", "mass", "mass.dist_front_pct", 55, "%",
       "§11",
       "Poloha kvádru = Lerp(střed zadku, střed předku, WeightDist) + CGHeight. "
       "Mimo 0–100 = extrémy schválně povoleny."),
    _m("cg_height", "CGHeight", "mass", "mass.cg_height", 0.8, "", "§11",
       "CGHeight > ~2 = převracení; bezpečně ≤ ~1.2."),
    _m("weight_box_size", "WeightBSize", "mass", "mass.box_size",
       [7.03, 5.35, 18.11], "", "§11", "≈ rozměry auta (kvádr #Weight v Body)."),
    _m("axle_size", "AxleSize", "mass", "mass.axle_size", 1.5, "", "§11",
       "Runtime díly Arm/Base/Axle/AxleP (1.5³)."),
    _m("axle_density", "AxleDensity", "mass", "mass.axle_density", 0.1, "", "§11",
       "Custom-zavěšení díly .01."),
    _u("wheelbase_etc", None, "mass", "dimensions.wheelbase_m", "§1, §3",
       "Rozvor/rozchod/ride-height ze souboru nevyčteny (float/CFrame gap). "
       "Postup: změřit ve Studiu (FL–RL, FL–FR), zapsat do vehicle-data/analyzed/.",
       ""),
    _u("wheel_radius", None, "tires", None, "§1, §10",
       "Poloměr kol (Size.x / wDia) bitově neověřen – float-lane gap. "
       "Postup: odečíst Size kol ve Studiu.",
       ""),
    # --- brzdy, ABS, TCS (§12) ---
    _m("brake_force", "BrakeForce", "brakes", "brakes.torque_Nm", 2500, "", "§12",
       "#BV = (FBrake/RBrakeForce × 60/FPS × brzda × tqABS) + EBrake×… + PBrake."),
    _m("brake_bias_front", "Bias", "brakes", "brakes.bias_front", 0.6, "0–1",
       "§12", "Extrémní bias (0/1) rizikový [P]."),
    _m("pbrake_force", "PBrakeForce", "brakes", "brakes.pbrake_force", 5000, "",
       "§12", "PBrake: jen zadek (bias 0)."),
    _m("pbrake_bias", "Bias(PBrake)", "brakes", "brakes.pbrake_bias", 0, "", "§12",
       "Klíč pro parkovací bias audit jmenovitě neuvádí ('Bias=0') – název je "
       "kvalifikovaný odhadem, hodnota 0 ověřena."),
    _m("engine_brake_force", "EBrakeForce", "brakes", "brakes.engine_brake",
       500, "", "§12", "Motorová brzda v redline."),
    _m("abs_threshold_sps", "ABSThreshold", "brakes", "brakes.abs_threshold_sps",
       20, "SPS", "§12",
       "ABSThreshold→0 = brzdy téměř nebrzdí. ABS = plné přerušení (tqABS=0), ne pulzování."),
    _m("tcs_threshold_sps", "TCSThreshold", "brakes", "brakes.tcs_threshold_sps",
       20, "SPS", "§12",
       "TCS: 1 − min(max(0, skluz−TCSThreshold)/TCSGradient,1) × (1−TCSLimit)."),
    _m("tcs_gradient", "TCSGradient", "brakes", "brakes.tcs_gradient", 20, "SPS",
       "§12", ""),
    _m("tcs_limit_pct", "TCSLimit", "brakes", "brakes.tcs_limit_pct", 10, "%",
       "§12", ""),
    _s("abs_pulse_logic", None, "brakes", None, "§12",
       "Pulzní ABS / chytré TCS vyžaduje zásah skriptem (současné ABS jen on/off).",
       "Přepínače T/Y za jízdy; flagy ABSActive/TCSActive/TCSAmt ve Values."),
    # --- aerodynamika (§13) – vše script-coded ---
    _s("drag_coeff", None, "aero", None, "§13",
       "Drag=.34 je konstanta v Aerodynamics (mimo Tune) – mění se skriptem "
       "nebo převodem do Tune.",
       "Drag = (0,0,speed²×Drag/30)."),
    _s("downforce_f", None, "aero", None, "§13",
       "Přítlak F=125 je konstanta ve skriptu – mění se skriptem.",
       "DownforceF.Force = (0, −speed/300×125, 0)."),
    _s("downforce_r", None, "aero", None, "§13",
       "Přítlak R=150 je konstanta ve skriptu – mění se skriptem.",
       "DownforceR.Force = (0, −speed/300×150, 0)."),
    _s("wind_volume", None, "aero", None, "§13",
       "Vol=1 (zvuk větru) je konstanta ve skriptu.", ""),
    # --- ostatní / GUI (§15, §16) ---
    _u("spring_color", None, "appearance", None, "§16",
       "Audit uvádí 'barva pružin' jako Tune-měnitelnou, ale název klíče ani "
       "hodnotu neuvádí – nevymýšlím.",
       "Matice 'co lze měnit čím': Karoserie | barva pružin | MiscWeld | díly…"),
    _u("electric_gauge_names", "ElecRedline/ElecTransition2", "engine",
       "engine.electric.gauge_names", "§15",
       "Gauges_AC6:62 čte ElecRedline/ElecTransition2, Tune má E_Redline/E_Trans2. "
       "Projeví se jen při Electric=true (zde mrtvé).",
       "Chyba kódu č. 3 – viz limits()."),
]


class AChassisV1Adapter(ChassisAdapter):
    """Adaptér pro A-Chassis 6C v1.5 U2.1 (LuaInt fork, kit 'Jeep').

    Jediný zdroj pravdy = Tune ModuleScript + Simulated + geometrie ramen
    (audit §19). Fyzika běží na klientu řidiče (LocalScript Drive) – automatické
    testy musí běžet s lokálním 'řidičem', ne čistě na serveru (§4).
    """

    id = "achassis-v1"

    def __init__(self) -> None:
        self._params = list(PARAMETERS)
        self._by_tune = {p.tune_key: p for p in self._params if p.tune_key}
        self._by_path = {p.config_path: p for p in self._params if p.config_path}

    # -- ChassisAdapter interface (§5.4) ------------------------------------
    def detect(self, model_copy_dir: str) -> float:
        """Heuristika nad pracovní kopií (binárku nikdy nemění).

        0.85 = přítomen `chasis-work-copy.rbxm` (očekávaný kit); 0.4 = jiný
        .rbxm ve stejné složce; 0.0 = nic k detekci. Plná 1.0 záměrně nikdy –
        float/CFrame gap (§1) nedovoluje tvrdit stoprocentní shodu.
        """
        try:
            names = os.listdir(model_copy_dir)
        except OSError:
            return 0.0
        if "chasis-work-copy.rbxm" in names:
            return 0.85
        if any(n.lower().endswith(".rbxm") for n in names):
            return 0.4
        return 0.0

    def list_parameters(self) -> list[ParameterDef]:
        return list(self._params)

    def apply_config(self, model_copy_dir: str, config: dict) -> PatchReport:
        """Promítne Tune-klíče z `config["parameters"]["tune"]` do VehicleConfig.

        Vrací PatchReport (applied = Tune-měnitelné; rejected = read-only /
        unknown klíče s důvodem). Binárku modelu nikdy nezapisuje – výstupem je
        validovaný slovník `patched_config` v reportu (klíč "patched_config"),
        který Engineering vrstva použije pro patch kopie.
        """
        report = PatchReport(adapter_id=self.id, model_copy_dir=model_copy_dir)
        if not isinstance(config, dict) or not isinstance(
            config.get("parameters"), dict
        ):
            report.warnings.append(
                "config nemá dict 'parameters' (§3.3) – nic neaplikováno"
            )
            patched = copy.deepcopy(config) if isinstance(config, dict) else {}
            return _ReportWithConfig(report, patched)

        params = config["parameters"]
        tune_patch = params.get("tune")
        if not isinstance(tune_patch, dict):
            report.warnings.append(
                "config['parameters'] neobsahuje dict 'tune' – nic neaplikováno; "
                "známé Tune-klíče viz list_parameters()"
            )
            return _ReportWithConfig(report, copy.deepcopy(config))

        patched = copy.deepcopy(config)
        patched_params = patched["parameters"]
        if not isinstance(patched_params.get("tune"), dict):
            patched_params["tune"] = {}

        for key, value in tune_patch.items():
            pdef = self._by_tune.get(key)
            if pdef is None:
                report.rejected.append({
                    "tune_key": key,
                    "reason": "neznámý klíč – audit ho nepotvrzuje; nezapisuji "
                              "(neúplné = unknown, nikdy nevymýšlet)",
                })
                continue
            if not pdef.mutable:
                report.rejected.append({
                    "tune_key": key,
                    "reason": pdef.read_only_reason,
                })
                continue
            old = pdef.default  # výchozí ověřená auditem; příchozí config nese požadavek
            patched_params["tune"][key] = value
            report.applied.append({
                "tune_key": key, "config_path": pdef.config_path,
                "from": old, "to": value,
            })

        # Mapované cesty §3.3: ověř, že Tune-měnitelné cesty v configu
        # neodporují 'tune' (varování, ne chyba).
        for path, pdef in self._by_path.items():
            if pdef.tune_key and pdef.mutable:
                continue
            if _lookup(patched_params, path) is not None and not pdef.mutable:
                report.warnings.append(
                    f"cesta '{path}' ({pdef.provenance}) je read-only "
                    f"({pdef.read_only_reason}); ponechána beze změny"
                )

        if not report.touched_model_files:
            report.warnings.append(
                "binárka modelu nezapsána (READ-ONLY režim FÁZE 1); "
                "patch kopie provede Engineering vrstva z 'patched_config'"
            )
        return _ReportWithConfig(report, patched)

    def limits(self) -> list[str]:
        return [
            # Chyby kódu z auditu §17 (vše [F], ověřeno ve zdrojích):
            "CHYBA 1 (§17.1, §9): Initialize:171 čte Tune.StAxisOffset, který "
            "v Tune chybí (grep negativní) – podezření na runtime error při "
            "stavbě nápravy; ověřit prvním spuštěním ve Studiu. Adaptér klíč "
            "vede jako unknown/read-only.",
            "CHYBA 2 (§17.2, §13): Aerodynamics:21 používá "
            "`Velocity.magnitude` místo `Magnitude` – odpor vzduchu se nikdy "
            "neaplikuje (přítlak ano). Oprava: jeden znak. V-max měřit až po "
            "opravě; maximálka kitu je bez odporu.",
            "CHYBA 3 (§17.3, §15): Gauges_AC6:62 čte "
            "ElecRedline/ElecTransition2, Tune má E_Redline/E_Trans2 – projeví "
            "se jen při Electric=true (zde mrtvé).",
            "CHYBA 4 (§17.4, §14): Simulated non-PGS větev odkazuje "
            "FWLgcyDensity/RWLgcyDensity (v Tune nejsou) – mrtvé, protože "
            "Initialize bez PGS skončí chybou.",
            # Neověřené hodnoty (§1):
            "FLOAT/CFRAME GAP (§1): bitově přesné hodnoty float/double/CFrame/"
            "Vector3 (Part.size, Part.CFrame, SpringConstraint "
            "Stiffness/Damping, NumberValue.Value, HingeConstraint úhly) "
            "neověřeny – kandidátní schéma (LE-deinterleave + rotL8) dává "
            "'čisté' hodnoty (např. Stiffness 2.39917), ale symetrie kol "
            "nevychází. Rozvor/rozchod/ride-height/poloměry kol = unknown; "
            "postup: Studio + kalibrační díl, pak vehicle-data/analyzed/.",
            # Tvrdé limity (§16):
            "Tvrdé limity (§16): 60Hz Heartbeat + škálování 60/RealPhysicsFPS "
            "(závislost na FPS); kola musí být koule jmenovitě FL/FR/RL/RR "
            "(jinak je Drive/Simulated ignorují); DriveSeat povinný; PGS "
            "povinné; fyzika běží na klientu řidiče (testy s lokálním řidičem).",
            "Aero a grip mimo Tune (§10, §13, §16): _WHEELTUNE (grip/wear) a "
            "aero-konstanty jsou script-coded – Optimizer je nesmí ladit "
            " Tune-cestou; volba: převést do Tune, nebo ladit skriptem.",
            "Kinematika ramen (§8, §16): custom SuspensionGeometry nelze měnit "
            "parametrem – jen přestavbou dílů/kloubů (geometry_overrides=null).",
            "Camber/caster/toe (§9): jen vizuální (CFrame.Angles), ne fyzika "
            "závěsu – skutečná geometrie nápravy jen konstrukcí.",
        ]


class _ReportWithConfig(PatchReport):
    """PatchReport + validovaný VehicleConfig dict pro Engineering vrstvu."""

    def __init__(self, report: PatchReport, patched_config: dict) -> None:
        super().__init__(
            adapter_id=report.adapter_id,
            model_copy_dir=report.model_copy_dir,
            applied=report.applied,
            rejected=report.rejected,
            warnings=report.warnings,
            touched_model_files=report.touched_model_files,
        )
        self.patched_config = patched_config

    def to_dict(self) -> dict:
        d = super().to_dict()
        d["patched_config"] = self.patched_config
        return d


def _lookup(mapping: dict, dotted: str | None) -> object:
    if not dotted:
        return None
    cur: object = mapping
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


# --------------------------------------------------------------------------
# Selftest (akceptace agenta D). Běh: python3 src/Chassis/adapters/achassis_v1.py
# Ověřuje: provenance measured/script-coded/unknown v list_parameters;
# apply_config aplikuje Tune-měnitelný parametr a odmítne read-only; exit 0.
# --------------------------------------------------------------------------
def run_selftest() -> dict:
    adapter = AChassisV1Adapter()
    raw_params = [p.to_dict() for p in adapter.list_parameters()]

    provs = {p["provenance"] for p in raw_params}
    assert {"measured", "script-coded", "unknown"} <= provs, (
        f"chybí provenance, mám jen {sorted(provs)}"
    )
    for p in raw_params:
        if p["provenance"] in ("script-coded", "unknown"):
            assert not p["mutable"], f"{p['name']} musí být read-only"
            assert p["read_only_reason"], f"{p['name']} bez důvodu odmítnutí"
        if p["provenance"] == "unknown":
            assert p["default"] is None, f"{p['name']}: unknown nesmí mít default"

    # apply_config: měnitelný parametr se aplikuje…
    cfg = {
        "config_id": "cfg_selftest",
        "parent_config_id": None,
        "vehicle_profile_id": "vp_selftest",
        "chassis_adapter": "achassis-v1",
        "parameters": {"tune": {"Horsepower": 210}},
        "rationale": "selftest",
        "model_patch_ref": None,
    }
    report = adapter.apply_config(
        "C:/.DATA/AutoEngineerAI/assets/chassis-original", cfg)
    assert isinstance(report, PatchReport), "apply_config musí vrátit PatchReport"
    assert len(report.applied) == 1, f"očekáván 1 applied, mám {report.applied}"
    assert report.applied[0]["tune_key"] == "Horsepower"
    assert report.applied[0]["from"] == 200, "from musí být auditová hodnota 200"
    assert report.applied[0]["to"] == 210
    assert report.to_dict()["patched_config"]["parameters"]["tune"]["Horsepower"] == 210

    # …read-only (script-coded) se odmítne s důvodem…
    cfg_ro = copy.deepcopy(cfg)
    cfg_ro["parameters"]["tune"] = {"Drag": 0.5}
    # "Drag" není Tune-klíč (aero konstanta je mimo Tune) → unknown-key reject.
    rep_ro = adapter.apply_config(
        "C:/.DATA/AutoEngineerAI/assets/chassis-original", cfg_ro)
    assert len(rep_ro.applied) == 0 and len(rep_ro.rejected) == 1

    cfg_ro2 = copy.deepcopy(cfg)
    cfg_ro2["parameters"]["tune"] = {"StAxisOffset": 0}
    rep_ro2 = adapter.apply_config(
        "C:/.DATA/AutoEngineerAI/assets/chassis-original", cfg_ro2)
    assert len(rep_ro2.applied) == 0 and len(rep_ro2.rejected) == 1
    assert rep_ro2.rejected[0]["reason"], "odmítnutí musí mít důvod"

    limits = adapter.limits()
    assert len(limits) >= 6, "limits() musí nést 4 chyby + float-gap + limity"
    joined = "\n".join(limits)
    for needle in ("StAxisOffset", "magnitude", "ElecRedline",
                   "FWLgcyDensity", "FLOAT/CFRAME"):
        assert needle in joined, f"v limits() chybí: {needle}"

    det = adapter.detect("C:/.DATA/AutoEngineerAI/assets/chassis-original")
    assert 0.0 <= det <= 1.0

    return {
        "selftest": "OK",
        "adapter_id": adapter.id,
        "n_parameters": len(raw_params),
        "provenance_counts": {
            p: sum(1 for r in raw_params if r["provenance"] == p)
            for p in ("measured", "script-coded", "unknown")
        },
        "detect_work_copy": det,
        "n_limits": len(limits),
        "apply_demo": report.to_dict(),
        "reject_unknown_key_demo": rep_ro.to_dict(),
        "reject_readonly_demo": rep_ro2.to_dict(),
    }


if __name__ == "__main__":
    result = run_selftest()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("SELFTEST OK")
