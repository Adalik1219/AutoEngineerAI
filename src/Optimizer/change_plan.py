"""Pravidlovy ChangePlan v0 z Diagnosis (ARCHITECTURE §3.4, plan FÁZE 7 DecisionAI v0).

Deterministicky, bez LLM: pevna pravidla symptom -> krok, stabilni poradi.
Kroky mimo optimalizacni prostor se generuji, ale optimizer je ignoruje
(prostor drzi search_space; viz TESTING-OPTIMIZATION §5.2 bod 5).
Pouze stdlib.
"""

from .search_space import get_param

# (klicova slova v symptom/probable_cause/area/metrikach, krok-sablona)
# Poradi = priorita pri shode vice pravidel. Deterministicke.
RULES = [
    {
        "match": ("accel", "t_0_100", "t_0_60", "akceler", "rozjezd", "launch"),
        "area": "transmission",
        "action": "set_final_drive",
        "param": "transmission.final_drive",
        "delta": 0.15,
        "expected_effect": "vyssi sila na kolech -> kratsi t_0_100 (riziko: nizsi V-max)",
        "risk": "zhorseni V-max omezenim prevodem; hlida A2/A4",
    },
    {
        "match": ("vmax", "v_max", "rychlost", "top speed"),
        "area": "transmission",
        "action": "set_final_drive",
        "param": "transmission.final_drive",
        "delta": -0.15,
        "expected_effect": "delsi prevod -> vyssi V-max (riziko: horsi akcelerace)",
        "risk": "zhorseni akcelerace; hlida A2/A4",
    },
    {
        "match": ("brake", "brzd", "decel", "stopping"),
        "area": "brakes",
        "action": "set_bias_front",
        "param": "brakes.bias_front",
        "delta": None,  # smer k 0.60 se dopocte z aktualni hodnoty
        "expected_effect": "bias k 0.60 -> kratsi brzdna draha",
        "risk": "nestabilita pri prebrzdeni zadku; hlida A2/A3",
    },
    {
        "match": ("slip", "prokluz", "trakc", "traction"),
        "area": "tires",
        "action": "review_grip",
        "param": None,
        "delta": None,
        "expected_effect": "kontrola gripu hnacich kol (mimo parametricky prostor v0)",
        "risk": "krok je diagnosticky, optimizer ho neaplikuje",
    },
    {
        "match": ("roll", "naklon", "understeer", "oversteer", "nedotac", "pretac", "stabil"),
        "area": "suspension",
        "action": "review_roll_stiffness",
        "param": None,
        "delta": None,
        "expected_effect": "kontrola tuhosti/klopeni (mimo parametricky prostor v0)",
        "risk": "krok je diagnosticky, optimizer ho neaplikuje",
    },
]


def _item_text(item):
    parts = [
            str(item.get("area", "")),
            str(item.get("symptom", "")),
            str(item.get("probable_cause", "")),
        ] + [str(k) for k in (item.get("evidence_metrics") or {}).keys()]
    return " ".join(parts).lower()


def plan_from_diagnosis(diagnosis, config, max_iterations=50):
    """ diagnosis (dict dle diagnosis-v1) + config -> ChangePlan (dict dle change_plan-v1).

    Pravidla se zkousi v pevnem poradi RULES; kazde pravidlo vystreli nejvyse
    jednou; kroky drzi poradi vystrelu. diagnosis_ref = diagnosis_id,
    plan_id = 'plan_' + zbytek id (deterministicke).
    """
    diag_id = diagnosis.get("diagnosis_id", "dg_unknown")
    suffix = diag_id[3:] if diag_id.startswith("dg_") else diag_id
    items = diagnosis.get("items") or []
    steps = []
    priorities = []
    fired = set()
    for rule in RULES:
        for item in items:
            text = _item_text(item)
            if any(key in text for key in rule["match"]):
                if id(rule) in fired:
                    continue
                fired.add(id(rule))
                step = {
                    "area": rule["area"],
                    "action": rule["action"],
                    "expected_effect": rule["expected_effect"],
                    "risk": rule["risk"],
                }
                if rule["param"]:
                    try:
                        current = get_param(config, rule["param"])
                    except (KeyError, TypeError):
                        current = None
                    delta = rule["delta"]
                    if delta is None and rule["param"] == "brakes.bias_front" \
                            and isinstance(current, (int, float)):
                        # Krok 0.01 smerem k 0.60 (kalibracni optimum SIM modelu).
                        delta = 0.01 if current < 0.60 else -0.01
                    step["from"] = current
                    step["to"] = (current + delta) if isinstance(
                        current, (int, float)) and isinstance(
                        delta, (int, float)) else None
                else:
                    step["from"] = item.get("area")
                    step["to"] = "review"
                step["diagnosis_symptom"] = item.get("symptom", "")
                steps.append(step)
                if rule["area"] not in priorities:
                    priorities.append(rule["area"])
                break
    if not steps:
        steps.append({
            "area": "transmission",
            "action": "probe_final_drive",
            "expected_effect": "sonda citlivosti staleho prevodu (zadny pozadavek z diagnozy)",
            "risk": "zadne; sonda se vyhodnoti A1–A4",
            "from": None,
            "to": None,
        })
        priorities.append("transmission")
    return {
        "schema_version": "1.0.0",
        "plan_id": "plan_" + suffix,
        "diagnosis_ref": diag_id,
        "steps": steps,
        "chassis_decision": "keep",  # v0 meni jen parametry, ne konstrukci
        "priorities": priorities,
        # Cile zastaveni: cilove skore se ridi tolerancemi (TARGET_MET);
        # target_score ve schematu je 0..1 higher-better konvence, nase TotalScore
        # je lower-better bez omezeni -> v0 ho neuvadi, rozhoduje budget + A1–A4.
        "stop_conditions": {"max_iterations": int(max_iterations)},
    }
