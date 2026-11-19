# Mustang GT 2024 EU – ověření zdrojů (M1.5 podklad)

**Datum ověření:** 2026-11-19
**Ověřováno proti:** `docs/VEHICLE-SPECIFICATIONS.md` (stav: návrh v1, vše „Dle zadání" / ESTIMATED / UNKNOWN)
**Metoda:** čtení veřejných zdrojů [1] [2] [3] webovými nástroji, doslovný přepis hodnot.
**Výsledek:** tabulka níže. Verdikty: POTVRZENO / ROZPOR / NENALEZENO.
**Status poznámka:** Tento report sám o sobě nepřiděluje status VERIFIED — ten dle
`VEHICLE-SPECIFICATIONS.md §2a` smí přidělit až úkol M1.5. Report je podklad pro M1.5.

---

## 1. Zdroje (přesné URL, stav k 2026-11-19)

| ID | Zdroj | URL | Stav |
|----|-------|-----|------|
| [1a] | Ford – 2024 Mustang EU Technical Specifications (PDF, primární URL ze SPEC) | `https://media.ford.com/content/dam/fordmedia/Europe/en/2024/01/NewMustang/2024_Ford_Mustang_technical_specification_EU.pdf` | K 2026-11-19 vrací z CZ **HTTP 503** (Akamai „Service Unavailable"); obsah ověřen přes [1b] a úvodní sekci se podařilo extrahovat i z této URL |
| [1b] | Ford – 2024 Ford Mustang tech spec EU (PDF mirror, stejný dokument, plný text) | `https://www.fromtheroad.ford.com/content/dam/fordmediasite/eur/en/library/2024/tech-specs/2024_Ford_Mustang_tech_spec_EU.pdf` | **Dostupné**, plný text extrahován (motor, převodovka, brzdy, kola, rozměry, hmotnosti) |
| [2] | Ford – „New Ford Mustang is an Icon Reborn" (tisková zpráva EU) | `https://www.fromtheroad.ford.com/eur/en/articles/2024/new-ford-mustang-is-an-icon-reborn` | **Dostupné**, plný text extrahován |
| [3] | ADAC Autokatalog – Mustang Fastback 5.0 Ti-VCT V8 GT (03/24–09/25) | `https://www.adac.de/rund-ums-fahrzeug/autokatalog/marken-modelle/ford/mustang/2generation/332370/` | **Dostupné**, plný text extrahován. POZOR: URL ve SPEC má překlep (`rund-um-fahrzeug` → 404); správně je `rund-ums-fahrzeug` |

Poznámka k [1]: poznámky pod čarou PDF — výkon/moment „based on premium fuel per SAE J1349",
CO₂/spotřeba dle WLTP (EC 715/2007, EU 2017/1151), hmotnosti jsou „lightest kerbweight assuming
driver at 75 kg, full fluid levels and 90 per cent fuel" bez panoramatické střechy.
„For editorial use only. Information correct at time of publication."

---

## 2. Ověření hodnot z VEHICLE-SPECIFICATIONS.md §2

| Parametr (SPEC) | Hodnota v SPEC | Verdikt | Zdroj / citace |
|---|---|---|---|
| Motor 5.0 Ti-VCT V8 | 5.0 Ti-VCT V8 | **POTVRZENO** | [1b] „5.0-litre V8; Valvetrain DOHC, Ti-VCT"; [2] „new Gen IV 5.0-litre V8… with the Ti-VCT variable camshaft timing"; [3] „Mustang Fastback 5.0 Ti-VCT V8, 8zyl, Frontmotor / V-Motor" |
| Zdvihový objem | 5 038 cm³ | **POTVRZENO** | [1b] „Displacement 5,038 cc; Bore x stroke 93.0 mm x 92.7 mm"; [3] „Hubraum 5038 ccm" |
| Max. výkon | 328 kW / 446 PS @ 7 250 rpm | **POTVRZENO** | [1b] „Horsepower 446PS @ 7,250 rpm" (kW v PDF neuvedeno; 446 PS = 328,0 kW); [2] „offers 446 PS and 540 Nm of torque"; [3] „328 kW (446 PS)… Leistung maximal bei 7250 U/min" |
| Max. moment | 540 Nm @ 5 100 rpm | **POTVRZENO** | [1b] „Torque 540Nm @ 5,100rpm"; [2] „540 Nm of torque"; [3] „540 Nm… Drehmoment maximal bei 5100 U/min" |
| Rozvor | 2 719 mm | **POTVRZENO** | [1b] „Wheelbase 2719"; [3] „Radstand 2719 mm" |
| Přední rozchod | 1 585 mm | **POTVRZENO** | [1b] „Track width, front 1585" (sloupec Mustang GT; Dark Horse 1595) |
| Zadní rozchod | 1 642 mm | **POTVRZENO** | [1b] „Track width, rear 1642" (sloupec Mustang GT; Dark Horse 1643) |
| Délka | 4 810 mm | **POTVRZENO** | [1b] „Overall length 4810" (GT; Dark Horse 4819); [3] „Länge 4810 mm" |
| Šířka bez zrcátek | 1 916 mm | **POTVRZENO** | [1b] „Overall width without mirrors 1916"; [3] „Breite 1916 mm" |
| Výška Fastback | 1 394–1 414 mm | **POTVRZENO** (rozmezí) | [1b] „Overall height, fastback 1394-1414"; [3] „Höhe 1404 mm" (= uvnitř rozmezí, konzistentní) |
| Pohotovostní hmotnost (manuál) cca 1 808 kg, odhad výrobce | cca 1 808 kg, ESTIMATED | **POTVRZENO** (vč. charakteru „odhad") | [1b] „Est. kerbweight, fastback manual 1808" + definice v pozn. 5 (řidič 75 kg, plné kapaliny, 90 % paliva); [3] „Leergewicht (EU) 1808 kg". Doporučení: ponechat `confidence` střední / ESTIMATED, Ford sám uvádí „Est." |
| Přední pneumatiky | 255/40 R19 | **POTVRZENO** | [1b] „(front) 19 in. x 9.0 in. 255/40R … Y (summer-only tyres)"; [3] „Reifengröße 255/40R19" |
| Zadní pneumatiky | 275/40 R19 | **POTVRZENO** | [1b] „(rear) 19 in. x 9.5 in. 275/40R Y (summer-only tyres)"; [3] „Reifengröße hinten 275/40R19" |
| Pohon zadních kol | RWD | **POTVRZENO** | [1b] „Front-engine, Rear-wheel drive with limited-slip differential"; [3] „Antriebsart Hinterrad" |
| Převodovka 6MT | 6stupňový manuál | **POTVRZENO** (nad rámec SPEC — ve SPEC jen v §1) | [1b] „Standard 6-speed manual with rev-matching, Getrag MT-82"; [3] „Schaltgetriebe, Anzahl Gänge 6" |
| 0–100 km/h, V-max (EU manuál) — ve SPEC UNKNOWN | — | **POTVRZENO (nový nález, ve SPEC chybí)** | [1b] Coupe (manual): „0-100 km/h 5.3 s; Max speed 250 km/h"; [3] „5,3 s; 250 km/h". Kandidát na doplnění do SPEC v M1.5 (nikoli z US dat — je to EU PDF) |
| Převodové poměry 1–6 — ve SPEC UNKNOWN | — | **POTVRZENO (nový nález, ve SPEC chybí)** | [1b] GT 6MT (Getrag MT-82): 3.237 / 2.104 / 1.422 / 1.000 / 0.814 / 0.622; stálý převod „3.15:1, 3.55:1 Limited-slip rear axle" — **nejasné, který platí pro EU 6MT Fastback** (viz §4 bod 2) |
| Brzdy standard GT — ve SPEC UNKNOWN | — | **ČÁSTEČNĚ POTVRZENO (rozměry), bias NENALEZENO** | [1b] GT: „Front 390 x 36 mm vented discs, Brembo six-piston 36 mm fixed aluminium callipers; Rear 355 x 28 mm vented discs, four-piston 30 mm fixed aluminium callipers; Pad Low-metallic; swept area 768 / 523 cm²". Bias (předozadní rozdělení) **nikde neuveden** |
| Průběh momentové křivky | — | **NENALEZENO** | V [1b] pouze body maxima; [2] pouze maxima; [3] pouze maxima → zůstává UNKNOWN |
| Rozložení hmotnosti P/Z, výška těžiště | — | **NENALEZENO** | V žádném ze zdrojů [1][2][3] → zůstává UNKNOWN |
| Brzdový bias | — | **NENALEZENO** | V žádném ze zdrojů [1][2][3] → zůstává UNKNOWN |
| Cd / čelní plocha | — | **NENALEZENO** | V žádném ze zdrojů [1][2][3] ([2] zmiňuje aero jen slovně: „Aerodynamics are optimised…", bez čísel) → zůstává UNKNOWN |

Geometrická kontrola průměrů pneu ve SPEC (686,6 / 702,6 mm): aritmetika souhlasí
(D = 19·25,4 + 2·W·A/100 → 482,6+204 = 686,6; 482,6+220 = 702,6). Není to měření — takto ponechat.

---

## 3. Zvlášť prověřované body (zadání)

1. **Výkon 328 kW / 446 PS @ 7250 — POTVRZENO.** [1b] 446 PS @ 7 250 rpm; [3] 328 kW (446 PS) @ 7250.
2. **Moment 540 Nm @ 5100 — POTVRZENO.** [1b], [2], [3] shodně.
3. **Rozvor 2719 — POTVRZENO.** [1b], [3].
4. **Rozchody 1585 / 1642 — POTVRZENO.** [1b] sloupec Mustang GT (nezaměnit s Dark Horse 1595/1643).
5. **Hmotnost ~1808 kg (odhad?) — POTVRZENO jako odhad výrobce.** [1b] „Est. kerbweight" s definicí;
   [3] 1808 kg Leergewicht (EU). Označení ESTIMATED ve SPEC je správné, ponechat.
6. **Pneu 255/40R19 + 275/40R19 — POTVRZENO.** [1b] (Y, summer-only) + [3].
7. **Převodové poměry — NALEZENY (očekávané NENALEZENO se nepotvrdilo).** [1b] uvádí kompletní
   řadu Getrag MT-82 i obě varianty 10AT; stálý převod GT „3.15:1, 3.55:1" bez rozlišení, která patří
   k EU manuálu. Momentová křivka jako taková (body rpm–Nm) **NENALEZENA** → UNKNOWN trvá.
8. **Brzdy standard GT — ČÁSTEČNĚ.** Rozměry a třmeny v [1b] (viz tabulka). Bias **NENALEZEN**.
   Navíc viz §4 bod 1: v EU je Performance Pack zřejmě standardem GT, takže předpoklad SPEC
   „standard GT bez Performance Packu" je třeba v M1.5 přehodnotit.

---

## 4. Rozpory a nejasnosti (žádný tvrdý rozpor v číslech; 3 drobnosti + 2 koncepční)

1. **„Standardní GT bez Performance Packu" vs EU realita — KONCEPČNÍ NESROVNALOST k dořešení v M1.5.**
   [2]: „Mustang GT comes with a choice of… 6-speed manual… A **standard** Performance Pack includes
   19-inch alloy wheels, a limited-slip differential…, **Brembo brakes**… and an Active Valve Exhaust."
   [1b] uvádí pro GT standardně brzdy Brembo 390 mm a LSD. Pro EU tedy varianta „GT bez Packu"
   zřejmě **neexistuje** — SPEC §4 („oddělené varianty… nesmí se přenášet") vychází z US logiky.
   Doporučení M1.5: rozhodnout, zda cílový profil = EU GT tak jak je (tj. vč. PP prvků), a pravidlo
   v SPEC upřesnit. Brzdové rozměry z [1b] pak platí přímo pro cílový vůz.
2. **Stálý převod EU manuálu nejednoznačný.** [1b] „Final drive 3.15:1, 3.55:1 Limited-slip rear axle"
   bez přiřazení k převodovce/trhu. Pro výpočty M3/M4 zatím **nepoužívat bez dalšího ověření**
   (prodejní konfigurátor Ford ČR/DE nebo workshop data); evidovat obě hodnoty jako kandidáty.
3. **CO₂: [1b] 274 vs [3] 275 g/km (Coupe manuál).** Drobnost; [2] pozn. 1 uvádí rozpětí 273–282
   („may vary according to vehicle variants offered by individual markets"). Není to rozpor
   v technických datech vozu, jen jiná varianta měření/zaokrouhlení.
4. **Poloměr otáčení: [1b] 12,2 m vs [3] 12,0 m.** Drobnost bez dopadu na model (uvádím pro úplnost).
5. **Šířka se zrcátky: [1b] 2080 (2097 RHD) vs [3] 2080.** Shoda pro LHD; ve SPEC zatím není —
   lze doplnit v M1.5.

---

## 5. Co zůstává UNKNOWN (nenalezeno v [1][2][3])

- Průběh momentové křivky (body rpm–Nm).
- Rozložení hmotnosti P/Z a výška těžiště.
- Brzdový bias (rozměry kotoučů/třmenů jsou známy, bias nikoli).
- Cd a čelní plocha (pouze slovní zmínky o aerodynamice v [2]).
- Převodové poměry: NALEZENY (viz výše) — necesita dalšího hledání, jen určit stálý převod EU 6MT.
- 0–100 / V-max: NALEZENY v [1b]+[3] — navrženo k doplnění do SPEC v M1.5.

---

## 6. Doporučení pro M1.5

1. Opravit URL [3] ve SPEC (`rund-ums-fahrzeug`) a přidat mirror URL [1b] jako zálohu k [1a].
2. Navrhnout status VERIFIED pro: motor, objem, výkon, moment, rozvor, rozchody, délku, šířku,
   výšku (rozmezí), hmotnost (jako ESTIMATED s definicí pozn. 5), pneu P/Z, pohon, převodovku 6MT.
3. Rozhodnout koncepční bod §4.1 (EU GT vč. Performance Pack?) před uzamčením brzd do profilu.
4. Doplnit do SPEC nově nalezené: převodové poměry 6MT + kandidáty stálého převodu (s vlajkou
   nejasnosti), brzdy GT z [1b], 0–100 5,3 s / V-max 250 km/h, šířku se zrcátky 2080 mm.
5. UNKNOWN nadále: momentová křivka, váhové rozložení + CG, brzdový bias, Cd/plocha.
