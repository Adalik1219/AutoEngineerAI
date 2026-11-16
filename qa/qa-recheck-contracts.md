# QA re-check — kontrakty / data (opravy 1–3 z qa-contracts-data.md)

**Vlastněný soubor:** `qa/qa-recheck-contracts.md` · **Datum:** 2026-11-16 · **Jazyk:** česky
**Rozsah:** re-check oprav 1–3, READ-ONLY vše mimo tento soubor (žádné git operace).
**Metoda:** vlastní běh `python tools/validate_contracts.py` + vlastní walk všech `valued` záznamů (stdlib `json`) + spot-check profilů.

## 1. Oprava č. 2 — schéma vynucuje `null ⇒ confidence: 0` — OVĚŘENO

- `contracts/reference_profile.schema.json:48-70` — `$defs.proven` nově obsahuje `allOf/anyOf`:
  `value: null ⇒ confidence: const 0`, jinak číslo/řetězec; `$comment: proven-null-confidence-0`.
- Vlastní běh validatoru: `python tools/validate_contracts.py` → **23/23 OK, 0 chyb**,
  včetně `reference_profile: null+0.5 správně zamítnut (2 chyb)` a `null+0 prošel`.
  (Vlastní přímé volání `validate_against_schema` mimo selftest selhalo na signatuře API,
  nikoli na datech — není vadou produktu; autoritativní je běh selftestu.)

## 2. Oprava č. 1 — profily: `null` vždy s `confidence: 0`, 9 examples VALID — OVĚŘENO

- Vlastní walk všech 3 profilů (`example-vehicle`, `honda-civic-fk8`, `toyota-gr86`):
  **23 záznamů `value: null`, 0× `confidence ≠ 0`** (dříve 4 + 10 + 9 × `0.2`).
- Selftest: `example-vehicle + civic + gr86 → [OK]`, všech **9 `*.valid.json` prošlo**.
- Spot-check `example-vehicle.json`: `yaw_inertia null/conf 0`, `drag_coefficient_cd null/conf 0`,
  `redline_rpm 7500/conf 0.9` — bez závad.

## 3. Oprava č. 3 — `pbrake_bias` je `_u` — OVĚŘENO

- `src/Chassis/adapters/achassis_v1.py:357` — `_u("pbrake_bias", "Bias(PBrake)?", …)`:
  název s otazníkem + důvod „Název klíče audit nepotvrzuje — do ověření ve Studiu read-only.
  Hodnota 0 ověřena ('Bias=0'); název je kvalifikovaný odhad (QA vlna 2).“ — požadavek splněn.

## 4. Škála VEHICLE-DATA sladěna s ARCH §3.2 — OVĚŘENO

- `docs/VEHICLE-DATA.md §3.2, ř. 74`: `0.0 | Neznámé / null; null ⇒ vždy confidence: 0
  (ARCH §3.2, strojně vynuceno schématem)` — pásmo `0.0–0.2 = neznámé` je pryč.

## Verdikt: PASS

Všechny 3 opravy ověřeny vlastním během validatoru a čtením zdrojů.

## Zbytkové vady (1, kosmetická)

- R1: `docs/VEHICLE-DATA.md §6 bod 1 (ř. 105)` stále říká
  „`value: null` + … + **nízká confidence**“ místo přesného „`confidence: 0`“.
  Věcně neškodné (§3.2 je jednoznačný a schéma to vynucuje), doporučeno sjednotit formulaci.
