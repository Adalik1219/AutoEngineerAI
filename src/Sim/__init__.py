"""AutoEngineerAI Sim — lokalni deterministicka simulace vozidla (mode local-sim).

Vlastnictvi: agent C (vlna 1). Pouze `src/Sim/*.py`.
Spotrebovava VehicleConfig (ARCHITECTURE §3.3), vola src/Physics pres
`physics_backend` (relativni import, bez kopirovani; viz jeho docstring).

Konvence: souradnice x vpred / y vlevo / z vzhuru, SI, g = 9.81.
Integrator: semi-implicitni Euler, pevny dt (default 1/240).
Determinismus: stejny config + seed + scenar + kod = bitove stejny CSV.
Nastroje: pouze Python 3 stdlib. Zadne git operace.
"""

from .config import SAMPLE_MX5_CONFIG, load_config, resolve_params
from .scenarios import SCENARIOS, get_scenario
from .vehicle import simulate

__version__ = "1.0.0"
__all__ = ["SCENARIOS", "SAMPLE_MX5_CONFIG", "get_scenario", "load_config",
           "resolve_params", "simulate"]
