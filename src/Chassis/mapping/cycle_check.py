# Detektor cyklu zavislosti katalogovych parametru (S-02, VARIANTA 1).
"""Detekce EXISTENCE cyklu v orientovanem grafu zavislosti (svedek, ne vypocet vsech cyklu).

Vrstvy (oddelene):
1. nacteni katalogu (``parameters.json``, pole ``depends_on``, klice ``id``),
2. validace struktury zaznamu,
3. stavba grafu ``A -> B`` (``A`` zavisi na ``B``),
4. kontrola integrity (neexistujici cil = chyba integrity, NE cyklus),
5. detekce cyklu (DFS WHITE/GRAY/BLACK, svedek),
6. vysledek (``has_cycle`` + ``witness_path`` + ``checked_nodes``/``checked_edges``).

Zdrojem pravdy je vzdy katalog. ``KNOWN_DEPENDS`` z ``dependencies.py``
je pouze pomocna reference (kryje ~1 % hran) a detektor na nem NIKDY
nezavisi jako na zdroji pravdy.

Vlastnosti:
- pouze stdlib, bez vedlejsich efektu (katalog se pri kontrole NEMENI),
- deterministicky vysledek (serazeni sousedi i vyber startovnich uzlu),
- svedek je UZAVRENA cesta: ``["a", "b", "a"]`` znamena ``a -> b -> a``,
  self-loop je ``["a", "a"]``; kazda po sobe jdouci dvojice je hrana grafu.
"""

from __future__ import annotations

import json
import warnings
from dataclasses import dataclass, field


# --- Chyby ---------------------------------------------------------------
# Kod anglicky, komentare cesky.


class CycleCheckError(ValueError):
    """Zakladni chyba kontroly cyklu (spatny vstup nebo integrita)."""


class InvalidGraphError(CycleCheckError):
    """Neplatny tvar grafu / zaznamu (typ, duplicitni id, nestringove hodnoty)."""


class UnknownDependencyError(CycleCheckError):
    """Hrana ukazuje na neexistujici cil (chyba integrity, NE cyklus)."""

    def __init__(self, source: str, target: str) -> None:
        self.source = source
        self.target = target
        super().__init__(
            f"integrity error: parameter {source!r} depends on "
            f"unknown target {target!r} (neni zadne id v katalogu)"
        )


# --- Vysledky ------------------------------------------------------------


@dataclass(frozen=True)
class CycleResult:
    """Vysledek detekce EXISTENCE cyklu (VARIANTA 1, ne vypocet vsech cyklu)."""

    has_cycle: bool
    # Uzavrena cesta svedka (prazdna kdyz cyklus neni); napr. ["a","b","a"].
    witness_path: list[str] = field(default_factory=list)
    checked_nodes: int = 0
    checked_edges: int = 0


@dataclass(frozen=True)
class CatalogCheckResult:
    """Vysledek plne kontroly katalogu (integrita + cyklus)."""

    has_cycle: bool
    witness_path: list[str] = field(default_factory=list)
    checked_nodes: int = 0
    checked_edges: int = 0
    # Seznam dvojic (source, missing_target); prazdny = integrita OK.
    integrity_errors: list[tuple[str, str]] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        """True jen kdyz neni chyba integrity ANI cyklus."""
        return not self.integrity_errors and not self.has_cycle


# --- Vrstva 1+2: nacteni a validace ---------------------------------------


def load_catalog_records(path: str) -> list[dict]:
    """Nacte zaznamy katalogu z ``parameters.json`` (read-only, katalog nemeni).

    Raises:
        InvalidGraphError: soubor neni JSON seznam zaznamu.
    """
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        raise InvalidGraphError(f"invalid catalog file {path!r}: {exc}") from exc
    if not isinstance(data, list):
        raise InvalidGraphError(
            f"invalid catalog file {path!r}: ocekavan seznam zaznamu, "
            f"nacten typ {type(data).__name__}"
        )
    return data


