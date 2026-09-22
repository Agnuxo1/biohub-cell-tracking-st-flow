from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


@dataclass(frozen=True)
class Candidate:
    """One proposed cell center in voxel coordinates."""

    node_id: int
    t: int
    z: int
    y: int
    x: int
    score: float = 1.0
    response: float = 0.0
    intensity: float = 0.0
    temporal_support: float = 0.0
    scale_um: float = 0.0

    def xyz_um(self, voxel_size_um: tuple[float, float, float]) -> tuple[float, float, float]:
        return tuple(float(c) * float(s) for c, s in zip((self.z, self.y, self.x), voxel_size_um))


@dataclass
class TrackGraph:
    """Submission-ready graph with integer node ids and directed temporal edges."""

    nodes: list[Candidate] = field(default_factory=list)
    edges: list[tuple[int, int]] = field(default_factory=list)

    def add_nodes(self, nodes: Iterable[Candidate]) -> None:
        self.nodes.extend(nodes)

    def validate(self) -> None:
        ids = [node.node_id for node in self.nodes]
        if len(ids) != len(set(ids)):
            raise ValueError("node_id must be unique")
        by_id = {node.node_id: node for node in self.nodes}
        for source, target in self.edges:
            if source not in by_id or target not in by_id:
                raise ValueError("edge references an unknown node")
            if by_id[target].t <= by_id[source].t:
                raise ValueError("edges must point forward in time")
