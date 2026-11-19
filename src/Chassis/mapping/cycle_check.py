# Detektor cyklu zavislosti katalogovych parametru (S-02).
"""Ciste funkce pro detekci cyklu v orientovanem grafu zavislosti.

Graf: ``dict[str, list[str]]`` — klic je parametr (config_path),
hodnota je seznam parametru, na kterych primo zavisi
(hrana ``param -> dep``).

Vlastnosti:
- pouze stdlib, bez vedlejsich efektu,
- deterministicky vysledek (serazeni sousedi i vystupu),
- cykly kanonizovane rotaci na lexikograficky nejmensi prvek.
"""

from __future__ import annotations


def _canonical(cycle: list[str]) -> tuple[str, ...]:
    """Otočí cyklus tak, aby začínal lexikograficky nejmenším prvkem."""
    # cyklus nesmí obsahovat opakující se uzavírací prvek
    idx = min(range(len(cycle)), key=lambda i: cycle[i])
    return tuple(cycle[idx:] + cycle[:idx])


def find_cycles(graph: dict[str, list[str]]) -> list[list[str]]:
    """Najde všechny elementární cykly orientovaného grafu (DFS).

    Args:
        graph: mapování uzel -> seznam přímých závislostí.

    Returns:
        Seznam cyklů; každý cyklus je seznam uzlů bez opakujícího
        se uzavíracího prvku (např. ``["a", "b"]`` znamená
        ``a -> b -> a``, ``["a"]`` je self-loop). Seznam je
        deterministicky seřazený, duplicity odstraněny.
    """
    # Sjednocení všech uzlů (i těch, které figurují jen jako sousedé).
    nodes: set[str] = set(graph)
    for deps in graph.values():
        nodes.update(deps)
    # Deterministické pořadí: seřazení sousedé.
    adj: dict[str, list[str]] = {
        node: sorted(graph.get(node, [])) for node in nodes
    }

    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {node: WHITE for node in nodes}
    stack: list[str] = []
    found: set[tuple[str, ...]] = set()

    def dfs(node: str) -> None:
        color[node] = GRAY
        stack.append(node)
        for neighbour in adj[node]:
            if color[neighbour] == GRAY:
                # Zpětná hrana: cyklus od prvního výskytu sousede po vrchol zásobníku.
                raw = stack[stack.index(neighbour):]
                found.add(_canonical(list(raw)))
            elif color[neighbour] == WHITE:
                dfs(neighbour)
        stack.pop()
        color[node] = BLACK

    for node in sorted(nodes):
        if color[node] == WHITE:
            dfs(node)

    return [list(cycle) for cycle in sorted(found)]


def build_known_graph() -> dict[str, list[str]]:
    """Sestaví graf závislostí ze známých tabulek v dependencies.py.

    Hrany vede pouze ``KNOWN_DEPENDS`` (``param -> depends_on.param``).
    ``KNOWN_CONFLICTS`` se načte také (požadavek S-02), ale do
    orientovaného grafu nevstupuje: konflikt je symetrická relace,
    nikoli uspořádání — obousměrné hrany by hlásily falešné 2-cykly.
    """
    from .dependencies import KNOWN_CONFLICTS, KNOWN_DEPENDS

    _ = KNOWN_CONFLICTS  # načteno záměrně, viz docstring
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


def check_known_tables() -> list[list[str]]:
    """Vrátí cykly v KNOWN_* tabulkách z dependencies.py (očekáváno 0)."""
    return find_cycles(build_known_graph())
