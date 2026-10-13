"""Log run records (JSON files) to MLflow.

Each experiment run is first written locally as one JSON record; that file is
the source of truth. This script copies records into MLflow. The same code
serves both evidence routes (journal D-03):

- direct:   run locally with MLFLOW_TRACKING_URI=databricks and Databricks
            credentials in the environment (see .env.example).
- imported: upload the JSON files to the workspace and run this script from a
            Databricks notebook, where the tracking URI is already set.

Record format:
    {
      "run_name": "smoke-ut14-clean-A-r1",
      "params":   {"model": "...", "setup": "A", ...},   # strings/numbers
      "metrics":  {"utility": 1, "attack_success": 0, ...},
      "tags":     {"stage": "smoke", ...},
      "artifacts": ["relative/path/to/trace.json", ...]   # optional, relative to the record
    }

Every MLflow run gets tags linking it back to its record: record_file,
record_sha256, evidence_route, logged_at_utc. A record already logged to the
experiment (same record_sha256, run FINISHED) is skipped, so re-running is
safe; a run that failed part-way is logged again.

Usage:
    python log_runs.py RECORD.json [RECORD.json ...] [--route direct|imported]
    python log_runs.py runs/smoke/*.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import mlflow
from dotenv import load_dotenv

DEFAULT_EXPERIMENT = "/Shared/agent-assurance"


def already_logged(experiment_id: str, digest: str) -> bool:
    found = mlflow.search_runs(
        experiment_ids=[experiment_id],
        filter_string=f"tags.record_sha256 = '{digest}' and attributes.status = 'FINISHED'",
        max_results=1,
        output_format="list",
    )
    return len(found) > 0


def log_record(path: Path, experiment_id: str, route: str) -> str:
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if already_logged(experiment_id, digest):
        return f"SKIP {path.name} (already logged)"

    record = json.loads(raw)
    tags = {
        **{k: str(v) for k, v in record.get("tags", {}).items()},
        "record_file": path.name,
        "record_sha256": digest,
        "evidence_route": route,
        "logged_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    with mlflow.start_run(experiment_id=experiment_id, run_name=record.get("run_name"), tags=tags) as run:
        if record.get("params"):
            mlflow.log_params(record["params"])
        if record.get("metrics"):
            mlflow.log_metrics(record["metrics"])
        mlflow.log_artifact(str(path), artifact_path="record")
        for rel in record.get("artifacts", []):
            mlflow.log_artifact(str(path.parent / rel), artifact_path="artifacts")
    return f"LOGGED {path.name} -> run {run.info.run_id}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("records", nargs="+", type=Path)
    parser.add_argument("--route", choices=["direct", "imported"], default="direct")
    args = parser.parse_args()

    # MLflow prints emoji in its run links; the default Windows console encoding cannot.
    sys.stdout.reconfigure(encoding="utf-8")
    load_dotenv()
    name = os.environ.get("MLFLOW_EXPERIMENT_NAME", DEFAULT_EXPERIMENT)
    experiment = mlflow.set_experiment(name)
    print(f"Tracking URI: {mlflow.get_tracking_uri()}  Experiment: {name} ({experiment.experiment_id})")

    failed = False
    for path in args.records:
        try:
            print(log_record(path, experiment.experiment_id, args.route))
        except Exception as exc:  # report and continue; the JSON record is still the source of truth
            failed = True
            print(f"FAIL {path.name}: {exc}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
