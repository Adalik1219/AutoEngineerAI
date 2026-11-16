# Testování a autonomní optimalizace – AutoEngineerAI

**Vlastněný soubor:** `C:/.DATA/AutoEngineerAI/docs/TESTING-OPTIMIZATION.md`
**Rozsah:** FÁZE 9–10 (kapitoly 5.10–5.14 a 7 dokumentu `docs/PROJECT-PLAN.md`).
**Jazyk:** česky. Identifikátory a kód anglicky.
**Stav:** Návrh (není implementováno, není ověřeno v Roblox runtime).

---

## 1. Shrnutí práce

Tento dokument navrhuje autonomní testovací a optimalizační systém AutoEngineerAI:

1. **Testovací prostředí** – opakovatelné tratě a scénáře pokrývající kapitolu 7 (výkon, brzdění, ovládání, podvozek, trakce, robustnost).
2. **Autonomního řidiče** (`AutonomousDriver`) – deterministický ovladač vozidla se stejnými vstupy pro každou variantu.
3. **Telemetrii a vyhodnocení** (`Telemetry`) – měřené kanály, metriky, výpočty odchylek od referenčního profilu.
4. **Autonomní optimalizér** (`AutonomousOptimizer`) – vícekriteriální optimalizace se zákazem zlepšit jeden parametr na úkor celku, s detekcí nestability, rollbackem a statistickým ověřením zlepšení.
5. **Validační politiku** – oddělení matematických testů, lokální simulace a skutečných Roblox runtime testů (dle zásady č. 10 hlavních principů: neověřenou simulaci nevydávat za důkaz).

Žádná část tohoto návrhu zatím není implementována ani změřena. Vše níže v sekcích 2–7 je návrh; fakta vs. předpoklady vs. neznámé jsou explicitně odděleny v sekci 8.

---

## 2. Architektura testovacího systému

### 2.1 Přehled komponent

```
┌─────────────────────┐     ┌──────────────────────┐     ┌─────────────────────┐
│  TestEnvironment    │────>│  AutonomousDriver    │────>│  VehicleUnderTest   │
│  (tratě + scénáře + │     │  (deterministické    │     │  (pracovní kopie    │
│   podmínky, povrchy │     │   řízení: plyn/brzda │     │   vozidla, verzovaná│
│   zatížení, počasí) │     │   /volant, řazení)   │     │   varianta configu) │
└─────────┬───────────┘     └──────────────────────┘     └─────────┬───────────┘
          │                                                        │
          │                 ┌──────────────────────┐               │
          └────────────────>│  TelemetryRecorder   │<──────────────┘
                            │  (vzorkování, časová │
                            │   razítka, jednotky) │
                            └─────────┬────────────┘
                                      │
                            ┌─────────▼────────────┐     ┌─────────────────────┐
                            │  MetricsEvaluator    │────>│  ReferenceProfile   │
                            │  (metriky, odchylky, │     │  (cílový profil +  │
                            │   skóre, stabilita)  │     │   tolerance, kap. 7)│
                            └─────────┬────────────┘     └─────────────────────┘
                                      │
                            ┌─────────▼────────────┐
                            │ AutonomousOptimizer  │
                            │ (kandidáti, algoritm.│
                            │  test, rollback)     │
                            └─────────┬────────────┘
                                      │
                            ┌─────────▼────────────┐
                            │ VariantStore +       │
                            │ ValidationGate       │
                            │ (historie, nejlepší  │
                            │  varianta, runtime)  │
                            └────────────────────┘
```

### 2.2 Odpovědnosti modulů

| Modul | Odpovědnost | Vstupy | Výstupy |
|---|---|---|---|
| `TestEnvironment` | Staví deterministickou scénu pro každý scénář: geometrie tratě, povrch (frikce), nerovnosti, počáteční podmínky (rychlost, zařazený stupeň, zatížení), okrajové podmínky (timeout, kritéria abortu). | `ScenarioSpec` | Připravená scéna + `RunContext` (seed, verze tratě) |
| `AutonomousDriver` | Vydává v každém kroku řídicí vstupy (throttle 0–1, brake 0–1, steer −1…1, řazení). Režimy: stopař (sleduje referenční čáru), rychlostní regulátor (drží cílovou rychlost), manévrový (předpis throttle/brake/steer jako funkce času nebo dráhy). Deterministický: stejný `ScenarioSpec` + stejná varianta ⇒ stejná sekvence vstupů. | `RunContext`, stav vozidla | Řídicí vektor `u(t)` |
| `TelemetryRecorder` | Vzorkuje kanály pevnou frekvencí, ukládá časová razítka simulačního času (nikoli wall-clock), jednotky SI, verzi tratě/řidiče/varianty. | Stav sim/vozidla | `RunTrace` (časové řady) |
| `MetricsEvaluator` | Z `RunTrace` počítá metriky (sekce 4), odchylky od reference, normalizované skóre, detekci nestability. | `RunTrace`, `ReferenceProfile` | `RunResult` (metriky + verdicts) |
| `AutonomousOptimizer` | Generuje kandidáty, plánuje testy, aplikuje vícekriteriální akceptační pravidlo, rollback, statistické ověření. | `RunResult` historie | Nová `CandidateVariant` nebo STOP |
| `VariantStore` | Verzuje každou variantu (config diff + skóre + surová telemetrie). Nikdy nepřepisuje, jen přidává. Nejlepší varianta je neměnná do nahrazení lepší. | Varianty + výsledky | `best_variant_id`, historie |
| `ValidationGate` | Odděluje 3 úrovně důkazu (sekce 6.4): MATH (jednotkové výpočty), SIM (lokální simulace), RUNTIME (skutečný Roblox). Postup do další úrovně jen při splnění kritérií. | `RunResult` | Verdict MATH/SIM/RUNTIME |

### 2.3 Klíčové principy

1. **Opakovatelnost:** každý běh má `run_id = hash(scenario_version, driver_version, variant_id, seed, physics_dt)`. Stejné vstupy ⇒ výsledek v toleranci (sekce 4.7). Bez seedu není výsledek platný.
2. **Izolace úrovní důkazu:** lokální simulace slouží k rychlému filtrování kandidátů; finální tvrzení o vozidle platí až po Roblox runtime testu (zásada: neověřenou simulaci nevydávat za důkaz).
3. **Varianta je neměnná:** optimalizér nikdy needituje `best_variant` in-place; vytváří kopii s diffem. Rollback = přepnutí pointeru, ne rekonstrukce hodnot.
4. **Žádný test bez abort kritérií:** každý scénář má definováno, kdy se běh předčasně ukončí (převrácení, opuštění tratě, timeout, NaN v telemetrii) – viz sekce 3.
5. **Vícekriteriálnost:** existuje jedno skalární `TotalScore` pro řazení, ale akceptace kandidáta vyžaduje splnění omezujících podmínek na všech chráněných metrikách (sekce 5.3). Zlepšení jedné metriky nesmí prolomit žádnou z nich.

