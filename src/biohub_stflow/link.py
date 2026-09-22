from __future__ import annotations

from collections import defaultdict
from math import sqrt
from typing import Iterable

from .model import Candidate, TrackGraph


def physical_distance_um(a: Candidate, b: Candidate, voxel_size_um: tuple[float, float, float]) -> float:
    az, ay, ax = a.xyz_um(voxel_size_um)
    bz, by, bx = b.xyz_um(voxel_size_um)
    return sqrt((az - bz) ** 2 + (ay - by) ** 2 + (ax - bx) ** 2)


def link_framewise_hungarian(
    candidates: Iterable[Candidate],
    voxel_size_um: tuple[float, float, float],
    gate_um: float = 7.0,
) -> TrackGraph:
    """Dependency-light fallback linker.

    The production notebook should replace this with the min-cost-flow backend when available.
    This implementation still uses physical distances, one-to-one assignments and an explicit
    gate, making it a deterministic smoke-test baseline rather than a voxel-space nearest-neighbour.
    """

    try:
        import numpy as np
        from scipy.optimize import linear_sum_assignment
    except ImportError as exc:  # pragma: no cover - only exercised on minimal environments
        raise RuntimeError("The fallback linker needs numpy and scipy") from exc

    nodes = sorted(candidates, key=lambda n: (n.t, n.node_id))
    graph = TrackGraph(nodes=list(nodes))
    by_t: dict[int, list[Candidate]] = defaultdict(list)
    for node in nodes:
        by_t[node.t].append(node)

    for t in sorted(by_t):
        left, right = by_t[t], by_t.get(t + 1, [])
        if not right:
            continue
        cost = np.full((len(left), len(right)), gate_um * 10.0, dtype=np.float32)
        for i, src in enumerate(left):
            for j, dst in enumerate(right):
                distance = physical_distance_um(src, dst, voxel_size_um)
                if distance <= gate_um:
                    cost[i, j] = distance
        rows, cols = linear_sum_assignment(cost)
        graph.edges.extend(
            (left[i].node_id, right[j].node_id)
            for i, j in zip(rows, cols)
            if cost[i, j] <= gate_um
        )

    graph.validate()
    return graph

