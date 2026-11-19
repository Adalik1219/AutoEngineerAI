# Vehicle Specifications – uzamčené cílové vozidlo

**Stav:** návrh v2 (hybridní režim, ke schválení) — povýšení M1.5 + přejmenování varianty 2026-11-19.
**Vazba:** `docs/IMPLEMENTATION_ROADMAP.md` (M1), `vehicle-data/references/` (profil `ford-mustang-gt-2024-eu-manual-standard.json`).
**Pravidla:** `docs/AGENT-RULES.md`, `AGENTS.md`. Česky; identifikátory anglicky.

---

## 1. Uzamčené první cílové vozidlo

| Pole | Hodnota |
|---|---|
| Značka / model | Ford Mustang GT 2024 (S650) |
| Trh | EU |
| Karoserie | Fastback |
| Převodovka | 6stupňový manuál Getrag MT-82 |
| Výbava | **EUROPEAN FACTORY STANDARD SPECIFICATION** (EU GT; Performance Pack je standardem EU GT — není samostatná varianta) |
| `vehicle_id` (stabilní, nemění se) | `ford-mustang-gt-2024-eu-manual-standard` |

**Historie názvu varianty (2026-11-19, rozhodnutí uživatele):** do 2026-11-19 se varianta
jmenovala „standardní GT bez Performance Packu“ (US logika oddělených variant). EU logika:
prvky Packu (Brembo, LSD) jsou standardem EU GT — varianta přejmenována na
EUROPEAN FACTORY STANDARD SPECIFICATION. Přejmenování do `trim` + `notes` profilu
(+ `meta.updated`); `vehicle_id` (kebab-case, stabilní ID) beze změny.

## 2. Technické údaje (ověřeno proti [1]/[1b]/[3] v M1.5; podklad `reports/MUSTANG-SOURCE-CHECK.md`)

| Parametr | Hodnota | Stav |
|---|---|---|
| Motor | 5.0 Ti-VCT V8 | VERIFIED [1] |
| Zdvihový objem | 5 038 cm³ | VERIFIED [1] |
| Max. výkon | 328 kW / 446 PS při 7 250 rpm | VERIFIED [1] |
| Max. moment | 540 Nm při 5 100 rpm | VERIFIED [1] |
| Rozvor | 2 719 mm | VERIFIED [1] |
| Přední rozchod | 1 585 mm | VERIFIED [1] (nezaměnit s Dark Horse 1 595) |
| Zadní rozchod | 1 642 mm | VERIFIED [1] (nezaměnit s Dark Horse 1 643) |
| Délka | 4 810 mm | VERIFIED [1] |
| Šířka bez zrcátek / se zrcátky | 1 916 / 2 080 mm | VERIFIED [1] |
| Výška Fastback | 1 394–1 414 mm | VERIFIED [1] (rozmezí; [3] 1 404 uvnitř) |
| Pohotovostní hmotnost (manuál) | cca 1 808 kg, odhad výrobce | ESTIMATED (Ford uvádí „Est.“) [1] |
| Kola přední / zadní | 19x9.0J / 19x9.5J | VERIFIED [1] |
| Přední pneumatiky | 255/40 R19 | VERIFIED [1] |
| Zadní pneumatiky | 275/40 R19 | VERIFIED [1] |
| Pohon | zadní kola (RWD), LSD | VERIFIED obecně [1] (typ/převod UNKNOWN — viz níže) |
| Převodovka | 6MT Getrag MT-82 s rev-matching | VERIFIED [1] |
| Převodové poměry 1–6 | 3.237 / 2.104 / 1.422 / 1.000 / 0.814 / 0.622 | VERIFIED [1] (factory, confidence 0.9) |
| Stálý převod | — | **UNKNOWN** (kandidáti 3.15:1 / 3.55:1 bez přiřazení k EU 6MT; GUARD: nepoužívat pro M3/M4) |
| Diferenciál zadní | limited-slip differential (LSD) | VERIFIED obecně [1]; přesný typ/převod **UNKNOWN** (není automaticky Torsen — ten patří Dark Horse) |
| Brzdové kotouče P/Z | 390x36 mm / 355x28 mm ventilované | VERIFIED [1] (EU factory standard) |
| Třmeny | vpředu Brembo six-piston 36 mm, vzadu four-piston 30 mm | VERIFIED [1] (Brembo je EU standard, ne Pack) |
| Rozdělení brzdného účinku P/Z, bias | — | **UNKNOWN** (v [1b]/[2]/[3] nepublikován) |
| 0–100 km/h (EU manuál) | 5,3 s | VERIFIED [1] (+ [3]) |
| V-max (EU manuál) | 250 km/h | VERIFIED [1] (+ [3]) |
| Průběh momentové křivky (body rpm–Nm) | — | **UNKNOWN** (nevymýšlet; max. výkon/moment ≠ křivka) |
| Rozložení hmotnosti P/Z, výška těžiště | — | **UNKNOWN** |
| Cd / čelní plocha | — | **UNKNOWN** |

