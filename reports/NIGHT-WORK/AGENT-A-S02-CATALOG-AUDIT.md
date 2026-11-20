# Agent A — S-02: Kompletní audit závislostí katalogu

- Repo: `C:/.DATA/AutoEngineerAI`, větev `feat/m2-m3-geometry`, SHA `90a1f63`
- Zdroje: `src/Chassis/catalog/parameters.json` (celý soubor, 3444 řádků), `src/Chassis/mapping/dependencies.py` (`KNOWN_DEPENDS`, `KNOWN_CONFLICTS`)
- Datum: 2026-11-20. Jazyk: čeština; identifikátory/kód anglicky.
- Omezení dodržena: pouze čtení repa, zápis jen tohoto souboru; RBXM / `C:/.DATA/RobloxSimulator` nedotčeny.

## 1. Konvence směru hran (platí pro celý dokument)

**`A -> B` znamená: parametr `A` má v `depends_on` uveden parametr `B`, tj. `A` závisí na `B`.**
Zdroj hrany = závislý parametr (ten, v jehož záznamu je `depends_on`), cíl hrany = předpoklad.
Příklad: `turbo_boost -> turbo_count` čti „`turbo_boost` závisí na `turbo_count`".
Pro konflikty se používá značení `A ! B` (symetrická relace „nelze měnit společně", ne orientovaná hrana).

## 2. Počty (souhrn)

| Metrika | Hodnota |
|---|---|
| Parametrů v katalogu | **138** (id unikátních 138, duplicity id 0) |
| Parametrů s neprázdným `depends_on` | **85** (bez závislostí 53) |
| Orientovaných hran `depends_on` | **101** |
| Neplatných odkazů v `depends_on` (cíl není id) | **0** |
| Self-loopů v `depends_on` | **0** |
| Duplicitních hran `depends_on` | **0** |
| Parametrů s vícenásobným `depends_on` (≥2) | **13** |
| Konfliktových záznamů (`conflicts`) | **24** hran od 20 parametrů (118 parametrů bez konfliktu) |
| Neplatných odkazů v `conflicts` | **5** (4 unikátní neexistující cíle) |
| Duplicitních hran `conflicts` | **0** |
| Skutečných cyklů `depends_on` (SCC velikosti > 1) | **12 komponent** (viz §5) |
| `depends_on` s chybějícím klíčem / jiným typem než list / nestringovou položkou | **0 / 0 / 0** |

Dodatky k integritě identifikátorů:
- `config_path`: 138 hodnot, 125 unikátních — **14× `None`** (duplicita hodnoty `None`): `abs_pulse_logic`, `camber_caster_toe`, `center_diff_logic`, `curve_shape_func`, `downforce_f`, `downforce_r`, `drag_coeff`, `shift_logic`, `wear_speed`, `wheel_lock_ratio`, `wheelspin_ratio`, `wind_volume`, `wheel_radius`, `spring_color`. Reálné cesty se tedy neopakují, ale 14 virtuálních parametrů nemá kam mapovat.
- `tune_key`: 118 unikátních — **21× `None`** (stejných 14 + `arm_kinematics`→`geometry_overrides`, `target_friction`→`tires.grip_long`, `wheelbase_etc`, `electric_gauge_names`, `legacy_wheel_density_f/r`, `steer_axis_offset` mají cestu, ale bez tune klíče).
- Všech 101 cílů `depends_on` jsou platná `id` (jmenný prostor `depends_on`/`conflicts` je konzistentně `id`, nikoli `config_path`/`tune_key` — ztráta při převodu id→cesta u `None`-záznamů viz §7).

## 3. Typy závislostí v katalogu

Jediný strojově čitelný typ směrové závislosti je **`depends_on: list[id]`** (všech 138 záznamů klíč má, vždy list stringů).
Další vztahové typy:
- **`conflicts: list[id]`** — 24 záznamů, symetrická relace „nelze měnit v jednom kroku", **není to cyklus** (viz klasifikace §6).
- **`used_in: list[str]`** (`Drive`/`Initialize`/…) — kontext použití, ne závislost; do grafu nepatří.
- Volný text (`function`, `physical_effect`, `source`) může závislost zmiňovat slovně, ale není strojový — nepočítáno mezi hrany.
- Prázdné seznamy: `depends_on: []` u 53 parametrů = bez závislostí (korektní stav, ne chyba); `conflicts: []` u 118 parametrů.

Vícenásobné závislosti (13 parametrů): `auto_shift_type` (2), `auto_up_thresh` (2), `flywheel` (2), `gear_ratios` (2), `sus_stiffness_f` (2), `sus_stiffness_r` (2), `tcs_threshold_sps` (2), `turbo_boost` (2), `abs_pulse_logic` (2), `center_diff_logic` (2), `curve_shape_func` (3), `sus_length_f` (3), `sus_length_r` (3).

## 4. Úplný seznam orientovaných hran `depends_on` (101)

Konvence: `zdroj -> cíl` = zdroj závisí na cíli (§1). Všechny cíle existují, žádné duplicity, žádné self-loopy.

```
abs_pulse_logic -> abs_threshold_sps
abs_pulse_logic -> tcs_threshold_sps
anchor_offset_f -> arm_kinematics
anchor_offset_r -> arm_kinematics
auto_down_thresh -> auto_shift_mode
auto_shift_mode -> trans_modes
auto_shift_type -> shift_down_time
auto_shift_type -> shift_up_time
auto_up_thresh -> auto_shift_mode
auto_up_thresh -> peak_rpm
brake_force -> abs_threshold_sps
center_diff_logic -> drive_config
center_diff_logic -> torque_vector
clutch_engage -> flywheel
clutch_kick -> clutch_enabled
compress_lim_f -> sus_length_f
compress_lim_r -> sus_length_r
compression_ratio -> turbo_boost
curve_shape_func -> curve_mult
curve_shape_func -> peak_rpm
curve_shape_func -> peak_sharpness
damper_f -> sus_stiffness_f
damper_r -> sus_stiffness_r
diff_preload_f -> differential_type
diff_preload_r -> differential_type
electric_end_mult -> electric_enabled
electric_end_percent -> electric_enabled
electric_front_mult -> electric_enabled
electric_gauge_names -> electric_enabled
electric_redline -> electric_enabled
electric_torque -> electric_enabled
electric_torque_end_mult -> electric_enabled
electric_torque_end_percent -> electric_enabled
electric_trans1 -> electric_enabled
electric_trans2 -> electric_enabled
engine_brake_force -> redline_rpm
extension_lim_f -> sus_length_f
extension_lim_r -> sus_length_r
final_drive -> gear_ratios
final_drive_mult -> final_drive
flywheel -> clutch_engage
flywheel -> rev_accel
front_diff_coast -> differential_type
front_diff_power -> differential_type
front_wishbone_len -> arm_kinematics
gear_ratios -> final_drive
gear_ratios -> final_drive_mult
idle_throttle -> idle_rpm
lock_thresh_c -> differential_type
lock_thresh_f -> differential_type
lock_thresh_r -> differential_type
lock_to_lock -> steer_ratio
min_steer -> steer_decay
pbrake_bias -> pbrake_force
pbrake_force -> pbrake_bias
peak_rpm -> auto_up_thresh
pre_compress_f -> sus_length_f
pre_compress_r -> sus_length_r
rear_diff_coast -> differential_type
rear_diff_power -> differential_type
rear_wishbone_len -> arm_kinematics
redline_rpm -> rev_bounce
rev_accel -> flywheel
rev_bounce -> redline_rpm
rpm_engage -> clutch_enabled
shift_down_time -> auto_shift_type
shift_logic -> trans_modes
shift_up_time -> auto_shift_type
slip_thresh_c -> differential_type
slip_thresh_f -> differential_type
slip_thresh_r -> differential_type
speed_engage -> clutch_enabled
steer_ratio -> lock_to_lock
supercharger_sensitivity -> supercharger_count
sus_angle_f -> arm_kinematics
sus_angle_r -> arm_kinematics
sus_length_f -> compress_lim_f
sus_length_f -> extension_lim_f
sus_length_f -> pre_compress_f
sus_length_r -> compress_lim_r
sus_length_r -> extension_lim_r
sus_length_r -> pre_compress_r
sus_stiffness_f -> pre_compress_f
sus_stiffness_f -> sus_length_f
sus_stiffness_r -> pre_compress_r
sus_stiffness_r -> sus_length_r
tcs_gradient -> tcs_threshold_sps
tcs_limit_pct -> tcs_threshold_sps
tcs_threshold_sps -> tcs_gradient
tcs_threshold_sps -> tcs_limit_pct
torque_vector -> drive_config
tq_lock -> clutch_enabled
turbo2_boost_lag -> turbo_count
turbo_boost -> compression_ratio
turbo_boost -> turbo_count
turbo_boost_lag -> turbo_count
weight_box_size -> weight_lb
weight_dist_pct -> weight_box_size
weight_lb -> weight_box_size
wheel_lock_ratio -> target_friction
wheelspin_ratio -> target_friction
```

Úplný seznam konfliktů `A ! B` (24; `!` = symetrická relace, ne hrana):
`anchor_offset_f ! arm_kinematics`, `anchor_offset_r ! arm_kinematics`, `arm_kinematics ! front_wishbone_len`, `arm_kinematics ! rear_wishbone_len`, `arm_kinematics ! sus_angle` (NEPLATNÉ ID), `differential_type ! lock_thresh_old` (NEPLATNÉ), `differential_type ! slip_thresh_old` (NEPLATNÉ), `drag_coeff ! aerodynamics_bug` (NEPLATNÉ), `electric_enabled ! electric_gauge_names`, `electric_gauge_names ! electric_redline`, `electric_gauge_names ! electric_trans2`, `electric_redline ! electric_gauge_names`, `electric_trans2 ! electric_gauge_names`, `final_drive_mult ! gauge_max_speed_display` (NEPLATNÉ), `front_wishbone_len ! arm_kinematics`, `lock_thresh_c/f/r ! differential_type`, `rear_wishbone_len ! arm_kinematics`, `slip_thresh_c/f/r ! differential_type`, `sus_angle_f ! arm_kinematics`, `sus_angle_r ! arm_kinematics`.

## 5. Všechny skutečné cykly (12 SCC, Tarjan; cesty v konvenci §1)

1. `tcs_gradient -> tcs_threshold_sps -> tcs_gradient` (a `tcs_limit_pct -> tcs_threshold_sps -> tcs_limit_pct`) — klasifikace: **cyklus**. Dvě prahové větve se navzájem podmiňují s centrálním prahem.
2. `redline_rpm -> rev_bounce -> redline_rpm` — **cyklus**.
3. `sus_length_f -> pre_compress_f -> sus_length_f` (+ totéž přes `extension_lim_f`, `compress_lim_f`) — **cyklus** (trojúhelník přes 3 limity, 4-uzlová komponenta).
4. `sus_length_r -> pre_compress_r -> sus_length_r` (+ přes `extension_lim_r`, `compress_lim_r`) — **cyklus**, zrcadlo (3).
5. `weight_box_size -> weight_lb -> weight_box_size` — **cyklus** (+ acyklický přívod `weight_dist_pct -> weight_box_size`).
6. `clutch_engage -> flywheel -> clutch_engage` a `flywheel -> rev_accel -> flywheel` — **cyklus** (3-uzlová komponenta, dva sdílené 2-cykly).
7. `pbrake_bias -> pbrake_force -> pbrake_bias` — **cyklus**.
8. `auto_shift_type -> shift_up_time -> auto_shift_type` (a totéž přes `shift_down_time`) — **cyklus** (typ vs. časy oběma směry).
9. `auto_up_thresh -> peak_rpm -> auto_up_thresh` — **cyklus**.
10. `final_drive -> gear_ratios -> final_drive` (+ delší `final_drive -> gear_ratios -> final_drive_mult -> final_drive`) — **cyklus** (3-uzlová komponenta).
11. `compression_ratio -> turbo_boost -> compression_ratio` — **cyklus** (komprese podmiňuje boost a naopak).
12. `lock_to_lock -> steer_ratio -> lock_to_lock` — **cyklus**.

Vzájemné páry (19, každý je 2-cyklus výše): `(auto_shift_type, shift_down_time)`, `(auto_shift_type, shift_up_time)`, `(auto_up_thresh, peak_rpm)`, `(clutch_engage, flywheel)`, `(compress_lim_f, sus_length_f)`, `(compress_lim_r, sus_length_r)`, `(compression_ratio, turbo_boost)`, `(extension_lim_f, sus_length_f)`, `(extension_lim_r, sus_length_r)`, `(final_drive, gear_ratios)`, `(flywheel, rev_accel)`, `(lock_to_lock, steer_ratio)`, `(pbrake_bias, pbrake_force)`, `(pre_compress_f, sus_length_f)`, `(pre_compress_r, sus_length_r)`, `(redline_rpm, rev_bounce)`, `(tcs_gradient, tcs_threshold_sps)`, `(tcs_limit_pct, tcs_threshold_sps)`, `(weight_box_size, weight_lb)`.

## 6. Klasifikace všech nálezů (povinná taxonomie)

- **cyklus**: všech 12 komponent z §5 (19 vzájemných párů). Každá cesta ověřena v datech, zdroj i cíl existují.
- **neexistující cíl**: v `depends_on` žádný (0). V `conflicts` 5 výskytů / 4 unikátní: `slip_thresh_old`, `lock_thresh_old` (oba z `differential_type`), `aerodynamics_bug` (z `drag_coeff`), `gauge_max_speed_display` (z `final_drive_mult`), `sus_angle` (z `arm_kinematics`; existují jen `sus_angle_f/r`).
- **duplicita**: 0 (ani v `depends_on`, ani v `conflicts`; id bez duplicit).
- **neplatné ID**: totožné s „neexistující cíl" výše + formátová vada `config_path`/`tune_key = None` u 14, resp. 21 záznamů (§2) — ID samotná platná jsou, ale mapování na cestu/klíč chybí.
- **nejednoznačný význam**: 12 parametrů má TENTÝŽ protějšek v `depends_on` i `conflicts` (`anchor_offset_f/r`, `front/rear_wishbone_len`, `sus_angle_f/r` vs `arm_kinematics`; `lock/slip_thresh_*` vs `differential_type`) — data tvrdí současně „vyžaduje" i „vylučuje se". Dále asymetrické konflikty: `electric_enabled -> electric_gauge_names` bez symetrické odpovědi (zpět vede jen `electric_gauge_names -> electric_redline/trans2`), a `differential_type`/`arm_kinematics` konflikty bez symetrického protizápisu u 10 parametrů.
- **konflikt-není-cyklus**: všech 24 záznamů `conflicts` — ani symetrické páry (`electric_redline ! electric_gauge_names`, `front_wishbone_len ! arm_kinematics` aj.) nejsou orientované cykly a nesmí se tak vyhodnocovat.
- **chyba formátu**: 0 strukturálních (všude list stringů). Obsahová formátová rizika: `None` cesty/klíče (§2) a konfliktní cíle ve starém názvosloví (`*_old`, `sus_angle` bez osy).

## 7. Rozdílový report katalog vs. `KNOWN_DEPENDS` / `KNOWN_CONFLICTS`

`KNOWN_DEPENDS` (config_path, 1 záznam): `engine.turbo.boost` závisí na `engine.turbo.count` (podmínka `min: 1`, důvod „plnicí tlak bez turbodmychadla nemá účinek").
Katalog (id): `turbo_boost` (`engine.turbo.boost`) má `depends_on: [turbo_count, compression_ratio]`.

| Hledisko | Výsledek |
|---|---|
| V katalogu (`turbo_boost -> turbo_count`) | ANO — odpovídá `KNOWN_DEPENDS` |
| V tabulce, v katalogu chybí | podmínka `min: 1` (katalog podmínky neumí, jen holá id); nic dalšího |
| V katalogu, v tabulce chybí | `turbo_boost -> compression_ratio`, zpětná `compression_ratio -> turbo_boost` (cyklus č. 11), a všech zbývajících **99 hran** — tabulka pokrývá **1 ze 101 hran (~1 %)** |
| Rozdíl identifikátorů | tabulka: `config_path` (`engine.turbo.boost`); katalog: `id` (`turbo_boost`) — převod funguje jen přes `config_path`, který je u 14 záznamů `None` (ztráta při převodu) |
| Rozdíl směru | žádný rozpor: obojí „parametr vyžaduje předpoklad" (katalog `A depends_on B` ≡ tabulka `param` + `depends_on[].param`) |

`KNOWN_CONFLICTS` (1 záznam): `transmission.final_drive_mult ! transmission.final_drive` (first-wins). Katalog: `final_drive_mult` má `depends_on: [final_drive]` a `conflicts: [gauge_max_speed_display]` (neplatné ID); `final_drive` nemá žádný konflikt. Tabulkový konflikt tedy **v katalogu vůbec není** (ani jedním směrem) a katalog místo něj tvrdí závislost stejné dvojice opačným směrem + zapojuje třetí uzel `gear_ratios` (cyklus č. 10). Podezření na phenotype-vs-genotype rozpor: final-drive konflikt existuje jen v tabulce, v datech chybí.

**Odpověď na otázku: NE — `KNOWN_DEPENDS` katalog nepokrývá** (1/101 hran + podmínková sémantika `min`, kterou katalog neumí).

## 8. Doporučení: data vs. algoritmus

**Opravit v DATECH (katalog):**
1. Rozbít 12 cyklů z §5: u každého páru rozhodnout směr (typicky konkretní parametr závisí na abstraktnějším limitu, ne naopak) a zpětnou hranu smazat — např. `peak_rpm -> auto_up_thresh` ponechat jen jedním směrem; `sus_length_*` vs. limity ponechat `limity -> sus_length` (limity jsou odvozeny z délky) a smazat `sus_length -> {pre_compress, extension_lim, compress_lim}`; `turbo_boost <-> compression_ratio` ponechat jen `turbo_boost -> compression_ratio` (nebo naopak dle fyziky A-Chassis) — koordinuje se s M3.
2. Opravit 5 neplatných konfliktů: `slip_thresh_old`/`lock_thresh_old` → `slip_thresh_f/r/c` + `lock_thresh_f/r/c`; `sus_angle` → `sus_angle_f`, `sus_angle_r`; `aerodynamics_bug` a `gauge_max_speed_display` buď doparametrizovat, nebo smazat.
3. Vyřešit 12× „závisí + vylučuje se zároveň" (§6 nejednoznačný význam): u `arm_kinematics`/`differential_type` skupin zvolit jeden vztah (doporučeno `depends_on`, konflikt smazat) a sjednotit symetrii konfliktů.
4. Doplnit `config_path`/`tune_key` u 14/21 `None` záznamů, nebo je explicitně označit `category: VIRTUAL` (virtuální logika bez mapování), aby převod id→cesta neztrácel.
5. Doplnit chybějící katalogový konflikt `final_drive_mult ! final_drive` (dle `KNOWN_CONFLICTS`), nebo vědomě zrušit tabulkový.

**Opravit v ALGORITMU (engine/selftest/MAPPING.md):**
6. Topologický sort musí cykly detekovat a hlásit cestou (`A -> B -> A`), ne zacyklit/ztišit — dokud data cykly obsahují, engine potřebuje deterministické pravidlo (doporučeno: hrany v SCC ignorovat + `warn`, nebo `first-wins` jako u konfliktů).
7. Sjednotit jmenný prostor: rozhodnout `id` vs `config_path` jako kanonický klíč závislostí a `loader.py`/`mapping_engine.py`/`dependencies.py` na něj převést (dnes katalog `id`, tabulka `config_path`).
8. Přidat validační selftest: každý cíl `depends_on`/`conflicts` musí být existující `id`; konflikty symetrické; `depends_on ∩ conflicts = ∅`; graf acyklický — jinak FAIL.
9. Rozšířit datový model, pokud má podmínka `min: 1` z `KNOWN_DEPENDS` platit: katalog dnes umí jen holé hrany, podmínkové závislosti (`min`/`max`/`equals`) zahodí.
