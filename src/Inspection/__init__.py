"""Balíček Inspection (M2 – RBXM Inspector & Scale Calibration).

Obsahuje rozhodovací pravidlo pro identifikaci kol (wheel_detect.py)
dle docs/IMPLEMENTATION_ROADMAP.md sekce M2 a produkční RBXM parser
(rbxm_parser.py: INST + PRNT + SSTR/META/Name + Shape/Size/CFrame
s provenancí; geometrie BLOCKED do Studio ground-truth).
"""

from src.Inspection.rbxm_parser import (
    NULL_PARENT,
    RbxmCorruptError,
    RbxmError,
    RbxmHierarchyError,
    lz4_decompress,
    parse_bytes,
    parse_rbxm,
)
from src.Inspection.wheel_detect import (
    INSPECTION_REPORT_SCHEMA,
    WHEEL_DESIGNATIONS,
    WHEEL_SHAPE,
    WHEELS_MODEL_NAME,
    HierarchyError,
    MissingParentError,
    ParentCycleError,
    classify_candidate,
    detect_wheels,
    is_blocked,
    is_in_wheels,
)

__all__ = [
    "INSPECTION_REPORT_SCHEMA",
    "NULL_PARENT",
    "RbxmCorruptError",
    "RbxmError",
    "RbxmHierarchyError",
    "WHEEL_DESIGNATIONS",
    "WHEEL_SHAPE",
    "WHEELS_MODEL_NAME",
    "HierarchyError",
    "MissingParentError",
    "ParentCycleError",
    "classify_candidate",
    "detect_wheels",
    "is_blocked",
    "is_in_wheels",
    "lz4_decompress",
    "parse_bytes",
    "parse_rbxm",
]
