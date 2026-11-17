# AutoEngineerAI – katalog parametrů A-Chassis (Agent A, FÁZE 4.1)
"""Katalog 125 parametrů adaptéru `achassis-v1` (docs/A-CHASSIS-PARAMETER-CATALOG.md).

Zmrazené rozhraní záznamu (19 polí) – neměnit bez koordinátora.
Načtení / validace / dotazy: `loader.py`.
"""
from __future__ import annotations

from src.Chassis.catalog.loader import (by_category, by_config_path,
                                        get_by_id, load, run_selftest,
                                        validate)

__all__ = ["load", "validate", "get_by_id", "by_category",
           "by_config_path", "run_selftest"]