---

## 3. Seznam testovacích scénářů

Každý scénář má: `id`, účel, pokrytí kapitoly 7, trať, počáteční podmínky, profil řidiče, měřené metriky, abort kritéria, počet opakování.

Konvence povrchů: `DRY_ASPHALT` (referenční), `WET_ASPHALT` (nižší frikce), `MIXED` (změna povrchu v polovině), `BUMP` (příčné nerovnosti definované amplitudy/vlnové délky – konkrétní hodnoty určí FÁZE 9 podle testovací tratě).

### S1 – Akcelerace 0–100 km/h (výkon)

- **Účel:** čas akcelerace, průběh výkonu, trakce při rozjezdu, reakce motoru + převodovky.
- **Pokrytí kap. 7:** Výkon (akcelerace, průběh výkonu, reakce motoru), Trakce (prokluz, rozjezd).
- **Trať:** rovina ≥ 800 m, `DRY_ASPHALT`, bez sklonu.
- **Počáteční podmínky:** v = 0, volnoběh, zatížení: řidič (75 kg ekvivalent) – viz sekce 8 (předpoklad, nutno sjednotit s FÁZÍ 5).
- **Řidič:** plný plyn od t=0 (s definovanou rampou 0 → 1 za 0.2 s, aby nebyl skok), automatické řazení v optimálních otáčkách (strategie verzovaná v `driver_version`), volant = 0.
- **Metriky:** `t_0_60`, `t_0_100`, `t_400m` (volitelně), `slip_ratio_max_launch`, `gear_shift_count`, křivka `v(t)`.
- **Abort:** opuštění pruhu > 2 m, `roll > 45°`, timeout 60 s, nedosažení 100 km/h.
- **Opakování:** 5× (statistický základ, sekce 5.5).

### S2 – Maximální rychlost V-max (výkon)

- **Účel:** V-max, stabilita ve vysoké rychlosti, průběh výkonu na horním konci.
- **Pokrytí:** Výkon (V-max), Robustnost (stabilita při různých rychlostech).
- **Trať:** rovina ≥ 3000 m (nebo ovál s velkým poloměrem, pokud rovina nestačí – rozhodnutí FÁZE 9), `DRY_ASPHALT`.
- **Řidič:** plný plyn, držet příměr; řazení automatické.
- **Metriky:** `v_max` (ustálená, definice viz 4.1), `t_to_vmax`, `yaw_rate_rms_high_speed`, `lat_deviation_rms`.
- **Abort:** stejné jako S1 + `yaw_rate > 30°/s` při přímé jízdě.
- **Opakování:** 3× (dlouhý běh, menší počet + delší ustálení).

### S3 – Brzdění 100–0 km/h (brzdění)

- **Účel:** brzdná dráha, zpomalení, stabilita při brzdění, opakovatelnost.
- **Pokrytí:** Brzdění (všechny 4 podbody).
- **Trať:** rovina, `DRY_ASPHALT` + varianta `WET_ASPHALT` (S3b).
- **Počáteční podmínky:** ustálených 100 km/h (±1 km/h tolerance vstupu do brzdné zóny), plyn = 0.
- **Řidič:** v brzdné zóně plná brzda (rampa 0 → 1 za 0.15 s), volant = 0, ABS dle konfigurace varianty (zapnuto/vypnuto je parametr varianty, ne řidiče).
- **Metriky:** `brake_distance_100_0`, `mean_decel`, `peak_decel`, `stopping_time`, `lat_deviation_braking`, `yaw_rate_max_braking`.
- **Abort:** protočení (`yaw > 90°`), opuštění pruhu > 2 m, převrácení.
- **Opakování:** 5× na každém povrchu.

### S4 – Konstantní poloměr / skidpad (ustálená zatáčka, under/oversteer)

- **Účel:** laterální limit, nedotáčivost/přetáčivost v ustáleném stavu.
- **Pokrytí:** Ovládání (průjezd zatáčkou, nedotáčivost, přetáčivost, stabilita).
- **Trať:** kruh konstantního poloměru R (návrh: R = 30 m; finální hodnotu určí FÁZE 9 podle měřítka tratě), `DRY_ASPHALT`.
- **Řidič:** stopař drží kruh; rychlost se zvyšuje po krocích 5 km/h na běh, dokud není dosažen limit (nedodržení poloměru nebo `lat_accel` plateau).
- **Metriky:** `a_lat_max_steady`, `understeer_gradient` (viz 4.3), `steer_angle_vs_lat_accel` křivka, `yaw_vs_steer_coherence`.
- **Abort:** vyjetí z koridoru ±2 m od kruhu, smyk (`sideslip β > 20°`), převrácení.
- **Opakování:** 3× na rychlostní krok.

### S5 – Dvojitá změna pruhu / losí test (přechodová stabilita)

- **Účel:** přechodová odezva řízení, stabilita, přetáčivost po rychlém manévru.
- **Pokrytí:** Ovládání (odezva řízení, stabilita), Podvozek (náklon, přenos hmotnosti).
- **Trať:** rovina s kužely dle ISO 3888-2 (rozměry škálované na šířku vozidla; přesné rozměry určí FÁZE 9).
- **Počáteční podmínky:** vstupní rychlost 60 km/h (stupňovitě 60/70/80, dokud projde bez shození/překročení).
- **Řidič:** předem definovaný profil natočení volantu jako funkce dráhy (replay, ne reaktivní regulátor – zajišťuje identické vstupy pro každou variantu).
- **Metriky:** `passed` (ano/ne), `max_entry_speed_passed`, `yaw_rate_overshoot`, `sideslip_max`, `roll_max`, `settling_time`.
- **Abort:** kontakt s kuželem (virtuálním), `roll > 45°`, hodiny (`yaw > 180°`).
- **Opakování:** 3× na rychlost.

### S6 – Slalom (odezva řízení)

- **Účel:** odezva řízení, agilita vs. stabilita.
- **Trať:** 10 kuželů, rozteč 18 m (škálovatelná; určí FÁZE 9).
- **Řidič:** stopař s preview (pure-pursuit, pevné parametry v `driver_version`).
- **Metriky:** `min_time_slalom`, `yaw_gain`, `steer_effort_rms`, počet shozených koridorů.
- **Opakování:** 3×.

### S7 – Nerovnosti / rozbitý povrch (podvozek)