def validate_catalog_records(records: list[dict]) -> list[str]:
    """Zkontroluje strukturu zaznamu katalogu; vraci seznam id (poradi zachovano).

    Kazdy zaznam musi byt dict s retezcovym ``id`` a ``depends_on`` typu
    list retezcu (chybejici ``depends_on`` = prazdny seznam).
    Duplicitni ``id`` je chyba.

    Raises:
        InvalidGraphError: pri jakekoli vade struktury (s konkretnim popisem).
    """
    if not isinstance(records, list):
        raise InvalidGraphError(
            "invalid catalog: ocekavan seznam zaznamu, "
            f"nacten typ {type(records).__name__}"
        )
    seen: set[str] = set()
    ids: list[str] = []
    for index, record in enumerate(records):
        where = f"zaznam #{index}"
        if not isinstance(record, dict):
            raise InvalidGraphError(f"invalid catalog: {where} neni dict")
        param_id = record.get("id")
        if not isinstance(param_id, str) or not param_id:
            raise InvalidGraphError(
                f"invalid catalog: {where} ma neplatne id {param_id!r} "
                "(ocekavan neprazdny retezec)"
            )
        if param_id in seen:
            raise InvalidGraphError(
                f"duplicate id: {param_id!r} se v katalogu opakuje "
                f"(druhy vyskyt u zaznamu #{index})"
            )
        seen.add(param_id)
        ids.append(param_id)
        deps = record.get("depends_on", [])
        if not isinstance(deps, list):
            raise InvalidGraphError(
                f"invalid catalog: {param_id!r} ma depends_on typu "
                f"{type(deps).__name__}, ocekavan list"
            )
        for item in deps:
            if not isinstance(item, str):
                raise InvalidGraphError(
                    f"invalid catalog: {param_id!r} ma v depends_on "
                    f"neplatnou polozku {item!r} (ocekavan retezec id)"
                )
    return ids


# --- Vrstva 3: stavba grafu ----------------------------------------------


def build_graph_from_records(records: list[dict]) -> dict[str, list[str]]:
    """Postavi graf ``A -> B`` (``A`` zavisi na ``B``) ze zaznamu katalogu.

    Validuje strukturu (viz ``validate_catalog_records``), deduplikuje hrany
    a deterministicky radi sousedy. Kazde id je klicem (i bez hran).
    Katalog (vstupni seznam) se NEMENI.
    """
    ids = validate_catalog_records(records)
    graph: dict[str, list[str]] = {param_id: [] for param_id in ids}
    for record in records:
        param_id = record["id"]
        deps = record.get("depends_on", [])
        graph[param_id] = sorted(set(deps))
    return graph


def build_graph_from_catalog(path: str) -> dict[str, list[str]]:
    """Nacte ``parameters.json`` a vrati graf ``A -> B`` (katalog nemeni)."""
    return build_graph_from_records(load_catalog_records(path))


# --- Vrstva 4: kontrola integrity ----------------------------------------


def check_integrity(graph: dict[str, list[str]]) -> list[tuple[str, str]]:
    """Vrati seznam chyb integrity ``(source, missing_target)``.

    Neexistujici cil je CHYBA INTEGRITY, nikoli cyklus. Prazdny seznam = OK.
    Vstupni graf se nemeni; vysledek je deterministicky serazen.
    """
    _require_valid_graph(graph)
    nodes = set(graph)
    errors: list[tuple[str, str]] = []
    for source in sorted(graph):
        for target in sorted(set(graph[source])):
            if target not in nodes:
                errors.append((source, target))
    return errors


# --- Vrstva 5: detekce EXISTENCE cyklu ------------------------------------


