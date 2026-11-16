"""AutoEngineerAI Sim — lokalni deterministicka simulace vozidla (mode local-sim).

Vlastnictvi: agent C (vlna 1). Pouze `src/Sim/*.py`.
Spotrebovava VehicleConfig (ARCHITECTURE §3.3), vola src/Physics pres
`physics_backend` (relativni import, bez kopirovani; viz jeho docstring).

Konvence: souradnice x vpred / y vlevo / z vzhuru, SI, g = 9.81.
Integrator: semi-implicitni Euler, pevny dt (default 1/240).
Determinismus: stejny config + seed + scenar + kod = bitove stejny CSV.
Nastroje: pouze Python 3 stdlib. Zadne git operace.

Package-level `run_scenario(config, scenario, mode)` je kontrakt
ARCH §5.3 — tenky obal nad `run.run_scenario` (souborova uroven),
ktery adaptuje argumenty (dict vs. cesta, aliasy scenaru).
"""

import json
import os
import tempfile

from .config import SAMPLE_MX5_CONFIG, load_config, resolve_params
from .scenarios import SCENARIOS, get_scenario
from .vehicle import simulate

__version__ = "1.0.0"

# Import az po __version__ (run.py si ho pri importu prebira z balicku).
from .run import DEFAULT_DT, MODE  # noqa: E402
from .run import run_scenario as _run_file_scenario  # noqa: E402

__all__ = ["SCENARIOS", "SAMPLE_MX5_CONFIG", "get_scenario", "load_config",
           "resolve_params", "simulate", "run_scenario"]

# Alias mapovani externich ID (Optimizer: S1_accel/S3_brake) na Sim scenare.
_SCENARIO_ALIASES = {
    "S1_accel": "straight_accel",
    "S1": "straight_accel",
    "S3_brake": "straight_brake_100_0",
    "S3": "straight_brake_100_0",
}


def _resolve_scenario_id(scenario):
    """Normalizuje scenario (str id nebo dict) na Sim scenario_id."""
    if isinstance(scenario, dict):
        for key in ("scenario_id", "id", "kind"):
            val = scenario.get(key)
            if isinstance(val, str):
                sid = _SCENARIO_ALIASES.get(val, val)
                if sid in SCENARIOS:
                    return sid
        raise ValueError("Neznamy scenar: %r" % (scenario,))
    if isinstance(scenario, str):
        sid = _SCENARIO_ALIASES.get(scenario, scenario)
        if sid not in SCENARIOS:
            raise ValueError("Neznamy scenar: %r" % (scenario,))
        return sid
    raise TypeError("scenario musi byt str nebo dict, ne %s"
                    % type(scenario).__name__)


def run_scenario(config, scenario, mode="local-sim", dt=DEFAULT_DT,
                 seed=0, out_dir=None):
    """Kontrakt ARCH §5.3: run_scenario(config, scenario, mode) -> RawTelemetry.

    Tenky obal nad `run.run_scenario(config_path, scenario_id, dt, seed,
    out_dir)` — adaptuje argumenty, simulace sama je identicka:
      config: VehicleConfig dict, nebo cesta k VehicleConfig JSON.
      scenario: Sim scenario_id (str), pripadne dict se scenario_id/id/kind;
        aliasy S1_accel/S3_brake (Optimizer) se mapuji na Sim scenare.
      mode: musi byt "local-sim" (jediny rezim Sim).
    Vraci (csv_path, manifest_path, manifest) — CSV telemetrie je
    RawTelemetry artefakt; manifest nese mode/seed/verze.
    """
    if not isinstance(mode, str) or mode != MODE:
        raise ValueError("Nepodporovany mode %r (ocekavano %r)"
                         % (mode, MODE))
    scenario_id = _resolve_scenario_id(scenario)
    if isinstance(config, dict):
        target_dir = out_dir or tempfile.mkdtemp(prefix="sim_run_")
        os.makedirs(target_dir, exist_ok=True)
        config_path = os.path.join(target_dir, "config.json")
        with open(config_path, "w", encoding="utf-8") as fh:
            json.dump(config, fh, indent=2, sort_keys=True)
        out_dir = target_dir
    elif isinstance(config, str):
        config_path = config
        if out_dir is None:
            out_dir = tempfile.mkdtemp(prefix="sim_run_")
    else:
        raise TypeError("config musi byt dict VehicleConfig nebo cesta "
                        "k JSON, ne %s" % type(config).__name__)
    return _run_file_scenario(config_path, scenario_id, dt, seed, out_dir)
