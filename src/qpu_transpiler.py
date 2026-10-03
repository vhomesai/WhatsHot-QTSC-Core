"""Deterministic vendor-neutral circuit planning and topology-aware transpilation."""

from __future__ import annotations

import json
from collections import deque
from dataclasses import asdict, dataclass, field
from hashlib import sha256
from math import isfinite
from typing import Any, Iterable, Literal

WorkloadType = Literal["qaoa_portfolio_risk", "qldpc_syndrome_extraction"]

SUPPORTED_GATES = {"H", "RX", "RZ", "RZZ", "CX", "MEASURE"}


@dataclass(frozen=True)
class GateIR:
    operation_id: str
    gate: str
    qubits: tuple[int, ...]
    dependencies: tuple[str, ...] = ()
    parameters: dict[str, float] = field(default_factory=dict)
    purpose: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CircuitIR:
    name: str
    workload_type: WorkloadType
    logical_qubits: int
    operations: tuple[GateIR, ...]
    qubit_roles: tuple[str, ...]
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "workload_type": self.workload_type,
            "logical_qubits": self.logical_qubits,
            "operations": [operation.to_dict() for operation in self.operations],
            "qubit_roles": list(self.qubit_roles),
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class PortfolioInstance:
    expected_returns: tuple[float, ...]
    covariance: tuple[tuple[float, ...], ...]
    risk_aversion: float
    budget_penalty: float
    target_cardinality: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "expected_returns": list(self.expected_returns),
            "covariance": [list(row) for row in self.covariance],
            "risk_aversion": self.risk_aversion,
            "budget_penalty": self.budget_penalty,
            "target_cardinality": self.target_cardinality,
        }


@dataclass(frozen=True)
class BackendSpec:
    key: str
    vendor: str
    model: str
    capacity: int
    topology: str
    coupling_edges: tuple[tuple[int, int], ...]

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["coupling_edges"] = [list(edge) for edge in self.coupling_edges]
        return result


@dataclass(frozen=True)
class RoutedOperation:
    operation_id: str
    gate: str
    logical_qubits: tuple[int, ...]
    physical_qubits: tuple[int, ...]
    layer: int
    dependencies: tuple[str, ...]
    source_operation_id: str
    parameters: dict[str, float]
    purpose: str
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _grid_edges(rows: int, columns: int) -> tuple[tuple[int, int], ...]:
    edges: list[tuple[int, int]] = []
    for row in range(rows):
        for column in range(columns):
            node = row * columns + column
            if column + 1 < columns:
                edges.append((node, node + 1))
            if row + 1 < rows:
                edges.append((node, node + columns))
    return tuple(edges)


def _heavy_hex_edges() -> tuple[tuple[int, int], ...]:
    rows, columns = 12, 13
    edges: list[tuple[int, int]] = []
    for row in range(rows):
        for column in range(columns - 1):
            edges.append((row * columns + column, row * columns + column + 1))
    for row in range(rows - 1):
        offset = (2 * row) % 4
        for column in range(offset, columns, 4):
            edges.append((row * columns + column, (row + 1) * columns + column))
    return tuple(edges)


BACKENDS: dict[str, BackendSpec] = {
    "ibm_heron": BackendSpec(
        key="ibm_heron",
        vendor="IBM",
        model="Heron",
        capacity=156,
        topology="Heavy-Hex",
        coupling_edges=_heavy_hex_edges(),
    ),
    "ionq_forte": BackendSpec(
        key="ionq_forte",
        vendor="IonQ",
        model="Forte",
        capacity=36,
        topology="All-to-All",
        coupling_edges=(),
    ),
    "rigetti_ankaa": BackendSpec(
        key="rigetti_ankaa",
        vendor="Rigetti",
        model="Ankaa",
        capacity=84,
        topology="Square lattice tunable couplers",
        coupling_edges=_grid_edges(7, 12),
    ),
}