Nominální (nevýpočtové, nezatížené) průměry z označení pneumatik — geometrický výpočet, ne měření:
přední 255/40 R19 = **686,6 mm**, zadní 275/40 R19 = **702,6 mm** (`D = 19·25,4 + 2·W·A/100`).

## 2a. Co znamená „Dle zadání“ a co VERIFIED

„Dle zadání“ = hodnota převzatá z uzamčeného zadání projektu, **nikoli nezávisle ověřený fakt**
(původní stav návrhu v1). Status `VERIFIED` (M1.5, 2026-11-19) smí nést jen hodnota s továrním
zdrojem [1]/[1b] (obálka `{value, unit, source, source_type: factory, confidence ≥ 0.8, notes}`).
Konzistence maxima již zkontrolována:
540 Nm @ 5 100 rpm → 288,4 kW < 328 kW maxima (maximum při 7 250 rpm, moment ≈ 432 Nm) — bez rozporu.

## 3. Zdroje

1. Ford – 2024 Mustang EU Technical Specifications (PDF): `https://media.ford.com/content/dam/fordmedia/Europe/en/2024/01/NewMustang/2024_Ford_Mustang_technical_specification_EU.pdf`
   (mirror [1b], ověřeno 2026-11-19: `https://www.fromtheroad.ford.com/content/dam/fordmediasite/eur/en/library/2024/tech-specs/2024_Ford_Mustang_tech_spec_EU.pdf`)
2. Ford – New Ford Mustang is an Icon Reborn: `https://www.fromtheroad.ford.com/eur/en/articles/2024/new-ford-mustang-is-an-icon-reborn`
3. ADAC – Mustang GT Fastback 5.0 V8, manuál: `https://www.adac.de/rund-ums-fahrzeug/autokatalog/marken-modelle/ford/mustang/2generation/332370/`

## 4. Pravidla variant

- Cílová varianta je **EUROPEAN FACTORY STANDARD SPECIFICATION** — Brembo, LSD a další prvky
  dříve řazené k Performance Packu jsou standardem EU GT a patří do EU profilu.
- **Žádné US varianty do EU profilu:** Tremec TR-3160, Torsen jako výbava Dark Horse, výkon
  Dark Horse 453 PS ani jiné US komponenty se nesmí dostat do EU profilu (test T18).
- EU a US specifikace se nesmí míchat (výkon i výbava se liší).
- Každá hodnota VERIFIED musí mít zdroj s URL a datem ověření; bez zdroje je hodnota ESTIMATED nebo UNKNOWN.
- Profil se ukládá jako `vehicle-data/references/ford-mustang-gt-2024-eu-manual-standard.json` dle `vehicle-data/references/_schema.json` (obálka `{value, unit, source, source_type, confidence, notes}`); UNKNOWN = `value: null` + prefix `CHYBÍ:`, odhad = prefix `ODHAD:`.
- Stálý převod UNKNOWN se nesmí použít jako definitivní hodnota (GUARD test T17 — použití → chyba).

## 5. Neověřené údaje k dořešení v M1

Momentová křivka, rozložení hmotnosti + výška těžiště, brzdový bias, Cd/plocha, stálý převod
EU 6MT (kandidáti 3.15:1 / 3.55:1 — ověřit konfigurátorem Ford CZ/DE nebo workshop daty S650).
Seznam je závazný vstup pro úkoly M1.5–M1.7 v `IMPLEMENTATION_ROADMAP.md`.
