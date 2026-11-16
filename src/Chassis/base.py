# AutoEngineerAI – ChassisAdapter (rozhraní dle docs/ARCHITECTURE.md §5.4)
#
# Vlastník: Agent D. Zdroj pravdy pro adaptéry A-Chassis.
# Audit: C:/.DATA/AutoEngineerAI/docs/A-CHASSIS-AUDIT.md (kapitoly citovány u parametrů).
# Pravidla: C:/.DATA/AutoEngineerAI/docs/AGENT-RULES.md. Python 3 stdlib, žádné git operace.
"""Společné rozhraní `ChassisAdapter` (ARCHITECTURE §5.4) a datové typy.

Jádro systému (optimizer, testy, export) nesahá na konkrétní chassis přímo –
vše jde přes toto rozhraní. Nový chassis = nová třída + záznam v registru
(`C:/.DATA/AutoEngineerAI/src/Chassis/registry.py`).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


# Provenance mapování parametru (povinná hodnota u každého ParameterDef):
#   "measured"      – klíč i hodnota ověřeny auditem ([F] v A-CHASSIS-AUDIT.md),
#   "script-coded"  – hodnota zakódovaná ve skriptech mimo Tune (read-only),
#   "unknown"       – klíč/hodnota v auditu nepotvrzeny; NIKDY se nevymýšlejí.
PROVENANCE_VALUES = ("measured", "script-coded", "unknown")


@dataclass
class ParameterDef:
    """Jeden mapovatelný parametr adaptéru.

    `name`: orientační název v prostoru VehicleConfig (anglicky).
    `tune_key`: klíč v `A-Chassis Tune` ModuleScriptu, nebo None (mimo Tune).
    `config_path`: tečková cesta ve `VehicleConfig["parameters"]` (§3.3),
        např. "engine.horsepower". `None` = nelze reprezentovat bez masashema.
    `provenance`: jedna z PROVENANCE_VALUES.
    `mutable`: smí `apply_config` zapsat? False u script-coded/unknown.
    `default`: hodnota z auditu, nebo None (= unknown, nevymýšlet).
    `source_ref`: přesný odkaz do auditu, např. "A-CHASSIS-AUDIT.md §5".
    """

    name: str
    tune_key: str | None
    category: str
    config_path: str | None
    provenance: str
    mutable: bool
    default: object = None
    unit: str = ""
    source_ref: str = ""
    notes: str = ""
    read_only_reason: str = ""

    def __post_init__(self) -> None:
        if self.provenance not in PROVENANCE_VALUES:
            raise ValueError(f"neznámá provenance: {self.provenance!r}")
        if self.provenance in ("script-coded", "unknown") and self.mutable:
            raise ValueError(
                f"parametr {self.name!r}: provenance {self.provenance!r} "
                "nesmí být mutable"
            )
        if not self.mutable and not self.read_only_reason:
            raise ValueError(
                f"parametr {self.name!r}: read-only bez důvodu – doplň reason"
            )
        if self.provenance == "unknown" and self.default is not None:
            raise ValueError(
                f"parametr {self.name!r}: provenance unknown nesmí mít default "
                f"(měl {self.default!r}) – hodnoty se nevymýšlejí"
            )

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "tune_key": self.tune_key,
            "category": self.category,
            "config_path": self.config_path,
            "provenance": self.provenance,
            "mutable": self.mutable,
            "default": self.default,
            "unit": self.unit,
            "source_ref": self.source_ref,
            "notes": self.notes,
            "read_only_reason": self.read_only_reason,
        }


@dataclass
class PatchReport:
    """Výsledek `apply_config`. Modelová binárka se zde nikdy nemění."""

    adapter_id: str
    model_copy_dir: str
    applied: list[dict] = field(default_factory=list)
    rejected: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    touched_model_files: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "adapter_id": self.adapter_id,
            "model_copy_dir": self.model_copy_dir,
            "applied": self.applied,
            "rejected": self.rejected,
            "warnings": self.warnings,
            "touched_model_files": self.touched_model_files,
        }


class ChassisAdapter(ABC):
    """Rozhraní dle ARCHITECTURE §5.4. `config` = VehicleConfig dict (§3.3)."""

    id: str = "abstract"

    @abstractmethod
    def detect(self, model_copy_dir: str) -> float:
        """Jistota 0..1, že pracovní kopie patří tomuto chassis."""
        raise NotImplementedError

    @abstractmethod
    def list_parameters(self) -> list[ParameterDef]:
        """Mapování měnitelných i read-only parametrů vč. provenance."""
        raise NotImplementedError

    @abstractmethod
    def apply_config(self, model_copy_dir: str, config: dict) -> PatchReport:
        """Validuje a promítne Tune-měnitelné klíče z VehicleConfig.

        Read-only (script-coded) a unknown klíče odmítne s důvodem
        (záznam v `PatchReport.rejected`), nikdy je netiše nepřeskočí.
        """
        raise NotImplementedError

    @abstractmethod
    def limits(self) -> list[str]:
        """Známá omezení adaptéru (chyby kódu, neověřené hodnoty, limity)."""
        raise NotImplementedError
