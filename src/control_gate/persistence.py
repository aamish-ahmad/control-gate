"""Transactional SQLite persistence for inspectable execution trajectories."""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from pathlib import Path

from control_gate.contracts import ExecutionRun, TrajectoryEvent


class RunStoreError(RuntimeError):
    """Base error for fail-closed persistence operations."""


class RunConflictError(RunStoreError):
    """A run identifier was reused with different content."""


class RunCorruptionError(RunStoreError):
    """Persisted run and event evidence no longer agree."""


class SQLiteRunStore:
    """Persist complete runs and separately inspectable ordered events."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with closing(self._connect()) as connection:
            with connection:
                connection.executescript(
                    """
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    intent_id TEXT NOT NULL,
                    intent_version INTEGER NOT NULL,
                    plan_id TEXT NOT NULL,
                    state TEXT NOT NULL,
                    payload TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS trajectory_events (
                    run_id TEXT NOT NULL,
                    sequence_number INTEGER NOT NULL,
                    event_id TEXT NOT NULL UNIQUE,
                    event_type TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    PRIMARY KEY (run_id, sequence_number),
                    FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE RESTRICT
                );
                """
                )

    @staticmethod
    def _canonical(value: object) -> str:
        return json.dumps(value, sort_keys=True, separators=(",", ":"))

    @classmethod
    def _validated(cls, run: ExecutionRun) -> tuple[ExecutionRun, str, tuple[str, ...]]:
        candidate = ExecutionRun.model_validate_json(run.model_dump_json())
        expected = tuple(range(len(candidate.events)))
        actual = tuple(event.sequence_number for event in candidate.events)
        if actual != expected or len({event.event_id for event in candidate.events}) != len(actual):
            raise RunCorruptionError("Trajectory events must be unique and contiguous from zero")
        payload = cls._canonical(candidate.model_dump(mode="json"))
        events = tuple(cls._canonical(event.model_dump(mode="json"))
                       for event in candidate.events)
        return candidate, payload, events

    def save(self, run: ExecutionRun) -> ExecutionRun:
        """Atomically write a new run; exact repeats are idempotent."""

        candidate, payload, event_payloads = self._validated(run)
        with closing(self._connect()) as connection:
            with connection:
                connection.execute("BEGIN IMMEDIATE")
                existing = connection.execute(
                    "SELECT payload FROM runs WHERE run_id = ?", (candidate.run_id,)
                ).fetchone()
                if existing is not None:
                    if existing["payload"] != payload:
                        raise RunConflictError(
                            f"Run {candidate.run_id} already exists with different content"
                        )
                    self._assert_events(connection, candidate, event_payloads)
                    return candidate
                connection.execute(
                    "INSERT INTO runs(run_id, intent_id, intent_version, plan_id, state, payload) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (candidate.run_id, candidate.intent_id, candidate.intent_version,
                     candidate.plan_id, candidate.state.value, payload),
                )
                connection.executemany(
                    "INSERT INTO trajectory_events(run_id, sequence_number, event_id, "
                    "event_type, timestamp, payload) VALUES (?, ?, ?, ?, ?, ?)",
                    ((candidate.run_id, event.sequence_number, event.event_id,
                      event.event_type.value, event.timestamp.isoformat(), event_payloads[index])
                     for index, event in enumerate(candidate.events)),
                )
        return candidate

    def get(self, run_id: str) -> ExecutionRun | None:
        """Read and cross-check a complete run and its event rows."""

        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT * FROM runs WHERE run_id = ?", (run_id,)
            ).fetchone()
            if row is None:
                return None
            try:
                run = ExecutionRun.model_validate_json(row["payload"])
            except Exception as error:
                raise RunCorruptionError("Persisted run payload is invalid") from error
            if (row["run_id"], row["intent_id"], row["intent_version"],
                    row["plan_id"], row["state"]) != (
                    run.run_id, run.intent_id, run.intent_version,
                    run.plan_id, run.state.value):
                raise RunCorruptionError("Run index columns do not match the payload")
            _, _, event_payloads = self._validated(run)
            self._assert_events(connection, run, event_payloads)
            return run

    def events(self, run_id: str) -> tuple[TrajectoryEvent, ...] | None:
        """Return the validated trajectory event stream in sequence order."""

        run = self.get(run_id)
        return None if run is None else run.events

    def _assert_events(self, connection: sqlite3.Connection, run: ExecutionRun,
                       expected: tuple[str, ...]) -> None:
        rows = connection.execute(
            "SELECT sequence_number, event_id, event_type, timestamp, payload "
            "FROM trajectory_events WHERE run_id = ? ORDER BY sequence_number",
            (run.run_id,),
        ).fetchall()
        if len(rows) != len(expected):
            raise RunCorruptionError("Persisted event count does not match the run")
        for index, (row, payload) in enumerate(zip(rows, expected, strict=True)):
            try:
                event = TrajectoryEvent.model_validate_json(row["payload"])
            except Exception as error:
                raise RunCorruptionError("Persisted trajectory event is invalid") from error
            if (row["sequence_number"], row["event_id"], row["event_type"],
                    row["timestamp"], row["payload"]) != (
                    index, event.event_id, event.event_type.value,
                    event.timestamp.isoformat(), payload):
                raise RunCorruptionError("Persisted event index does not match its payload")
