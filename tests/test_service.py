"""C6 FastAPI engineering-boundary acceptance tests."""

import sqlite3

from fastapi.testclient import TestClient

from control_gate.invoice_runtime import DEMO_REQUEST
from control_gate.service import create_app


def test_http_run_is_persisted_and_inspectable_after_app_recreation(tmp_path):
    path = tmp_path / "service.sqlite3"
    first = TestClient(create_app(path))
    created = first.post("/v1/runs", json={"request": DEMO_REQUEST})
    assert created.status_code == 201
    run = created.json()
    assert run["state"] == "COMPLETED"
    assert run["evidence"]["stage_payment"]["external_actions_performed"] == 0

    second = TestClient(create_app(path))
    fetched = second.get(f"/v1/runs/{run['run_id']}")
    events = second.get(f"/v1/runs/{run['run_id']}/events")
    assert fetched.status_code == events.status_code == 200
    assert fetched.json() == run
    assert events.json() == run["events"]
    assert [event["sequence_number"] for event in events.json()] == list(
        range(len(events.json()))
    )


def test_service_health_and_openapi_are_inspectable(tmp_path):
    client = TestClient(create_app(tmp_path / "service.sqlite3"))
    assert client.get("/health").json() == {"status": "ok"}
    schema = client.get("/openapi.json").json()
    assert schema["info"]["title"] == "Control Gate"
    assert set(schema["paths"]) == {
        "/health", "/v1/runs", "/v1/runs/{run_id}",
        "/v1/runs/{run_id}/events",
    }
    assert all("resume" not in path for path in schema["paths"])


def test_malformed_request_and_unknown_run_fail_without_persistence(tmp_path):
    path = tmp_path / "service.sqlite3"
    client = TestClient(create_app(path))
    assert client.post("/v1/runs", json={"request": ""}).status_code == 422
    assert client.post("/v1/runs", json={"wrong": "field"}).status_code == 422
    assert client.get("/v1/runs/missing").status_code == 404
    assert client.get("/v1/runs/missing/events").status_code == 404
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM runs").fetchone()[0] == 0


def test_corrupt_persisted_evidence_is_not_served(tmp_path):
    path = tmp_path / "service.sqlite3"
    client = TestClient(create_app(path))
    run = client.post("/v1/runs", json={"request": DEMO_REQUEST}).json()
    with sqlite3.connect(path) as connection:
        connection.execute(
            "DELETE FROM trajectory_events WHERE run_id = ? AND sequence_number = 0",
            (run["run_id"],),
        )
    response = client.get(f"/v1/runs/{run['run_id']}")
    assert response.status_code == 500
    assert response.json() == {"detail": "Persisted run evidence is invalid"}
