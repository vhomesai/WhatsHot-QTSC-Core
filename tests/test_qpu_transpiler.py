import json
import math
import subprocess
from dataclasses import replace

import pytest

import src.qpu_transpiler as qpu_transpiler
from scripts.generate_transpilation_deployment_report import render_report
from src.db_manager import DatabaseManager
from src.edge_engine import TriqeeEdgeEngine
from src.qpu_transpiler import (
    BACKENDS,
    BackendSpec,
    CircuitIR,
    GateIR,
    PortfolioInstance,
    _shortest_path,
    _transpile_connected,
    analyze_ionq_capacity_partition,
    build_qaoa_portfolio_circuit,
    build_qldpc_syndrome_circuit,
    circuit_depth,
    exact_decimal_count,
    plan_multivendor_workload,
    representative_portfolio_instance,
    transpile_circuit,
    validate_circuit,
    validate_portfolio_instance,
)
from src.si_agent_core import SovereignSIAgent


WORKLOADS = ("qaoa_portfolio_risk", "qldpc_syndrome_extraction")


def _apply_single_qubit(state, qubit_count, qubit, matrix):
    result = [0j] * len(state)
    mask = 1 << qubit
    for index, amplitude in enumerate(state):
        source_bit = 1 if index & mask else 0
        base = index & ~mask
        for target_bit in (0, 1):
            result[base | (target_bit << qubit)] += (
                matrix[target_bit][source_bit] * amplitude
            )
    return result


def _apply_cx(state, control, target):
    result = [0j] * len(state)
    for index, amplitude in enumerate(state):
        destination = index ^ (1 << target) if index & (1 << control) else index
        result[destination] += amplitude
    return result


def _product_state(single_qubit_states):
    state = [1 + 0j]
    for zero, one in single_qubit_states:
        expanded = [0j] * (len(state) * 2)
        for index, amplitude in enumerate(state):
            expanded[index] = amplitude * zero
            expanded[index + len(state)] = amplitude * one
        state = expanded
    return state


def _simulate_operations(state, operations, qubit_count):
    inv_sqrt_two = 1 / math.sqrt(2)
    for operation in operations:
        if operation.gate == "H":
            state = _apply_single_qubit(
                state,
                qubit_count,
                operation.qubits[0],
                (
                    (inv_sqrt_two, inv_sqrt_two),
                    (inv_sqrt_two, -inv_sqrt_two),
                ),
            )
        elif operation.gate == "CX":
            state = _apply_cx(state, *operation.qubits)
        elif operation.gate != "MEASURE":
            raise AssertionError(f"Unexpected syndrome gate: {operation.gate}")
    return state


def _ancilla_one_probability(state, ancilla):
    return sum(
        abs(amplitude) ** 2
        for index, amplitude in enumerate(state)
        if index & (1 << ancilla)
    )


def _assert_dependency_safe(operations):
    by_id = {operation["operation_id"]: operation for operation in operations}
    occupied_by_layer = {}
    for operation in operations:
        for dependency in operation["dependencies"]:
            assert dependency in by_id
            assert by_id[dependency]["layer"] < operation["layer"]
        occupied = occupied_by_layer.setdefault(operation["layer"], set())
        assert occupied.isdisjoint(operation["physical_qubits"])
        occupied.update(operation["physical_qubits"])


def _assert_topology_safe(plan):
    native_edges = {
        tuple(sorted(edge)) for edge in plan["backend"]["coupling_edges"]
    }
    for operation in plan["routed_operations"]:
        assert all(
            0 <= physical < plan["backend"]["capacity"]
            for physical in operation["physical_qubits"]
        )
        if len(operation["physical_qubits"]) == 2:
            assert tuple(sorted(operation["physical_qubits"])) in native_edges
    _assert_dependency_safe(plan["routed_operations"])


