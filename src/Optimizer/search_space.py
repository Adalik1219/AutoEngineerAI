"""Parametricky prostor optimalizace (ARCHITECTURE §5.2, TESTING-OPTIMIZATION §5.1).

search_space(config, plan) -> explicitni rozsahy 2–3 parametru.
Meze jsou tvrde (bezpecnostni filtr kandidaty mimo meze zamita bez testu).
Pouze stdlib.
"""

# Tvrde meze + diskretizacni krok. Kalibrace SIM (Agent G, vlna 1):
# final_drive [2.5, 4.2] pokrýva tovarni 2.866 i degradovane okraje;
# nad ~4.0 si model vynuti 4. rychlostni stupen do 100 km/h a vazi V-max
# prevodem (interierove optimum), pod ~2.6 chyba sila na kolech.
PARAM_DEFS = {
    "transmission.final_drive": {
        "min": 2.5, "max": 4.2, "step": 0.15, "unit": "-",
        "label": "staly prevod",
    },
    "engine.peak_torque_nm": {
        "min": 180.0, "max": 250.0, "step": 5.0, "unit": "Nm",
        "label": "spickovy moment motoru",
    },
    "brakes.bias_front": {
        "min": 0.55, "max": 0.70, "step": 0.01, "unit": "-",
        "label": "brzdny bias na predni napravu",
    },
}

# Poradi sond (koordinatni sestup). final_drive prvni: primarni paka
# pro selftest se zhorsenym stalym prevodem.
CORE_ORDER = [
    "transmission.final_drive",
    "engine.peak_torque_nm",
    "brakes.bias_front",
]


def get_param(config, name):
    """Hodnota teckovane cesty v config['parameters'] (napr. 'transmission.final_drive')."""
    node = config["parameters"]
    for part in name.split("."):
        if not isinstance(node, dict) or part not in node:
            raise KeyError("parametr %r v konfiguraci chybi" % name)
        node = node[part]
    return node


def set_param(config, name, value):
    """Nastavi teckvanou cestu v config['parameters'] (in-place, volat na kopii)."""
    parts = name.split(".")
    node = config["parameters"]
    for part in parts[:-1]:
        if not isinstance(node.get(part), dict):
            raise KeyError("cesta %r v konfiguraci chybi" % name)
        node = node[part]
    node[parts[-1]] = value


def _plan_priority(plan):
    """Poradi parametru podle plan.priorities, pokud odkazuji na zname parametry."""
    if not isinstance(plan, dict):
        return []
    prios = plan.get("priorities") or []
    area_to_param = {
        "transmission": "transmission.final_drive",
        "engine": "engine.peak_torque_nm",
        "powertrain": "transmission.final_drive",
        "brakes": "brakes.bias_front",
        "braking": "brakes.bias_front",
    }
    ordered = []
    for area in prios:
        param = area_to_param.get(str(area).lower())
        if param and param not in ordered:
            ordered.append(param)
    return ordered


def search_space(config, plan=None):
    """Vrati list explicitnich rozsahu: [{name, min, max, step, unit, current}].

    `plan` (ChangePlan) muze urcit poradi priorit; rozsahy zustavaji tvrde.
    Nezane kroky planu mimo tento prostor se ignoruji (optimizer na ne nesaha).
    """
    ordered = _plan_priority(plan)
    for name in CORE_ORDER:
        if name not in ordered:
            ordered.append(name)
    space = []
    for name in ordered:
        spec = PARAM_DEFS[name]
        try:
            current = get_param(config, name)
        except KeyError:
            current = None
        space.append({
            "name": name,
            "min": spec["min"],
            "max": spec["max"],
            "step": spec["step"],
            "unit": spec["unit"],
            "current": current,
        })
    return space
