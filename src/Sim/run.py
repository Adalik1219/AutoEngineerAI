"""CLI: python -m src.Sim.run --config <VehicleConfig.json>
      --scenario <id> [--dt 0.0041667] [--seed 1] --out <dir>

Zapise RAW telemetrii `telemetry.csv` (fixni sloupce) + `manifest.json`
{code_version, seed, scenario_version, mode: local-sim}.
Opakovani identickeho testu = stejne argumenty -> bitove stejny CSV.
"""

import argparse
import csv
import hashlib
import json
import os
import sys

from . import physics_backend as phys
from .config import load_config, validate_params
from .scenarios import SCENARIOS, SCENARIO_VERSIONS, get_scenario
from .vehicle import TELEMETRY_COLUMNS, simulate
from . import __version__ as SIM_VERSION

DEFAULT_DT = 1.0 / 240.0
MODE = "local-sim"


def sim_src_version():
    """code_version bez git operaci: sha256 vlastnich zdroju src/Sim/*.py."""
    here = os.path.dirname(os.path.abspath(__file__))
    digest = hashlib.sha256()
    for name in sorted(os.listdir(here)):
        if name.endswith(".py"):
            with open(os.path.join(here, name), "rb") as fh:
                digest.update(fh.read())
    return "sim-src-" + digest.hexdigest()[:16]


def _fmt(value):
    if isinstance(value, float):
        return repr(value)
    return str(value)


def run_scenario(config_path, scenario_id, dt, seed, out_dir):
    cfg, used_defaults = load_config(config_path)
    params = cfg["parameters"]
    errors = validate_params(params)
    if errors:
        raise ValueError("Neplatny config: " + "; ".join(errors))
    scenario_def = get_scenario(scenario_id)
    rows, abort, probe = simulate(params, scenario_def, dt, seed)

    os.makedirs(out_dir, exist_ok=True)
    csv_path = os.path.join(out_dir, "telemetry.csv")
    with open(csv_path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow(TELEMETRY_COLUMNS)
        for row in rows:
            writer.writerow([_fmt(v) for v in row])
    with open(csv_path, "rb") as fh:
        csv_sha = hashlib.sha256(fh.read()).hexdigest()

    manifest = {
        "code_version": sim_src_version(),
        "sim_version": SIM_VERSION,
        "seed": seed,
        "scenario_version": SCENARIO_VERSIONS[scenario_id],
        "mode": MODE,
        "scenario_id": scenario_id,
        "config_id": cfg.get("config_id", "cfg_unnamed"),
        "dt": dt,
        "backend": phys.backend_name(),
        "expected_physics_api": list(phys.EXPECTED_PHYSICS_API),
        "used_defaults": used_defaults,
        "rows": len(rows),
        "duration_s": rows[-1][0] if rows else 0.0,
        "telemetry_sha256": csv_sha,
        "telemetry_columns": list(TELEMETRY_COLUMNS),
        "abort": {"flag": abort is not None, "reason": abort},
        "rng_probe": probe,
    }
    manifest_path = os.path.join(out_dir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, sort_keys=True)
        fh.write("\n")
    return csv_path, manifest_path, manifest


def main(argv=None):
    ap = argparse.ArgumentParser(description="AutoEngineerAI Sim (local-sim)")
    ap.add_argument("--config", required=False,
                    help="Cesta k VehicleConfig JSON")
    ap.add_argument("--scenario", required=False, choices=SCENARIOS,
                    help="ID scenare")
    ap.add_argument("--dt", type=float, default=DEFAULT_DT,
                    help="Pevny krok (default 1/240)")
    ap.add_argument("--seed", type=int, default=0,
                    help="Seed RNG (default 0)")
    ap.add_argument("--out", required=False, help="Vystupni adresar")
    ap.add_argument("--list-scenarios", action="store_true",
                    help="Vypise scenare a skonci")
    args = ap.parse_args(argv)
    if args.list_scenarios:
        for sid in SCENARIOS:
            print("%s (v%s)" % (sid, SCENARIO_VERSIONS[sid]))
        return 0
    if not args.config or not args.scenario or not args.out:
        ap.error("--config, --scenario a --out jsou povinne")
    if not (0.0 < args.dt <= 1.0 / 30.0):
        ap.error("--dt musi byt v (0, 1/30]")
    csv_path, manifest_path, manifest = run_scenario(
        args.config, args.scenario, args.dt, args.seed, args.out)
    print("OK scenario=%s rows=%d abort=%s" % (
        args.scenario, manifest["rows"], manifest["abort"]["reason"]))
    print("csv: " + csv_path)
    print("manifest: " + manifest_path)
    print("sha256: " + manifest["telemetry_sha256"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
