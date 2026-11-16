# AutoEngineerAI
## Hlavní projektový plán a technická roadmapa

**Projekt:** AutoEngineerAI  
**Typ:** Autonomní inženýrský systém pro Roblox vozidla  
**Stav:** Plánování a přípravná fáze  
**Priorita:** Technická správnost, automatizace, měřitelné výsledky a dlouhodobá rozšiřitelnost

---

# 1. VIZE PROJEKTU

Cílem AutoEngineerAI je vytvořit autonomní systém, který dokáže vzít existující vozidlo v Robloxu a samostatně jej upravit tak, aby se jeho jízdní vlastnosti, fyzika, konstrukce a chování co nejvíce přiblížily zadanému skutečnému automobilu.

Uživatel nebude muset ručně hledat hodnoty, nastavovat odpružení, upravovat převodovku nebo opakovaně testovat různé konfigurace.

Uživatel pouze:
1. Dodá model vozidla z Robloxu.
2. Zadá skutečné vozidlo, které má být předlohou.
3. Spustí analýzu.
4. Počká na automatické vyhodnocení, úpravy a testování.
5. Obdrží nejlepší ověřenou variantu vozidla.

AutoEngineerAI musí samo rozhodovat, jaké změny jsou potřeba.

Nemá být pouze konfigurátorem hodnot. Má fungovat jako autonomní virtuální automobilový inženýr.

# 2. HLAVNÍ PRINCIPY

1. Maximální možná automatizace bez ručního ladění uživatelem.
2. Každá změna musí mít technické zdůvodnění.
3. Každá důležitá změna musí být ověřena testováním.
4. Optimalizace musí vycházet z měřitelných výsledků.
5. Systém musí rozumět souvislostem mezi jednotlivými částmi vozidla.
6. Musí umět pracovat s různými konstrukcemi a fyzikálními systémy.
7. Musí umět rozhodnout, zda původní systém zachovat, upravit, nebo nahradit.
8. Musí umět vrátit neúspěšné změny.
9. Musí uchovávat historii konfigurací a výsledků.
10. Nesmí vydávat neověřenou simulaci za důkaz skutečného fungování v Robloxu.

# 3. VSTUPNÍ ZDROJE A EXISTUJÍCÍ PROJEKTY

## 3.1 Nový projekt AutoEngineerAI

Vznikne samostatný GitHub repozitář.

Pracovní název:
`Adalik1219/AutoEngineerAI`

Tento repozitář bude obsahovat celý nový systém, dokumentaci, testy, nástroje a vlastní databáze.

## 3.2 RobloxSimulator

Existující repozitář `Adalik1219/RobloxSimulator` bude sloužit výhradně jako zdroj technických poznatků.

Pravidla:
- Nikdy jej neupravovat.
- Nevytvářet v něm nové branche ani commity.
- Nevytvářet v něm pull requesty.
- Nepřidávat na něj runtime závislost AutoEngineerAI.
- Studovat jeho matematiku, algoritmy, fyzikální řešení a testovací principy.
- Převzít pouze ověřené a zdokumentované poznatky.

Využitelné oblasti:
- dynamika vozidel,
- pneumatiky a přenos sil,
- slip a grip,
- motor a převodovka,
- výpočet momentů,
- řízení,
- přenos hmotnosti,
- fyzikální integrace,
- jednotky a převody,
- testování a validace.

Všechna omezení původního projektu musí být při přenosu respektována.

## 3.3 A-Chassis

Soubor `chasis.rbxm` bude jeden z hlavních výchozích referenčních systémů.

Musí být nejprve skutečně analyzován.

Originál se zachová beze změny. Veškeré úpravy budou probíhat na pracovních kopiích.

A-Chassis nebude automaticky považován za jedinou možnou technologii. AutoEngineerAI musí umět vyhodnotit, zda je vhodnější:
- ponechat původní systém,
- upravit jeho konfiguraci,
- upravit jeho skripty,
- upravit konstrukci vozidla,
- nebo vytvořit či použít jiný fyzikální systém.

# 4. CÍLOVÝ PRACOVNÍ POSTUP

Každé vozidlo projde následujícím procesem:

