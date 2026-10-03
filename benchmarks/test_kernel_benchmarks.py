"""Opt-in benchmark gates; invoke this file explicitly."""

import pytest

from benchmarks.run_benchmarks import render_markdown_report, run_all


@pytest.mark.benchmark
def test_real_kernel_latency_and_physical_accuracy() -> None:
    result = run_all()

    assert result["passed"] is True
    assert result["recurrent"]["passed"] is True
    assert result["wasm"]["passed"] is True
    assert result["wasm"]["physical_accuracy"]["passed"] is True
    assert result["wasm"]["methodology"]["operation_count_per_batch"] == 10_000
    state = result["recurrent"]["methodology"]["state"]
    assert state["lanes"] == 64
    assert state["lanes_updated_per_sample"] == 64
    assert state["update_operations_per_sample"] == 64
    assert state["lane_index_sequence"] == "0..63 exactly once"

    rendered = render_markdown_report(
        result,
        generated_at="2026-01-01T00:00:00+00:00",
        command="python benchmarks/run_benchmarks.py",
    )
    assert "Generated at `2026-01-01T00:00:00+00:00`" in rendered
    assert "64 updates/sample" in rendered
    assert "Exactly 10,000 operations/batch" in rendered
    for value in result["wasm"]["physical_accuracy"]["maximum_errors"].values():
        assert f"{value:.12g}" in rendered