@pytest.mark.parametrize("workload_type", WORKLOADS)
def test_all_vendor_plans_are_deterministic_serializable_and_capacity_safe(workload_type):
    options = {"qaoa_p": 1} if workload_type == "qaoa_portfolio_risk" else {}
    first = plan_multivendor_workload(workload_type, **options)
    second = plan_multivendor_workload(workload_type, **options)

    assert first == second
    assert first["logical_qubits"] == 48
    assert first["hardware_execution"] is False
    assert json.loads(json.dumps(first))["workload_type"] == workload_type
    assert tuple(first["plans"]) == ("ibm_heron", "rigetti_ankaa")
    assert tuple(first["unsupported_backends"]) == ("ionq_forte",)

    original_ids = {
        operation["operation_id"] for operation in first["circuit_ir"]["operations"]
    }
    for backend_key, plan in first["plans"].items():
        assert plan["backend"]["key"] == backend_key
        assert plan["logical_qubits"] == 48
        assert plan["status"] == "READY_FOR_ASYNC_VENDOR_SUBMISSION"
        expected_capacity = 156 if backend_key == "ibm_heron" else 84
        expected_topology = (
            "Heavy-Hex"
            if backend_key == "ibm_heron"
            else "Square lattice tunable couplers"
        )
        assert plan["backend"]["capacity"] == expected_capacity
        assert plan["backend"]["topology"] == expected_topology
        assert plan["optimized_depth"] <= plan["baseline_depth"]
        assert plan["depth_non_regression"] is True
        assert plan["optimized_swap_count"] >= 0
        _assert_topology_safe(plan)
        routed_source_ids = {
            operation["source_operation_id"]
            for operation in plan["routed_operations"]
        }
        assert routed_source_ids == original_ids
        source_operations = {
            operation["operation_id"]: operation
            for operation in first["circuit_ir"]["operations"]
        }
        routed_operations = {
            operation["operation_id"]: operation
            for operation in plan["routed_operations"]
        }
        for operation_id, source in source_operations.items():
            assert routed_operations[operation_id]["parameters"] == source["parameters"]
            assert routed_operations[operation_id]["metadata"] == source["metadata"]
        swap_decomposition = [
            operation
            for operation in plan["routed_operations"]
            if operation["metadata"].get("abstract_semantic") == "SWAP"
        ]
        assert len(swap_decomposition) == plan["optimized_swap_count"] * 3
        assert all(operation["gate"] == "CX" for operation in swap_decomposition)

    diagnostic = first["unsupported_backends"]["ionq_forte"]
    assert diagnostic["status"] == "UNSUPPORTED_EXACT_CIRCUIT_CUTTING"
    assert diagnostic["backend"]["capacity"] == 36
    assert diagnostic["fragment_widths"] == [36, 12]
    assert diagnostic["swap_count"] == 0
    assert diagnostic["cut_count"] > 0
    assert diagnostic["submission_ready"] is False
    assert diagnostic["intact_48_qubit_execution_claimed"] is False
    exact_count = diagnostic["rejected_amplitude_expansion_term_count"]
    assert set(exact_count) == {"decimal", "encoding", "semantics"}
    assert int(exact_count["decimal"]) == 2 ** diagnostic["cut_count"]
    assert "not an experiment" in exact_count["semantics"]


def test_workload_ir_roles_dependencies_and_stabilizers():
    qaoa = build_qaoa_portfolio_circuit(3)
    assert qaoa.logical_qubits == 48
    assert qaoa.metadata["p_depth"] == 3
    assert qaoa.metadata["interaction_count_per_cost_layer"] == 1128
    assert set(qaoa.qubit_roles) == {"portfolio_asset"}
    assert any(operation.dependencies for operation in qaoa.operations)
    assert sum(operation.gate == "MEASURE" for operation in qaoa.operations) == 48
    assert {
        operation.metadata["classical_bit"]
        for operation in qaoa.operations
        if operation.gate == "MEASURE"
    } == set(range(48))
    assert all(
        "angle_radians" in operation.parameters
        for operation in qaoa.operations
        if operation.gate in {"RX", "RZ", "RZZ"}
    )
    assert qaoa.metadata["readout"]["bit_value"].startswith("1 selects")
    assert circuit_depth(qaoa) > 0

    qldpc = build_qldpc_syndrome_circuit()
    assert qldpc.qubit_roles.count("data") == 36
    assert qldpc.qubit_roles.count("ancilla") == 12
    assert len(qldpc.metadata["stabilizers"]) == 12
    assert {item["check_type"] for item in qldpc.metadata["stabilizers"]} == {"X", "Z"}
    assert all(len(item["data_support"]) == 4 for item in qldpc.metadata["stabilizers"])
    assert {operation.gate for operation in qldpc.operations} == {"H", "CX", "MEASURE"}
    assert "toy qLDPC-like" in qldpc.metadata["code_classification"]

    for stabilizer in qldpc.metadata["stabilizers"]:
        stabilizer_id = stabilizer["stabilizer_id"]
        operations = [
            operation
            for operation in qldpc.operations
            if stabilizer_id in operation.purpose
        ]
        ancilla = stabilizer["ancilla"]
        cx_operations = [operation for operation in operations if operation.gate == "CX"]
        if stabilizer["check_type"] == "Z":
            assert [operation.gate for operation in operations] == [
                "CX",
                "CX",
                "CX",
                "CX",
                "MEASURE",
            ]
            assert all(operation.qubits[1] == ancilla for operation in cx_operations)
        else:
            assert [operation.gate for operation in operations] == [
                "H",
                "CX",
                "CX",
                "CX",
                "CX",
                "H",
                "MEASURE",
            ]
            assert all(operation.qubits[0] == ancilla for operation in cx_operations)
        assert operations[-1].metadata["basis"] == "Z"