1. Načtení vozidla.
2. Analýza modelu a jeho konstrukce.
3. Identifikace fyzikálního systému.
4. Analýza aktuálních jízdních vlastností.
5. Získání referenčních údajů skutečného automobilu.
6. Vytvoření cílového technického profilu.
7. Porovnání současného a požadovaného stavu.
8. Vytvoření technického plánu změn.
9. Rozhodnutí o zachování nebo nahrazení fyzikálního systému.
10. Provedení změn na pracovní kopii.
11. Automatické testování.
12. Vyhodnocení odchylek.
13. Automatická optimalizace.
14. Opakování testování a optimalizace.
15. Validace nejlepší varianty.
16. Export finálního vozidla a výsledné dokumentace.

# 5. MODULY SYSTÉMU

## 5.1 Vehicle Importer

Zodpovědnost:
- načítání Roblox modelů,
- příprava pracovních kopií,
- kontrola integrity modelu,
- identifikace formátu a struktury,
- bezpečný export výsledků.

## 5.2 Vehicle Analyzer

Automaticky analyzuje:
- hierarchii objektů,
- geometrii,
- rozměry,
- hmotnost,
- těžiště,
- kola a jejich umístění,
- odpružení,
- řízení,
- konstrukci,
- použité constraints,
- fyzikální vlastnosti,
- skripty a konfigurace.

Musí vytvořit strukturovaný technický profil vozidla.

## 5.3 Chassis Intelligence

Rozpoznává použitý fyzikální systém.

Musí:
- identifikovat A-Chassis a další podporované systémy,
- analyzovat jejich architekturu,
- identifikovat dostupné parametry,
- zjistit jejich závislosti,
- rozpoznat limity daného systému,
- určit možnosti jeho úprav a rozšíření.

## 5.4 Vehicle Reference Intelligence

Získává a spravuje technické údaje skutečných vozidel.

Sleduje:
- rozměry,
- hmotnost,
- těžiště a rozložení hmotnosti, pokud jsou dostupné,
- motor,
- výkon,
- točivý moment,
- otáčky,
- převodovku,
- převodové poměry,
- pohon,
- diferenciály,
- pneumatiky,
- brzdy,
- odpružení,
- geometrii,
- akceleraci,
- maximální rychlost,
- brzdnou dráhu,
- další dostupné měřitelné vlastnosti.

Každý údaj musí mít informaci o zdroji, důvěryhodnosti a případné nejistotě.

## 5.5 Vehicle Physics Analysis

Vyhodnocuje fyzikální stav vozidla a vztahy mezi jeho jednotlivými částmi.

Zaměřuje se na:
- síly,
- momenty,
- hmotnost,
- setrvačnost,
- přenos zatížení,
- trakci,
- stabilitu,
- dynamiku kol,
- odpružení,
- brzdění,
- akceleraci,
- zatáčení.

Musí umět identifikovat příčinu problému, nejen jeho viditelný projev.

## 5.6 Engineering Decision AI

Hlavní rozhodovací modul.

Rozhoduje:
- které části vozidla je potřeba změnit,
- jaké parametry upravit,
- zda změnit geometrii,
- zda změnit konstrukci,
- zda zachovat A-Chassis,
- zda A-Chassis zásadně upravit,
- zda je nutné použít jiný fyzikální systém.

Musí vytvořit plán změn včetně očekávaného výsledku a rizik.

## 5.7 Engineering Modules

Samostatné moduly pro jednotlivé technické oblasti.

### Motor
- výkon,
- točivý moment,
- průběh momentu,
- otáčky,
- volnoběh,
- odezva motoru,
- přeplňování, pokud je relevantní.

### Převodovka
- počet převodových stupňů,
- převodové poměry,
- řazení,
- reakce převodovky,
- maximální rychlost a akcelerace.

### Pohon
- FWD,
- RWD,
- AWD,
- rozdělení momentu,
- diferenciály,
- trakce jednotlivých kol.

### Pneumatiky
- rozměry,
- poloměr,
- grip,
- podélný a boční slip,
- přenos sil,
- vliv zatížení.