- **Účel:** vertikální pohyb, komprese/odskok, kontakt pneumatik, odolnost simulace.
- **Pokrytí:** Podvozek (všechny podbody), Robustnost (odolnost proti nestabilitě simulace).
- **Trať:** rovina 400 m s definovaným polem nerovností (sinus + náhodné hrboly ze seedu; amplituda/vlnová délka verzovaná).
- **Řidič:** rychlostní regulátor 60 km/h.
- **Metriky:** `vert_accel_rms`, `suspension_travel_max/min` na kolo, `tire_contact_loss_time` (čas bez kontaktu), `pitch_rms`, `roll_rms`.
- **Abort:** ztráta kontaktu všech 4 kol > 0.5 s (let – neplatný běh pro tuto metriku), převrácení, NaN.
- **Opakování:** 5× (s pevným seedem nerovností – stejné hrboly pro všechny varianty).

### S8 – Změna povrchu / split-mu (trakce + stabilita)

- **Účel:** chování při náhlé změně adheze, trakce různých pohonů (FWD/RWD/AWD).
- **Pokrytí:** Trakce, Robustnost (různé povrchy).
- **Trať:** rovina, v polovině skok `DRY → WET` (S8a při akceleraci 0–80), varianta split-mu (levá/pravá strana různá frikce, S8b při brzdění ze 60).
- **Metriky:** `slip_ratio_max`, `traction_time_loss`, `yaw_disturbance` (max |yaw_rate| po změně), `lat_deviation_after_change`.
- **Opakování:** 5×.

### S9 – Zatížení (robustnost + podvozek)

- **Účel:** citlivost na hmotnost (prázdný vs. plný).
- **Pokrytí:** Robustnost (různé zatížení), Podvozek (světlá výška, dosednutí).
- **Trať:** kombinace S1 (krátká akcelerace) + S7 (krátké nerovnosti) + S3 (jedno brzdění).
- **Podmínky:** 3 úrovně: `EMPTY` (jen řidič), `HALF` (+200 kg), `FULL` (+400 kg, nebo max. užitečná dle reference). Těžiště nákladu v kufru / rovnoměrně – definuje FÁZE 9.
- **Metriky:** delta `t_0_100`, delta `brake_distance`, `suspension_bottoming_count` (dosednutí na dorazy), `ground_clearance_min`.
- **Opakování:** 3× na úroveň.

### S10 – Ustálená vysokorychlostní stabilita + boční vítr (robustnost)

- **Účel:** stabilita při různých rychlostech, odolnost proti poruše.
- **Trať:** rovina, rychlostní regulátor 130 km/h (nebo 80 % V-max reference, podle toho, co je nižší – bezpečnost simulace).
- **Porucha:** definovaný boční impuls (náraz větru `F_lat` po dobu 1 s, velikost verzovaná) v t = 10 s.
- **Metriky:** `lat_deviation_max_gust`, `recovery_time` (návrat do ±0.3 m), `yaw_rate_max_gust`.
- **Opakování:** 5×.

### S11 – Kruhový test trakce / rozjezd do kopce (pohon)

- **Účel:** přenos výkonu, chování FWD/RWD/AWD, diferenciály.
- **Trať:** svah 10 % (sklon verzovaný), start z klidu do kopce, `DRY` + varianta `WET`.
- **Metriky:** `hill_launch_success` (ano/ne), `slip_time_total`, ` rollback_distance`.
- **Opakování:** 5×.

### Minimální matice pro optimalizační smyčku vs. plná validace

- **Rychlá smyčka** (každý kandidát): S1, S3 (dry), S4 (3 rychlostní kroky), S5 (60 km/h), S7 (krátká verze). Důvod: pokrývá výkon/brzdy/zatáčku/stabilitu/podvozek za přijatelný čas.
- **Plná validace** (nejlepší kandidát před povýšením na `best`): všechny S1–S11 včetně wet/split/full-load variant.
- Počty opakování výše jsou návrhem; FÁZE 9 je upraví podle naměřeného rozptylu (sekce 5.5).

---

## 4. Telemetrie, metriky a výpočty

### 4.1 Telemetrické kanály (vzorkování ≥ 60 Hz simulačního času)

| Kanál | Jednotka | Zdroj | Poznámka |
|---|---|---|---|
| `t_sim` | s | engine | Simulační čas, ne wall-clock. Základ všech derivací. |
| `v_long`, `v_lat` | m/s | stav vozidla | Podélná/příčná rychlost v souřadnicích vozidla. |
| `v_kmh` | km/h | odvozeno | `v_kmh = 3.6 * sqrt(v_long² + v_lat²)`; pro S1–S3 se používá `v_long`. |
| `a_long`, `a_lat` | m/s² | IMU/stav | Filtrovaný dolní propustí (cutoff určí FÁZE 9; návrh 10 Hz) před RMS metrikami. |
| `yaw_rate` | rad/s | stav | Kolem svislé osy. |
| `roll`, `pitch` | rad | stav | Náklon/klopení karoserie. |
| `steer_angle` | rad | řidič | Skutečné natočení kol (ne volantu), průměr přední nápravy. |
| `throttle`, `brake` | 0–1 | řidič | Pro kontrolu determinismu vstupů. |
| `rpm`, `gear` | 1/min, – | motor | Pro diagnostiku řazení. |
| `wheel_omega_FL/FR/RL/RR` | rad/s | kola | Pro výpočet skluzu. |
| `susp_travel_FL/FR/RL/RR` | m | podvozek | Zdvih od statické polohy (+ komprese). |
| `wheel_load_FL/FR/RL/RR` | N | kontakt | Normálová síla na kolo. |
| `tire_contact_FL/FR/RL/RR` | bool | kontakt | Kontakt s povrchem. |
| `slip_ratio` (na hnací kola) | – | odvozeno | Viz 4.2. |
| `sideslip_beta` | rad | odvozeno | `β = atan2(v_lat, |v_long|)`; při \|v_long\| < 1 m/s neplatné (flag). |
| `pos_x`, `pos_y` | m | trať | Odchylka od referenční čáry. |
| `engine_torque` | N·m | motor | Volitelné, pokud model poskytuje. |

Každý záznam `RunTrace` obsahuje: `scenario_id`, `scenario_version`, `driver_version`, `variant_id`, `seed`, `physics_dt`, vzorkovací frekvenci, jednotky, abort flag + důvod.

### 4.2 Definice klíčových metrik

