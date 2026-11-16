"""Reference Intelligence — loader, validace a porovnání referenčních profilů.

Vlastník (Agent E): vehicle-data/references/<nové>.json + src/Reference/*.py
Pravidla obálek viz docs/VEHICLE-DATA.md. Pouze Python 3 stdlib.
"""

from .compare import DEFAULT_TOLERANCES, compare
from .loader import REFERENCE_FILENAMES, load_all, load_profile, project_root
from .validate import check_consistency, validate_against_schema, validate_profile

__all__ = [
    "DEFAULT_TOLERANCES",
    "REFERENCE_FILENAMES",
    "check_consistency",
    "compare",
    "load_all",
    "load_profile",
    "project_root",
    "validate_against_schema",
    "validate_profile",
]