### Odpružení
- pružiny,
- tlumiče,
- zdvih,
- komprese,
- odskok,
- stabilizátory,
- zatížení jednotlivých kol.

### Řízení
- úhel natočení,
- převod řízení,
- Ackermann,
- odezva řízení,
- stabilita při vyšších rychlostech.

### Geometrie
- rozvor,
- rozchod,
- poloha kol,
- camber,
- caster,
- toe,
- geometrie zavěšení.

### Brzdy
- brzdný moment,
- rozdělení brzdné síly,
- ABS,
- stabilita při brzdění,
- brzdná dráha.

### Konstrukce a fyzika
- rozložení hmotnosti,
- těžiště,
- momenty setrvačnosti,
- konstrukce podvozku,
- fyzikální constraints,
- propojení částí vozidla.

## 5.8 Geometry Engineering

Pokročilý modul pro úpravy geometrie a konstrukce.

Musí umět:
- analyzovat původní geometrii,
- porovnat ji s cílovým vozidlem,
- navrhnout potřebné změny,
- měnit umístění kol a komponent,
- upravovat geometrii zavěšení,
- upravovat konstrukci,
- ověřovat fyzikální funkčnost změn.

Nesmí provádět destruktivní změny bez zálohy a validace.

## 5.9 Physics Engine Intelligence

Rozhoduje o vhodném fyzikálním systému.

Možnosti:
- zachovat A-Chassis,
- upravit A-Chassis,
- vytvořit adaptér,
- použít nový vlastní fyzikální systém.

Nový systém musí být posuzován podle:
- přesnosti,
- stability,
- výkonu,
- rozšiřitelnosti,
- kompatibility s Roblox runtime,
- kvality testování.

## 5.10 Test Environment

Zajišťuje opakovatelné testování vozidel.

Musí obsahovat:
- testovací tratě,
- rovné úseky,
- zatáčky,
- brzdné úseky,
- nerovnosti,
- změny povrchu,
- různé jízdní situace,
- automatické řízení,
- sběr telemetry.

## 5.11 Autonomous Driver

Automaticky ovládá testované vozidlo.

Musí umět:
- rozjíždět se,
- zrychlovat,
- brzdit,
- zastavovat,
- zatáčet,
- držet definovanou rychlost,
- sledovat testovací trasu,
- opakovat stejné scénáře.

Výsledky testů musí být reprodukovatelné v rámci definovaných tolerancí.

## 5.12 Telemetry and Evaluation

Zaznamenává:
- rychlost,
- zrychlení,
- brzdění,
- otáčky,
- otáčení kol,
- úhly řízení,
- zatížení kol,
- síly a momenty,
- náklon karoserie,
- prokluz,
- stabilitu,
- průjezd zatáčkami,
- odchylky od cílového profilu.

Musí poskytovat přehledné výsledky a srovnání s referenčním vozidlem.

## 5.13 Autonomous Optimizer

Automaticky hledá nejlepší nastavení.

Musí:
1. Vyhodnotit současný stav.
2. Identifikovat největší odchylky.
3. Určit parametry s největším vlivem.
4. Vytvořit kandidátní změny.
5. Otestovat jednotlivé varianty.
6. Vyhodnotit výsledky.
7. Vybrat lepší varianty.
8. Pokračovat v optimalizaci.
9. Zachovat nejlepší známý výsledek.
10. Zastavit při dosažení cíle nebo limitu optimalizace.

Optimalizace musí zohledňovat více vlastností současně. Nesmí například zlepšit akceleraci za cenu nepřijatelné ztráty stability.

## 5.14 Validation System

Kontroluje:
- fyzikální správnost,
- stabilitu,
- reprodukovatelnost,
- regresní chyby,
- funkčnost v Roblox runtime,
- shodu s cílovými vlastnostmi.

Rozlišuje matematické testy, lokální integrační testy a skutečné Roblox runtime testy.

## 5.15 Export and Reporting

Předává:
- finální model,
- použitou konfiguraci,
- změněné skripty,
- seznam konstrukčních změn,
- výsledky testů,
- srovnání s cílovým vozidlem,
- známá omezení,
- historii optimalizace.

# 6. HLAVNÍ FÁZE VÝVOJE

