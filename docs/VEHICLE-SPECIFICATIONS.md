# Vehicle Specifications – uzamčené cílové vozidlo

**Stav:** návrh v1 (hybridní režim, ke schválení).
**Vazba:** `docs/IMPLEMENTATION_ROADMAP.md` (M1), `vehicle-data/references/` (profil `ford-mustang-gt-2024-eu-manual-standard.json` — zatím NEEXISTUJE, vytvoří ho M1).
**Pravidla:** `docs/AGENT-RULES.md`, `AGENTS.md`. Česky; identifikátory anglicky.

---

## 1. Uzamčené první cílové vozidlo

| Pole | Hodnota |
|---|---|
| Značka / model | Ford Mustang GT 2024 (S650) |
| Trh | EU |
| Karoserie | Fastback |
| Převodovka | 6stupňový manuál |
| Výbava | Standardní GT, **bez Performance Packu** |
| `vehicle_id` (návrh) | `ford_mustang_gt_2024_eu_manual_standard` |

## 2. Technické údaje (před použitím ověřit proti zdrojům)

| Parametr | Hodnota | Stav |
|---|---|---|
| Motor | 5.0 Ti-VCT V8 | VERIFIED (zdroj [1]) |
| Zdvihový objem | 5 038 cm³ | VERIFIED (zdroj [1]) |
| Max. výkon | 328 kW / 446 PS při 7 250 rpm | VERIFIED (zdroj [1]) |
| Max. moment | 540 Nm při 5 100 rpm | VERIFIED (zdroj [1]) |
| Rozvor | 2 719 mm | VERIFIED (zdroj [1]) |
| Přední rozchod | 1 585 mm | VERIFIED (zdroj [1]) |
| Zadní rozchod | 1 642 mm | VERIFIED (zdroj [1]) |
| Délka | 4 810 mm | VERIFIED (zdroj [1]) |
| Šířka bez zrcátek | 1 916 mm | VERIFIED (zdroj [1]) |
| Výška Fastback | 1 394–1 414 mm | VERIFIED (rozmezí, zdroj [1]) |
| Pohotovostní hmotnost (manuál) | cca 1 808 kg, odhad výrobce | ESTIMATED |
| Přední pneumatiky | 255/40 R19 | VERIFIED (zdroj [1]) |
| Zadní pneumatiky | 275/40 R19 | VERIFIED (zdroj [1]) |
| Pohon | zadní kola | VERIFIED |
| Převodové poměry 1–6 + stálý převod | — | **UNKNOWN** (nevymýšlet) |
| Průběh momentové křivky (body rpm–Nm) | — | **UNKNOWN** (nevymýšlet; max. výkon/moment ≠ křivka) |
| Rozložení hmotnosti P/Z, výška těžiště | — | **UNKNOWN** |
| Brzdové kotouče P/Z, bias | — | **UNKNOWN** (standard GT ≠ Performance Pack) |
| 0–100 km/h, V-max (EU manuál) | — | **UNKNOWN** (nevymýšlet z US dat) |
| Cd / čelní plocha | — | **UNKNOWN** |

Nominální (nevýpočtové, nezatížené) průměry z označení pneumatik — geometrický výpočet, ne měření:
přední 255/40 R19 = **686,6 mm**, zadní 275/40 R19 = **702,6 mm** (`D = 19·25,4 + 2·W·A/100`).

## 3. Zdroje

1. Ford – 2024 Mustang EU Technical Specifications (PDF): `https://media.ford.com/content/dam/fordmedia/Europe/en/2024/01/NewMustang/2024_Ford_Mustang_technical_specification_EU.pdf`
2. Ford – New Ford Mustang is an Icon Reborn: `https://www.fromtheroad.ford.com/eur/en/articles/2024/new-ford-mustang-is-an-icon-reborn`
3. ADAC – Mustang GT Fastback 5.0 V8, manuál: `https://www.adac.de/rund-um-fahrzeug/autokatalog/marken-modelle/ford/mustang/2generation/332370/`

## 4. Pravidla variant

- Standardní GT a Performance Pack jsou **oddělené varianty** — brzdy, diferenciál a další komponenty Packu se nesmí přenášet do standardního GT.
- EU a US specifikace se nesmí míchat (výkon i výbava se liší).
- Každá hodnota VERIFIED musí mít zdroj; bez zdroje je hodnota ESTIMATED nebo UNKNOWN.
- Profil se ukládá jako `vehicle-data/references/ford-mustang-gt-2024-eu-manual-standard.json` dle `vehicle-data/references/_schema.json` (obálka `{value, unit, source, source_type, confidence}`); UNKNOWN = `value: null`.

## 5. Neověřené údaje k dořešení v M1

Převodové poměry, momentová křivka, rozložení hmotnosti, brzdy standardního GT, 0–100/V-max pro EU manuál, aerodynamika. Seznam je závazný vstup pro úkoly M1.5–M1.7 v `IMPLEMENTATION_ROADMAP.md`.
