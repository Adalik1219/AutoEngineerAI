# CATALOG-PROPOSALS-AND-USER-INPUTS — inventář 14 návrhů + U1–U6 (NÁVRHY, nic neaplikováno)

**Stav:** vše `Neschváleno` · **Katalog/motor/RBXM/schémata:** NEMĚNĚNY · **M3 CLOSED**
**Zdroje:** `AGENT-A-CATALOG-REMEDIATION.md` §3+§7 (blob viz git), aktuální hrany ověřeny čtením `parameters.json` 20. 11. 2026 (138 záznamů)
**Pravidlo:** žádný návrh nesmí být schválen jen proto, že odstraní cyklus; oprava nesmí zničit významovou závislost. Dopad každé změny na S-02 nutno před schválením ověřit simulací (acykličnost + integrita + mapovací testy).

## ČÁST 1 — 14 katalogových návrhů (vše Neschváleno, vlastník důkazu Agent A)

| ID | Katalogové ID / hrany | Současný stav (depends_on) | Navrhovaná změna | Důvod (A) | Závislosti/dopad | Riziko | Schválení |
|---|---|---|---|---|---|---|---|
| P01 | K01 auto_shift_type | `auto_shift_type→{shift_up,shift_down}` + zpětné | smazat obě hrany z auto_shift_type | nadbytečný směr | shift_* zůstávají závislé na auto_shift_type | nízké (M2) | Neschváleno |
| P02 | K02 peak_rpm→auto_up_thresh | obousměrné s auto_up_thresh→peak_rpm | smazat `peak_rpm→auto_up_thresh` | nadbytečný směr | práh řazení zůstává odvozen | nízké (M2) | Neschváleno |
| P03 | K03 spojka | `clutch_engage→flywheel`; `flywheel→{rev_accel,clutch_engage}`; `rev_accel→flywheel` | smazat `flywheel→clutch_engage`, `flywheel→rev_accel` (příp. společný uzel) | obousměrný výpočet | spojka/dif/převodovka | střední (M3 + koordinátor) | Neschváleno |
| P04 | K04 sus front | `sus_length_f→{pre_compress,extension_lim,compress_lim}_f` + zpětné | smazat 3 hrany ze sus_length_f (+ výhledově uzly free/max/min_length_f) | nadbytečný směr | zavěšení F, S-02, M3 | střední | Neschváleno |
| P05 | K05 sus rear | zrcadlo K04 | smazat 3 hrany ze sus_length_r (+ uzly R) | nadbytečný směr | zavěšení R, S-02, M3 | střední | Neschváleno |
| P06 | K06 compression_ratio→turbo_boost | obousměrné s turbo_boost→compression_ratio | smazat `compression_ratio→turbo_boost` | nadbytečný směr | motor/turbo mapa | nízké–střední | Neschváleno |
| P07 | K07 final_drive/gear_ratios/final_drive_mult | `final_drive→gear_ratios`; `gear_ratios→{final_drive,final_drive_mult}`; `final_drive_mult→final_drive` | smazat `final_drive→gear_ratios`, `gear_ratios→final_drive_mult` + rozhodnout konflikt `final_drive_mult ! final_drive` | obousměrný výpočet + duplicita vrstev multu | převodovka, Sim citlivost (C3), U-převody | střední (koordinátor) | Neschváleno |
| P08 | K08 lock_to_lock↔steer_ratio | obousměrné | smazat OBĚ (společný vzorec SteerOuter) | chybný model oběma směry | řízení, S-02 | nízké–střední | Neschváleno |
| P09 | K09 pbrake_force→pbrake_bias | obousměrné s pbrake_bias→pbrake_force | smazat `pbrake_force→pbrake_bias` | nadbytečný směr | brzdy (C2 bias) | nízké (M2) | Neschváleno |
| P10 | K10 redline_rpm→rev_bounce | obousměrné s rev_bounce→redline_rpm | smazat `redline_rpm→rev_bounce` | nadbytečný směr | motor limit | nízké (M2) | Neschváleno |
| P11 | K11 tcs_* | `tcs_threshold_sps→{tcs_gradient,tcs_limit_pct}` + zpětné | smazat obě hrany z threshold_sps | nadbytečný směr | TCS, S-02 svědek | nízké (M2) | Neschváleno |
| P12 | K12 weight_box_size↔weight_lb | obousměrné | smazat OBĚ (hustota společným výpočtem) | chybný model | hmotnost | nízké–střední | Neschváleno |
| P13 | 5 neplatných konfliktů | cíle `slip_thresh_old, lock_thresh_old, aerodynamics_bug, gauge_max_speed_display, sus_angle` v `conflicts`, jako záznamy NEEXISTUJÍ (ověřeno čtením) | přejmenovat na F/R/C varianty; `sus_angle`→F/R; smazat `drag_coeff ! aerodynamics_bug`, `final_drive_mult ! gauge_max_speed_display` (nebo doparametrizovat) | překlep/odstraněný/zastaralý | integrita katalogu | nízké (M2) | Neschváleno |
| P14 | 12× dep+conf | závislost i konflikt téže dvojice (skupiny arm_kinematics, differential_type, asymetrické konflikty) | smazat konflikt na straně potomka, `depends_on` ponechat; sjednotit symetrii | závislost ≠ konflikt | S-02 integrita | nízké–střední | Neschváleno |

## ČÁST 2 — U1–U6 (upřímný stav evidence)

**Nález:** přesné definice U1–U6 NEEXISTUJÍ v žádném reportu. Jediný zdroj je souhrnný řádek R3 ve `FINAL-IMPLEMENTATION-WAVE-REPORT.md` (§Výsledky agentů + §R-rozhodnutí). Níže je tento řádek rozveden na 6 položek — každá je `POTŘEBUJE definici uživatele`, nikoliv hotový požadavek. Odděleno od normalizačních U1–U4 (`normalized_ids.json` unresolved — jiná množina).

| Kód | Pracovní název (z R3) | Co je doloženo | Co chybí | Typ | Blokuje |
|---|---|---|---|---|---|
| U1 | Mustang asset + licence | nic (pouze zmínka) | soubor, zdroj, licence, formát | rozhodnutí + soubor (uživatel) | M3 geometrie |
| U2 | Studio měření | checklist v AGENT-C-STUDIO-INPUT-REQUIREMENTS | provedení + důkaz | měření (uživatel ve Studiu) | M2 VERIFIED |
| U3 | verified_in_studio rámec | nic | definice kdo/co potvrzuje | rozhodnutí (uživatel) | M2→M3 brána |
| U4 | final drive 3.15/3.55 | kandidáti bez přiřazení (F/E) | rozhodnutí + zdroj | rozhodnutí (uživatel) | mapování převodů |
| U5 | převody (poměry MT-82) | poměry 1–6 VERIFIED, ostatní ? | potvrzení sady + zdroj | rozhodnutí (uživatel) | mapování převodovky |
| U6 | validační cíle 5.3 s / 250 km/h | hodnoty VERIFIED jako CÍLE (E §1: cíle, ne vstupy) | schválení použití jako cílů | rozhodnutí (uživatel) | M8 evaluace |

## Rozhodnutí požadovaná od uživatele (souhrn)
R1: schválit/odmítnout P01–P14 jednotlivě (žádné hromadné „oprav cykly") · R2: schválit 4 PROPOSED schémata · R3: definovat/dodat U1–U6 · R4: potvrdit vyřešení vakuí (po G-kontrole) · R5: odsouhlasit další vlnu.