## FÁZE 0 – Založení projektu

Cíl: vytvořit samostatný základ AutoEngineerAI.

Úkoly:
- založit nový GitHub repozitář,
- vytvořit README,
- vytvořit hlavní projektový plán,
- definovat architektonické principy,
- definovat pravidla práce agentů,
- připravit systém dokumentace,
- připravit verzování a zálohování.

Výstup: samostatný a zdokumentovaný projekt.

## FÁZE 1 – Audit A-Chassis

Cíl: zjistit, co skutečně obsahuje původní A-Chassis.

Úkoly:
- prozkoumat hierarchii,
- analyzovat skripty,
- zmapovat parametry,
- identifikovat fyzikální model,
- zmapovat závislosti,
- zjistit možnosti automatických úprav,
- identifikovat omezení,
- připravit technickou dokumentaci.

Výstup: kompletní technický audit A-Chassis.

## FÁZE 2 – Knowledge Transfer z RobloxSimulatoru

Cíl: vybrat využitelné technické principy.

Úkoly:
- analyzovat matematické moduly,
- analyzovat dynamiku vozidla,
- analyzovat pneumatiky,
- analyzovat pohon,
- analyzovat přenos sil,
- analyzovat jednotky,
- analyzovat testovací systém,
- zdokumentovat omezení,
- vybrat vhodné algoritmy a principy.

Výstup: dokument přenositelných znalostí.

RobloxSimulator zůstává nezměněn.

## FÁZE 3 – Architektura AutoEngineerAI

Cíl: vytvořit kompletní technický návrh systému.

Úkoly:
- rozdělit systém na moduly,
- definovat datové struktury,
- definovat rozhraní,
- definovat formáty konfigurací,
- navrhnout workflow,
- navrhnout pluginovou nebo adaptérní architekturu pro chassis systémy,
- navrhnout testování,
- navrhnout optimalizaci.

Výstup: schválená architektura.

## FÁZE 4 – Vehicle Importer a Analyzer

Cíl: systém musí umět vozidlo načíst a analyzovat.

Úkoly:
- import modelu,
- analýza struktury,
- analýza rozměrů,
- identifikace kol,
- analýza hmotnosti,
- analýza těžiště,
- identifikace komponent,
- identifikace fyzikálního systému,
- vytvoření datového profilu.

Výstup: automatický technický profil vstupního vozidla.

## FÁZE 5 – Reference Intelligence

Cíl: vytvořit referenční databázi skutečných automobilů.

Úkoly:
- navrhnout datové schéma,
- přidat zdroje údajů,
- vytvořit systém důvěryhodnosti,
- zpracovat první referenční vozidla,
- řešit chybějící údaje,
- sjednotit jednotky,
- vytvořit cílový profil automobilu.

Výstup: databáze a automaticky vytvářený referenční profil.

## FÁZE 6 – Physics and Engineering Analysis

Cíl: pochopit fyzikální stav vozidla a jeho odchylky.

Úkoly:
- analyzovat síly a momenty,
- analyzovat pohon,
- analyzovat trakci,
- analyzovat řízení,
- analyzovat odpružení,
- analyzovat hmotnost,
- analyzovat stabilitu,
- vytvořit porovnání s referencí.

Výstup: technická diagnóza vozidla.

## FÁZE 7 – Engineering Decision AI

Cíl: systém musí sám rozhodnout, jak vozidlo upravit.

Úkoly:
- vyhodnotit technické rozdíly,
- určit příčiny odchylek,
- identifikovat změnitelné parametry,
- určit nutné konstrukční změny,
- rozhodnout o zachování nebo výměně chassis,
- stanovit priority změn,
- odhadnout rizika a očekávané výsledky.

Výstup: automaticky vytvořený plán technických úprav.

## FÁZE 8 – Engineering Implementation

Cíl: automaticky provádět navržené úpravy.

Úkoly:
- upravovat parametry,
- upravovat motor,
- upravovat převodovku,
- upravovat pohon,
- upravovat pneumatiky,
- upravovat odpružení,
- upravovat řízení,
- upravovat geometrii,
- upravovat konstrukci,
- vytvářet nové komponenty,
- bezpečně verzovat každou variantu.

