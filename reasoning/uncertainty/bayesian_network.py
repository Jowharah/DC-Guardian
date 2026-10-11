"""
DC-Guardian Reasoning
Minimal discrete Bayesian network with exact inference.

A small, dependency-free implementation: variables with finite states,
conditional probability tables (CPTs) keyed by parent states, and exact
posterior queries by enumeration over the joint distribution. The networks
used in DC-Guardian have a handful of nodes, so enumeration is exact and fast.

Kept dependency-free on purpose (no pgmpy) so the Reasoning layer adds no new
runtime requirement and every computation can be inspected in a report.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import product


PROBABILITY_TOLERANCE = 1e-9


@dataclass(frozen=True)
class Node:
    name: str
    states: tuple[str, ...]
    parents: tuple[str, ...] = ()
    # Maps a tuple of parent states (in `parents` order) to a distribution
    # over `states`. A root node uses the empty tuple as its only key.
    cpt: dict[tuple[str, ...], tuple[float, ...]] = field(default_factory=dict)


class BayesianNetwork:
    """Discrete Bayesian network with exact enumeration inference."""

    def __init__(self, nodes: list[Node]):
        self._nodes = {}
        for node in nodes:
            if node.name in self._nodes:
                raise ValueError(f"Duplicate node: {node.name}")
            self._nodes[node.name] = node
        self._order = self._topological_order()
        for node in nodes:
            self._validate_cpt(node)

    # --------------------------------------------------------------
    # Structure
    # --------------------------------------------------------------

    @property
    def nodes(self) -> dict[str, Node]:
        return dict(self._nodes)

    def _topological_order(self) -> list[str]:
        order, visiting, done = [], set(), set()

        def visit(name):
            if name in done:
                return
            if name in visiting:
                raise ValueError("The network contains a cycle.")
            if name not in self._nodes:
                raise ValueError(f"Unknown parent node: {name}")
            visiting.add(name)
            for parent in self._nodes[name].parents:
                visit(parent)
            visiting.discard(name)
            done.add(name)
            order.append(name)

        for name in self._nodes:
            visit(name)
        return order

    def _validate_cpt(self, node: Node) -> None:
        parent_states = [self._nodes[p].states for p in node.parents]
        expected = set(product(*parent_states)) if parent_states else {()}
        if set(node.cpt) != expected:
            raise ValueError(f"CPT for {node.name} must cover exactly the parent combinations {sorted(expected)}.")
        for key, distribution in node.cpt.items():
            if len(distribution) != len(node.states):
                raise ValueError(f"CPT row {key} of {node.name} has the wrong length.")
            if any(p < 0 for p in distribution):
                raise ValueError(f"CPT row {key} of {node.name} has a negative probability.")
            if abs(sum(distribution) - 1.0) > PROBABILITY_TOLERANCE:
                raise ValueError(f"CPT row {key} of {node.name} does not sum to 1.")

    # --------------------------------------------------------------
    # Inference
    # --------------------------------------------------------------

    def _probability(self, name: str, assignment: dict[str, str]) -> float:
        node = self._nodes[name]
        key = tuple(assignment[p] for p in node.parents)
        return node.cpt[key][node.states.index(assignment[name])]

    def joint(self, assignment: dict[str, str]) -> float:
        """Probability of a complete assignment of every node."""
        result = 1.0
        for name in self._order:
            result *= self._probability(name, assignment)
        return result

    def query(self, variable: str, evidence: dict[str, str] | None = None) -> dict[str, float]:
        """Exact posterior P(variable | evidence) by enumeration.

        Evidence may omit any observed node; omitted nodes are marginalized,
        so missing information never has to be guessed.
        """
        evidence = dict(evidence or {})
        if variable not in self._nodes:
            raise ValueError(f"Unknown query variable: {variable}")
        if variable in evidence:
            raise ValueError("The query variable cannot also be evidence.")
        for name, state in evidence.items():
            if name not in self._nodes:
                raise ValueError(f"Unknown evidence variable: {name}")
            if state not in self._nodes[name].states:
                raise ValueError(f"Unknown state {state!r} for {name}.")

        hidden = [n for n in self._order if n != variable and n not in evidence]
        totals = {}
        for state in self._nodes[variable].states:
            total = 0.0
            for values in product(*(self._nodes[h].states for h in hidden)):
                assignment = {**evidence, variable: state, **dict(zip(hidden, values))}
                total += self.joint(assignment)
            totals[state] = total
        normalizer = sum(totals.values())
        if normalizer <= 0:
            raise ValueError("The evidence has zero probability under this network.")
        return {state: value / normalizer for state, value in totals.items()}
