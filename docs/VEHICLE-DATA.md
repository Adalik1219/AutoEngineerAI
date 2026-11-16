# Vehicle Reference Data — systém referenčních dat reálných vozidel

**Vlastník:** tento dokument + `vehicle-data/references/_schema.json` + `vehicle-data/references/example-vehicle.json`
**Kontext:** `C:/.DATA/AutoEngineerAI/docs/PROJECT-PLAN.md` kapitola 5.4 a 7, `C:/.DATA/AutoEngineerAI/docs/AGENT-RULES.md`
**Stav:** návrh v1 (FÁZE 5)

---

## 1. Účel

Modul Vehicle Reference Intelligence (5.4) dodává cílový technický profil reálného vozu pro fáze 6–7 a testovací kritéria kapitoly 7 (výkon, brzdění, ovládání, podvozek, trakce, robustnost). Každý údaj musí nést zdroj, důvěryhodnost a nejistotu (5.4: „Každý údaj musí mít informaci o zdroji, důvěryhodnosti a případné nejistotě").

## 2. Datový formát

### 2.1 Jeden soubor = jeden konkrétní vůz

Jeden JSON profil = jedna kombinace generace + motorizace + převodovky + karoserie + trhu. Důvod: hmotnost, převody, rozměry i výkon se mezi těmito variantami liší (viz ukázka: 2.0 MT má stálý převod 2.866, 2.0 AT 3.583; soft-top vs. RF se liší o ~50 kg).

Pojmenování: `vehicle-data/references/<vehicle-id>.json`, kde `vehicle-id` je lowercase slug, např. `mazda-mx5-nd-20-184-softtop-6mt-eu`.

### 2.2 Obálka hodnoty (povinná pro každé číslo)

```json
{ "value": 205, "unit": "Nm", "source": "Mazda AU brožura; auto-data",
  "source_type": "factory", "confidence": 1.0, "notes": null }
```

- `value` — číslo, řetězec (typové označení) nebo `null` (neznámé, viz 6).
- `unit` — kanonická jednotka (viz 8). Bez jednotky je záznam neplatný.
- `source` — konkrétní zdroj (název dokumentu + ideálně URL/rok vydání).
- `source_type` — `factory` | `measurement` | `aggregator` | `estimate` (viz 4).
- `confidence` — 0–1 dle stupnice v kapitole 3.
- `notes` — povinné u `estimate` a při rozporech zdrojů.

Řetězcové popisné údaje (např. `front_type`) jsou prostý text bez obálky; jejich zdroj se dokládá v nejbližší číselné hodnotě nebo v `notes`.

### 2.3 Sekce profilu

| Sekce | Obsah | Povinnost |
|---|---|---|
| `identity`, `meta` | značka, model, generace, trim, roky, karoserie, trh; autor, datum, status | povinné |
| `dimensions` | délka, šířky, výška, rozvor, rozchody, světlost, poloměr otáčení | povinné kromě světlosti |
| `mass` | pohotovostní, suchá, celková, užitečná, rozložení %, výška těžiště, moment setrvačnosti, nádrž | pohotovostní + nádrž povinné; těžiště/setrvačnost smí být `null` + odhad |
| `wheels_tires` | designace pneu P/Z, šířka, profil, ráfek, vypočtený průměr | povinné |
| `engine` | kód, uspořádání, objem, vrtání, zdvih, komprese, plnění, vstřikování, rozvody, orientace, výkon/otáčky, moment/otáčky, redline, volnoběh, oktan | povinné kromě volnoběhu |
| `torque_curve` | body [rpm, Nm], typ bodu, interpolace | povinné (aspoň 2 tovární kotvy) |
| `transmission` | typ, počet stupňů, poměry 1–n, zpátečka, stálý převod, čas řazení (simulační) | povinné kromě času řazení |
| `drivetrain` | layout, hnaná náprava, diferenciály, split (AWD) | povinné |
| `performance` | V-max, 0–100, 0–60 mph, brzda 100–0 | V-max + 0–100 povinné; brzda smí být odhad |
| `brakes` | typ P/Z, průměry kotoučů, ABS, bias | povinné kromě biasu |
| `suspension` | typ P/Z, stabilizátory, tuhosti, poznámka tlumiče | typy povinné; tuhosti smí být `null` |
| `alignment` | camber/caster/toe | smí být odhad s nízkou důvěrou |
| `aero` | Cx, čelní plocha, poznámka přítlaku | Cx smí být `null` |

Plné strojové schéma: `C:/.DATA/AutoEngineerAI/vehicle-data/references/_schema.json` (JSON Schema draft 2020-12, `schema_version: "1.0.0"`).

## 3. Zdroje dat a skóre důvěryhodnosti

### 3.1 Hierarchie zdrojů

1. **Tovární (OEM):** brožury, technické specifikace, dílenské manuály, tiskové zprávy výrobce. Příklad: Mazda AU/NZ brožury (převody 5.087/2.991/2.035/1.594/1.286/1.000, stálý 2.866).
2. **Nezávislé měření:** magazínové testy (brzdná dráha, reálná akcelerace), brzda motoru, vážení. Vždy uvést metodiku a podmínky.
3. **Agregátory:** ultimatespecs, auto-data, Wikipedia — pouze pokud se shodují ≥2 nezávislé zdroje nebo je doložen OEM původ. Nikdy jediný agregátor pro kritický parametr.
4. **Odhad:** dopočet, aproximace, přenos z příbuzné varianty. Vždy `source_type: estimate`, confidence ≤ 0.5, `notes` začíná „ODHAD:".

### 3.2 Stupnice confidence

| Hodnota | Význam | Příklad |
|---|---|---|
| 1.0 | Tovární údaj, ověřen dokumentem | objem 1998 cm³, převody MX-5 |
| 0.85–0.95 | Shoda více zdrojů / OEM nepřímo | rozměry, V-max 219 km/h |
| 0.6–0.8 | Jeden věrohodný zdroj nebo měření s metodikou | hmotnost dle trhu, 0–100 |
| 0.3–0.5 | Kvalifikovaný odhad | těžiště, geometrie, brzda 100–0 |
| 0.0–0.2 | Neznámé / zástupný symbol (`null`) | Cx, tuhosti pružin, setrvačnost |

### 3.3 Zdrojové registry (pro tento návrh použité)

- Mazda AU/NZ oficiální brožury MX-5 (PDF): převody 6MT/6AT, stálý převod, vrtání/zdvih 83,5 × 91,2, komprese 13,0, nádrž 45 l, palivo 95 RON.
- US 2019 MX-5 specifikace (manuály): převody 6MT 5.087–1.000, stálý 2.866 / AT 3.583.
- Wikipedia Mazda MX-5 (ND): rozvor 2310, rozměry, výkony 96/118/135 kW, moment 205 Nm/4000, redline 7500, hmotnostní pásma.
- ultimatespecs ND 2.0 184: rozchody 1495/1505, brzdy 280/280, pneu 205/45 R17, V-max 219, 0–100 6,5 s.
- auto-data ND facelift 2023: V-max 219, 0–100 6,5 s, 0–60 mph 6,2 s, redline 7500, brzdy 280 mm, ABS.
- Arnold Clark (prodejní data EU): šířka 1735/1918, výška 1230, rozvor 2310, GVW 1260, užitečná 219, min. pohotovostní 1041, nádrž 45 l, poloměr 10,4 m.

## 4. Rozlišení továrna / měření / odhad

`source_type` je povinný a určuje, jak smí údaj použít navazující moduly:

- `factory` — cílový parametr pro Engineering Decision AI (fáze 7). Odchylka simulace od něj je chyba modelu.
- `measurement` — validační cíl s tolerancí (podmínky testu v `notes`: povrch, teplota, pneu, zatížení). Kapitola 7: „Pokud přesné údaje nejsou dostupné, musí být nejistota výslovně uvedena."
- `aggregator` — pracovní hodnota; při sporu s OEM vždy vítězí OEM.
- `estimate` — nikdy se nesmí tvářit jako fakt. V JSON má `notes: "ODHAD: ..."`, v reportech se zobrazuje kurzívou/varováním. Odhady se nesmí řetězit (odhad z odhadu → confidence −0.1, min. 0.2, a záznam do `notes`).

Křivka momentu (`torque_curve`): každý bod má `point_type` (factory/measured/interpolated/estimated). Plná křivka z brzdy je pro sériová auta typicky neveřejná → kotvy z továrny (moment + výkon) + interpolovaný tvar s nízkou důvěrou.

## 5. Generace a výbavy

- Profil je verzován `schema_version` + `meta.updated`. Změna čísla = nový `updated` + důvod (nový zdroj, oprava, nová výbava).
- Příbuzné varianty (soft-top vs. RF, 1.5 vs. 2.0, MT vs. AT) jsou samostatné soubory, nikdy větvení uvnitř jednoho souboru. Společné dědí lidsky (kopií), ne odkazem — formát nemá dědičnost, aby byl každý profil samostatně validovatelný.
- `trim` + `market` + `model_years` jednoznačně určují platnost (např. před/po 2019: 160 → 184 k, redline 6800 → 7500).
- Rozdíly výbav (LSD vs. otevřený dif, 16" vs. 17" kola, Bilstein) patří do `notes` příslušné sekce; je-li rozdíl zásadní pro fyziku, vzniká samostatný profil.

## 6. Řešení chybějících údajů

1. `value: null` + `source_type: estimate` + nízká confidence + `notes: "CHYBÍ: ..."` (viz Cx, tuhosti, setrvačnost v ukázce). Prázdné pole ani vymyšlené číslo není dovoleno.
2. Dopočet je povolen, pokud je vzorec uveden: průměr pneu z designace, moment z výkonu (P = M·ω), čelní plocha 0,85 × š × v. Takový bod má `point_type: interpolated` / `source_type: estimate`, confidence 0.4–0.95 dle metody.
3. Pořadí náhrad: OEM příbuzné varianty → nezávislé měření → fyzikální aproximace → kalibrační parametr simulace (označen, ladí optimizer ve fázi 10, nikdy se nezapisuje zpět jako fakt).
4. Brzdná dráha, časy na okruhu a spotřeba nejsou tovární parametry — vždy `measurement` nebo `estimate`, nikdy `factory`.

## 7. Převody jednotek

Kanonické jednotky v souboru: **mm, kg, kW, Nm, rpm, km/h, s, m, l, %, deg, m²**. Převodní pravidla (zaokrouhlení až na konci výpočtu):

- 1 in = 25,4 mm; 1 lb = 0,45359237 kg; 1 hp = 0,7457 kW; 1 PS = 0,73549875 kW; 1 lb·ft = 1,35581795 Nm; 1 mph = 1,609344 km/h; 1 US gal = 3,78541 l.
- Výkon: uvádět kW (primární) + PS/hp v `notes` (184 PS = 135 kW = 181 hp).
- Teplota (okrajově): °F = °C × 9/5 + 32. Tlak pneu: 1 psi = 6,89476 kPa (až bude sekce doplněna).
- Průměr pneu: D[mm] = 25,4 × rim[in] + 2 × (šířka × profil/100).

## 8. Aktualizace a validace

1. Nový/lepší zdroj → aktualizovat `value`, `source`, `confidence`, `meta.updated`; starou hodnotu stručně zmínit v `notes` (audit trail).
2. Každý profil musí projít JSON-validací proti `_schema.json` a kontrolou konzistence: výkon ≈ moment × otáčky (P[kW] = M[Nm] × n/9549), V-max dosažitelná převody (teoretická rychlost na nejvyšší stupeň při redline ≥ V-max), průměr pneu odpovídá designaci.
3. Statusy: `draft` → `review` → `approved`. Do `approved` smí jen profil bez `null` v povinných polích a bez `estimate` s confidence < 0.3 v kritických polích (výkon, převody, hmotnost, pneu).
4. Soubory žijí v `C:/.DATA/AutoEngineerAI/vehicle-data/references/`; čtení pro fáze 5–7, zápis jen přes Reference Intelligence.

## 9. Ukázkový profil: Mazda MX-5 ND 2.0 SkyActiv-G 184 (EU, soft-top, 6MT, 2019–2023)

Plný strojový profil: `C:/.DATA/AutoEngineerAI/vehicle-data/references/example-vehicle.json` (`vehicle_id: mazda-mx5-nd-20-184-softtop-6mt-eu`). Důvod volby: jednoduchá koncepce (RWD, atmosférický 4válec, 6MT s publikovanými převody), kompletní OEM data pro převodovku a motor, malý rozptyl hmotnosti — vhodný první cíl pro fáze 5–7. Shrnutí klíčových hodnot:

- Rozměry: 3915 × 1735 × 1230 mm, rozvor 2310, rozchody 1495/1505, nádrž 45 l.
- Hmotnost: pohotovostní **~1075 kg (ODHAD z pásma 1041–1116)**, GVW 1260 kg.
- Motor PE-VPS 1998 cm³, 13,0:1, **135 kW/7000, 205 Nm/4000, redline 7500** (factory).
- Převodovka 6MT **5.087 / 2.991 / 2.035 / 1.594 / 1.286 / 1.000**, zpátečka 4.696, stálá **2.866** (factory).
- Pohon RWD, zadní LSD dle výbavy (ověřit VIN), pneu 205/45 R17 (Ø ~616 mm).
- Podvozek: double wishbone / multilink + stabilizátory; brzdy 280/280 mm + ABS.
- Výkony: V-max 219 km/h, 0–100 6,5 s (factory); brzda 100–0 ~37 m **(ODHAD)**.
- Neznámé/odhady: Cx (`null`), tuhosti pružin (`null`), výška těžiště 460 mm, setrvačnost (dopočítat), geometrie camber/caster/toe (odhady 0.3–0.35), plná křivka momentu (2 tovární kotvy + odhad tvaru).

Kontrola konzistence: 205 Nm × 4000/9549 ≈ 85,9 kW (v pořádku < 135 kW); 184 Nm @7000 z výkonu 135 kW (P = M·ω → M = 135000×60/(2π×7000) ≈ 184 Nm) — souhlasí s bodem křivky. Teoretická rychlost na 6. stupeň při 7500 ot.: obvod kola ~1,936 m × (7500/60)/(1,0×2,866) ≈ 84,4 m/s ≈ 304 km/h > 219 km/h — V-max je tedy omezena výkonem/odporem, ne převody. Konzistentní.

## 10. Fakta / předpoklady / neznámé

**Ověřená fakta:** motor 1998 cm³, 135 kW/7000, 205 Nm/4000, komprese 13,0, vrtání/zdvih; převody 6MT + stálý 2,866; rozvor 2310; nádrž 45 l; koncepce RWD; brzdy 280/280; pneu 205/45 R17 (vyšší výbava); V-max 219; 0–100 6,5 s. Zdroje viz 3.3, cesty `C:/.DATA/AutoEngineerAI/vehicle-data/references/example-vehicle.json`, `C:/.DATA/AutoEngineerAI/vehicle-data/references/_schema.json`.

**Předpoklady:** pohotovostní 1075 kg (střed pásma); rozložení ~52:48; těžiště 460 mm; geometrie z dílenských tolerancí; tvar momentové křivky; brake bias 65 %; čas řazení 0,4 s jako simulační parametr.

**Neznámé:** Cx (Mazda neuvádí); tuhosti pružin a křivky tlumičů; moment setrvačnosti; přesné rozložení hmotnosti tohoto trimu; LSD vs. otevřený dif dle konkrétní výbavy; brzdná dráha jako tovární údaj neexistuje.

## 11. Rizika a omezení

1. Hmotnostní pásmo ±40 kg zásadně mění poměr výkon/hmotnost — cílový profil bez VIN/výbavy má nejistotu min. ±3 %.
2. Agregátory se rozcházejí (výška 1230 vs. 1235, světlost 135 vs. 141, okruh 9,4 vs. 10,4 m) — nutná metodika v `notes`, ne tiché průměrování.
3. Momentová křivka z 2 kotev je pro fázi 10 (optimalizace odezvy motoru) nedostatečná — riziko špatného průběhu výkonu; mitigace: brzda/měření nebo konzervativní interpolace.
4. Odhady geometrie a tuhostí nesmí řídit destruktivní změny konstrukce (fáze 11) — nejprve měření/kalibrace.
5. Přenos US/JP dat na EU trim (hmotnosti, emisní naladění) — vždy uvést trh v `identity.market`.

## 12. Další kroky

1. Doplnit 2. profil odlišné koncepce (např. FWD hot-hatch) pro ověření obecnosti schématu.
2. Napsat validátor (JSON Schema + konzistenční kontroly z kap. 8) do `tools/`.
3. Získat dílenský manuál ND pro geometrii a tuhosti; nahradit odhady v `alignment`/`suspension`.
4. Definovat mapování profil → cílový profil pro Engineering Decision AI (fáze 7) a toleranční pásma dle kapitoly 7 PROJECT-PLANu.
5. Zavést zdrojový registr jako samostatný soubor, až počet profilů přesáhne ~5.