def _append_gate(
    operations: list[GateIR],
    last_by_qubit: dict[int, str],
    gate: str,
    qubits: tuple[int, ...],
    *,
    parameters: dict[str, float] | None = None,
    purpose: str = "",
    metadata: dict[str, Any] | None = None,
) -> None:
    dependencies = tuple(
        dict.fromkeys(last_by_qubit[qubit] for qubit in qubits if qubit in last_by_qubit)
    )
    operation_id = f"op_{len(operations):04d}"
    operations.append(
        GateIR(
            operation_id,
            gate,
            qubits,
            dependencies,
            parameters or {},
            purpose,
            metadata or {},
        )
    )
    for qubit in qubits:
        last_by_qubit[qubit] = operation_id


def representative_portfolio_instance() -> PortfolioInstance:
    expected_returns = tuple(round(0.035 + (index % 12) * 0.0025, 6) for index in range(48))
    covariance = tuple(
        tuple(
            round(
                0.018 + (row % 5) * 0.001
                if row == column
                else 0.0025 / (1 + abs(row - column))
                if abs(row - column) <= 3
                else 0.0,
                8,
            )
            for column in range(48)
        )
        for row in range(48)
    )
    return PortfolioInstance(
        expected_returns=expected_returns,
        covariance=covariance,
        risk_aversion=0.65,
        budget_penalty=0.08,
        target_cardinality=12,
    )


def validate_portfolio_instance(instance: PortfolioInstance) -> None:
    size = len(instance.expected_returns)
    if size != 48 or len(instance.covariance) != size:
        raise ValueError("Portfolio instance must contain exactly 48 assets.")
    if any(len(row) != size for row in instance.covariance):
        raise ValueError("Portfolio covariance matrix must be 48 by 48.")
    values = [
        *instance.expected_returns,
        *(value for row in instance.covariance for value in row),
        instance.risk_aversion,
        instance.budget_penalty,
    ]
    if any(not isfinite(value) for value in values):
        raise ValueError("Portfolio coefficients must be finite.")
    if instance.risk_aversion < 0.0 or instance.budget_penalty <= 0.0:
        raise ValueError("Risk aversion must be non-negative and budget penalty positive.")
    if not 1 <= instance.target_cardinality < size:
        raise ValueError("Portfolio target cardinality must be between 1 and 47.")
    for row in range(size):
        if instance.covariance[row][row] < 0.0:
            raise ValueError("Portfolio covariance diagonal must be non-negative.")
        for column in range(row + 1, size):
            if instance.covariance[row][column] != instance.covariance[column][row]:
                raise ValueError("Portfolio covariance matrix must be symmetric.")


def _portfolio_ising_coefficients(
    instance: PortfolioInstance,
) -> tuple[tuple[float, ...], tuple[tuple[int, int, float], ...]]:
    size = len(instance.expected_returns)
    linear_qubo = [
        -instance.expected_returns[index]
        + instance.risk_aversion * instance.covariance[index][index]
        + instance.budget_penalty * (1 - 2 * instance.target_cardinality)
        for index in range(size)
    ]
    quadratic_qubo = {
        (left, right): (
            2.0 * instance.risk_aversion * instance.covariance[left][right]
            + 2.0 * instance.budget_penalty
        )
        for left in range(size)
        for right in range(left + 1, size)
    }
    z_linear = tuple(
        -linear_qubo[index] / 2.0
        - sum(
            coefficient / 4.0
            for pair, coefficient in quadratic_qubo.items()
            if index in pair
        )
        for index in range(size)
    )
    zz_terms = tuple(
        (left, right, coefficient / 4.0)
        for (left, right), coefficient in quadratic_qubo.items()
    )
    return z_linear, zz_terms