@pytest.mark.parametrize(
    ("stabilizer_id", "data_states", "expected_syndrome"),
    [
        ("S01", [(1, 0), (1, 0), (1, 0), (1, 0)], 0.0),
        ("S01", [(0, 1), (1, 0), (1, 0), (1, 0)], 1.0),
        (
            "S00",
            [(1 / math.sqrt(2), 1 / math.sqrt(2))] * 4,
            0.0,
        ),
        (
            "S00",
            [
                (1 / math.sqrt(2), -1 / math.sqrt(2)),
                *([(1 / math.sqrt(2), 1 / math.sqrt(2))] * 3),
            ],
            1.0,
        ),
    ],
)
def test_qldpc_check_statevector_syndrome_semantics(
    stabilizer_id,
    data_states,
    expected_syndrome,
):
    circuit = build_qldpc_syndrome_circuit()
    stabilizer = next(
        item
        for item in circuit.metadata["stabilizers"]
        if item["stabilizer_id"] == stabilizer_id
    )
    mapping = {
        logical: local
        for local, logical in enumerate(
            [*stabilizer["data_support"], stabilizer["ancilla"]]
        )
    }
    local_operations = [
        replace(
            operation,
            qubits=tuple(mapping[qubit] for qubit in operation.qubits),
        )
        for operation in circuit.operations
        if stabilizer_id in operation.purpose
    ]
    initial = _product_state([*data_states, (1, 0)])
    final = _simulate_operations(initial, local_operations, 5)
    probability_one = _ancilla_one_probability(final, 4)

    assert probability_one == pytest.approx(expected_syndrome, abs=1e-12)


def test_ionq_diagnostic_fails_closed_and_preserves_exact_counts_in_node():
    circuit = build_qaoa_portfolio_circuit(1)
    diagnostic = analyze_ionq_capacity_partition(
        circuit,
        BACKENDS["ionq_forte"],
    )

    assert diagnostic["status"] == "UNSUPPORTED_EXACT_CIRCUIT_CUTTING"
    assert diagnostic["fragment_widths"] == [36, 12]
    assert diagnostic["swap_count"] == 0
    assert diagnostic["submission_ready"] is False
    assert "fragments" not in diagnostic
    assert "experiment_multiplier" not in diagnostic
    fragment_by_qubit = {
        qubit: fragment_index
        for fragment_index, group in enumerate(
            diagnostic["fragment_logical_qubits"]
        )
        for qubit in group
    }
    crossing_ids = {
        operation.operation_id
        for operation in circuit.operations
        if len(operation.qubits) == 2
        and fragment_by_qubit[operation.qubits[0]]
        != fragment_by_qubit[operation.qubits[1]]
    }
    assert {item["operation_id"] for item in diagnostic["cut_interactions"]} == (
        crossing_ids
    )
    with pytest.raises(ValueError, match="UNSUPPORTED_EXACT_CIRCUIT_CUTTING"):
        transpile_circuit(circuit, "ionq_forte")

    exact = exact_decimal_count(
        2 ** 80 + 123,
        "Regression value above Number.MAX_SAFE_INTEGER.",
    )
    payload = json.dumps(exact)
    completed = subprocess.run(
        [
            "node",
            "-e",
            (
                "let s='';process.stdin.on('data',d=>s+=d);"
                "process.stdin.on('end',()=>{const v=JSON.parse(s);"
                "if(v.decimal!=='1208925819614629174706299')process.exit(2);"
                "if(typeof v.decimal!=='string')process.exit(3);"
                "process.stdout.write(JSON.stringify(v));});"
            ),
        ],
        input=payload,
        text=True,
        capture_output=True,
        check=True,
    )
    assert json.loads(completed.stdout) == exact


