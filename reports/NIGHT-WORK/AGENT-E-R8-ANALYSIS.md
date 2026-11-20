# Agent E-R8 — analýza F/R a L/R párů (Fáze 1/5)
Vlastník: subagent E-R8 · Datum: 2026-11-20 · Větev: fix/normalization-evidence-integrity · read-only, katalog neměněn

## Autoritativní definice R8
F/R a L/R páry jsou odlišné parametry (odlišné Tune klíče) — neslučují se podle podobnosti. Úplnost dvojice se vynucuje jen je-li doložena zdrojem.

## Doložené F/R dvojice (12; všechny `_f`/`_r`)
anchor_offset, compress_lim, damper, diff_preload, downforce (1 sdílený řádek 173; tune_key null, odlišné skriptové konstanty F=125/R=150), extension_lim, lock_thresh (+`_c` trojice), pre_compress, slip_thresh (+`_c`), sus_angle, sus_length, sus_stiffness. Důkaz: odlišné `tune_key` v `src/Chassis/catalog/parameters.json` + zdrojové řádky (91/92, 87/88, 79/80, 164/165, 173, 85/86, 166, 83/84, 166, 89/90, 81/82, 77/78).
**L/R: 0 výskytů** `_l`/`left` v 94 ID i ve 138 katalogových ID — R8-L/R je prázdná množina, kontrolní větev připravena.

## Ne-páry (pouhá podobnost názvů)
`front_diff_power/coast` vs `rear_diff_power/rear_diff_coast` (osy předek/zadek × power/coast), `slip_*` vs `lock_*` (slip×lock), `brake_bias_front` singleton bez protějšku.

## Mezery implementace (před opravou)
Jen `_f`/`_r` suffix-pravidlo; L/R chybí; automatický předpoklad protějšku (singleton s legitimní příponou = false FAIL; sloučenina bez suffixu projde); neověřuje distinct `tune_key`; neřeší trio F/R/C.

## Navržená kontrola (předáno Agentu E, implementováno)
Explicitní párová tabulka `FR_PAIRS` (12) + `LR_PAIRS` ([]) odvozená z katalogu. FAIL: chybí člen páru / sloučený kmen (`downforce`) / členové sdílí stejný ne-null `tune_key`. Žádné generické `endswith(_f/_r/_l)`; nové páry jen doloženým zápisem.

## Testy (5)
F/R sloučení → FAIL; chybějící člen → FAIL; L/R chybějící člen (syntetický pár, dočasný `LR_PAIRS`) → FAIL; falešné spárování (`front_diff_power`) → žádný R8 FAIL, jen E1/R2; všech 12 odděleně → bez R8 FAIL.
