"""Autonomni optimalizator (ARCHITECTURE §5.13, TESTING-OPTIMIZATION §5).

Vlastnik: Agent G. Pouze stdlib.
Koordinatni sestup (sondy +-krok) + grid kombinace 2 parametru,
vicekriterialni straze A1–A5, append-only historie, rollback na best.
Skore: nizsi TotalScore = lepsi (souhlasne s src/Telemetry/evaluate.py).
"""

from .optimizer import propose_candidates, run_optimization, safety_filter
from .search_space import CORE_ORDER, PARAM_DEFS, get_param, search_space, set_param
from .change_plan import plan_from_diagnosis
from .statistics import describe, mann_whitney_less
from .acceptance import acceptance_decision
from .store import VariantStore

__all__ = [
    "propose_candidates",
    "run_optimization",
    "safety_filter",
    "search_space",
    "get_param",
    "set_param",
    "PARAM_DEFS",
    "CORE_ORDER",
    "plan_from_diagnosis",
    "describe",
    "mann_whitney_less",
    "acceptance_decision",
    "VariantStore",
]
