# Agent A — Katalog: přesná klasifikace 12 SCC + návrh nápravy (BEZ změn dat)

- Repo: `C:/.DATA/AutoEngineerAI`, větev `feat/m2-m3-geometry`, HEAD `557ee39` (strom čistý, ověřeno `git status`)
- Zdroj: `src/Chassis/catalog/parameters.json` (čteno, NEMĚNĚNO)
- Vstup: `reports/NIGHT-WORK/AGENT-A-S02-CATALOG-AUDIT.md` (vše přepočítáno znovu, neopsáno)
- Datum: 2026-11-20. Jazyk: čeština; identifikátory/kód anglicky.
- Konvence: **`A -> B` = `A` má v `depends_on` uveden `B`, tj. `A` závisí na `B`.** `A ! B` = symetrický konflikt.
- Tento dokument NEMĚNÍ žádná data. Obsahuje pouze návrhy. Katalog `parameters.json` zůstal nedotčen (ověřeno `git status --short`: žádná modifikace).

## 1. Potvrzená čísla (přepočítáno z dat)

| Metrika | Hodnota |
|---|---|
| Parametrů v katalogu | **138** (id unikátních 138, duplicity 0) |
| Orientovaných hran `depends_on` | **101** |
| Neplatných cílů `depends_on` | **0** |
| Self-loopů / duplicitních hran `depends_on` | **0 / 0** |
| Záznamů `conflicts` | **24** od 20 parametrů |
| Neplatných cílů `conflicts` | **5** (5 unikátních cílů) |
| SCC velikosti > 1 (Tarjan) | **12** |
| Jednoduchých orientovaných cyklů (Johnson) | **20** (19× 2-cyklus + 1× 3-cyklus) |
| Případů `depends_on` + `conflicts` na téže dvojici | **12** |

## 2. SCC ≠ cyklus (povinné rozlišení)

- **SCC (komponenta silné souvislosti)** = maximální množina uzlů vzájemně dosažitelných. Počet SCC říká, **kolik nezávislých problémových shluků** existuje: **12**.
- **Jednoduchý cyklus** = konkrétní uzavřená cesta bez opakování uzlů. Počet cyklů říká, **kolik jednotlivých uzavřených cest** shluky obsahují: **20**.
- Vztah: jedna SCC může obsahovat více cyklů (sdílejí uzly/hrany). Příklad: komponenta K04 (sus F) = 1 SCC, ale 3 jednoduché 2-cykly. Komponenta K10 (final-drive) = 1 SCC, ale 2 cykly (jeden 2-cyklus + jeden 3-cyklus `final_drive -> gear_ratios -> final_drive_mult -> final_drive`).
- Provozní důsledek se počítá po **SCC** (atomická jednotka opravy: celá komponenta se musí rozbít najednou), zatímco počet **cyklů** určuje, kolik hran je minimálně nutné odstranit/přepsat.

## 3. Klasifikace komponent (podrobně)

### K01 — auto_shift_type / shift_up_time / shift_down_time (3 uzly, 4 vnitřní hrany)

- Uzly: `auto_shift_type`, `shift_down_time`, `shift_up_time`.
- Vnitřní hrany: `auto_shift_type -> shift_down_time`, `auto_shift_type -> shift_up_time`, `shift_down_time -> auto_shift_type`, `shift_up_time -> auto_shift_type`.
- Význam: `shift_*_time -> auto_shift_type` = časy řazení platí jen při zvoleném typu automatu (podmíněná platnost — správný směr). `auto_shift_type -> shift_*_time` = typ vyžaduje konkrétní časy (typ DCT existuje i bez nich — nesprávný směr).
- Provozní důsledky: pořadí aplikace tune `AutoShiftType` vs `ShiftUpTime/ShiftDnTime` nedefinované; validátor „vyžaduje" hlásí oběma směry.
- Verdikt: **chybný model — nadbytečný/obrácený směr** (nikoli skutečný cyklus; typ je nezávislý vstup, časy jsou podmíněné).
- Návrh: **jeden směr** — ponechat `shift_down_time -> auto_shift_type`, `shift_up_time -> auto_shift_type`; smazat `auto_shift_type -> shift_down_time`, `auto_shift_type -> shift_up_time`. Důvod: časy jsou aktivní jen při automatu, typ platí sám o sobě.
- Riziko změny: nízké (pouze pořadí validace tune převodovky).
- Schválení: koordinátor + vlastník M2 (převodovka).

