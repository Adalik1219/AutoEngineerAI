"""Verejny kontrakt modulu Telemetry: evaluate() dle §5.3 ARCHITECTURE.md."""

try:
    from .evaluate import (
        GROUP_WEIGHTS,
        HARD_LIMITS_DEFAULT,
        evaluate,
    )
    from .metrics import TELEMETRY_COLUMNS, compute_metrics, load_telemetry
except ImportError:  # prime spousteni jako skript z vlastniho adresare
    from evaluate import (
        GROUP_WEIGHTS,
        HARD_LIMITS_DEFAULT,
        evaluate,
    )
    from metrics import TELEMETRY_COLUMNS, compute_metrics, load_telemetry

__all__ = [
    "evaluate",
    "compute_metrics",
    "load_telemetry",
    "TELEMETRY_COLUMNS",
    "GROUP_WEIGHTS",
    "HARD_LIMITS_DEFAULT",
]
