# Agent C — adversariální testy validátoru (Fáze 9)
Vlastník: Agent C · Datum: 2026-11-20 · Větev: fix/normalization-evidence-integrity · HEAD: 72c16c278f2d7555fe17afd8354e744a6d04d8c1

## Orákulum (neopakuje logiku validátoru)
Pristine `normalized_ids.json` → `fails=[]` + PENDING (ORIGINAL_60, ACCEPTED, 4× ESTIMATED-k-revizi), exit 2. Negativní mutace = deepcopy + právě 1 změna → očekávaný FAIL + klíč, exit 1 (resp. PENDING, exit 2 u review-testů 44/45). Revert → opět exit 2 (citlivost + specificita ověřena každým testem).

## Pokrytí: 51 testů (14 původních + 37 nových), všechny procházejí
- E1 (testy 15–20 + 01/02/10/11): cizí řádek, `[True]`, duplicita `[52,52]`, řádek bez ID, chybějící člen skupiny, ID bez opory, prázdné rows.
- R7 (21–24 + 07): prohození `drive_config↔differential_type`, chybný status 1 ID, status člena skupiny, konstatování absence multi-`source_rows` + divergentní fixture.
- R8 (25–29 + 09): F/R sloučení, chybějící člen, L/R chybějící člen (dočasný pár), falešné spárování (`front_diff_power` → žádný R8 FAIL, jen E1/R2), správné oddělení 12 párů.
- R3/R6 (30–37 + 03): `primary_name` běžného, cizí alias běžného, Název chybí v aliases, prázdné aliases člena, alias=cizí ID, cizí tune_key, `primary_name` člena≠ID, cizí tune jako ID.
- E3 (38–45 + 08): VERIFIED `xxx`/bez hodnoty/bez lokátoru/`puvod=odhad`, ESTIMATED bez původu/bez zdroje, slabý původ→PENDING, UNKNOWN s konkrétním cílem→PENDING.
- 60/94 (46–51 + 12): 60 z 94→FAIL, 59→FAIL, APPROVED-ok (strukturálně, 60 zůstává PENDING), špatné sha→FAIL, chybějící ID→FAIL, změna dat po schválení→FAIL.

## 12 sabotážních mutací S1–S12 (mapování na testy)
S1 prohození statusů→21; S2 60 z 94→46; S3 falešný alias (`Weight` jako ID)→03; S4 primary_name→36; S5 F/R sloučení→25; S6 L/R sloučení→27 (syntetický pár); S7 falešný důkaz→38/08; S8 blob SHA→10; S9 zdrojový řádek→01/19; S10 člen skupiny→05/18; S11 status člena→23; S12 změna po schválení→51. Každá: FAIL (resp. PENDING u review) s očekávaným klíčem; revert čistý.

## Verdikt Agenta C
Všech 51 testů prochází; každá sabotáž je odmítnuta konkrétní kontrolou. Testy nejsou opakováním logiky validátoru (black-box deepcopy-orákulum). Nezávislou QA s vlastními mutacemi provádí Agent G.
