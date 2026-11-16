"""Identifikátory artefaktů pipeline: vzory a validace. Pouze stdlib."""

from __future__ import annotations

import re

from .errors import ContractError

PATTERNS = {
    "profile": r"^vp_[A-Za-z0-9_]+$",
    "reference": r"^rp_[A-Za-z0-9_]+$",
    "config": r"^cfg_[A-Za-z0-9_]+$",
    "plan": r"^plan_[A-Za-z0-9_]+$",
    "result": r"^tr_[A-Za-z0-9_]+$",
    "diagnosis": r"^dg_[A-Za-z0-9_]+$",
    "run": r"^run_[A-Za-z0-9_]+$",
}

_COMPILED = {k: re.compile(v) for k, v in PATTERNS.items()}

KIND_LABEL = {
    "profile": "profil vozidla (vp_)",
    "reference": "referenční profil (rp_)",
    "config": "konfigurace (cfg_)",
    "plan": "plán změn (plan_)",
    "result": "výsledek testu (tr_)",
    "diagnosis": "diagnóza (dg_)",
    "run": "běh (run_)",
}


def is_valid(kind: str, value: object) -> bool:
    """Vrátí True, pokud `value` je řetězec odpovídající vzoru druhu `kind`."""
    rx = _COMPILED.get(kind)
    if rx is None:
        raise KeyError(f"neznámý druh identifikátoru: {kind}")
    return isinstance(value, str) and rx.match(value) is not None


def require_valid(kind: str, value: object, path: str = "$") -> str:
    """Zkontroluje identifikátor, při neshodě vyhodí ContractError (česky)."""
    label = KIND_LABEL.get(kind, kind)
    if not isinstance(value, str) or not value:
        raise ContractError(path, f"identifikátor {label} musí být neprázdný řetězec")
    if not is_valid(kind, value):
        raise ContractError(
            path,
            f"identifikátor {label} má špatný tvar: {value!r} "
            f"(očekáván vzor {PATTERNS[kind]})",
        )
    return value
