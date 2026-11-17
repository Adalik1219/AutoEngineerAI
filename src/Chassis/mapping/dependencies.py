# AutoEngineerAI – Mapping: strukturované závislosti (Agent B)
"""Strukturované závislosti katalogových parametrů (datové tabulky, ne volný text).

Strojově čitelný doplněk katalogu `parameters.json` (Agent A): každá závislost
a konflikt je záznam v tabulce níže (param, podmínka, řešení, důvod, zdroj).
`src/Chassis/mapping_engine.py` čte `depends_on`/`conflicts` přímo z katalogu;
tyto tabulky dokumentují známé případy pro A-Chassis a slouží jako zdroj pro
`docs/MAPPING.md` a selftest. Pouze stdlib, žádné git operace.
"""

from __future__ import annotations

# Pravidla kategorií: co engine s parametrem smí udělat.
CATEGORY_RULES: list[dict] = [
    {
        "category": "MUTABLE_TUNE",
        "mutable": True,
        "map_action": "apply",
        "reason_template": "mapováno: {config_path} -> {tune_key}",
    },
    {
        "category": "SCRIPT_CONTROLLED",
        "mutable": False,
        "map_action": "reject",
        "reason_template": (
            "kategorie SCRIPT_CONTROLLED: hodnota žije ve skriptu mimo Tune "
            "({tune_key}); změna jen zásahem do kódu ({change_method})"
        ),
    },
    {
        "category": "STRUCTURE_CONTROLLED",
        "mutable": False,
        "map_action": "reject",
        "reason_template": (
            "kategorie STRUCTURE_CONTROLLED: hodnota je dána konstrukcí modelu "
            "({tune_key}); parametrem nelze měnit ({change_method})"
        ),
    },
    {
        "category": "READ_ONLY",
        "mutable": False,
        "map_action": "reject",
        "reason_template": (
            "kategorie READ_ONLY: pouze ke čtení ({tune_key}); zápis odmítnut"
        ),
    },
    {
        "category": "UNKNOWN",
        "mutable": False,
        "map_action": "reject",
        "reason_template": (
            "kategorie UNKNOWN: klíč/hodnota v auditu nepotvrzeny ({tune_key}); "
            "nikdy se nevymýšlejí"
        ),
    },
]

# Známé závislosti: parametr smí být aplikován, jen když platí podmínka.
# Podmínka: {"param": <config_path>, "min"/"max"/"equals": <hodnota>, "reason": <text>}.
KNOWN_DEPENDS: list[dict] = [
    {
        "param": "engine.turbo.boost",
        "depends_on": [
            {
                "param": "engine.turbo.count",
                "min": 1,
                "reason": "plnicí tlak bez turbodmychadla nemá účinek",
            }
        ],
        "source": "A-CHASSIS-AUDIT.md §5",
    },
]

# Známé konflikty: dva parametry nelze měnit v jednom kroku.
# resolution "first-wins": vítězí abecedně první config_path, druhý je rejected.
KNOWN_CONFLICTS: list[dict] = [
    {
        "param": "transmission.final_drive_mult",
        "conflicts_with": ["transmission.final_drive"],
        "resolution": "first-wins",
        "reason": (
            "FDMult je multiplikativní škálování FinalDrive; "
            "současná změna obou je nejednoznačná (Gauges navíc čtou "
            "FDMult jen vizuálně, fyzika ne)"
        ),
        "source": "A-CHASSIS-AUDIT.md §5, §6",
    },
]
