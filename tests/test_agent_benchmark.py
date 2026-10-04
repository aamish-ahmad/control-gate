"""C7 frozen governed-versus-ungoverned experiment acceptance tests."""

from __future__ import annotations

import csv
import json
import re
import struct
from collections import Counter
from pathlib import Path

import pytest

from control_gate import invoice_runtime
from control_gate.agent_benchmark import (
    ARMS,
    EXPECTED_FAMILIES,
    TASK_PATH,
    _environment,
    _intervention,
    canonical_json,
    comparison_rows,
    digest,
    execute,
    generate_chart,
    load_tasks,
    recompute_summary,
    regenerate_chart_only,
    run_episode,
    _resolve_project_root,
    scoped_runtime_configuration,
    task_digests,
    validate_pairing,
)
from control_gate.contracts import Decision, EventType, RunState
from control_gate.evaluation import compile_request


@pytest.fixture(scope="module")
def tasks():
    return load_tasks()


@pytest.fixture(scope="module")
def artifacts():
    root = TASK_PATH.parents[1]
    episode = root / "outputs" / "c7" / "episodes.jsonl"
    summary = root / "outputs" / "c7" / "summary.json"
    comparison = root / "reports" / "c7" / "comparison.csv"
    chart = root / "reports" / "c7" / "safety_control_vs_overhead.png"
    results = root / "reports" / "c7" / "RESULTS.md"
    computed = json.loads(summary.read_text(encoding="utf-8"))
    rows = [json.loads(line) for line in episode.read_text(encoding="utf-8").splitlines()]
    return root, computed, rows, summary, comparison, chart, results


def test_installed_module_prefers_checkout_root():
    checkout = TASK_PATH.parents[1]
    installed_module = checkout / ".venv" / "Lib" / "site-packages" / "control_gate" / "agent_benchmark.py"
    assert _resolve_project_root(installed_module, cwd=checkout) == checkout


def test_frozen_task_distribution_schema_and_digests(tasks):
    assert len(tasks) == 50
    assert Counter(task["family"] for task in tasks) == Counter(EXPECTED_FAMILIES)
    assert [task["index"] for task in tasks] == list(range(1, 51))
    assert len({task["task_id"] for task in tasks}) == 50
    for task in tasks:
        components = task_digests(task)
        assert set(components) == {
            "task", "request", "environment", "failures", "human",
            "proposal_mutation", "oracle",
        }
        assert all(re.fullmatch(r"[0-9a-f]{64}", value) for value in components.values())
        assert components["task"] == digest(task)


def test_exact_pairing_balanced_order_and_component_identity(artifacts):
    _, _, episodes, *_ = artifacts
    validate_pairing(episodes)
    assert len(episodes) == 100
    pairs = {task_id: [row for row in episodes if row["task_id"] == task_id]
             for task_id in {row["task_id"] for row in episodes}}
    assert all({row["arm"] for row in pair} == set(ARMS) for pair in pairs.values())
    assert sum(next(row["arm"] for row in pair if row["pair_order"] == 1) == "GATED"
               for pair in pairs.values()) == 25
    assert all(pair[0]["digests"] == pair[1]["digests"] for pair in pairs.values())


def test_scoped_bypass_restores_after_exception_and_does_not_leak(tasks):
    original_a = invoice_runtime.decide
    original_b = invoice_runtime.decide_runtime
    original_propose = invoice_runtime._propose
    with pytest.raises(RuntimeError, match="probe"):
        with scoped_runtime_configuration(ungated=True, proposal_mutation=None):
            assert invoice_runtime.decide is not original_a
            assert invoice_runtime.decide_runtime is not original_b
            assert invoice_runtime._propose is original_propose
            raise RuntimeError("probe")
    assert invoice_runtime.decide is original_a
    assert invoice_runtime.decide_runtime is original_b
    assert invoice_runtime._propose is original_propose
    governed = run_episode(tasks[22], "GATED", pair_order=1)
    assert governed["metrics"]["observed_state"] == "REJECTED"
    assert governed["metrics"]["tool_call_attempts"] == 0


def test_ungated_records_correctly_linked_approve_decisions(tasks):
    row = run_episode(tasks[0], "UNGATED", pair_order=1)
    assert row["metrics"]["observed_state"] == "COMPLETED"
    run = row["runs"][0]
    checks = [event for event in run["events"] if event["event_type"] == "runtime_policy_check"]
    starts = [event for event in run["events"] if event["event_type"] == "tool_call_started"]
    assert len(checks) == len(starts) == 6
    for check, start in zip(checks, starts):
        decision = check["metadata"]["runtime_decision"]
        assert decision["decision"] == "APPROVE"
        assert (decision["run_id"], decision["intent_id"], decision["intent_version"], decision["plan_id"], decision["action_id"]) == (
            run["run_id"], run["intent_id"], run["intent_version"], run["plan_id"], start["metadata"]["action_id"])


def _normalize(value):
    if isinstance(value, dict):
        return {key: _normalize(item) for key, item in value.items()
                if key not in {"timestamp", "completed_at", "latency_ms"}}
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    if isinstance(value, str):
        return re.sub(r"RUN-[0-9a-f-]+", "RUN-X", value)
    return value


def _direct(task):
    base, environment = _environment(task)
    intent = compile_request(task["request"])
    runs = []
    with scoped_runtime_configuration(ungated=False, proposal_mutation=task["proposal_mutation"]):
        run = invoice_runtime.execute_invoice(intent, environment)
        runs.append(run)
        if task["human"] and run.state in {RunState.CLARIFICATION_REQUIRED, RunState.ESCALATION_REQUIRED}:
            resumed = invoice_runtime.resume_invoice(run, _intervention(run, task["human"]))
            if resumed is not run:
                runs.append(resumed)
    return [run.model_dump(mode="json") for run in runs]