@pytest.mark.parametrize("invalid_depth", [0, 9, 1.5, True])
def test_invalid_qaoa_depth_fails(invalid_depth):
    with pytest.raises(ValueError, match="QAOA p depth"):
        build_qaoa_portfolio_circuit(invalid_depth)


def test_portfolio_instance_validation_and_coefficient_influence():
    representative = representative_portfolio_instance()
    validate_portfolio_instance(representative)
    first = build_qaoa_portfolio_circuit(1, representative)
    changed_returns = list(representative.expected_returns)
    changed_returns[0] += 0.1
    changed = replace(representative, expected_returns=tuple(changed_returns))
    second = build_qaoa_portfolio_circuit(1, changed)

    first_rz = next(
        operation
        for operation in first.operations
        if operation.gate == "RZ" and operation.qubits == (0,)
    )
    second_rz = next(
        operation
        for operation in second.operations
        if operation.gate == "RZ" and operation.qubits == (0,)
    )
    assert first_rz.parameters["angle_radians"] != second_rz.parameters["angle_radians"]
    assert first.metadata["portfolio_instance"]["target_cardinality"] == 12
    assert len(first.metadata["ising_quadratic_terms"]) == 1128

    invalid_instances = [
        PortfolioInstance((0.1,), ((0.1,),), 0.5, 1.0, 1),
        replace(representative, covariance=representative.covariance[:-1]),
        replace(
            representative,
            covariance=(
                representative.covariance[0][:-1],
                *representative.covariance[1:],
            ),
        ),
        replace(
            representative,
            expected_returns=(math.nan, *representative.expected_returns[1:]),
        ),
        replace(representative, risk_aversion=-0.1),
        replace(representative, budget_penalty=0.0),
        replace(representative, target_cardinality=48),
        replace(
            representative,
            covariance=(
                (
                    -0.1,
                    *representative.covariance[0][1:],
                ),
                *representative.covariance[1:],
            ),
        ),
    ]
    asymmetric_rows = [list(row) for row in representative.covariance]
    asymmetric_rows[0][1] += 0.01
    invalid_instances.append(
        replace(
            representative,
            covariance=tuple(tuple(row) for row in asymmetric_rows),
        )
    )
    for invalid in invalid_instances:
        with pytest.raises(ValueError):
            validate_portfolio_instance(invalid)


@pytest.mark.parametrize(
    ("data_qubits", "ancilla_qubits", "message"),
    [
        (0, 48, "positive data/ancilla"),
        (36, 0, "positive data/ancilla"),
        (35, 12, "positive data/ancilla"),
        (1.5, 46.5, "positive data/ancilla"),
        (True, 47, "positive data/ancilla"),
        (4, 44, "four distinct"),
    ],
)
def test_invalid_qldpc_layout_fails(data_qubits, ancilla_qubits, message):
    with pytest.raises(ValueError, match=message):
        build_qldpc_syndrome_circuit(data_qubits, ancilla_qubits)


