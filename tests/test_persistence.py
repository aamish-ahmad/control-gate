"""C6 transactional trajectory-persistence acceptance tests."""

import sqlite3

import pytest

from control_gate.contracts import RunState
from control_gate.invoice_runtime import DEMO_REQUEST, execute_invoice
from control_gate.persistence import (
    RunConflictError,
    RunCorruptionError,
    SQLiteRunStore,
)


def test_complete_run_and_ordered_events_survive_store_recreation(tmp_path):
    path = tmp_path / "runs.sqlite3"
    run = execute_invoice(DEMO_REQUEST)
    SQLiteRunStore(path).save(run)

    restored_store = SQLiteRunStore(path)
    restored = restored_store.get(run.run_id)
    assert restored == run
    assert restored_store.events(run.run_id) == run.events
    assert [event.sequence_number for event in restored.events] == list(
        range(len(restored.events))
    )
    assert restored.state is RunState.COMPLETED
    assert restored.evidence["stage_payment"]["external_actions_performed"] == 0
    path.unlink()
    assert not path.exists()


def test_exact_repeat_is_idempotent_but_changed_run_is_rejected(tmp_path):
    store = SQLiteRunStore(tmp_path / "runs.sqlite3")
    run = execute_invoice(DEMO_REQUEST)
    assert store.save(run) == store.save(run)

    run.token_count = 1
    with pytest.raises(RunConflictError, match="different content"):
        store.save(run)
    assert store.get(run.run_id).token_count == 0


def test_noncontiguous_event_stream_is_rejected_before_write(tmp_path):
    store = SQLiteRunStore(tmp_path / "runs.sqlite3")
    run = execute_invoice(DEMO_REQUEST)
    run.events = tuple(
        event.model_copy(update={"sequence_number": event.sequence_number + 1})
        for event in run.events
    )
    with pytest.raises(RunCorruptionError, match="contiguous"):
        store.save(run)
    assert store.get(run.run_id) is None


@pytest.mark.parametrize("table,column", [
    ("runs", "state"),
    ("trajectory_events", "event_type"),
    ("trajectory_events", "payload"),
])
def test_database_index_or_event_divergence_fails_closed(tmp_path, table, column):
    path = tmp_path / "runs.sqlite3"
    store = SQLiteRunStore(path)
    run = execute_invoice(DEMO_REQUEST)
    store.save(run)
    with sqlite3.connect(path) as connection:
        if table == "runs":
            connection.execute(
                "UPDATE runs SET state = 'FAILED' WHERE run_id = ?", (run.run_id,)
            )
        elif column == "event_type":
            connection.execute(
                "UPDATE trajectory_events SET event_type = 'run_failed' "
                "WHERE run_id = ? AND sequence_number = 0", (run.run_id,)
            )
        else:
            connection.execute(
                "UPDATE trajectory_events SET payload = '{}' "
                "WHERE run_id = ? AND sequence_number = 0", (run.run_id,)
            )
    with pytest.raises(RunCorruptionError):
        store.get(run.run_id)


def test_unknown_run_has_no_synthetic_evidence(tmp_path):
    store = SQLiteRunStore(tmp_path / "runs.sqlite3")
    assert store.get("missing") is None
    assert store.events("missing") is None