Výstup: automaticky upravené pracovní kopie vozidla.

## FÁZE 9 – Test Environment a Autonomous Driver

Cíl: umožnit systému testovat vozidla bez ručního řízení.

Úkoly:
- vytvořit testovací prostředí,
- vytvořit testovací scénáře,
- vytvořit automatického řidiče,
- implementovat měření,
- implementovat telemetry,
- zajistit opakovatelnost,
- oddělit lokální simulaci od Roblox runtime.

Výstup: automatizovaný testovací systém.

## FÁZE 10 – Autonomous Optimization

Cíl: systém musí sám najít nejlepší nastavení.

Úkoly:
- definovat optimalizační cíle,
- definovat omezení,
- implementovat generování kandidátů,
- implementovat optimalizační algoritmy,
- testovat kandidáty,
- vyhodnocovat výsledky,
- uchovávat nejlepší konfiguraci,
- vracet neúspěšné změny,
- zavést automatické zastavení optimalizace.

Výstup: autonomní optimalizační systém.

## FÁZE 11 – Advanced Geometry and Physics Engineering

Cíl: umožnit hluboké zásahy do vozidla.

Úkoly:
- automatická změna geometrie,
- úprava konstrukce,
- úprava zavěšení,
- změny polohy komponent,
- úprava fyzikálních constraints,
- tvorba vlastních komponent,
- případná náhrada A-Chassis,
- integrace alternativního fyzikálního systému.

Výstup: systém schopný řešit i problémy, které nelze vyřešit změnou parametrů.

## FÁZE 12 – Validation and Regression Testing

Cíl: ověřit výsledné vozidlo.

Úkoly:
- fyzikální validace,
- testy stability,
- testy řízení,
- testy akcelerace,
- testy brzdění,
- testy zatáčení,
- testy různých povrchů,
- regresní testy,
- skutečné Roblox runtime testy,
- vyhodnocení odchylek.

Výstup: validovaná finální varianta s doloženými výsledky.

## FÁZE 13 – Export a finální předání

Cíl: předat uživateli hotový výsledek.

Úkoly:
- export modelu,
- export konfigurace,
- export potřebných skriptů,
- vytvoření technického reportu,
- přehled všech změn,
- přehled výsledků testování,
- dokumentace omezení,
- možnost obnovit původní variantu.

Výstup: kompletní výsledné Roblox vozidlo.

# 7. TESTOVACÍ A HODNOTICÍ KRITÉRIA

Každé vozidlo musí být hodnoceno podle více nezávislých oblastí.

## Výkon
- akcelerace,
- maximální rychlost,
- průběh výkonu,
- pružnost,
- reakce motoru.

## Brzdění
- brzdná dráha,
- zpomalení,
- stabilita při brzdění,
- opakovatelnost.

## Ovládání
- odezva řízení,
- průjezd zatáčkou,
- nedotáčivost,
- přetáčivost,
- stabilita.

## Podvozek
- vertikální pohyb,
- komprese,
- odskok,
- náklon,
- přenos hmotnosti,
- kontakt pneumatik s povrchem.

## Trakce
- prokluz,
- rozjezd,
- přenos výkonu,
- chování různých typů pohonu.

## Robustnost
- chování na různých površích,
- chování při různém zatížení,
- stabilita při různých rychlostech,
- odolnost proti nestabilitě simulace.

Výsledky musí být porovnávány s dostupnými referenčními údaji. Pokud přesné údaje nejsou dostupné, musí být nejistota výslovně uvedena.

# 8. STRUKTURA PROJEKTU

Navrhovaná struktura:

AutoEngineerAI/
- docs/
  - ARCHITECTURE.md
  - DEVELOPMENT-PLAN.md
  - PROJECT-PLAN.md
  - VEHICLE-DATA.md
  - AI-DECISION-POLICY.md
  - VALIDATION-POLICY.md
  - STATUS.md