def test_circuit_validation_rejects_malformed_ir():
    valid_roles = ("data", "data")
    with pytest.raises(ValueError, match="roles"):
        validate_circuit(CircuitIR("bad", "qaoa_portfolio_risk", 2, (), ("data",), {}))

    cases = [
        (
            (
                GateIR("duplicate", "H", (0,)),
                GateIR("duplicate", "H", (1,)),
            ),
            "Duplicate",
        ),
        ((GateIR("bad_gate", "X", (0,)),), "Unsupported"),
        ((GateIR("bad_arity", "CX", (0,)),), "arity"),
        ((GateIR("bad_duplicate_qubit", "CX", (0, 0)),), "arity"),
        ((GateIR("bad_index", "H", (2,)),), "outside"),
        ((GateIR("bad_dependency", "H", (0,), ("missing",)),), "dependency"),
        ((GateIR("bad_parameter", "RX", (0,), (), {"angle_radians": math.nan}),), "parameter"),
        ((GateIR("missing_angle", "RZ", (0,)),), "angle"),
        ((GateIR("bad_measurement", "MEASURE", (0,)),), "Measurement"),
    ]
    for operations, message in cases:
        with pytest.raises(ValueError, match=message):
            validate_circuit(
                CircuitIR(
                    "bad",
                    "qaoa_portfolio_risk",
                    2,
                    operations,
                    valid_roles,
                    {},
                )
            )

    empty = CircuitIR("empty", "qaoa_portfolio_risk", 1, (), ("data",), {})
    assert circuit_depth(empty) == 0


def test_ionq_diagnostic_and_decimal_count_validate_inputs():
    circuit = build_qaoa_portfolio_circuit(1)
    with pytest.raises(ValueError, match="36-AQ Forte"):
        analyze_ionq_capacity_partition(circuit, BACKENDS["ibm_heron"])
    for invalid in (-1, 1.5, True):
        with pytest.raises(ValueError, match="non-negative integer"):
            exact_decimal_count(invalid, "invalid")


def test_invalid_backend_width_and_disconnected_topology_fail_explicitly():
    circuit = build_qaoa_portfolio_circuit()
    with pytest.raises(ValueError, match="Unsupported QPU backend"):
        transpile_circuit(circuit, "unknown")

    narrow = CircuitIR(
        "narrow",
        "qaoa_portfolio_risk",
        2,
        (GateIR("op", "CX", (0, 1)),),
        ("data", "data"),
        {},
    )
    with pytest.raises(ValueError, match="exactly 48"):
        transpile_circuit(narrow, "ibm_heron")

    insufficient = BackendSpec("tiny", "Test", "Tiny", 47, "Path", tuple())
    with pytest.raises(ValueError, match="capacity"):
        _transpile_connected(circuit, insufficient)

    with pytest.raises(ValueError, match="No topology path"):
        _shortest_path({0: set(), 1: set()}, 0, 1)


def test_incomplete_routing_and_ionq_transpilation_fail_closed(monkeypatch):
    circuit = build_qaoa_portfolio_circuit(1)
    incomplete_route = {
        "initial_placement": {},
        "final_placement": {},
        "operations": [],
        "swap_count": 0,
        "native_two_qubit_gate_count": 0,
        "depth": 0,
    }
    monkeypatch.setattr(
        qpu_transpiler,
        "_route_with_placement",
        lambda *_args: incomplete_route,
    )
    with pytest.raises(AssertionError, match="Executable semantics"):
        _transpile_connected(circuit, BACKENDS["ibm_heron"])

    monkeypatch.undo()
    with pytest.raises(ValueError, match="UNSUPPORTED_EXACT_CIRCUIT_CUTTING"):
        transpile_circuit(circuit, "ionq_forte")


def test_backend_specs_are_serialized_with_declared_capacities():
    assert BACKENDS["ibm_heron"].to_dict()["capacity"] == 156
    assert BACKENDS["ionq_forte"].to_dict()["coupling_edges"] == []
    assert len(BACKENDS["rigetti_ankaa"].coupling_edges) > 0


def test_unsupported_workload_fails():
    with pytest.raises(ValueError, match="Unsupported 48-qubit workload"):
        plan_multivendor_workload("not_a_workload")


