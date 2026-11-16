# mass.py — hmotnost, těžiště, setrvačnost (čisté funkce, žádný stav, žádné I/O).
#
# VSTUPY / VÝSTUPY / JEDNOTKY
#   Vstupy: hmotnosti [kg], pozice [m] v souřadnicích x vpřed / y vlevo / z vzhůru,
#           rozměry kvádru [m]. Výstupy: kg, m, kg*m^2.
# PŘEDPOKLADY
#   - Tuhé těleso; těžiště = vážený průměr bodových hmot.
#   - Kvádr homogenní, osy shodné s osami vozidla, momenty k těžišti.
# LIMITY
#   - Neřeší ohyb/kapaliny (palivo), ani plnou matici rotovanou mimo osy vozu.
# ZDROJE VZORCŮ (principy, ne kopie kódu):
#   - C:/.DATA/RobloxSimulator/game/shared/vehicle/Chassis/MassProperties.luau
#     (součet hmot, vážené CoM, plný tenzor Ixx=Σm(ry²+rz²) atd., produkty −Σm·rx·ry)
#   - g default 9.81 dle C:/.DATA/RobloxSimulator/game/shared/vehicle/Types/EnvironmentSI.luau
# FLAG source: "measured" (ověřená fakta) / "estimated" (odhady) / "simplified" (zjednodušení).

"""Hmotnostní vlastnosti vozidla: součet, těžiště, setrvačnost."""

from __future__ import annotations

import math

G = 9.81  # m/s^2, SI (EnvironmentSI.luau: g = 9.81)

# Klasifikace parametrů: které vstupy bývají měřené a co je zjednodušení modelu.
SOURCES = {
    "masses_kg": "measured",        # vážení vozu / dílů
    "positions_m": "estimated",      # odhad z geometrie modelu, pokud není měřeno
    "cuboid_dims_m": "estimated",    # aproximace karoserie kvádrem
    "uniform_density": "simplified",  # homogenní kvádr není skutečné rozložení hmoty
    "point_mass_com": "simplified",   # bodové hmoty místo spojitého tělesa
}


def _finite(x: float, name: str) -> float:
    if not isinstance(x, (int, float)) or not math.isfinite(float(x)):
        raise ValueError(f"{name} musi byt konecne cislo")
    return float(x)


def total_mass(masses_kg: list) -> float:
    """Součet hmot. Vstup: [kg] (>=0). Výstup: kg."""
    if not masses_kg:
        raise ValueError("masses_kg nesmi byt prazdne")
    total = 0.0
    for i, m in enumerate(masses_kg):
        m = _finite(m, f"masses_kg[{i}]")
        if m < 0.0:
            raise ValueError("hmotnost nesmi byt zaporna")
        total += m
    if total <= 0.0:
        raise ValueError("celkova hmotnost musi byt > 0")
    return total


def center_of_mass(masses_kg: list, positions_m: list) -> tuple:
    """Vážené těžiště. Vstup: hmotnosti [kg], pozice [(x,y,z)] [m], x vpřed, y vlevo, z vzhůru.
    Výstup: (x, y, z) [m]."""
    if len(masses_kg) != len(positions_m) or not masses_kg:
        raise ValueError("masses_kg a positions_m musi mit stejnou nenulovou delku")
    total = total_mass(list(masses_kg))
    cx = cy = cz = 0.0
    for i, (m, p) in enumerate(zip(masses_kg, positions_m)):
        m = _finite(m, f"masses_kg[{i}]")
        if len(p) != 3:
            raise ValueError(f"positions_m[{i}] musi mit 3 slozky")
        x = _finite(p[0], f"positions_m[{i}][0]")
        y = _finite(p[1], f"positions_m[{i}][1]")
        z = _finite(p[2], f"positions_m[{i}][2]")
        cx += m * x
        cy += m * y
        cz += m * z
    return (cx / total, cy / total, cz / total)


def inertia_cuboid(mass_kg: float, lx_m: float, ly_m: float, lz_m: float) -> tuple:
    """Setrvačnost homogenního kvádru k těžišti. Vstup: kg, rozměry [m]
    (lx podél x vpřed, ly podél y vlevo, lz podél z vzhůru).
    Výstup: (Ixx, Iyy, Izz) [kg*m^2].
    Vzorce: Ixx=m/12*(ly²+lz²), Iyy=m/12*(lx²+lz²), Izz=m/12*(lx²+ly²)."""
    m = _finite(mass_kg, "mass_kg")
    lx = _finite(lx_m, "lx_m")
    ly = _finite(ly_m, "ly_m")
    lz = _finite(lz_m, "lz_m")
    if m <= 0.0 or lx <= 0.0 or ly <= 0.0 or lz <= 0.0:
        raise ValueError("mass_kg a rozmery musi byt > 0")
    return (
        m / 12.0 * (ly * ly + lz * lz),
        m / 12.0 * (lx * lx + lz * lz),
        m / 12.0 * (lx * lx + ly * ly),
    )


def inertia_tensor_point_masses(masses_kg: list, positions_m: list, com_m: tuple) -> tuple:
    """Plný tenzor setrvačnosti soustavy bodových hmot k těžišti.
    Vstup: hmotnosti [kg], pozice [m], těžiště [m]. Výstup: (Ixx,Iyy,Izz,Ixy,Ixz,Iyz)
    [kg*m^2], kde Ixy=−Σm·rx·ry atd. (konvence MassProperties.luau)."""
    if len(masses_kg) != len(positions_m) or not masses_kg:
        raise ValueError("masses_kg a positions_m musi mit stejnou nenulovou delku")
    if len(com_m) != 3:
        raise ValueError("com_m musi mit 3 slozky")
    cx = _finite(com_m[0], "com_m[0]")
    cy = _finite(com_m[1], "com_m[1]")
    cz = _finite(com_m[2], "com_m[2]")
    ixx = iyy = izz = ixy = ixz = iyz = 0.0
    for i, (m, p) in enumerate(zip(masses_kg, positions_m)):
        m = _finite(m, f"masses_kg[{i}]")
        if m < 0.0:
            raise ValueError("hmotnost nesmi byt zaporna")
        if len(p) != 3:
            raise ValueError(f"positions_m[{i}] musi mit 3 slozky")
        rx = _finite(p[0], "x") - cx
        ry = _finite(p[1], "y") - cy
        rz = _finite(p[2], "z") - cz
        ixx += m * (ry * ry + rz * rz)
        iyy += m * (rx * rx + rz * rz)
        izz += m * (rx * rx + ry * ry)
        ixy += -m * rx * ry
        ixz += -m * rx * rz
        iyz += -m * ry * rz
    return (ixx, iyy, izz, ixy, ixz, iyz)


def weight_N(mass_kg: float, g: float = G) -> float:
    """Tíha. Vstup: kg, [m/s^2]. Výstup: N."""
    m = _finite(mass_kg, "mass_kg")
    g = _finite(g, "g")
    if m <= 0.0 or g <= 0.0:
        raise ValueError("mass_kg a g musi byt > 0")
    return m * g