def _require_valid_graph(graph: dict[str, list[str]]) -> None:
    """Overi tvar grafu ``dict[str, list[str]]``; pri vade hlasi druh chyby."""
    if not isinstance(graph, dict):
        raise InvalidGraphError(
            f"invalid graph: ocekavan dict, nacten typ {type(graph).__name__}"
        )
    for key, value in graph.items():
        if not isinstance(key, str):
            raise InvalidGraphError(
                f"invalid graph: uzel {key!r} neni retezec"
            )
        if not isinstance(value, list):
            raise InvalidGraphError(
                f"invalid graph: sousedi uzlu {key!r} nejsou list "
                f"(typ {type(value).__name__})"
            )
        for item in value:
            if not isinstance(item, str):
                raise InvalidGraphError(
                    f"invalid graph: hrana {key!r} -> {item!r}: "
                    "cil neni retezec"
                )


def find_witness(graph: dict[str, list[str]]) -> list[str] | None:
    """Najde SVEDKA existence cyklu (uzavrena cesta) nebo vrati None.

    Korektni DFS se tremi barvami: WHITE (nenavstiven), GRAY (na aktualni
    ceste v rekurzivnim zasobniku), BLACK (hotov, uz se nerozviji).
    Zpetna hrana na GRAY uzel = cyklus; vyrez cesty od prvniho vyskytu
    uzlu po vrchol zasobniku + uzaviraci uzel je platny svedek.
    BLACK uzly se nerozvijeji (vykon), ale detekce v aktualni ceste zustava
    korektni: kazdy hlaseny svedek je skutecny cyklus a kazdy dosazitelny
    cyklus je nalezen (existence, NE vypocet vsech cyklu).
    Deterministicke: serazeni uzly i sousede.
    """
    _require_valid_graph(graph)
    # Sjednoceni uzlu (i tech, ktere figuruji jen jako cile hran).
    nodes: set[str] = set(graph)
    for deps in graph.values():
        nodes.update(deps)
    adj: dict[str, list[str]] = {
        node: sorted(set(graph.get(node, []))) for node in nodes
    }

    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {node: WHITE for node in nodes}
    stack: list[str] = []
    witness: list[str] | None = None

    def dfs(node: str) -> bool:
        nonlocal witness
        color[node] = GRAY
        stack.append(node)
        for neighbour in adj[node]:
            if witness is not None:
                break
            if color[neighbour] == GRAY:
                # Zpetna hrana v aktualni ceste: skutecny cyklus.
                witness = stack[stack.index(neighbour):] + [neighbour]
                break
            if color[neighbour] == WHITE:
                if dfs(neighbour):
                    break
        stack.pop()
        color[node] = BLACK
        return witness is not None

    for node in sorted(nodes):
        if witness is not None:
            break
        if color[node] == WHITE:
            dfs(node)
    return witness


def has_cycle(graph: dict[str, list[str]]) -> CycleResult:
    """Rozhodne EXISTENCI cyklu a vrati vysledek se svedkem a statistikou.

    Returns:
        CycleResult(has_cycle, witness_path, checked_nodes, checked_edges).
        ``witness_path`` je uzavrena cesta (prazdna kdyz cyklus neni),
        ``checked_nodes``/``checked_edges`` je pocet uzlu / unikatnich hran
        grafu, nad kterym detekce bezela.
    """
    _require_valid_graph(graph)
    nodes: set[str] = set(graph)
    for deps in graph.values():
        nodes.update(deps)
    edge_count = sum(len(set(graph.get(node, []))) for node in nodes)
    witness = find_witness(graph)
    return CycleResult(
        has_cycle=witness is not None,
        witness_path=witness if witness is not None else [],
        checked_nodes=len(nodes),
        checked_edges=edge_count,
    )


# --- Vrstva 6: plna kontrola katalogu -------------------------------------


