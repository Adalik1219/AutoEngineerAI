# AutoEngineerAI – Mapping: strukturované tabulky závislostí (Agent B)
"""Balíček `src/Chassis/mapping` (vlastník: Agent B).

Obsahuje datové tabulky pro Mapping Engine (viz `dependencies.py`):
pravidla kategorií, známé závislosti a známé konflikty. Samotné mapování
implementuje `src/Chassis/mapping_engine.py`, který čte `depends_on`/
`conflicts` přímo z katalogového záznamu (katalog je zdrojem pravdy;
tyto tabulky jeho známé případy dokumentují pro A-Chassis).
"""

from __future__ import annotations

from src.Chassis.mapping.dependencies import (
    CATEGORY_RULES,
    KNOWN_CONFLICTS,
    KNOWN_DEPENDS,
)

__all__ = ["CATEGORY_RULES", "KNOWN_CONFLICTS", "KNOWN_DEPENDS"]
