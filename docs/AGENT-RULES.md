# Pravidla pro AI agenty – AutoEngineerAI

1. Znáš společný kontext (`docs/PROJECT-PLAN.md`) a svůj přesně vymezený úkol + svůj vlastněný výstupní soubor. Mimo něj nic nevytvářej ani neupravuj.
2. Píšeš česky. Identifikátory, názvy tříd a kód anglicky.
3. U každého závěru rozliš: **ověřená fakta / předpoklady / neznámé**. Uváděj zdroje a přesné cesty k souborům (absolutní, např. `C:/.DATA/RobloxSimulator/...`).
4. Neodhaduj obsah souborů, které jsi skutečně neprozkoumal (čtením nebo/inspekčními nástroji).
5. `C:/.DATA/RobloxSimulator` je READ-ONLY: žádný zápis, commit, branch, PR, nastavení. Ověř před prací `git -C 'C:/.DATA/RobloxSimulator' rev-parse --show-toplevel` a po práci potvrď nulový diff (`status --short` prázdný).
6. Originál `C:/Users/adamr/Downloads/chasis.rbxm` nikdy nepřepisuj; pracuj pouze s kopiemi v `C:/.DATA/AutoEngineerAI/assets/chassis-original/` nebo scratchi.
7. Navrhuj řešení s ohledem na celý AutoEngineerAI. Neprováděj změny mimo svůj rozsah.
8. Narazíš-li na problém, popiš jej a navrhni řešení místo obcházení.
9. Výstup = soubor, který vlastníš + závěrečné shrnutí: provedená práce, technické poznatky, ověřená fakta, nevyřešené otázky, rizika/omezení, doporučené další kroky.
10. Subagent si může vytvořit vlastního subagenta pouze uvnitř svého rozsahu a svého vlastněného souboru.