def check_catalog_records(records: list[dict]) -> CatalogCheckResult:
    """Plna kontrola zaznamu katalogu: integrita + existence cyklu.

    Poradi: nejprve integrita (neexistujici cil = chyba integrity, NE cyklus),
    pak detekce cyklu nad platnou casti grafu. Vstup se NEMENI.
    """
    graph = build_graph_from_records(records)
    integrity_errors = check_integrity(graph)
    if integrity_errors:
        # Pri chybe integrity cyklus nevyhodnocujeme (graf neni dobre definovan).
        nodes: set[str] = set(graph)
        for deps in graph.values():
            nodes.update(deps)
        edge_count = sum(len(set(graph.get(node, []))) for node in nodes)
        return CatalogCheckResult(
            has_cycle=False,
            witness_path=[],
            checked_nodes=len(nodes),
            checked_edges=edge_count,
            integrity_errors=integrity_errors,
        )
    result = has_cycle(graph)
    return CatalogCheckResult(
        has_cycle=result.has_cycle,
        witness_path=result.witness_path,
        checked_nodes=result.checked_nodes,
        checked_edges=result.checked_edges,
        integrity_errors=[],
    )


def check_catalog_file(path: str) -> CatalogCheckResult:
    """Plna kontrola souboru ``parameters.json`` (read-only)."""
    return check_catalog_records(load_catalog_records(path))


# --- Pomocna reference: KNOWN_* tabulky (NENI zdroj pravdy) ---------------


def build_known_graph() -> dict[str, list[str]]:
    """Sestavi graf z ``KNOWN_DEPENDS`` v dependencies.py (POUZE pomocna reference).

    NENI zdrojem pravdy (kryje ~1 % katalogovych hran). Slouzi jen jako
    minimalni priklad / selftest. ``KNOWN_CONFLICTS`` do orientovaneho grafu
    nevstupuji: konflikt je symetricka relace, ne usporadani — obousmerne
    hrany by hlasily falesne 2-cykly.
    """
    from .dependencies import KNOWN_CONFLICTS, KNOWN_DEPENDS

    _ = KNOWN_CONFLICTS  # nacteno zamerne, viz docstring
    graph: dict[str, list[str]] = {}
    for record in KNOWN_DEPENDS:
        param = record.get("param")
        if not isinstance(param, str):
            continue
        deps: list[str] = []
        depends_on = record.get("depends_on", [])
        if isinstance(depends_on, list):
            for item in depends_on:
                if isinstance(item, dict) and isinstance(item.get("param"), str):
                    deps.append(item["param"])
        graph.setdefault(param, [])
        for dep in deps:
            if dep not in graph[param]:
                graph[param].append(dep)
        graph.setdefault(param, graph.get(param, []))
    return graph


def check_known_tables() -> CycleResult:
    """Vrati vysledek detekce nad KNOWN_* tabulkami (ocekavano bez cyklu).

    Pomocna reference, NENI kontrola katalogu. Pro katalog pouzij
    ``check_catalog_file`` / ``check_catalog_records``.
    """
    return has_cycle(build_known_graph())


# --- DEPRECATED: slib "vsech cyklu" bez garance uplnosti ------------------


def find_cycles(graph: dict[str, list[str]]) -> list[list[str]]:
    """DEPRECATED: slibovala *vsechny* elementarni cykly bez garance uplnosti.

    Puvodni naivni DFS s BLACK-rezem totiz nektere cykly nenajde (staci
    prekryvajici se cykly), takze jmeno ``find_cycles`` klamalo.
    VARIANTA 1 garantuje jen EXISTENCI cyklu se svedkem — pouzij
    ``has_cycle()`` / ``find_witness()``. Tento wrapper vraci ``[svedek]``
    (bez uzaviraciho prvku, v historickem formatu) nebo ``[]``.
    """
    warnings.warn(
        "find_cycles() je DEPRECATED (negarantuje vsechny cykly); "
        "pouzij has_cycle() / find_witness()",
        DeprecationWarning,
        stacklevel=2,
    )
    witness = find_witness(graph)
    if witness is None:
        return []
    # Historicky format: bez opakujiciho se uzaviraciho prvku.
    return [witness[:-1]]
