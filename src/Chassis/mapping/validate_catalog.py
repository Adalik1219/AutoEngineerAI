# Tenka integrace kontroly katalogu do validacni cesty mapovani (S-02, Agent C).
"""Verdikt katalogu pro mapovani: OK vs BLOCKED.

Obal nad ``check_catalog_file`` / ``check_catalog_records`` z
``cycle_check.py`` (zdroj pravdy se nemeni, jen se pridava branici
verdikt pro volajiciho mapovani):

- cyklus v ``depends_on`` -> ``BLOCKED`` s konkretnim svedkem (cesta),
- chyba integrity (hrana na neexistujici id) -> ``BLOCKED`` s JINYM
  duvodem nez cyklus (integrita, NE cyklus),
- jinak -> ``OK``.

Format katalogu: ``parameters.json`` = list zaznamu ``{id, depends_on}``
(stejne jako ``cycle_check``). Pouze stdlib, read-only ke katalogu.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .cycle_check import check_catalog_file, check_catalog_records

STATUS_OK = "OK"
STATUS_BLOCKED = "BLOCKED"

REASON_OK = "OK: katalog bez cyklu a bez chyb integrity"
REASON_CYCLE = "CYCLE: katalog obsahuje cyklus depends_on"
REASON_INTEGRITY = "INTEGRITY: katalog obsahuje odkazy na neexistujici id"


@dataclass(frozen=True)
class MappingCatalogVerdict:
    """Branici verdikt katalogu pro mapovaci cestu."""

    status: str  # STATUS_OK | STATUS_BLOCKED
    reason: str  # lidsky duvod; prefix OK: / CYCLE: / INTEGRITY:
    witness_path: list[str] = field(default_factory=list)
    integrity_errors: list[tuple[str, str]] = field(default_factory=list)

    @property
    def allowed(self) -> bool:
        """True jen kdyz mapovani smi pokracovat (status == OK)."""
        return self.status == STATUS_OK


def _verdict_from(has_cycle: bool, witness: list[str],
                  errors: list[tuple[str, str]]) -> MappingCatalogVerdict:
    if errors:
        detail = ", ".join("%s -> %s" % (s, t) for s, t in errors)
        return MappingCatalogVerdict(
            status=STATUS_BLOCKED,
            reason="%s (%s)" % (REASON_INTEGRITY, detail),
            witness_path=[],
            integrity_errors=list(errors),
        )
    if has_cycle:
        return MappingCatalogVerdict(
            status=STATUS_BLOCKED,
            reason="%s (%s)" % (REASON_CYCLE, " -> ".join(witness)),
            witness_path=list(witness),
            integrity_errors=[],
        )
    return MappingCatalogVerdict(status=STATUS_OK, reason=REASON_OK)


def validate_catalog_for_mapping(path: str) -> MappingCatalogVerdict:
    """Zkontroluje ``parameters.json`` pro mapovaci cestu (read-only).

    Vraci ``MappingCatalogVerdict``: ``OK`` (lze mapovat) nebo
    ``BLOCKED`` (cyklus / integrita + duvod + svedek).
    """
    result = check_catalog_file(path)
    return _verdict_from(result.has_cycle, result.witness_path,
                         result.integrity_errors)


def validate_records_for_mapping(records: list[dict]) -> MappingCatalogVerdict:
    """Stejny verdikt nad jiz nactenymi zaznamy katalogu (vstup se nemeni)."""
    result = check_catalog_records(records)
    return _verdict_from(result.has_cycle, result.witness_path,
                         result.integrity_errors)