- **Časy akcelerace:** `t_0_100` = první `t_sim`, kdy `v_long ≥ 27.78 m/s` (100 km/h), měřeno od startu povelu plného plynu. Interpolace mezi vzorky lineárně. Stejně `t_0_60` (16.67 m/s).
- **Ustálená V-max:** průměr `v_long` za posledních 5 s běhu, pokud `std(v_long) < 0.5 m/s` v tomto okně; jinak `v_max = max` s flagem `not_settled`.
- **Brzdná dráha:** dráha `s` od vstupu do brzdné zóny (povel brzdy = 1) do `v_long < 0.1 m/s`: `s = ∫ v_long dt` (lichoběžníková integrace). `mean_decel = v₀² / (2·s)`, kde `v₀` = skutečná vstupní rychlost (korekce na odchylku od 100 km/h).
- **Skluz (slip ratio), hnací kolo:** `κ = (ω·r − v_wx) / max(|v_wx|, ε)`, kde `v_wx` = podélná rychlost středu kola, `r` = valivý poloměr (z varianty), `ε = 1.0 m/s` (ochrana proti dělení nulou při rozjezdu). Při rozjezdu se navíc měří `slip_time_total` = čas s `|κ| > 0.2`.
- **Laterální zrychlení ustálené:** medián `a_lat` v prostředních 50 % kruhu S4 (ořez náběhu/ výjezdu).
- **Understeer gradient (S4):** směrnice `K_us = dδ / d(a_lat)` v lineární oblasti (regrese nejmenších čtverců přes rychlostní kroky před saturací), kde `δ` = průměrný úhel předních kol. `K_us > 0` = nedotáčivost, `< 0` = přetáčivost. Vyžaduje min. 3 platné kroky; jinak metrika `invalid` + flag.
- **RMS metriky:** `rms(x) = sqrt(mean(x²))` na vymezeném okně po filtraci. Platí pro `yaw_rate`, `vert_accel`, `lat_deviation`.
- **Dosednutí podvozku:** počet vzorků, kdy `susp_travel ≥ travel_max − 2 mm` (práh určí FÁZE 9 dle modelu).
- **Ztráta kontaktu:** `tire_contact_loss_time` = celkový čas, kdy dané kolo má `contact = false` (S7, mimo letový abort).

### 4.3 Odchylky od reference a normalizace

Pro každou metriku `m` s referenční hodnotou `ref` a tolerancí `tol` (z `ReferenceProfile`, FÁZE 5):

- **Relativní odchylka (cíl = hodnota):** `dev = (m − ref) / max(tol, |ref|·tol_rel)`.
  - `tol_rel` návrh: 3 % pro časy/drhy/rychlosti, 10 % pro komfortní RMS (vert. zrychlení), 5 % pro brzdnou dráhu. Finální hodnoty určí FÁZE 5 + 9 podle důvěryhodnosti zdroje reference.
- **Cíl = minimum** (např. brzdná dráha při chybějící referenci): `dev = (m − best_known) / scale`, kde `scale` = počáteční rozptyl.
- **Cíl = maximum** (např. `a_lat_max`): `dev = (best_known − m) / scale`.
- **Binární průchod** (S5/S11): `dev = 0` při průchodu, `dev = −1 + (v_entry / v_target)` při neúspěchu (čím vyšší rychlost selhání, tím menší penalizace – návrh, validuje FÁZE 9).

### 4.4 Agregované skóre (vícekriteriální)

Vážený součet normalizovaných odchylek po skupinách kapitoly 7:

```
GroupScore_g  = mean(dev_m)  za metriky m ve skupině g
TotalScore    = Σ_g W_g · GroupScore_g  +  Σ_k P_k · penalty_k
```

- **Váhy `W_g` (návrh, součet = 1):** Výkon 0.25, Brzdění 0.20, Ovládání 0.25, Podvozek 0.10, Trakce 0.10, Robustnost 0.10. Váhy jsou konfigurovatelné a verzované; nejsou fyzikální pravdou, ale inženýrskou prioritou (schvaluje FÁZE 10 / koordinátor).
- **Penalizace `penalty_k`:** tvrdé přičtení za porušení bezpečnosti/stability: převrácení, protočení, opuštění tratě, NaN, ztráta kontaktu nad prahem. Hodnota `P_k` je řádově větší než typické `GroupScore` (návrh: +10 za kritickou událost), takže nestabilní varianta nikdy nevyhraje na rychlost.
- **Chráněné metriky (tvrdá omezení):** `brake_distance`, `yaw_rate_overshoot_S5`, `roll_max_S5`, `tire_contact_loss_S7`, `lat_deviation_braking`. Kandidát, který jakoukoli chráněnou metriku zhorší nad `hard_limit` oproti `best`, je zamítnut bez ohledu na `TotalScore` (sekce 5.3).

### 4.5 Detekce nestability (běh je neplatný / varianta penalizována)

Běh je označen `UNSTABLE` (neplatný pro skóre, započítán do penalizace varianty), pokud nastane cokoli z:

1. `|roll| > 60°` nebo `|pitch| > 60°` (převrácení / salto).
2. NaN/Inf v jakémkoli kanálu (numerická nestabilita).
3. `pos` mimo trať o > 5 m (S1–S3, S7) nebo mimo koridor (S4–S6) po dobu > 1 s.
4. Teleport/skok: `|Δpos| > v·dt·5 + 1 m` mezi vzorky (detekce fyzikálního exploitu).
5. Ztráta kontaktu všech kol > 0.5 s v S1–S6 (let není platný průjezd).
6. `yaw_rate` překročí 120°/s mimo S5 manévr (rotace).

Prahové hodnoty jsou návrhem; FÁZE 9 je kalibruje na skutečném měřítku tratí. Tři po sobě jdoucí `UNSTABLE` u jedné varianty ⇒ varianta `REJECTED`, návrat k `best` (sekce 5.4).

### 4.6 Opakovatelnost a tolerance

- Každý scénář se opakuje N× (sekce 3). Metrika běhu = **medián** z platných opakování (odolný proti odlehlým hodnotám); rozptyl = IQR (mezikvartilové rozpětí).
- **Determinismus řidiče:** vstupy `u(t)` musí být bitově identické mezi opakováními (kontroluje hash vstupní sekvence). Pokud se liší, chyba je v řidiči, ne ve vozidle – běh neplatný.
- **Fyzikální rozptyl:** pokud IQR metriky u `best_variant` překročí `repeat_tol` (návrh: 2 % pro časy, 3 % pro dráhy, 5 % pro RMS), scénář je označen `FLAKY` a optimalizér na něm nesmí stavět akceptační rozhodnutí (pouze diagnostika) do opravy tratě/seedů.
- Verze tratě, řidiče a `physics_dt` jsou součástí `run_id`; změna kterékoli z nich invaliduje historické porovnání (nutný re-baseline `best`).

### 4.7 Kalibrace a re-baseline