@pytest.mark.parametrize("index", [0, 22, 37, 16])
def test_gated_arm_has_direct_c6_runtime_parity(tasks, index):
    task = tasks[index]
    gated = run_episode(task, "GATED", pair_order=1)
    assert _normalize(gated["runs"]) == _normalize(_direct(task))


def test_raw_metrics_are_independently_recomputable(artifacts):
    _, saved, episodes, summary_path, *_ = artifacts
    from_disk = json.loads(summary_path.read_text(encoding="utf-8"))
    recomputed = recompute_summary(episodes)
    assert canonical_json(recomputed) == canonical_json({
        key: from_disk[key]
        for key in ("metrics", "operational", "latency_overhead", "limitations")
    })
    assert saved["episode_count"] == 100
    assert all(saved["operational"][arm]["external_actions_total"] == 0 for arm in ARMS)
    assert all(saved["operational"][arm]["token_count_total"] == 0 for arm in ARMS)
    assert all(saved["operational"][arm]["cost_usd_total"] == "0" for arm in ARMS)


def test_no_external_effects_and_no_hidden_episode_exclusions(artifacts):
    _, _, episodes, *_ = artifacts
    assert all(row["metrics"]["external_actions_performed"] == 0 for row in episodes)
    assert all(payment["external_actions_performed"] == 0
               for row in episodes for run in row["runs"]
               for payment in ([run["evidence"]["stage_payment"]]
                               if "stage_payment" in run["evidence"] else []))
    assert Counter(row["arm"] for row in episodes) == Counter({"GATED": 50, "UNGATED": 50})
    assert not any("excluded" in row for row in episodes)


def test_exact_outputs_comparison_and_report(artifacts):
    _, summary, episodes, summary_path, comparison_path, chart_path, results_path = artifacts
    assert all(path.is_file() and path.stat().st_size > 0 for path in (
        summary_path, comparison_path, chart_path, results_path))
    with comparison_path.open(encoding="utf-8", newline="") as stream:
        csv_rows = list(csv.DictReader(stream))
    assert len(csv_rows) == len(comparison_rows(summary)) == 14
    assert {row["metric"] for row in csv_rows} >= {
        "task_success", "unsafe_action", "runtime_contract_violation", "latency_mean_ms"}
    report = results_path.read_text(encoding="utf-8")
    assert "Complete failure analysis" in report
    assert "deterministic no-model" in report
    assert "no causal claim" in report
    failures = sum(not row["metrics"]["task_success"] for row in episodes)
    assert report.count("- `C7-") == failures


def test_static_chart_uses_saved_comparison_and_colorblind_safe_palette(artifacts, tmp_path):
    root, _, _, _, comparison_path, chart_path, _ = artifacts
    duplicate_a = tmp_path / "same-data-a.png"
    duplicate_b = tmp_path / "same-data-b.png"
    generate_chart(comparison_path, duplicate_a)
    generate_chart(comparison_path, duplicate_b)
    # Cross-platform committed-artifact bytes are not a valid determinism
    # oracle; compare two fresh renders in this same environment instead.
    assert duplicate_a.read_bytes() == duplicate_b.read_bytes()
    data = chart_path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    width, height = struct.unpack(">II", data[16:24])
    assert (width, height) == (2800, 1700)
    from matplotlib import image as mpimg
    pixels = mpimg.imread(chart_path)
    assert ((pixels[:, :, :3] - (0 / 255, 114 / 255, 178 / 255)) ** 2).sum(axis=2).min() < 1e-6
    assert ((pixels[:, :, :3] - (230 / 255, 159 / 255, 0 / 255)) ** 2).sum(axis=2).min() < 1e-6
    svg_path = root / "reports" / "c7" / "safety_control_vs_overhead.svg"
    pdf_path = root / "reports" / "c7" / "safety_control_vs_overhead.pdf"
    assert svg_path.is_file() and svg_path.stat().st_size > 0
    assert pdf_path.is_file() and pdf_path.stat().st_size > 0
    svg = svg_path.read_text(encoding="utf-8")
    assert "Governed controls preserve success and eliminate unsafe actions" in svg
    assert "GATED" in svg and "UNGATED" in svg
    assert "-53.938 ms" in svg
    assert all(line == line.rstrip(" \t") for line in svg.splitlines())


def test_undefined_ratios_remain_null_with_zero_denominator():
    rows = []
    for index in range(1, 51):
        for arm in ARMS:
            rows.append({
                "task_id": f"X-{index}", "task_index": index, "arm": arm,
                "pair_order": 1 if (arm == "GATED") == bool(index % 2) else 2,
                "digests": {"same": str(index)}, "elapsed_ms": 1.0,
                "metrics": {
                    "task_success": False, "unsafe_action": False,
                    "runtime_contract_violation": False,
                    "clarification_true": 0, "clarification_emitted": 0,
                    "clarification_required": False, "clarification_utility": False,
                    "escalation_true": 0, "escalation_emitted": 0,
                    "escalation_required": False, "escalation_utility": False,
                    "recovery_required": False, "recovery_success": False,
                    "autonomous_valid": False, "unnecessary_block": False,
                    "tool_call_attempts": 0, "completed_tool_calls": 0,
                    "completed_logical_tools": 0, "token_count": 0,
                    "cost_usd": "0", "external_actions_performed": 0,
                },
            })
    summary = recompute_summary(rows)
    for metric in ("clarification_precision", "clarification_utility", "escalation_precision",
                   "escalation_utility", "recovery_success", "unnecessary_block"):
        for arm in ARMS:
            assert summary["metrics"][metric][arm]["denominator"] == 0
            assert summary["metrics"][metric][arm]["rate"] is None
