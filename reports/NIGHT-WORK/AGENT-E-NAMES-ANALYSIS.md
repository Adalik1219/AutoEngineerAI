# Agent E-NAMES — analýza názvů a aliasů (Fáze 1/6)
Vlastník: subagent E-NAMES · Datum: 2026-11-20 · Větev: fix/normalization-evidence-integrity · read-only

## Ověřené vztahy (L52/L152/L173, `weight_lb`, `clutch_enabled`, `rev_decay`, `downforce_f`)
- `logical_id` = řetězec z buňky Interní ID po rozbalení R2 (běžný řádek 1:1, např. `` `weight_lb` ``).
- Běžný záznam: `primary_name` = Název (`weight_lb`→`Weight`), `aliases`=[].
- Skupina: `primary_name`=ID, původní Název v `aliases` (`rev_decay`→`["RevDecay","RevAccel/Decay/Bounce"]`, `clutch_enabled`→`["Clutch","Clutch…"]`).
- Alias = Název/Tune klíč; `tune_key` katalogu se s `aliases` dříve neporovnával vůbec.
- Pokrytí (před opravou): R3-kontrola pro všech 94 ID; R6-kontrola jen pro členy skupin s katalogovým ID.

## Mezery (před opravou)
R6-c (běžný `primary_name`=Název) chybí; R6-d (cizí alias u běžného) chybí; R6-e (alias=právě Název+tune) chybí; `tune_key` vs `aliases` neporovnáno; duplicitní aliasy neřešeny. Audit (řádky 52–59) definuje R3/R6 správně — mezery byly jen ve validátoru, ne v datech.

## Úplná logika (předáno Agentu E, implementováno)
Běžný řádek: `primary_name == Název` (testy 30, 36-regrese); každý alias = Název vlastního řádku NEBO vlastní `tune_key` (testy 31, 32, 33); žádný alias není katalogové ID (34) ani cizí `tune_key` (35); duplicitní alias jen u sourozenců sdíleného řádku (`Clutch…`, `RevAccel/Decay/Bounce`); placeholder `—` se nepočítá jako kolize (sdílený Název-placeholder `downforce_f/r`, `wear_speed`, `wheel_lock_ratio`, `wheelspin_ratio`). `tune_key` jiného parametru jako `logical_id` → `alias-jako-ID` (37).
