"""Převody jednotek SI <-> Roblox. Pouze stdlib.

Kanonické konstanty (ověřeno čtením READ-ONLY zdrojů):
- 1 stud = 0.28 m a KG_PER_RMU = 1000 * 0.28^3 = 21.952 kg
  (C:/.DATA/RobloxSimulator/game/server/RobloxAdapter/UnitMap.luau,
   C:/.DATA/RobloxSimulator/docs/CONTROL-RESET.md)
- gravitace g = 9.81 m/s²
  (C:/.DATA/RobloxSimulator/game/shared/vehicle/Types/EnvironmentSI.luau)
- výchozí integrační krok dt = 1/240 s
  (C:/.DATA/RobloxSimulator/game/shared/vehicle/Types/SIContract.luau)

Souřadnice: x vpřed, y vlevo, z vzhůru; yaw kolem +z. Úhly se délkou
nemění, převádějí se jen stupně <-> radiány.
"""

from __future__ import annotations

import math

METERS_PER_STUD = 0.28
KG_PER_RMU = 1000.0 * METERS_PER_STUD ** 3  # = 21.952
GRAVITY_MPS2 = 9.81
DEFAULT_DT = 1.0 / 240.0

STUDS_PER_METER = 1.0 / METERS_PER_STUD

MM_PER_INCH = 25.4
MM_PER_M = 1000.0


def mm_to_m(mm: float) -> float:
    """Milimetry -> metry (SI)."""
    return _finite(mm, "mm") / MM_PER_M


def m_to_mm(meters: float) -> float:
    """Metry (SI) -> milimetry."""
    return _finite(meters, "meters") * MM_PER_M


def tire_diameter_mm(width_mm: float, aspect_ratio_pct: float,
                     rim_diameter_in: float) -> float:
    """Nominální (nezatížený) průměr pneu z designace v mm.

    D = rim_in * 25.4 + 2 * width_mm * aspect_pct / 100.
    Nominální výpočet, ne měření — tolerance dezénu cca ±5 mm;
    výsledek je ESTIMATED, ne VERIFIED reference.
    """
    w = _finite(width_mm, "width_mm")
    a = _finite(aspect_ratio_pct, "aspect_ratio_pct")
    r = _finite(rim_diameter_in, "rim_diameter_in")
    if w <= 0 or a <= 0 or r <= 0:
        raise ValueError("rozměry pneu musí být > 0: "
                         f"{width_mm!r}, {aspect_ratio_pct!r}, "
                         f"{rim_diameter_in!r}")
    return r * MM_PER_INCH + 2.0 * w * a / 100.0


def _finite(value: float, name: str) -> float:
    v = float(value)
    if not math.isfinite(v):
        raise ValueError(f"{name} musí být konečné číslo, je {value!r}")
    return v


def studs_to_m(studs: float) -> float:
    """Studs -> metry."""
    return _finite(studs, "studs") * METERS_PER_STUD


def m_to_studs(meters: float) -> float:
    """Metry -> studs."""
    return _finite(meters, "meters") / METERS_PER_STUD


def studs_per_s_to_mps(speed: float) -> float:
    """Rychlost stud/s -> m/s (stejné měřítko jako délky)."""
    return _finite(speed, "speed") * METERS_PER_STUD


def mps_to_studs_per_s(speed: float) -> float:
    """Rychlost m/s -> stud/s."""
    return _finite(speed, "speed") / METERS_PER_STUD


def rmu_to_kg(mass_rmu: float) -> float:
    """Hmotnost RMU -> kg (hustota 1 RMU/stud³ = 1000 kg/m³)."""
    return _finite(mass_rmu, "mass_rmu") * KG_PER_RMU


def kg_to_rmu(mass_kg: float) -> float:
    """Hmotnost kg -> RMU."""
    return _finite(mass_kg, "mass_kg") / KG_PER_RMU


def n_to_roblox_force(force_n: float) -> float:
    """Síla N -> RMU·stud/s²."""
    return _finite(force_n, "force_n") / (KG_PER_RMU * METERS_PER_STUD)


def roblox_force_to_n(force_rbx: float) -> float:
    """Síla RMU·stud/s² -> N."""
    return _finite(force_rbx, "force_rbx") * (KG_PER_RMU * METERS_PER_STUD)


def nm_to_roblox_torque(torque_nm: float) -> float:
    """Moment N·m -> RMU·stud²/s²."""
    return _finite(torque_nm, "torque_nm") / (KG_PER_RMU * METERS_PER_STUD ** 2)


def roblox_torque_to_nm(torque_rbx: float) -> float:
    """Moment RMU·stud²/s² -> N·m."""
    return _finite(torque_rbx, "torque_rbx") * (KG_PER_RMU * METERS_PER_STUD ** 2)


def kmh_to_mps(kmh: float) -> float:
    """km/h -> m/s."""
    return _finite(kmh, "kmh") / 3.6


def mps_to_kmh(mps: float) -> float:
    """m/s -> km/h."""
    return _finite(mps, "mps") * 3.6


def deg_to_rad(deg: float) -> float:
    """Stupně -> radiány."""
    return math.radians(_finite(deg, "deg"))


def rad_to_deg(rad: float) -> float:
    """Radiány -> stupně."""
    return math.degrees(_finite(rad, "rad"))