def build_qaoa_portfolio_circuit(
    p_depth: int = 2,
    portfolio: PortfolioInstance | None = None,
) -> CircuitIR:
    if not isinstance(p_depth, int) or isinstance(p_depth, bool) or not 1 <= p_depth <= 8:
        raise ValueError("QAOA p depth must be an integer between 1 and 8.")
    selected_portfolio = portfolio or representative_portfolio_instance()
    validate_portfolio_instance(selected_portfolio)
    z_linear, zz_terms = _portfolio_ising_coefficients(selected_portfolio)
    operations: list[GateIR] = []
    last_by_qubit: dict[int, str] = {}
    for qubit in range(48):
        _append_gate(operations, last_by_qubit, "H", (qubit,), purpose="initial superposition")
    for layer in range(p_depth):
        gamma = (layer + 1) / (p_depth + 1)
        beta = (p_depth - layer) / (p_depth + 1)
        for qubit, coefficient in enumerate(z_linear):
            _append_gate(
                operations,
                last_by_qubit,
                "RZ",
                (qubit,),
                parameters={
                    "angle_radians": 2.0 * gamma * coefficient,
                    "ising_coefficient": coefficient,
                    "gamma": gamma,
                },
                purpose="portfolio linear return/risk/cardinality cost",
            )
        for left, right, coefficient in zz_terms:
            _append_gate(
                operations,
                last_by_qubit,
                "RZZ",
                (left, right),
                parameters={
                    "angle_radians": 2.0 * gamma * coefficient,
                    "ising_coefficient": coefficient,
                    "gamma": gamma,
                },
                purpose="portfolio covariance and cardinality cost",
            )
        for qubit in range(48):
            _append_gate(
                operations,
                last_by_qubit,
                "RX",
                (qubit,),
                parameters={"angle_radians": 2.0 * beta, "beta": beta},
                purpose="QAOA mixer",
            )
    for qubit in range(48):
        _append_gate(
            operations,
            last_by_qubit,
            "MEASURE",
            (qubit,),
            purpose="portfolio bitstring readout",
            metadata={"classical_bit": qubit, "basis": "Z"},
        )
    return CircuitIR(
        name=f"qaoa_portfolio_risk_48q_p{p_depth}",
        workload_type="qaoa_portfolio_risk",
        logical_qubits=48,
        operations=tuple(operations),
        qubit_roles=tuple("portfolio_asset" for _ in range(48)),
        metadata={
            "p_depth": p_depth,
            "objective": (
                "minimize -expected_return + risk_aversion*x^T*covariance*x "
                "+ budget_penalty*(sum(x)-target_cardinality)^2"
            ),
            "portfolio_instance": selected_portfolio.to_dict(),
            "ising_linear_coefficients": list(z_linear),
            "ising_quadratic_terms": [list(term) for term in zz_terms],
            "readout": {
                "basis": "Z",
                "classical_bits": list(range(48)),
                "bit_value": "1 selects the corresponding asset",
                "objective_evaluation": "evaluate the typed portfolio objective from each bitstring",
            },
            "interaction_count_per_cost_layer": len(zz_terms),
        },
    )