1. Před každou optimalizační kampaní se změří `baseline = metrics(best_variant)` na aktuálních verzích tratí/řidiče (min. plná matice 1× + rychlá matice pro statistiku).
2. Po jakékoli změně tratě/řidiče/fyzikálního kroku se `baseline` přeměří; staré `TotalScore` se nesmí míchat s novými.
3. Všechny jednotky SI; převody (mph → km/h, ft → m) explicitně v `TelemetryRecorder`, nikdy v metrikách.

---

## 5. Autonomní optimalizační algoritmus

### 5.1 Vstupy, výstupy, invarianty

- **Vstup:** `best_variant`, `ReferenceProfile` (cíle + tolerance + váhy), parametrový prostor s mezemi (z Chassis Intelligence / FÁZE 8: který parametr, min–max, krok, závislost), rozpočet (max. běhů / max. času), `hard_limits` chráněných metrik.
- **Výstup:** nová `best_variant` (nebo potvrzení stávající) + historie všech kandidátů + report (sekce 6.5).
- **Invarianty:**
  - I1: `best_variant` je vždy platná, testovaná, revertibilní (pointer + neměnná data).
  - I2: žádný kandidát se nestane `best` bez plné validace (sekce 3) a statistického testu (5.5).
  - I3: žádný kandidát nezhorší chráněnou metriku nad `hard_limit` (5.3).
  - I4: každá změna má zdůvodnění (která odchylka → který parametr → očekávaný směr), dle principu č. 2.

### 5.2 Generování kandidátů (strategie)

1. **Jednoparametrické sondy (koordinátní sestup):** pro top-K parametrů dle citlivosti (5.6) vygeneruj `±krok`. Slouží k odhadu gradientu/směru. Levné, interpretovatelné, první volba na začátku kampaně.
2. **Lokální mutace:** náhodná perturbace 1–2 parametrů v mezích (uniformní v normalizovaném prostoru). Udržuje diverzitu, uniká z plošin.
3. **Rekombinace (elitní):** křížení dvou nejlepších historických variant (průměr / náhodná volba po parametrech). Pouze pokud oba rodiče prošli plnou validací.
4. **Modelový návrh (volitelný, pozdější fáze):** náhrada náhodné mutace Bayesovským návrhem (Gaussian Process na `TotalScore`) – až po dostatku dat (≥ 30 vyhodnocených kandidátů). Není povinný pro první implementaci; nesmí být jediným generátorem (riziko modelové slepoty).
5. **Bezpečnostní filtr před testem:** kandidát mimo meze, s porušenou závislostí (např. `gear_ratio` neuspořádané, součet brzdného biasu ≠ 100 %) nebo s krokem větším než `max_step` je zamítnut bez testu (důvod zalogován).

Pořadí v kampani: začni sondami (interpretabilita) → mutace/rekombinace (průzkum) → modelové návrhy (exploatace). Poměr průzkum/exploatace verzovaný (návrh počátečního: 50 % sondy, 30 % mutace, 20 % rekombinace).

### 5.3 Vícekriteriální akceptační pravidlo (zákaz jednostranného zlepšení)

Kandidát `C` je přijat jako nový `best` **právě tehdy**, když platí **všechny** podmínky:

```
A1: TotalScore(C)  <  TotalScore(best) − margin
    (margin = max(stat_margin, 0.5 % · |TotalScore(best)|); stat_margin ze sekce 5.5)

A2: pro každou chráněnou metriku p:
    metric_p(C) ≤ metric_p(best) + hard_limit_p
    (hard_limit_p: např. brzdná dráha +1 %, roll_max +2 %, yaw_overshoot +5 %;
     nulová tolerance pro převrácení/protočení – jakýkoli výskyt = zamítnutí)

A3: žádný běh C v plné validaci není UNSTABLE (4.5) a počet abortů ≤ počet abortů best.

A4: statistický test zlepšení je pozitivní (5.5) – není náhoda.

A5: ValidationGate RUNTIME (je-li v této kampani vyžadován) prošel (6.4).
```

Příklad zakázaného obchodu: `t_0_100` −8 % ale `brake_distance` +3 % ⇒ A2 selže ⇒ zamítnuto, i když `TotalScore` kleslo. Pravidlo je záměrně konzervativní: falešné odmítnutí je levné (další kandidát), falešné přijetí drahé (ztráta stability).

### 5.4 Rollback a uchování nejlepší varianty

- `VariantStore` drží: `best_id`, `best_result` (plná validace + statistika), frontu kandidátů, archiv zamítnutých (s důvodem: která podmínka A1–A5 selhala).
- **Rollback** = atomické přepnutí `best_id` zpět na předchozí `best` (kandidát se nikdy nestává `best` destruktivně). Protože varianty jsou neměnné, rollback je O(1) a nemůže selhat na částečném přepisu.
- **Okamžitý rollback během kampaně:** pokud 3 po sobě jdoucí kandidáti selžou na A2/A3 (stabilita), optimalizér se vrátí k jednoparametrickým sondám s polovičním krokem (předpoklad: přestřelil krok, ne špatný směr). Po 2 takových halvingech bez úspěchu ⇒ STOP (konvergence/plató).
- Každý rollback je zalogován: `from_id → to_id`, důvod, metriky, které selhaly.

### 5.5 Statistické ověření zlepšení (ne náhoda)

Pro každé akceptační rozhodnutí se porovnávají **distribuce opakování** `best` vs. `C` (ne jednotlivé běhy):

1. **Primární test (neparametrický):** Mann-Whitney U test na `TotalScore` jednotlivých běhů rychlé matice (n ≥ 5 na stranu), hladina `α = 0.05`. Důvod neparametrického: metriky (časy, dráhy) nebývají normální a n je malé.
2. **Velikost efektu:** mediánový rozdíl `Δ = median(C) − median(best)` musí překročit `praktický práh` (návrh: 1 % `TotalScore` nebo příslušnou `tol` metriky). Statisticky významné, ale prakticky nulové zlepšení se nepřijímá (šetří rozpočet, brání driftu).
3. **Konzistence napříč scénáři:** žádný scénář rychlé matice se nesmí zhoršit o více než `scenario_tol` (návrh 3 %) ani při splněném celkovém testu – druhá vrstva zákazu jednostrannosti na úrovni scénářů.
4. **Potvrzení na plné matici:** kandidát, který projde 1–3 na rychlé matici, se změří plnou maticí (3–5 opakování); A1–A4 se přepočítají na plných datech. Teprve pak povýšení.
5. **FLAKY stopka:** je-li zapojený scénář označen `FLAKY` (4.6), rozhodnutí se odkládá (stav `UNDECIDED`), neschvaluje.

Minimální rozpočty: rychlé rozhodnutí ≥ 5+5 běhů, povýšení na `best` ≥ plná matice obou variant. Méně není důkaz, jen indikace.

### 5.6 Citlivost a priorita parametrů (kterým směrem hledat)

