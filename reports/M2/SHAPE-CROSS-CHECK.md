# M2 — Shape Cross-Check: lane-pořadí hypotézy (Agent D)

**Datum:** 2026-11-19 · **Větev:** `feat/m2-m3-geometry` (HEAD `8b30447`)
**Vlastník:** Agent D · **Soubor:** `reports/M2/SHAPE-CROSS-CHECK.md` (nový)
**Režim:** Studio read-only (search/inspect, Edit, bez Play, bez zápisu). Parser read-only.

## Verdikt: POTVRZENA

MSB-first mapování sedí na všech 4 ověřených instancích (3× Block + 1× Cylinder).
Současný parser (`_decode_enum_lanes`, lane0=LSB) dekóduje hodnoty 1/Block jako
`0x01000000 = 16777216` a 2/Cylinder jako `0x02000000 = 33554432` → `unread`.

## Důkazy

Pracovní kopie hash před/po: `dc8747e016e1402cce579e289881426ef8f78fbb4b10855acd7c070c2c1fefdf`
(230 421 B, shodný — G-01 drží). Parser census: 4× `Ball` (id 3/52/101/150, kola),
104× `unread 16777216`, 1× `unread 33554432` (id 801).

| Parser id | Name (parser) | Parser `props.shape` | Studio cesta | Studio `Shape` | Sedí MSB? |
|---|---|---|---|---|---|
| 9 | `SpringBottom` (Part) | unread 16777216 (=0x01000000 → MSB 1 = Block) | `ServerStorage.VehicleTemplates.JeepTemplate.Wheels.FL.SuspensionGeometry.SpringBottom` | `Enum.PartType.Block` (Size 0.25,0.25,0.25) | ANO |
| 14 | `CLower` (Part) | unread 16777216 (→ MSB 1 = Block) | `…Wheels.FL.SuspensionGeometry.Weld.CLower` | `Enum.PartType.Block` (Size 0.5,0.5,1) | ANO |
| 17 | `CUpper` (Part) | unread 16777216 (→ MSB 1 = Block) | `…Wheels.FL.SuspensionGeometry.Weld.CUpper` | `Enum.PartType.Block` (Size 0.5,0.5,1) | ANO |
| 801 | `Collision_BackWheel` (Part) | unread 33554432 (=0x02000000 → MSB 2 = Cylinder) | `ServerStorage.VehicleTemplates.JeepTemplate.CollisionParts.Collision_BackWheel` | `Enum.PartType.Cylinder` | ANO |

Vizuální tvar: názvy + Size konzistentní (kvádry podvozku vs válec kolizního dílu);
`Shape` čteno přímo z vlastností instancí (authoritative, ne vizuální odhad).
Kola `Ball` (id 3/52/101/150) invariantní vůči pořadí lane — nedotčena.

## Mapování

- LSB-first (současný kód): 1 → 16777216 (unread), 2 → 33554432 (unread). Špatně.
- MSB-first (hypotéza): lane0 je MSB → 0x01000000 >> 24 = 1 = Block; 0x02000000 >> 24 = 2 = Cylinder. Správně, potvrzeno 4/4.

## Dopad / další krok

- N1 (z `RBXM-INSPECTOR-REPORT.md` §6) je tímto uzavřen jako potvrzená chyba dekodéru,
  nikoli dokumentace: `_decode_enum_lanes` přepnout na MSB-first + re-verifikace
  (104× Block, 1× Cylinder musí přejít do `read`; kola Ball beze změny).
- Neopravuji (cizí kód, role D je cross-check). Předáno koordinátorovi / Agentu A.
- Studio: pouze `search_game_tree` + `inspect_instance` na výše uvedených cestách;
  nic se neměnilo, Play se neotevíral.