def test_edge_engine_exposes_48_qubit_plans_and_validation():
    engine = TriqeeEdgeEngine()
    qaoa = engine.compile_qpu_transpilation_job(
        qubit_count=48,
        target_backend="ibm_heron",
        qaoa_p=1,
    )
    assert qaoa["qubit_count"] == 48
    assert qaoa["transpilation_plan"]["workload_type"] == "qaoa_portfolio_risk"
    assert qaoa["circuit_depth"] == qaoa["transpilation_plan"]["optimized_depth"]

    with pytest.raises(ValueError, match="UNSUPPORTED_EXACT_CIRCUIT_CUTTING"):
        engine.compile_qpu_transpilation_job(
            qubit_count=48,
            target_backend="ionq_forte",
            workload_type="qldpc_syndrome_extraction",
        )

    bundle = engine.plan_48_qubit_workload(
        "qldpc_syndrome_extraction",
        data_qubits=36,
        ancilla_qubits=12,
    )
    assert bundle["workload_type"] == "qldpc_syndrome_extraction"

    with pytest.raises(ValueError, match="Unsupported QPU backend"):
        engine.compile_qpu_transpilation_job(
            qubit_count=48,
            target_backend="unsupported",
        )
    with pytest.raises(ValueError, match="Unsupported 48-qubit workload"):
        engine.plan_48_qubit_workload("unsupported")


def test_si_routes_and_narrates_honest_multivendor_plans(tmp_path):
    agent = SovereignSIAgent(DatabaseManager(str(tmp_path / "qpu.db")))

    qaoa_request = agent.route_intent_and_tools(
        "Transpile QAOA portfolio p=3 on Rigetti QPU"
    )[-1]
    assert qaoa_request["params"] == {
        "qubits": 48,
        "depth": 12,
        "backend": "rigetti_ankaa",
        "workload_type": "qaoa_portfolio_risk",
        "qaoa_p": 3,
    }
    qldpc_request = agent.route_intent_and_tools(
        "Compile qLDPC syndrome extraction on IonQ QPU"
    )[-1]
    assert qldpc_request["params"]["backend"] == "ionq_forte"
    assert qldpc_request["params"]["workload_type"] == "qldpc_syndrome_extraction"
    legacy_hamiltonian = agent.route_intent_and_tools(
        "Compile the global triangle Hamiltonian"
    )[-1]
    assert legacy_hamiltonian["params"] == {"qubits": 24, "depth": 14}

    connected = agent.generate_response("Transpile QAOA portfolio p=1 on Rigetti QPU")
    assert connected["qpu_artifact"]["transpilation_plan"]["optimized_swap_count"] > 0
    assert "depth" in connected["response_text"]
    assert "Deterministic plan only; no hardware execution." in connected["response_text"]

    with pytest.raises(ValueError, match="UNSUPPORTED_EXACT_CIRCUIT_CUTTING"):
        agent.generate_response("Compile qLDPC syndrome extraction on IonQ QPU")

    benchmark = agent.generate_response("Generate executive morning briefing")
    assert "Multi-Vendor QPU Transpiler Benchmark" in benchmark["response_text"]
    assert "not real QPU executions" in benchmark["response_text"]
    benchmark_result = next(
        item["result"]
        for item in benchmark["tools_executed"]
        if item["tool_name"] == "benchmark_multivendor_qpu"
    )
    assert benchmark_result["logical_workload_qubits"] == 48
    assert all(
        comparison["hardware_execution"] is False
        for comparison in benchmark_result["backends_compared"]
    )
    ionq = next(
        comparison
        for comparison in benchmark_result["backends_compared"]
        if comparison["backend_key"] == "ionq_forte"
    )
    assert ionq["status"] == "UNSUPPORTED_EXACT_CIRCUIT_CUTTING"
    assert ionq["submission_ready"] is False


def test_tracked_report_renderer_uses_live_plan_metrics():
    report = render_report(
        generated_at="2026-01-01T00:00:00+00:00",
        command="python scripts/generate_transpilation_deployment_report.py",
    )

    assert "Generated at `2026-01-01T00:00:00+00:00`" in report
    assert "No vendor QPU was contacted" in report
    assert (
        "Authoritative Docker Compose/Caddy executable validation status: "
        "PENDING CI"
    ) in report
    assert "It was not run on this report host." in report
    for workload_type in WORKLOADS:
        options = {"qaoa_p": 1} if workload_type == "qaoa_portfolio_risk" else {}
        bundle = plan_multivendor_workload(workload_type, **options)
        for plan in bundle["plans"].values():
            assert f"| {plan['original_depth']} | {plan['baseline_depth']} |" in report
            assert str(plan["optimized_swap_count"]) in report
        diagnostic = bundle["unsupported_backends"]["ionq_forte"]
        assert diagnostic["status"] in report
        assert diagnostic["rejected_amplitude_expansion_term_count"]["decimal"] in report
