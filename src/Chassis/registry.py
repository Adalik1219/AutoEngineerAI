# AutoEngineerAI – registr adaptérů chassis (ARCHITECTURE §5.4, kap. 7)
#
# Vlastník: Agent D. Rozsah: POUZE tento soubor (+ base.py, adapters/achassis_v1.py).
# Pravidla: C:/.DATA/AutoEngineerAI/docs/AGENT-RULES.md. Python 3 stdlib, žádné git operace.
"""Registr `ChassisAdapter` implementací.

Registrováno: `achassis-v1` (A-Chassis 6C – plně implementován).
Rezervováno: `future-custom-v1` (vlastní chassis budoucnosti, §5.4/§5.9 –
  zatím neimplementován; `get_adapter` pro něj vrací jasnou chybu místo
  tichého selhání, `is_ready` je False).
"""
from __future__ import annotations

import sys
from typing import Callable

try:
    from src.Chassis.base import ChassisAdapter
except ImportError:  # přímé spuštění jako skript
    import os

    _ROOT = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    if _ROOT not in sys.path:
        sys.path.insert(0, _ROOT)
    from src.Chassis.base import ChassisAdapter


def _load_achassis_v1() -> type[ChassisAdapter]:
    from src.Chassis.adapters.achassis_v1 import AChassisV1Adapter

    return AChassisV1Adapter


# id → továrna (None = rezervováno, implementace zatím neexistuje)
_FACTORIES: dict[str, Callable[[], type[ChassisAdapter]] | None] = {
    "achassis-v1": _load_achassis_v1,
    "future-custom-v1": None,
}


def register_adapter(
    adapter_id: str, factory: Callable[[], type[ChassisAdapter]]
) -> None:
    """Zaregistruje nový adaptér (nový chassis = nová třída + záznam zde)."""
    if not adapter_id or not callable(factory):
        raise ValueError("register_adapter: neprázdné id + volatelná továrna")
    _FACTORIES[adapter_id] = factory


def is_ready(adapter_id: str) -> bool:
    """True, pokud má id implementovanou třídu (ne jen rezervaci)."""
    return _FACTORIES.get(adapter_id) is not None


def list_adapters() -> list[dict]:
    """Seznam všech známých adaptérů vč. stavu ready/reserved."""
    out = []
    for adapter_id, factory in _FACTORIES.items():
        out.append({
            "id": adapter_id,
            "status": "ready" if factory is not None else "reserved",
        })
    return out


def get_adapter(adapter_id: str) -> ChassisAdapter:
    """Vrátí instanci adaptéru; pro rezervované/neznámé id chyba s důvodem."""
    if adapter_id not in _FACTORIES:
        raise KeyError(
            f"neznámý adaptér {adapter_id!r}; známé: {sorted(_FACTORIES)}"
        )
    factory = _FACTORIES[adapter_id]
    if factory is None:
        raise NotImplementedError(
            f"adaptér {adapter_id!r} je rezervován (§5.4 future-custom-v1), "
            "ale zatím neimplementován – nový chassis = nová třída "
            "implementující ChassisAdapter + registrace zde"
        )
    return factory()()


if __name__ == "__main__":
    import json

    print(json.dumps(list_adapters(), ensure_ascii=False, indent=2))
    a = get_adapter("achassis-v1")
    print("adapter:", a.id, "| parametrů:", len(a.list_parameters()))
    try:
        get_adapter("future-custom-v1")
    except NotImplementedError as exc:
        print("future-custom-v1:", exc)