- Po každé sadě sond spočítej **jednorozměrnou citlivost**: `S_p = ΔTotalScore / Δp_norm` pro parametr `p` (normalizovaný krok). Seřaď `|S_p|` – největší řídí další sondy.
- **Korelace s odchylkami (diagnostika, ne důkaz):** pro interpretaci `která odchylka → který parametr` drž matici očekávaných vazeb (návrh počáteční, validuje FÁZE 6/8):
  - `t_0_100` vysoké → výkon/moment, převodové poměry, grip hnacích kol, hmotnost.
  - `v_max` nízká → výkon ve vysokých otáčkách, nejvyšší převod, odpor (je-li modelován).
  - `brake_distance` dlouhá → brzdný moment, bias, grip.
  - nedotáčivost (`K_us > 0` velké) → tuhost přední nápravy / zadní stabilizátor, tlak/grip, geometrie.
  - přetáčivost (`K_us < 0`) → opačně + diferenciál, rozdělení momentu.
  - `roll_max` velký → pružiny/stabilizátory/tlumiče, těžiště.
  - `slip` velký → grip, diferenciál, dávkování momentu, AWD bias.
- Citlivost se přeměřuje po každém povýšení `best` (krajina se mění). Historické `S_p` se nezdědí bez re-sondy.

### 5.7 Zastavovací podmínky (kdy přestat)

Kampaň končí při **prvním** splněném:

1. **Cíl splněn:** všechny metriky s referencí jsou v `tol` a žádná chráněná metrika není na hraně (`< 80 % hard_limitu`) – stav `TARGET_MET`.
2. **Rozpočet vyčerpán:** max. běhů / max. času – stav `BUDGET_OUT` (návrh limitů určí FÁZE 10 podle ceny běhu; každý návrh kandidáta musí rozpočet kontrolovat před testem).
3. **Konvergence:** posledních K kandidátů (návrh K = 10) bez přijetí + 2 halving kroku – stav `CONVERGED`.
4. **Nestabilita:** podíl `UNSTABLE` běhů v kampani > 20 % – stav `UNSTABLE_STOP` (chyba je v prostoru/mezích, ne v počtu pokusů; vyžaduje lidský/architektonický zásah – změnu mezí, ne další kandidáty).
5. **Degradace prostředí:** scénář označen `FLAKY` na kritické metrice – stav `ENV_BLOCKED` (opravit trať, pak re-baseline).

### 5.8 Pseudokód hlavní smyčky

```python
# Jazyk: Python (pseudokód). Identifikátory anglicky.
# Vstupy: best, reference, param_space, budget, hard_limits, weights

def optimize(best, reference, param_space, budget, hard_limits, weights):
    baseline = full_validation(best)          # re-baseline na aktuálních tratích
    store.save_baseline(best, baseline)
    step_scale = 1.0

    while not budget.exhausted():
        # 1. Diagnóza: největší odchylky + citlivosti
        gaps = rank_gaps(baseline, reference)          # seřazené odchylky (sekce 4.3)
        sensitivities = probe_sensitivities(best, param_space, step_scale)
        # 2. Generování kandidátů (sekce 5.2)
        candidates = generate_candidates(
            best, gaps, sensitivities, param_space, strategy_mix, store.history
        )
        accepted_in_round = False

        for cand in candidates:
            if budget.exhausted():
                break
            if not safety_filter(cand, param_space):   # meze, závislosti, max_step
                store.reject(cand, reason="SAFETY_FILTER")
                continue

            # 3. Rychlá matice: S1, S3dry, S4, S5-60, S7short (sekce 3)
            quick = run_quick_matrix(cand)             # N opakování, medián + IQR
            if unstable_rate(quick) > 0:
                store.reject(cand, reason="UNSTABLE_QUICK")
                continue
            if violates_hard_limits(quick, baseline, hard_limits):  # A2 předběžně
                store.reject(cand, reason="HARD_LIMIT")
                continue
            if not stat_test_passes(quick, baseline_quick, alpha=0.05):  # A4 předběžně
                store.reject(cand, reason="NO_SIGNIFICANT_GAIN")
                continue

            # 4. Plná validace kandidáta (sekce 3: S1–S11)
            full = full_validation(cand)
            decision = acceptance_decision(full, baseline, hard_limits, weights)  # A1–A5
            if decision.accept:
                store.promote(cand, full, reason=decision.summary)  # atomický pointer swap
                best, baseline = cand, full
                sensitivities = {}        # krajina se změnila → re-sonda v dalším kole
                accepted_in_round = True
                break                     # nové kolo od nového best
            else:
                store.reject(cand, reason=decision.failed_condition)
                rollback_to(best)         # pointer zůstává; explicitní auditní záznam

        # 5. Adaptace kroku / zastavení (sekce 5.4, 5.7)
        if not accepted_in_round:
            step_scale *= 0.5
            if step_scale < MIN_STEP_SCALE:
                return stop("CONVERGED", best)
        else:
            step_scale = min(1.0, step_scale * 1.2)

        if check_stop_conditions(store, budget):      # TARGET_MET / BUDGET_OUT /
            break                                     # UNSTABLE_STOP / ENV_BLOCKED

    return stop(decide_stop_reason(store, budget), best)


def acceptance_decision(full_cand, full_best, hard_limits, weights):
    # A1: celkové skóre s margínem
    total_cand = total_score(full_cand, weights)
    total_best = total_score(full_best, weights)
    margin = max(stat_margin(full_cand, full_best), 0.005 * abs(total_best))
    if not (total_cand < total_best - margin):
        return Reject("A1_TOTAL_SCORE")
    # A2: chráněné metriky
    for p, lim in hard_limits.items():
        if metric(full_cand, p) > metric(full_best, p) + lim:
            return Reject(f"A2_HARD_LIMIT:{p}")
    # A3: stabilita
    if has_unstable(full_cand) or abort_count(full_cand) > abort_count(full_best):
        return Reject("A3_STABILITY")
    # A4: statistika (Mann-Whitney + praktický práh + konzistence scénářů)
    if not mann_whitney_passes(full_cand, full_best, alpha=0.05):
        return Reject("A4_STATISTICS")
    if median_gain(full_cand, full_best) < PRACTICAL_THRESHOLD:
        return Reject("A4_PRACTICAL_GAIN")
    if any_scenario_regressed(full_cand, full_best, tol=SCENARIO_TOL):
        return Reject("A4_SCENARIO_REGRESSION")
    # A5: runtime gate (je-li vyžadován)
    if runtime_gate_required() and not runtime_gate_passed(full_cand):
        return Reject("A5_RUNTIME")
    return Accept(f"gain={total_best - total_cand:.4f}")
```

