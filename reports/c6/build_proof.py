"""Build the bounded C6 persistence/service proof; this is not an experiment."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

from control_gate.invoice_runtime import DEMO_REQUEST
from control_gate.service import create_app


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "reports" / "c6" / "engineering_proof.json"


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def main() -> None:
    with TemporaryDirectory() as directory:
        database = Path(directory) / "runs.sqlite3"
        with TestClient(create_app(database)) as first:
            created = first.post("/v1/runs", json={"request": DEMO_REQUEST})
            assert created.status_code == 201
            run = created.json()

        with TestClient(create_app(database)) as restarted:
            fetched = restarted.get(f"/v1/runs/{run['run_id']}")
            events = restarted.get(f"/v1/runs/{run['run_id']}/events")
            service_paths = sorted(restarted.get("/openapi.json").json()["paths"])
            assert fetched.status_code == events.status_code == 200
            assert fetched.json() == run
            assert events.json() == run["events"]
            assert run["evidence"]["stage_payment"]["external_actions_performed"] == 0

        with closing(sqlite3.connect(database)) as connection:
            run_rows = connection.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
            event_rows = connection.execute(
                "SELECT COUNT(*) FROM trajectory_events WHERE run_id = ?",
                (run["run_id"],),
            ).fetchone()[0]
            sqlite_integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]

        proof = {
            "phase": "C6",
            "case": "fastapi_sqlite_restart_readback",
            "service_paths": service_paths,
            "state": run["state"],
            "run_id": run["run_id"],
            "intent_id": run["intent_id"],
            "intent_version": run["intent_version"],
            "event_count": len(run["events"]),
            "event_sequence": [event["sequence_number"] for event in run["events"]],
            "run_rows": run_rows,
            "event_rows": event_rows,
            "sqlite_integrity": sqlite_integrity,
            "restart_readback_equal": fetched.json() == run,
            "event_readback_equal": events.json() == run["events"],
            "external_actions_performed": 0,
            "run_sha256": hashlib.sha256(canonical(run)).hexdigest(),
            "events_sha256": hashlib.sha256(canonical(run["events"])).hexdigest(),
            "run": run,
        }
        assert proof["event_sequence"] == list(range(proof["event_count"]))
        assert proof["run_rows"] == 1
        assert proof["event_rows"] == proof["event_count"]
        assert proof["sqlite_integrity"] == "ok"
        OUTPUT.write_text(json.dumps(proof, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps({key: value for key, value in proof.items() if key != "run"},
                         indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