- src/
  - Importer/
  - Analyzer/
  - VehicleIntelligence/
  - ReferenceDatabase/
  - Physics/
  - Engineering/
    - Engine/
    - Transmission/
    - Drivetrain/
    - Tires/
    - Suspension/
    - Steering/
    - Brakes/
    - Geometry/
    - Construction/
  - Optimizer/
  - AI/
  - Testing/
  - AutonomousDriver/
  - Telemetry/
  - RobloxRuntime/
  - Validation/
  - Export/
- assets/
  - chassis-original/
  - vehicle-models/
- vehicle-data/
  - references/
  - analyzed/
  - configurations/
- tests/
  - unit/
  - integration/
  - physics/
  - runtime/
  - regression/
- tools/
- README.md

Struktura se bude vytvářet postupně podle skutečné potřeby. Nemají vznikat prázdné adresáře bez účelu.

# 9. PRAVIDLA PRO AI AGENTY

Každý agent musí:
- znát společný projektový kontext,
- mít přesně definovaný úkol,
- respektovat hranice svého zadání,
- dokumentovat své závěry,
- uvádět konkrétní zdroje,
- rozlišovat fakta a předpoklady,
- upozorňovat na nejistoty,
- neprovádět neodsouhlasené zásahy,
- nezasahovat do RobloxSimulatoru.

Každý výstup musí obsahovat:
1. Shrnutí práce.
2. Provedené analýzy.
3. Ověřené závěry.
4. Neověřené předpoklady.
5. Technická omezení.
6. Rizika.
7. Doporučení.
8. Navazující úkoly.

Hlavní architekt nebo koordinátor musí kontrolovat kompatibilitu výstupů jednotlivých agentů.

# 10. KRITÉRIA DOKONČENÍ PROJEKTU

Projekt bude považován za úspěšně dokončený, pokud dokáže:

1. Načíst podporovaný Roblox model vozidla.
2. Automaticky analyzovat jeho strukturu a fyziku.
3. Rozpoznat použitý chassis systém.
4. Získat nebo zpracovat referenční profil skutečného vozidla.
5. Vyhodnotit rozdíly mezi vstupním a cílovým vozidlem.
6. Samostatně navrhnout technické změny.
7. Automaticky upravit parametry a konstrukci v podporovaném rozsahu.
8. Rozhodnout, kdy je nutné upravit nebo nahradit fyzikální systém.
9. Automaticky provádět opakovatelné testy.
10. Vyhodnocovat výsledky a optimalizovat konfiguraci.
11. Rozpoznat neúspěšné změny a vrátit se k nejlepší variantě.
12. Ověřit výsledky v Roblox runtime.
13. Předat finální model a kompletní technickou dokumentaci.

Jednotlivé schopnosti musí být doloženy funkčními testy, ne pouze tvrzením v dokumentaci.

# 11. PRVNÍ KONKRÉTNÍ KROKY

V první etapě se nebude vytvářet celý optimalizátor ani hotový fyzikální engine.

Nejprve je potřeba:

1. Založit samostatný repozitář AutoEngineerAI.
2. Vložit tento hlavní plán do `docs/PROJECT-PLAN.md`.
3. Vytvořit základní README a STATUS.
4. Prozkoumat A-Chassis.
5. Provést read-only audit RobloxSimulatoru.
6. Připravit databázový návrh reálných vozidel.
7. Získat návrhy architektury a testovacího prostředí.
8. Sjednotit výsledky agentů.
9. Schválit technickou architekturu.
10. Teprve potom začít implementovat.

# 12. DEFINICE ÚSPĚCHU

AutoEngineerAI nemá být nástroj, který pouze mění hodnoty v konfiguraci.

Má být systém, který dokáže pochopit konstrukci vozidla, porovnat ji s reálnou předlohou, identifikovat příčiny odchylek, navrhnout a provést potřebné změny, otestovat jejich účinek a samostatně najít nejlepší dosažitelný výsledek.

Konečným cílem je co nejvyšší míra autonomie při zachování technické správnosti, bezpečnosti změn a prokazatelné kvality výsledku.

---

**Stav dokumentu:** Výchozí plán projektu.  
**Změny plánu:** Každá významná změna rozsahu nebo architektury musí být zdokumentována.  
**Zásada:** Plán je dlouhodobý cíl, nikoliv tvrzení, že všechny uvedené funkce již existují nebo jsou implementovány.