### 5.9 Rozhraní (návrh API, stabilizuje FÁZE 10)

```
ScenarioSpec      { scenario_id, version, track, surface, initial_state, load, seed }
RunContext        { run_id, scenario, driver_version, variant_id, physics_dt }
ControlVector     { throttle: 0..1, brake: 0..1, steer: -1..1, gear: int | auto }
RunTrace          { context, samples[60+ Hz], abort_flag, input_hash }
RunResult         { trace_id, metrics{}, deviations{}, group_scores{}, total, verdicts }
CandidateVariant  { variant_id, parent_id, param_diff{}, rationale }
AcceptanceDecision{ accept: bool, failed_condition, summary, stats{} }
```

---

## 6. Od testu k důkazu: validace a reportování

### 6.1 Co se měří kde (oddělení úrovní)

| Úroveň | Co to je | K čemu slouží | Co netvrdí |
|---|---|---|---|
| MATH | Jednotkové výpočty metrik z umělých dat (offline, bez fyziky). | Správnost vzorců 4.2–4.4, integrace, interpolace. | Nic o vozidle. |
| SIM | Lokální simulace (rychlý filtr kandidátů). | Pořadí kandidátů, citlivosti, předvýběr. | Není důkaz chování v Robloxu. |
| RUNTIME | Skutečný Roblox runtime test (sekce 6.4). | Jediný platný důkaz pro finální tvrzení. | — |

Každý report musí u každého čísla uvést úroveň (MATH/SIM/RUNTIME). Číslo bez úrovně je neplatné.

### 6.2 Regresní politika

- Po každém povýšení `best` se spustí **regresní sada**: rychlá matice na všech dříve projetých scénářích + kontrola, že žádná dříve splněná `tol` se nerozbila.
- Každá změna tratě/řidiče/fyzikálního kroku ⇒ povinný re-baseline + plná regresní sada před pokračováním kampaně.
- Historie `VariantStore` je append-only; mazání historie je zakázáno (auditovatelnost).

### 6.3 Fyzikální sanity kontroly (před skóre)

Před výpočtem `TotalScore` musí projít:

1. Zachování řádu: `t_0_100` v (1 s, 60 s), `v_max` v (20, 400 km/h), `brake_distance_100_0` v (10, 300 m). Mimo ⇒ `SUSPECT` (chyba měření, ne super-výsledek).
2. Konzistence: `mean_decel ≈ v₀²/(2·s)` (±5 %); `∫v dt ≈ dráha` (±2 %). Nesoulad ⇒ chyba integrace/vzorkování.
3. Determinismus vstupů: hash `u(t)` shodný napříč opakováními. Neshoda ⇒ chyba řidiče.

### 6.4 Roblox runtime brána (návrh; detail patří FÁZI 9/12 + `ROBLOX-RUNTIME.md`)

- RUNTIME test = stejný `ScenarioSpec` + stejný `AutonomousDriver` (portovaný do Robloxu) + telemetrie zapsaná zevnitř runtime.
- Požadavky: verzovaná runtime trať (stejná geometrie/povrchy jako SIM v mezích dokumentované tolerance), stejné počáteční podmínky, stejný `physics_dt` (nebo zdokumentovaný rozdíl + re-baseline).
- Povýšení na finální `best` vyžaduje RUNTIME průchod plné matice (alespoň 3 opakování na scénář rychlé matice + 1× plná matice). SIM-only `best` se označuje `UNCONFIRMED_RUNTIME` a nesmí do exportu (FÁZE 13).
- Rozdíl SIM vs. RUNTIME nad `sim2runtime_tol` (návrh 5 % na časech/drahách) ⇒ stav `SIM_DRIFT`: zastavit optimalizaci v SIM, diagnostikovat model, ne pokračovat v ladění proti chybnému simulátoru.

### 6.5 Minimální obsah reportu kampaně (pro Export, FÁZE 13)

1. `best_variant_id` + úplný `param_diff` proti výchozí variantě + zdůvodnění každé změny (I4).
2. Tabulka metrik: reference / baseline / best, odchylky, `tol`, úroveň důkazu u každého čísla.
3. Historie kandidátů: počet testovaných/přijatých/zamítnutých + důvody zamítnutí (A1–A5).
4. Statistika: n, medián, IQR, výsledek Mann-Whitney, velikost efektu.
5. Stabilita: počet `UNSTABLE`/abortů, seznam incidentů.
6. Známá omezení a `FLAKY` scénáře.
7. Verze: tratě, řidič, `physics_dt`, seed, commit/diff identifikátory.

---

## 7. Rizika a omezení návrhu

1. **Sim-to-real propast (SIM vs. Roblox):** lokální simulace může řadit kandidáty jinak než runtime. Mitigace: SIM jen filtr, RUNTIME brána (6.4), `SIM_DRIFT` stopka. Bez ní hrozí přetrénování na chybu simulátoru.
2. **Cena běhů:** plná matice × opakování × kandidáti = stovky až tisíce běhů. Mitigace: rychlá matice jako filtr, statistické minimum (5+5), rozpočtová stopka, modelové návrhy až při dostatku dat.
3. **Řidič jako skrytá proměnná:** nedeterministický nebo reaktivně odlišně reagující řidič znehodnotí porovnání (lepší čas = lepší řidič, ne lepší auto). Mitigace: replay profilů u manévrů (S5), hash vstupů, verzování `driver_version`, re-baseline při změně.
4. **Váhy nejsou fyzika:** `W_g` a `hard_limit_p` jsou inženýrské volby; špatné váhy = formálně optimální, ale řidičsky špatné auto (např. přetáčivé, ale rychlé). Mitigace: konzervativní A2/A4, povinná S5/S4 stabilita v rychlé matici, lidské schválení vah před kampaní.
5. **Plošiny a lokální minima:** koordinátní sondy uváznou. Mitigace: mutace/rekombinace, halving kroku max. 2×, pak STOP místo nekonečného vrtání.
6. **FLAKY tratě:** křehká trať (citlivá na seed/pořadí) produkuje falešná přijetí/odmítnutí. Mitigace: `FLAKY` detekce (4.6), `ENV_BLOCKED` stopka.
7. **Numerická nestabilita fyziky:** tuhé odpružení / velký `physics_dt` ⇒ exploze. Mitigace: abort kritéria, `UNSTABLE` kvóta (5.7/4), sanity kontroly (6.3). Nikdy neladit parametry tak, aby obcházely nestabilitu (např. tlumením na úkor reality) bez záznamu v omezeních.
8. **Chybějící reference:** bez `ref`/`tol` z FÁZE 5 nelze počítat odchylky – optimalizér by maximalizoval bez cíle. Mitigace: bez reference pouze `best_known` relativní cíle + explicitní flag `NO_REFERENCE` v reportu; nikdy netvrdit shodu s reálným vozem.
9. **Zatížení a povrchy jako kombinatorická exploze:** S3×2 povrchy × S9×3 zatížení × opakování. Mitigace: rychlá vs. plná matice, wet/full-load jen ve validaci, ne v každé sondě.
10. **Bezpečnost dat:** destruktivní přepsání `best`. Mitigace: neměnné varianty + pointer swap + append-only historie (I1, 5.4).