def build_qldpc_syndrome_circuit(
    data_qubits: int = 36,
    ancilla_qubits: int = 12,
) -> CircuitIR:
    if (
        not isinstance(data_qubits, int)
        or not isinstance(ancilla_qubits, int)
        or isinstance(data_qubits, bool)
        or isinstance(ancilla_qubits, bool)
        or data_qubits <= 0
        or ancilla_qubits <= 0
        or data_qubits + ancilla_qubits != 48
        or data_qubits < 4
    ):
        raise ValueError("qLDPC layout requires positive data/ancilla counts totaling 48.")
    operations: list[GateIR] = []
    last_by_qubit: dict[int, str] = {}
    stabilizers: list[dict[str, Any]] = []
    for ancilla_offset in range(ancilla_qubits):
        ancilla = data_qubits + ancilla_offset
        support = tuple(
            dict.fromkeys(
                (
                    (ancilla_offset * 3) % data_qubits,
                    (ancilla_offset * 3 + 1) % data_qubits,
                    (ancilla_offset * 3 + 2) % data_qubits,
                    (ancilla_offset * 3 + data_qubits // 2) % data_qubits,
                )
            )
        )
        if len(support) != 4:
            raise ValueError("qLDPC stabilizers require four distinct data qubits.")
        stabilizers.append(
            {
                "stabilizer_id": f"S{ancilla_offset:02d}",
                "ancilla": ancilla,
                "data_support": list(support),
                "check_type": "X" if ancilla_offset % 2 == 0 else "Z",
                "measurement_basis": "Z",
            }
        )
        check_type = stabilizers[-1]["check_type"]
        if check_type == "X":
            _append_gate(
                operations,
                last_by_qubit,
                "H",
                (ancilla,),
                purpose=f"prepare |+> for X stabilizer S{ancilla_offset:02d}",
            )
        for data_qubit in support:
            control_target = (
                (ancilla, data_qubit)
                if check_type == "X"
                else (data_qubit, ancilla)
            )
            _append_gate(
                operations,
                last_by_qubit,
                "CX",
                control_target,
                purpose=f"extract {check_type} stabilizer S{ancilla_offset:02d}",
                metadata={
                    "control": control_target[0],
                    "target": control_target[1],
                    "check_type": check_type,
                },
            )
        if check_type == "X":
            _append_gate(
                operations,
                last_by_qubit,
                "H",
                (ancilla,),
                purpose=f"rotate X stabilizer S{ancilla_offset:02d} to Z readout",
            )
        _append_gate(
            operations,
            last_by_qubit,
            "MEASURE",
            (ancilla,),
            purpose=f"measure {check_type} stabilizer S{ancilla_offset:02d}",
            metadata={"basis": "Z", "syndrome_bit": ancilla_offset},
        )
    return CircuitIR(
        name="qldpc_syndrome_extraction_48q",
        workload_type="qldpc_syndrome_extraction",
        logical_qubits=48,
        operations=tuple(operations),
        qubit_roles=tuple(
            ["data"] * data_qubits + ["ancilla"] * ancilla_qubits
        ),
        metadata={
            "data_qubits": data_qubits,
            "ancilla_qubits": ancilla_qubits,
            "stabilizers": stabilizers,
            "code_classification": (
                "defined toy qLDPC-like parity-check benchmark; no named code, "
                "distance, threshold, or correction capability is claimed"
            ),
        },
    )


def validate_circuit(circuit: CircuitIR) -> None:
    if circuit.logical_qubits <= 0 or len(circuit.qubit_roles) != circuit.logical_qubits:
        raise ValueError("Circuit qubit roles must match its positive logical width.")
    seen: set[str] = set()
    for operation in circuit.operations:
        if operation.operation_id in seen:
            raise ValueError(f"Duplicate operation id: {operation.operation_id}")
        if operation.gate not in SUPPORTED_GATES - {"SWAP"}:
            raise ValueError(f"Unsupported circuit gate: {operation.gate}")
        expected_arity = 2 if operation.gate in {"RZZ", "CX"} else 1
        if len(operation.qubits) != expected_arity or len(set(operation.qubits)) != expected_arity:
            raise ValueError(f"Invalid qubit arity for {operation.operation_id}.")
        if any(qubit < 0 or qubit >= circuit.logical_qubits for qubit in operation.qubits):
            raise ValueError(f"Qubit index outside circuit width in {operation.operation_id}.")
        if any(dependency not in seen for dependency in operation.dependencies):
            raise ValueError(f"Invalid dependency in {operation.operation_id}.")
        if any(not isinstance(value, (int, float)) or not isfinite(value) for value in operation.parameters.values()):
            raise ValueError(f"Invalid gate parameter in {operation.operation_id}.")
        if operation.gate in {"RX", "RZ", "RZZ"} and "angle_radians" not in operation.parameters:
            raise ValueError(f"Missing executable angle in {operation.operation_id}.")
        if operation.gate == "MEASURE" and operation.metadata.get("basis") != "Z":
            raise ValueError(f"Measurement basis missing in {operation.operation_id}.")
        seen.add(operation.operation_id)


def circuit_depth(circuit: CircuitIR) -> int:
    validate_circuit(circuit)
    layers: dict[str, int] = {}
    for operation in circuit.operations:
        layers[operation.operation_id] = 1 + max(
            (layers[dependency] for dependency in operation.dependencies),
            default=0,
        )
    return max(layers.values(), default=0)


def _adjacency(spec: BackendSpec) -> dict[int, set[int]]:
    adjacency = {qubit: set() for qubit in range(spec.capacity)}
    for left, right in spec.coupling_edges:
        adjacency[left].add(right)
        adjacency[right].add(left)
    return adjacency


def _shortest_path(adjacency: dict[int, set[int]], start: int, goal: int) -> list[int]:
    queue: deque[int] = deque([start])
    previous: dict[int, int | None] = {start: None}
    while queue:
        node = queue.popleft()
        if node == goal:
            path: list[int] = []
            current: int | None = node
            while current is not None:
                path.append(current)
                current = previous[current]
            return list(reversed(path))
        for neighbour in sorted(adjacency[node]):
            if neighbour not in previous:
                previous[neighbour] = node
                queue.append(neighbour)
    raise ValueError(f"No topology path between physical qubits {start} and {goal}.")


def _interaction_placement(circuit: CircuitIR, spec: BackendSpec) -> dict[int, int]:
    interaction_degree = {qubit: 0 for qubit in range(circuit.logical_qubits)}
    for operation in circuit.operations:
        if len(operation.qubits) == 2:
            for qubit in operation.qubits:
                interaction_degree[qubit] += 1
    adjacency = _adjacency(spec)
    logical_order = sorted(interaction_degree, key=lambda item: (-interaction_degree[item], item))
    physical_order = sorted(adjacency, key=lambda item: (-len(adjacency[item]), item))
    return dict(zip(logical_order, physical_order[: circuit.logical_qubits]))


def _route_with_placement(
    circuit: CircuitIR,
    spec: BackendSpec,
    initial_placement: dict[int, int],
) -> dict[str, Any]:
    adjacency = _adjacency(spec)
    logical_to_physical = dict(initial_placement)
    physical_to_logical: dict[int, int | None] = {
        physical: logical for logical, physical in logical_to_physical.items()
    }
    for physical in range(spec.capacity):
        physical_to_logical.setdefault(physical, None)
    routed: list[RoutedOperation] = []
    source_terminal: dict[str, str] = {}
    operation_layers: dict[str, int] = {}
    physical_terminal: dict[int, str] = {}
    logical_swap_count = 0

    def schedule(
        operation_id: str,
        gate: str,
        logical_qubits: tuple[int, ...],
        physical_qubits: tuple[int, ...],
        dependencies: Iterable[str],
        source_operation_id: str,
        parameters: dict[str, float],
        purpose: str,
        metadata: dict[str, Any],
    ) -> None:
        dependency_ids = tuple(
            dict.fromkeys(
                [
                    *dependencies,
                    *(
                        physical_terminal[physical]
                        for physical in physical_qubits
                        if physical in physical_terminal
                    ),
                ]
            )
        )
        layer = 1 + max(
            (operation_layers[dependency] for dependency in dependency_ids),
            default=0,
        )
        routed.append(
            RoutedOperation(
                operation_id,
                gate,
                logical_qubits,
                physical_qubits,
                layer,
                dependency_ids,
                source_operation_id,
                parameters,
                purpose,
                metadata,
            )
        )
        operation_layers[operation_id] = layer
        for physical in physical_qubits:
            physical_terminal[physical] = operation_id

    for operation in circuit.operations:
        dependency_ids = [
            source_terminal[dependency] for dependency in operation.dependencies
        ]
        if len(operation.qubits) == 2:
            left_logical, right_logical = operation.qubits
            left_physical = logical_to_physical[left_logical]
            right_physical = logical_to_physical[right_logical]
            path = _shortest_path(adjacency, left_physical, right_physical)
            for swap_index, (source, destination) in enumerate(zip(path[:-2], path[1:-1])):
                logical_swap_count += 1
                swap_id = f"{operation.operation_id}_swap_{swap_index:03d}"
                source_logical = physical_to_logical[source]
                destination_logical = physical_to_logical[destination]
                swap_logical_qubits = tuple(
                    logical
                    for logical in (source_logical, destination_logical)
                    if logical is not None
                )
                for decomposition_index, direction in enumerate(
                    ((source, destination), (destination, source), (source, destination))
                ):
                    decomposition_id = f"{swap_id}_cx_{decomposition_index}"
                    schedule(
                        decomposition_id,
                        "CX",
                        swap_logical_qubits,
                        direction,
                        dependency_ids,
                        operation.operation_id,
                        {},
                        "native CX decomposition of one logical routing SWAP",
                        {
                            "routing_swap_id": swap_id,
                            "decomposition_index": decomposition_index,
                            "abstract_semantic": "SWAP",
                        },
                    )
                    dependency_ids = [decomposition_id]
                physical_to_logical[source], physical_to_logical[destination] = (
                    destination_logical,
                    source_logical,
                )
                if source_logical is not None:
                    logical_to_physical[source_logical] = destination
                if destination_logical is not None:
                    logical_to_physical[destination_logical] = source
            physical_qubits = (
                logical_to_physical[left_logical],
                logical_to_physical[right_logical],
            )
        else:
            physical_qubits = (logical_to_physical[operation.qubits[0]],)
        schedule(
            operation.operation_id,
            operation.gate,
            operation.qubits,
            physical_qubits,
            dependency_ids,
            operation.operation_id,
            operation.parameters,
            operation.purpose,
            operation.metadata,
        )
        source_terminal[operation.operation_id] = operation.operation_id

    return {
        "initial_placement": {
            str(logical): physical for logical, physical in sorted(initial_placement.items())
        },
        "final_placement": {
            str(logical): physical for logical, physical in sorted(logical_to_physical.items())
        },
        "operations": [operation.to_dict() for operation in routed],
        "swap_count": logical_swap_count,
        "native_two_qubit_gate_count": sum(
            len(operation.physical_qubits) == 2 for operation in routed
        ),
        "depth": max((operation.layer for operation in routed), default=0),
    }


def _transpile_connected(circuit: CircuitIR, spec: BackendSpec) -> dict[str, Any]:
    if circuit.logical_qubits > spec.capacity:
        raise ValueError(f"{spec.model} capacity is insufficient for intact circuit.")
    baseline = _route_with_placement(
        circuit,
        spec,
        {logical: logical for logical in range(circuit.logical_qubits)},
    )
    candidate = _route_with_placement(circuit, spec, _interaction_placement(circuit, spec))
    optimized = candidate if candidate["depth"] <= baseline["depth"] else baseline
    routed_by_id = {
        operation["operation_id"]: operation
        for operation in optimized["operations"]
    }
    for source in circuit.operations:
        routed_source = routed_by_id.get(source.operation_id)
        if (
            routed_source is None
            or routed_source["parameters"] != source.parameters
            or routed_source["purpose"] != source.purpose
            or routed_source["metadata"] != source.metadata
        ):
            raise AssertionError(
                f"Executable semantics were not preserved for {source.operation_id}."
            )
    placement_selected = (
        "interaction-aware" if optimized is candidate else "baseline non-regression fallback"
    )
    return {
        "mode": "intact_topology_routing",
        "heuristic": (
            "interaction-degree placement, deterministic shortest-path SWAP routing, "
            "and earliest dependency-safe parallel layer scheduling"
        ),
        "placement_selected": placement_selected,
        "baseline_depth": baseline["depth"],
        "baseline_swap_count": baseline["swap_count"],
        "optimized_depth": optimized["depth"],
        "optimized_swap_count": optimized["swap_count"],
        "transpiled_native_two_qubit_gate_count": optimized[
            "native_two_qubit_gate_count"
        ],
        "depth_non_regression": optimized["depth"] <= baseline["depth"],
        "initial_placement": optimized["initial_placement"],
        "final_placement": optimized["final_placement"],
        "routed_operations": optimized["operations"],
    }


def exact_decimal_count(value: int, semantics: str) -> dict[str, str]:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError("Exact decimal counts require a non-negative integer.")
    return {
        "decimal": str(value),
        "encoding": "exact base-10 non-negative integer string",
        "semantics": semantics,
    }


def analyze_ionq_capacity_partition(
    circuit: CircuitIR,
    spec: BackendSpec | None = None,
) -> dict[str, Any]:
    selected_spec = spec or BACKENDS["ionq_forte"]
    if selected_spec.key != "ionq_forte" or selected_spec.capacity != 36:
        raise ValueError("IonQ partition diagnostics require the 36-AQ Forte target.")
    interaction_degree = {qubit: 0 for qubit in range(circuit.logical_qubits)}
    for operation in circuit.operations:
        if len(operation.qubits) == 2:
            for qubit in operation.qubits:
                interaction_degree[qubit] += 1
    logical_order = sorted(
        interaction_degree,
        key=lambda qubit: (-interaction_degree[qubit], qubit),
    )
    groups = (
        tuple(sorted(logical_order[: selected_spec.capacity])),
        tuple(sorted(logical_order[selected_spec.capacity :])),
    )
    fragment_by_qubit = {
        logical: fragment_index
        for fragment_index, group in enumerate(groups)
        for logical in group
    }
    cut_interactions = [
        {
            "operation_id": operation.operation_id,
            "gate": operation.gate,
            "qubits": list(operation.qubits),
            "parameters": operation.parameters,
        }
        for operation in circuit.operations
        if len(operation.qubits) == 2
        and fragment_by_qubit[operation.qubits[0]]
        != fragment_by_qubit[operation.qubits[1]]
    ]
    rejected_amplitude_terms = 2 ** len(cut_interactions)
    return {
        "status": "UNSUPPORTED_EXACT_CIRCUIT_CUTTING",
        "backend": selected_spec.to_dict(),
        "logical_qubits": circuit.logical_qubits,
        "fragment_widths": [len(group) for group in groups],
        "fragment_logical_qubits": [list(group) for group in groups],
        "cut_count": len(cut_interactions),
        "cut_interactions": cut_interactions,
        "swap_count": 0,
        "reason": (
            "Independent-fragment density-matrix/process-tensor reconstruction "
            "for the complete cross-fragment gate sequence is not implemented. "
            "No interactions are deleted and no submission-ready plan is emitted."
        ),
        "rejected_amplitude_expansion_term_count": exact_decimal_count(
            rejected_amplitude_terms,
            (
                "diagnostic count of terms in the rejected ket-only operator-Schmidt "
                "expansion; not an experiment, shot, or reconstruction multiplier"
            ),
        ),
        "intact_48_qubit_execution_claimed": False,
        "submission_ready": False,
    }


def transpile_circuit(circuit: CircuitIR, backend_key: str) -> dict[str, Any]:
    validate_circuit(circuit)
    if backend_key not in BACKENDS:
        raise ValueError(f"Unsupported QPU backend: {backend_key}")
    spec = BACKENDS[backend_key]
    if circuit.logical_qubits != 48:
        raise ValueError("Multi-vendor workload planning requires exactly 48 logical qubits.")
    if spec.key == "ionq_forte":
        diagnostic = analyze_ionq_capacity_partition(circuit, spec)
        raise ValueError(
            f"{diagnostic['status']}: {diagnostic['reason']}"
        )
    routed = _transpile_connected(circuit, spec)
    digest = sha256(
        (
            backend_key
            + ":"
            + json.dumps(circuit.to_dict(), sort_keys=True, separators=(",", ":"))
        ).encode("utf-8")
    ).hexdigest()[:16]
    return {
        "plan_id": f"qpu_plan_{digest}",
        "status": "READY_FOR_ASYNC_VENDOR_SUBMISSION",
        "workload_type": circuit.workload_type,
        "circuit_name": circuit.name,
        "logical_qubits": circuit.logical_qubits,
        "original_gate_count": len(circuit.operations),
        "original_depth": circuit_depth(circuit),
        "backend": spec.to_dict(),
        "circuit_ir": circuit.to_dict(),
        **routed,
    }


def plan_multivendor_workload(
    workload_type: WorkloadType,
    *,
    qaoa_p: int = 2,
    data_qubits: int = 36,
    ancilla_qubits: int = 12,
) -> dict[str, Any]:
    if workload_type == "qaoa_portfolio_risk":
        circuit = build_qaoa_portfolio_circuit(qaoa_p)
    elif workload_type == "qldpc_syndrome_extraction":
        circuit = build_qldpc_syndrome_circuit(data_qubits, ancilla_qubits)
    else:
        raise ValueError(f"Unsupported 48-qubit workload: {workload_type}")
    plans = {
        backend_key: transpile_circuit(circuit, backend_key)
        for backend_key in ("ibm_heron", "rigetti_ankaa")
    }
    unsupported_backends = {
        "ionq_forte": analyze_ionq_capacity_partition(
            circuit,
            BACKENDS["ionq_forte"],
        )
    }
    return {
        "workload_type": workload_type,
        "logical_qubits": 48,
        "circuit_ir": circuit.to_dict(),
        "plans": plans,
        "unsupported_backends": unsupported_backends,
        "hardware_execution": False,
        "result_scope": "deterministic transpilation plans and heuristic estimates only",
    }