### K02 — auto_up_thresh / peak_rpm (2 uzly, 2 hrany)

- Hrany: `auto_up_thresh -> peak_rpm`, `peak_rpm -> auto_up_thresh`.
- Význam: `auto_up_thresh -> peak_rpm` = práh −200 je definován relativně k `PeakRPM` 6800 (správně, viz `function`). `peak_rpm -> auto_up_thresh` = vrchol křivky vyžaduje práh řazení (nesprávně; peak je vlastnost motorové křivky).
- Důsledky: motorová křivka a práh řazení se navzájem blokují při postupném ladění.
- Verdikt: **chybný model — obrácený směr** (odvozený parametr vs. nezávislý vstup).
- Návrh: **jeden směr** — ponechat `auto_up_thresh -> peak_rpm`; smazat `peak_rpm -> auto_up_thresh`. Důvod: práh je odvozen od peaku, ne naopak.
- Riziko: nízké.
- Schválení: koordinátor + M2.

### K03 — clutch_engage / flywheel / rev_accel (3 uzly, 4 hrany)

- Hrany: `clutch_engage -> flywheel`, `flywheel -> clutch_engage`, `flywheel -> rev_accel`, `rev_accel -> flywheel`.
- Význam: `clutch_engage -> flywheel` = chování záběru závisí na setrvačnosti (správně). `rev_accel -> flywheel` = točivost se interpretuje přes setrvačník (správně). Opačné dvě hrany (`flywheel -> clutch_engage`, `flywheel -> rev_accel`) tvrdí, že setrvačník vyžaduje oba — setrvačnost je přitom nezávislý vstup (500).
- Důsledky: trojice se nedá seřadit; fyzikálně jde o spřaženou soustavu (spojka–setrvačník–točivost), ale `depends_on` modeluje pořadí, ne spřažení.
- Verdikt: **chybný model — obousměrný výpočet** (fyzikální vazba zapsaná jako dvě jednostranné závislosti; nejblíže „skutečné" vazbě ze všech 12, ale jako `depends_on` cyklus neplatný).
- Návrh: **jeden směr ke společnému vstupu** — ponechat `clutch_engage -> flywheel`, `rev_accel -> flywheel`; smazat `flywheel -> clutch_engage`, `flywheel -> rev_accel`. Alternativa ( preferuje-li M3 ): **společný výpočetní uzel** „clutch skupina" aplikovaná atomicky. Důvod: flywheel je nezávislý vstup, oba ostatní jsou na něm podmíněné.
- Riziko: střední (mění pořadí aplikace spojky; dotýká se chování rozjezdu).
- Schválení: M3 (chassis/pohon) + koordinátor.

### K04 — sus_length_f / pre_compress_f / extension_lim_f / compress_lim_f (4 uzly, 6 hran)

- Hrany: `sus_length_f -> pre_compress_f`, `sus_length_f -> extension_lim_f`, `sus_length_f -> compress_lim_f`, `pre_compress_f -> sus_length_f`, `extension_lim_f -> sus_length_f`, `compress_lim_f -> sus_length_f`.
- Význam (z `physical_effect`): `FreeLength = FSusLength + FPreCompress`, `Max = +FExtensionLim`, `Min = −FCompressLim`. Limity/offsety jsou **vstupy** vzorců, odvozené `Free/Max/Min` v katalogu jako uzly **neexistují**. Záznam míchá vstupy a (chybějící) odvozené hodnoty.
- Důsledky: přední náprava nemá definované pořadí montáže délka→limity; M3 geometrie na tom staví.
- Verdikt: **chybný model — odvozený parametr místo vstupu** (chybí uzly pro `Free/Max/MinLength`).
- Návrh: **oddělení vstupu a odvozeného** — ponechat `pre_compress_f -> sus_length_f`, `extension_lim_f -> sus_length_f`, `compress_lim_f -> sus_length_f` (offsety se aplikují na základ); smazat tři opačné hrany `sus_length_f -> …`. Dlouhodobě doplnit odvozené uzly `free_length_f/max_length_f/min_length_f` závislé na všech čtyřech. Důvod: základ se montuje první, offsety po něm.
- Riziko: střední (jádro M3 geometrie).
- Schválení: M3 + koordinátor.

### K05 — sus_length_r / pre_compress_r / extension_lim_r / compress_lim_r (zrcadlo K04)

- Hrany a význam: zrcadlové K04 (vzorec R: `FreeLength = RSusLength + RPreCompress` atd.).
- Verdikt: **chybný model — odvozený parametr místo vstupu** (stejný jako K04).
- Návrh: **oddělení vstupu a odvozeného** — ponechat `*_r -> sus_length_r` (tři hrany limitů), smazat `sus_length_r -> {pre_compress_r, extension_lim_r, compress_lim_r}`; výhledově odvozené uzly R.
- Riziko: střední (M3).
- Schválení: M3 + koordinátor. (Opravit současně s K04 — stejný pattern, jedna revize.)

### K06 — compression_ratio / turbo_boost (2 uzly, 2 hrany)

- Hrany: `compression_ratio -> turbo_boost`, `turbo_boost -> compression_ratio` (plus acyklický přívod `turbo_boost -> turbo_count`).
- Význam: `turbo_boost -> compression_ratio` = boost vstupuje do `HP_T` vzorce spolu s `CompressionRatio` (správně). `compression_ratio -> turbo_boost` = kompresní poměr (konstrukční vlastnost motoru) vyžaduje boost (nesprávně).
- Důsledky: motorový výkonový vzorec nemá směr výpočtu; souvisí s `KNOWN_DEPENDS` (`engine.turbo.boost` vyžaduje `count`, podmínku `min: 1` katalog neumí — viz S02 §7).
- Verdikt: **chybný model — obrácený směr**.
- Návrh: **jeden směr** — ponechat `turbo_boost -> compression_ratio`; smazat `compression_ratio -> turbo_boost`. Důvod: poměr je nezávislý vstup, boost je na něm podmíněn ve vzorci. Podmínku `min: 1` řešit rozšířením modelu, ne hranou.
- Riziko: nízké až střední (vzorec `HP_T`).
- Schválení: M2 + M3 (motor).

### K07 — final_drive / gear_ratios / final_drive_mult (3 uzly, 4 hrany, 2 cykly)

- Hrany: `final_drive -> gear_ratios`, `gear_ratios -> final_drive`, `gear_ratios -> final_drive_mult`, `final_drive_mult -> final_drive`.
- Význam: `final_drive_mult -> final_drive` = násobič 1.1 modifikuje stálý převod 3.545 (správně, nejsilnější hrana). `gear_ratios -> final_drive` = stupně se interpretují se stálým převodem, `V-max` (správně ). `final_drive -> gear_ratios` = stálý převod vyžaduje stupně (slabé). `gear_ratios -> final_drive_mult` = stupně vyžadují násobič (nesprávně; násobič působí na final, ne na stupně — **duplicita vrstev**).
- Cykly v SCC: 2-cyklus (`final_drive ↔ gear_ratios`) + 3-cyklus (`final_drive -> gear_ratios -> final_drive_mult -> final_drive`).
- Důsledky: finální převod `fFDr` nemá výpočetní směr; navíc rozpor s `KNOWN_CONFLICTS` (`final_drive_mult ! final_drive` existuje jen v tabulce, v katalogu chybí a katalog místo něj tvrdí závislost).
- Verdikt: **chybný model — obousměrný výpočet + duplicita vrstev** (násobič je vrstva nad `final_drive`, ne partner `gear_ratios`).
- Návrh: **jeden směr + oddělení vrstev** — ponechat `gear_ratios -> final_drive` a `final_drive_mult -> final_drive`; smazat `final_drive -> gear_ratios` a `gear_ratios -> final_drive_mult`. Výsledek je řetěz `gear_ratios -> final_drive <- final_drive_mult` (acyklický). Důvod: stupně jsou základ, final je násobí, mult modifikuje final. Konflikt `final_drive_mult ! final_drive` z tabulky rozhodnout zvlášť (buď doplnit, nebo tabulku zrušit).
- Riziko: střední (převodovka + Gauges `V-max`; dotýká se M3).
- Schválení: M2 + M3 + koordinátor (včetně rozhodnutí o tabulkovém konfliktu).

### K08 — lock_to_lock / steer_ratio (2 uzly, 2 hrany)

- Hrany: `lock_to_lock -> steer_ratio`, `steer_ratio -> lock_to_lock`.
- Význam: `SteerOuter = LockToLock×180/SteerRatio` (2.6/15 → 31.2°). Oba jsou **nezávislé vstupy téhož vzorce**; ani jeden nevyžaduje druhý.
- Důsledky: řízení nemá seřaditelné vstupy, ačkoli žádný problém s pořadím neexistuje.
- Verdikt: **chybný model — obousměrný výpočet** (společný vzorec zapsán jako dvě závislosti).
- Návrh: **společný výpočetní uzel** — smazat **obě** hrany (oba nezávislé vstupy), engine počítá `SteerOuter` atomicky z obou. Důvod: žádný směr není „správnější"; závislost je fiktivní.
- Riziko: nízké.
- Schválení: M2 (koordinátor).

### K09 — pbrake_bias / pbrake_force (2 uzly, 2 hrany)

- Hrany: `pbrake_bias -> pbrake_force`, `pbrake_force -> pbrake_bias`.
- Význam: `pbrake_bias -> pbrake_force` = bias (0, jen zadek) se aplikuje na sílu 5000 (správně). `pbrake_force -> pbrake_bias` = síla vyžaduje bias (nesprávně; síla existuje samostatně).
- Důsledky: okruh ruční brzdy bez pořadí aplikace.
- Verdikt: **chybný model — obrácený směr**.
- Návrh: **jeden směr** — ponechat `pbrake_bias -> pbrake_force`; smazat `pbrake_force -> pbrake_bias`. Důvod: rozdělení se aplikuje na sílu, ne naopak.
- Riziko: nízké.
- Schválení: M2.

### K10 — redline_rpm / rev_bounce (2 uzly, 2 hrany)

- Hrany: `redline_rpm -> rev_bounce`, `rev_bounce -> redline_rpm`.
- Význam: `rev_bounce -> redline_rpm` = sražení 250 je chování na omezovači 8000 (podmíněné — správně). `redline_rpm -> rev_bounce` = omezovač vyžaduje sražení (nesprávně; omezovač platí sám).
- Důsledky: omezovač a jeho projev se vzájemně blokují.
- Verdikt: **chybný model — obrácený směr**.
- Návrh: **jeden směr** — ponechat `rev_bounce -> redline_rpm`; smazat `redline_rpm -> rev_bounce`. Důvod: projev je podmíněn omezovačem.
- Riziko: nízké.
- Schválení: M2.

### K11 — tcs_threshold_sps / tcs_gradient / tcs_limit_pct (3 uzly, 4 hrany)

- Hrany: `tcs_gradient -> tcs_threshold_sps`, `tcs_limit_pct -> tcs_threshold_sps`, `tcs_threshold_sps -> tcs_gradient`, `tcs_threshold_sps -> tcs_limit_pct`.
- Význam (vzorec): škrcení `1−min(max(0,skluz−práh)/gradient,1)×(1−limit)`. Gradient (strmost) a limit (zbytkový moment) jsou parametry **funkce prahu** → směry `gradient -> threshold`, `limit -> threshold` správně. Opačné hrany tvrdí, že práh 20 SPS vyžaduje oba — práh existuje i s defaulty.
- Důsledky: TCS trojice (bezpečnostní systém) bez definovaného pořadí; špatný směr opravy by změnil chování prokluzu.
- Verdikt: **chybný model — odvozené chování vs. vstup** (nadbytečný směr od centra k parametrům).
- Návrh: **jeden směr** — ponechat `tcs_gradient -> tcs_threshold_sps`, `tcs_limit_pct -> tcs_threshold_sps`; smazat `tcs_threshold_sps -> tcs_gradient`, `tcs_threshold_sps -> tcs_limit_pct`. Důvod: parametry funkce jsou podmíněny prahem, práh nikoli jimi.
- Riziko: nízké až střední (TCS je bezpečnostní; změna jen pořadí, ne hodnot).
- Schválení: M2 + vlastník brzd/TCS.

### K12 — weight_box_size / weight_lb (2 uzly, 2 hrany + acyklický přívod)

- Hrany: `weight_box_size -> weight_lb`, `weight_lb -> weight_box_size`. Přívod mimo SCC: `weight_dist_pct -> weight_box_size` (acyklický, ponechat).
- Význam: rozměr kvádru [7.03, 5.35, 18.11] a cílová hmotnost 3439 lb jsou **nezávislé vstupy**; hustota kvádru se **dopočítává z obou** (viz `physical_effect`). Ani jeden nevyžaduje druhý.
- Důsledky: hmotnostní model bez směru výpočtu hustoty.
- Verdikt: **chybný model — obousměrný výpočet** (společný odvozený výsledek).
- Návrh: **společný výpočetní uzel** — smazat **obě** hrany; hustotu počítat atomicky ze size+weight (odvozená hodnota, ne hrana). Přívod `weight_dist_pct -> weight_box_size` ponechat. Důvod: jako u K08 není žádný směr správnější.
- Riziko: nízké.
- Schválení: M2 (koordinátor).

## 4. Souhrnná tabulka

| ID komponenty | Parametry | Problém | Doporučené řešení | Riziko | Potřebné schválení |
|---|---|---|---|---|---|
| K01 | `auto_shift_type`, `shift_up/down_time` | nadbytečný směr (typ↔časy) | jeden směr: časy → typ; smazat `auto_shift_type → shift_*` | nízké | M2 + koordinátor |
| K02 | `auto_up_thresh`, `peak_rpm` | obrácený směr (peak vyžaduje práh) | jeden směr: práh → peak; smazat `peak_rpm → auto_up_thresh` | nízké | M2 |
| K03 | `clutch_engage`, `flywheel`, `rev_accel` | obousměrný výpočet (spřažená soustava) | jeden směr ke vstupu: оба → `flywheel`; příp. společný uzel | střední | M3 + koordinátor |
| K04 | `sus_length_f` + 3 limity F | vstup vs. odvozené (chybí Free/Max/Min) | oddělení: limity → délka; smazat `sus_length_f → …` (3 hrany) | střední | M3 + koordinátor |
| K05 | `sus_length_r` + 3 limity R | totéž, zrcadlo | totéž pro R (opravit s K04 v jedné revizi) | střední | M3 + koordinátor |
| K06 | `compression_ratio`, `turbo_boost` | obrácený směr (poměr vyžaduje boost) | jeden směr: boost → poměr; smazat `compression_ratio → turbo_boost` | nízké–střední | M2 + M3 |
| K07 | `final_drive`, `gear_ratios`, `final_drive_mult` | obousměrný výpočet + duplicita vrstev (mult) | `gear_ratios → final_drive ← final_drive_mult`; smazat 2 hrany; rozhodnout tabulkový konflikt | střední | M2 + M3 + koordinátor |
| K08 | `lock_to_lock`, `steer_ratio` | obousměrný výpočet (společný vzorec) | společný uzel `SteerOuter`; smazat obě hrany | nízké | M2 |
| K09 | `pbrake_bias`, `pbrake_force` | obrácený směr (síla vyžaduje bias) | jeden směr: bias → síla; smazat `pbrake_force → pbrake_bias` | nízké | M2 |
| K10 | `redline_rpm`, `rev_bounce` | obrácený směr (omezovač vyžaduje sražení) | jeden směr: bounce → redline; smazat `redline_rpm → rev_bounce` | nízké | M2 |
| K11 | `tcs_threshold_sps`, `tcs_gradient`, `tcs_limit_pct` | nadbytečný směr centrum → parametry | jeden směr: gradient/limit → práh; smazat 2 opačné hrany | nízké–střední | M2 + brzdy/TCS |
| K12 | `weight_box_size`, `weight_lb` | obousměrný výpočet (hustota z obou) | společný uzel (hustota); smazat obě hrany; přívod `weight_dist_pct` ponechat | nízké | M2 |

Shrnutí verdiktů: **skutečný datový cyklus 0 / chybný model 12** (z toho 8× nadbytečný/obrácený směr: K01, K02, K04, K05, K06, K09, K10, K11; 4× obousměrný výpočet/společný uzel: K03, K07, K08, K12; duplicita vrstev navíc u K07). Kategorie „závislost vs. konflikt" a „duplicita" se v SCC nevyskytují (viz §6 — všechny případy `depends_on ∩ conflicts` leží mimo cykly).

## 5. Pět neplatných `conflicts`-odkazů (pouze návrhy, nic nemazáno)

| # | Zdroj | Neplatný cíl | Příčina | Bezpečný návrh |
|---|---|---|---|---|
| 1 | `differential_type` | `slip_thresh_old` | zastaralý odkaz (přejmenováno na `slip_thresh_f/r/c`) | nahradit `[slip_thresh_f, slip_thresh_r, slip_thresh_c]`, nebo smazat (potomci konflikt nesou z druhé strany) |
| 2 | `differential_type` | `lock_thresh_old` | zastaralý odkaz (přejmenováno na `lock_thresh_f/r/c`) | nahradit `[lock_thresh_f, lock_thresh_r, lock_thresh_c]`, nebo smazat (viz výše) |
| 3 | `arm_kinematics` | `sus_angle` | zastaralý/nespecifikovaný odkaz (existují jen `sus_angle_f/r`) | nahradit `[sus_angle_f, sus_angle_r]` |
| 4 | `drag_coeff` | `aerodynamics_bug` | odstraněný/neexistující parametr (`drag_coeff` je konstanta MIMO Tune, žádný „bug" parametr v katalogu není) | smazat konflikt (konstanta se nekonfiguruje) |
| 5 | `final_drive_mult` | `gauge_max_speed_display` | odstraněný/chybějící parametr (Gauges `V-max` se počítají z `Ratios`, viz `gear_ratios.effect`; display uzel v katalogu není) | smazat, příp. doparametrizovat `gauge_max_speed_display` jako `VIRTUAL`/display-only |

## 6. Analýza 12× `depends_on` + současně `conflicts` (každý případ; nic neodstraněno)

Společný vzor: potomek `X` má `depends_on: [P]` **a zároveň** `conflicts: [P]`. Data tvrdí „vyžaduje P" i „nelze měnit s P". Ve všech 12 případech je `depends_on` věcně správně (podmíněná platnost) a `conflicts` je nadbytečný/duplicitní — **doporučení (pouze návrh): konflikt na straně potomka smazat, `depends_on` ponechat**; symetrii sjednotit. Změna NEPROVEDENA.

Skupina A — `arm_kinematics` (custom geometrie vs. procedurální větev):

1. `anchor_offset_f` (dep+conf `arm_kinematics`): offset ukotvení platí jen v custom geometrii → dep správně; konflikt duplicitní. Návrh: konflikt smazat.
2. `anchor_offset_r`: totéž (R). Návrh: konflikt smazat.
3. `front_wishbone_len` (neaktivní procedurální větev): délka ramene vyžaduje kinematiku → dep správně; konflikt navíc symetrický z `arm_kinematics`. Návrh: konflikt u potomka smazat (asymetrie: `arm_kinematics` konflikt uvádí, potomek by ho nemusel).
4. `rear_wishbone_len`: totéž (R). Návrh: konflikt u potomka smazat.
5. `sus_angle_f`: úhel ramen (neaktivní větev, 80) vyžaduje kinematiku → dep správně. Návrh: konflikt u potomka smazat; na straně `arm_kinematics` opravit `sus_angle` → `sus_angle_f/r` (§5/3).
6. `sus_angle_r`: totéž (R). Návrh: konflikt u potomka smazat.

Skupina B — `differential_type` (typ difu vs. prahy F/R/C):

7. `lock_thresh_f`: práh uzávěrky platí jen pro daný typ difu → dep správně; konflikt duplicitní. Návrh: konflikt smazat.
8. `lock_thresh_r`: totéž. Návrh: konflikt smazat.
9. `lock_thresh_c`: totéž (centr). Návrh: konflikt smazat.
10. `slip_thresh_f`: práh prokluzu podmíněn typem → dep správně. Návrh: konflikt smazat.
11. `slip_thresh_r`: totéž. Návrh: konflikt smazat.
12. `slip_thresh_c`: totéž (centr). Návrh: konflikt smazat.

Poznámka k asymetrii (mimo 12, pro úplnost, též beze změny): `electric_enabled ! electric_gauge_names` je jednostranný (zpět vede `electric_gauge_names ! electric_redline/trans2`, nikoli `! electric_enabled`); `front/rear_wishbone_len ↔ arm_kinematics` jsou symetrické, ale `anchor_offset_f/r` a `sus_angle_f/r` protizápis na straně `arm_kinematics` nemají. Sjednotit v téže revizi jako §5/1–3.

## 7. Navržené datové změny (pouze návrhy — NEPROVEDENO, NEAPLIKOVÁNO)

1. K01: smazat `auto_shift_type → shift_down_time`, `auto_shift_type → shift_up_time`.
2. K02: smazat `peak_rpm → auto_up_thresh`.
3. K03: smazat `flywheel → clutch_engage`, `flywheel → rev_accel` (příp. společný uzel clutch skupiny).
4. K04: smazat `sus_length_f → pre_compress_f/extension_lim_f/compress_lim_f` (3 hrany); výhledově uzly `free/max/min_length_f`.
5. K05: smazat `sus_length_r → pre_compress_r/extension_lim_r/compress_lim_r` (3 hrany); výhledově uzly R.
6. K06: smazat `compression_ratio → turbo_boost`.
7. K07: smazat `final_drive → gear_ratios`, `gear_ratios → final_drive_mult`; rozhodnout tabulkový konflikt `final_drive_mult ! final_drive`.
8. K08: smazat `lock_to_lock → steer_ratio` i `steer_ratio → lock_to_lock` (společný vzorec `SteerOuter`).
9. K09: smazat `pbrake_force → pbrake_bias`.
10. K10: smazat `redline_rpm → rev_bounce`.
11. K11: smazat `tcs_threshold_sps → tcs_gradient`, `tcs_threshold_sps → tcs_limit_pct`.
12. K12: smazat `weight_box_size → weight_lb` i `weight_lb → weight_box_size` (hustota společným výpočtem).
13. Konflikty: `slip_thresh_old` → `[slip_thresh_f/r/c]`; `lock_thresh_old` → `[lock_thresh_f/r/c]`; `sus_angle` → `[sus_angle_f, sus_angle_r]`; smazat `drag_coeff ! aerodynamics_bug`, `final_drive_mult ! gauge_max_speed_display` (nebo doparametrizovat).
14. 12× dep+conf: smazat konflikt na straně potomka, `depends_on` ponechat; sjednotit symetrii (§6).