---

## 8. Fakta / předpoklady / neznámé / další kroky

### 8.1 Ověřená fakta (zdroje)

- F1: Rozsah tohoto návrhu je vymezen kapitolami 5.10–5.14 a 7 dokumentu `C:/.DATA/AutoEngineerAI/docs/PROJECT-PLAN.md` (Test Environment, Autonomous Driver, Telemetry and Evaluation, Autonomous Optimizer, Validation System; hodnoticí kritéria Výkon/Brzdění/Ovládání/Podvozek/Trakce/Robustnost). Zdroj: `read_file PROJECT-PLAN.md`, řádky 326–404 a 650–694.
- F2: Systém musí být vícekriteriální s explicitním zákazem zlepšit jednu vlastnost na úkor celku (akcelerace vs. stabilita jako uvedený příklad). Zdroj: `PROJECT-PLAN.md` §5.13, řádek 392.
- F3: Výsledky testů musí být reprodukovatelné v definovaných tolerancích; důkazní úrovně MATH/SIM/RUNTIME se rozlišují a neověřená simulace se nesmí vydávat za důkaz. Zdroj: `PROJECT-PLAN.md` §5.11 řádek 355, §5.14 řádek 404, hlavní princip č. 10.
- F4: Každá varianta musí být verzovaná, nejlepší výsledek zachován, neúspěšné změny vráceny; optimalizace má definované zastavení (cíl/limit). Zdroj: `PROJECT-PLAN.md` §5.13 body 9–10, FÁZE 10.
- F5: Pravidla práce: česky, identifikátory anglicky; vlastněn je pouze tento soubor; `C:/.DATA/RobloxSimulator` je read-only; originál `chasis.rbxm` se nepřepisuje. Zdroj: `C:/.DATA/AutoEngineerAI/docs/AGENT-RULES.md` (všech 10 bodů).
- F6: Cílový adresář `C:/.DATA/AutoEngineerAI/docs/` existuje a obsahuje `AGENT-RULES.md`, `ARCHITECTURE.md`, `PROJECT-PLAN.md`, `ROBLOX-RUNTIME.md`, `STATUS.md`. Zdroj: `terminal ls` tohoto úkolu.

### 8.2 Předpoklady (neověřeno, musí potvrdit příslušné fáze)

- P1: Simulační čas je dostupný s přesností pro vzorkování ≥ 60 Hz a `physics_dt` je fixní/zdokumentovaný. (Bez toho neplatí 4.1/4.6.) Potvrdí FÁZE 9.
- P2: Valivý poloměr kol, hmotnost nákladu (75 kg řidič; HALF +200 kg; FULL +400 kg), rozměry tratí (R = 30 m, slalom 18 m, kužely ISO 3888-2) jsou škálovatelné na model – konkrétní čísla v tomto dokumentu jsou návrhy, ne specifikace. Potvrdí FÁZE 5/9.
- P3: Parametrový prostor má spojité meze a známé závislosti (z Chassis Intelligence). Bez nich nefunguje bezpečnostní filtr (5.2). Potvrdí FÁZE 1/8.
- P4: Referenční profil poskytne `ref + tol + důvěryhodnost` pro klíčové metriky (jinak platí režim `NO_REFERENCE`, sekce 7 bod 8). Potvrdí FÁZE 5.
- P5: Mann-Whitney U + medián/IQR jsou adekvátní pro n = 3–5; praktické prahy (1 % TotalScore, 3 % scénář, α = 0.05) jsou kalibrovatelné po prvních měřeních rozptylu. Potvrdí FÁZE 9/10 prvním baseline měřením.
- P6: Roblox runtime unese portovaného `AutonomousDriver` a telemetrický zápis bez zkreslení fyziky (nebo je zkreslení měřitelné). Potvrdí FÁZE 9/12 + `ROBLOX-RUNTIME.md`.

### 8.3 Neznámé (nelze rozhodnout v tomto dokumentu)

- N1: Skutečná cena jednoho běhu (SIM vs. RUNTIME) – určí rozpočet a poměr rychlá/plná matice.
- N2: Skutečný rozptyl metrik na reálných tratích – určí `repeat_tol`, `FLAKY` prahy, minimální n.
- N3: Které parametry A-Chassis jsou skutečně měnitelné za běhu a které vyžadují zásah do skriptů/konstrukce (hranice FÁZE 8 vs. 11).
- N4: Přesná geometrie testovacích tratí v Roblox měřítku (délky rovin, poloměry, kužely) – návrh v sekci 3 je funkční, ne metrický.
- N5: Finální váhy `W_g` a `hard_limit_p` – inženýrské rozhodnutí, ne odvození; vyžaduje schválení koordinátorem před první kampaní.
- N6: Zda bude k dispozici Bayesovská nadstavba (5.2 bod 4) – volitelná, neblokuje první implementaci.

### 8.4 Doporučené další kroky (pro koordinátora)

1. FÁZE 9: implementovat `TestEnvironment` + 3 pilotní scénáře (S1, S3-dry, S5-60) + `TelemetryRecorder` dle 4.1; změřit rozptyl → kalibrovat 4.6/5.5.
2. FÁZE 9: portovat `AutonomousDriver` (replay + rychlostní regulátor) do Roblox runtime; ověřit hash vstupů napříč opakováními.
3. FÁZE 5: dodat `ReferenceProfile` pro 1–2 pilotní vozy včetně `tol` a důvěryhodnosti (blokuje 4.3).
4. FÁZE 1/8: dodat parametrový prostor s mezemi a závislostmi (blokuje bezpečnostní filtr 5.2).
5. FÁZE 10: implementovat smyčku 5.8 s pravidlem A1–A5, `VariantStore` (append-only) a report 6.5; první kampaň na pilotních scénářích s `UNCONFIRMED_RUNTIME` flagem.
6. FÁZE 12: RUNTIME brána (6.4) + `SIM_DRIFT` detekce; teprve pak povyšovat na finální `best` pro export (FÁZE 13).
7. Koordinátor: schválit váhy `W_g`, `hard_limit_p`, rozpočty a prahy před první kampaní; verzovat je.

---

**Historie dokumentu:** v1 (2026-11-16) – počáteční návrh FÁZE 9–10. Změny verzovat s důvodem.
