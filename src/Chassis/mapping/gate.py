# Brana S-02: jediny bezpecny vstup do mapovani (Agent B).
"""Spolecna brana katalogu pro vsechny verejne vstupni body mapovani.

Poradi (vzdy v tomto sledu, zadna paralelni validace, zadna cesta bez brany):
    nacteni katalogu -> struktura -> integrita -> detekce cyklu -> OK/BLOCKED.

Pri BLOCKED: zadna zmena cile, presny duvod, zadny castecny stav:
    - ``CYCLE: ...`` + ``witness_path`` (uzavrena cesta v grafu ``depends_on``),
    - ``INTEGRITY: ...`` + ``integrity_errors`` (hrana na neexistujici id),
    - ``INVALID: ...`` (katalog nelze nacist nebo ma neplatnou strukturu).

Implementace: tenky obal nad ``validate_catalog.py``
(``validate_catalog_for_mapping`` / ``validate_records_for_mapping``),
ktery je zdrojem verdiktu OK/BLOCKED; navic zachyti chyby nacteni
a struktury (``InvalidGraphError`` / ``OSError``) a prevede je na
BLOCKED/INVALID misto vyjimky, aby volajici mapovaci cesty nemusely
resit vyjimky a vzdy vracely atomicky (nulova zmena) vysledek.
Detektor ``cycle_check.py`` se nemeni, jen se pouziva.
Pouze stdlib, read-only ke katalogu.
"""

from __future__ import annotations

from .cycle_check import CycleCheckError, InvalidGraphError
from .validate_catalog import (
    STATUS_BLOCKED,
    STATUS_OK,
    MappingCatalogVerdict,
    validate_catalog_for_mapping,
    validate_records_for_mapping,
)

__all__ = [
    "STATUS_OK",
    "STATUS_BLOCKED",
    "REASON_INVALID",
    "MappingCatalogVerdict",
    "gate_catalog_file",
    "gate_catalog_records",
]

REASON_INVALID = "INVALID: katalog nelze nacist nebo ma neplatnou strukturu"


def _normalize_for_detector(records: list[dict]) -> list[dict]:
    """Projekce zaznamu na retezcove hrany pro detektor (katalog nemeni).

    ``mapping_engine`` podporuje v ``depends_on`` krome retezcu i
    strukturovane zavislosti ``{"param": <id>, "min"/"max"/"equals": ...}``
    (viz ``_check_depends``) — kazda takova je realnou hranou
    ``id -> param`` a musi vstoupit do detekce cyklu i integrity.
    Slovnikova podminka (min/max/equals) grafovou existenci hrany nemeni,
    proto se pro detektor pouzije jen cil ``param``. Neplatna polozka
    (slovnik bez ``param``, jiny typ) = INVALID.
    Chybejici ``depends_on`` / ``None`` = ``[]`` (shodne s ``_norm_entry``
    v ``mapping_engine``). Ciste retezcove katalogy (vcetne skutecneho
    ``parameters.json``) prochazeji beze zmeny.
    """
    if not isinstance(records, list):
        raise InvalidGraphError(
            "invalid catalog: ocekavan seznam zaznamu, "
            "nacten typ %s" % type(records).__name__
        )
    normalized: list[dict] = []
    for index, record in enumerate(records):
        where = "zaznam #%d" % index
        if not isinstance(record, dict):
            raise InvalidGraphError(
                "invalid catalog: %s neni dict" % where)
        param_id = record.get("id")
        if not isinstance(param_id, str) or not param_id:
            raise InvalidGraphError(
                "invalid catalog: %s ma neplatne id %r "
                "(ocekavan neprazdny retezec)" % (where, param_id))
        deps = record.get("depends_on", [])
        if deps is None:
            deps = []
        if not isinstance(deps, list):
            raise InvalidGraphError(
                "invalid catalog: %r ma depends_on typu %s, ocekavan list"
                % (param_id, type(deps).__name__))
        edges: list[str] = []
        for item in deps:
            if isinstance(item, str):
                edges.append(item)
            elif isinstance(item, dict) and isinstance(
                    item.get("param"), str) and item["param"]:
                edges.append(item["param"])
            else:
                raise InvalidGraphError(
                    "invalid catalog: %r ma v depends_on neplatnou polozku "
                    "%r (ocekavan retezec id nebo {'param': id, ...})"
                    % (param_id, item))
        normalized.append({"id": param_id, "depends_on": edges})
    return normalized


def _blocked_invalid(detail: str) -> MappingCatalogVerdict:
    """BLOCKED/INVALID verdikt (chyba nacteni nebo struktury, NE cyklus)."""
    return MappingCatalogVerdict(
        status=STATUS_BLOCKED,
        reason="%s (%s)" % (REASON_INVALID, detail),
        witness_path=[],
        integrity_errors=[],
    )


def gate_catalog_records(records: list[dict]) -> MappingCatalogVerdict:
    """Verdikt brany nad jiz nactenymi zaznamy (vstup se nemeni).

    Poradi: struktura -> integrita -> detekce cyklu -> OK/BLOCKED.
    Neplatna struktura = BLOCKED/INVALID (vyjimka se nepropaguje).
    Strukturovane zavislosti ``{'param': ...}`` se normalizuji na hrany
    (viz ``_normalize_for_detector``) a vstupuji do jedine pipeline.
    """
    try:
        return validate_records_for_mapping(_normalize_for_detector(records))
    except CycleCheckError as exc:
        return _blocked_invalid(str(exc))


def gate_catalog_file(path: str) -> MappingCatalogVerdict:
    """Verdikt brany nad souborem ``parameters.json`` (read-only).

    Poradi: nacteni -> struktura -> integrita -> detekce cyklu -> OK/BLOCKED.
    Chyba cteni/souboru = BLOCKED/INVALID (vyjimka se nepropaguje).
    """
    try:
        return validate_catalog_for_mapping(path)
    except CycleCheckError as exc:
        return _blocked_invalid(str(exc))
    except OSError as exc:
        return _blocked_invalid("soubor %r: %s" % (path, exc))
