"""FastAPI boundary over the verified C5 supplier-invoice trajectory."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field

from control_gate.contracts import ExecutionRun, TrajectoryEvent
from control_gate.invoice_runtime import execute_invoice
from control_gate.persistence import RunConflictError, RunCorruptionError, SQLiteRunStore


class CreateRunRequest(BaseModel):
    """HTTP input only; authorization remains owned by the existing runtime."""

    model_config = ConfigDict(extra="forbid")
    request: str = Field(min_length=1)


def _default_database_path() -> Path:
    configured = os.environ.get("CONTROL_GATE_DB_PATH")
    return (Path(configured) if configured else
            Path(tempfile.gettempdir()) / "control-gate" / "runs.sqlite3")


def create_app(database_path: str | Path | None = None) -> FastAPI:
    """Construct a service with an explicit or environment-backed run store."""

    api = FastAPI(title="Control Gate", version="0.1.0")
    api.state.run_store = SQLiteRunStore(database_path or _default_database_path())

    @api.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @api.post("/v1/runs", response_model=ExecutionRun,
              status_code=status.HTTP_201_CREATED)
    def create_run(payload: CreateRunRequest, request: Request) -> ExecutionRun:
        try:
            run = execute_invoice(payload.request)
            return request.app.state.run_store.save(run)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except RunConflictError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @api.get("/v1/runs/{run_id}", response_model=ExecutionRun)
    def get_run(run_id: str, request: Request) -> ExecutionRun:
        try:
            run = request.app.state.run_store.get(run_id)
        except RunCorruptionError as error:
            raise HTTPException(status_code=500, detail="Persisted run evidence is invalid") from error
        if run is None:
            raise HTTPException(status_code=404, detail="Run not found")
        return run

    @api.get("/v1/runs/{run_id}/events", response_model=list[TrajectoryEvent])
    def get_events(run_id: str, request: Request) -> tuple[TrajectoryEvent, ...]:
        try:
            events = request.app.state.run_store.events(run_id)
        except RunCorruptionError as error:
            raise HTTPException(status_code=500, detail="Persisted run evidence is invalid") from error
        if events is None:
            raise HTTPException(status_code=404, detail="Run not found")
        return events

    return api


app = create_app()
