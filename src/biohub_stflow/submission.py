from __future__ import annotations

import csv
from pathlib import Path

from .model import TrackGraph


HEADER = [
    "id", "dataset", "row_type", "node_id", "t", "z", "y", "x", "source_id", "target_id"
]


def write_submission(graphs: dict[str, TrackGraph], output_csv: str | Path) -> Path:
    """Write the official Kaggle node/edge CSV schema."""

    rows: list[list[object]] = []
    for dataset, graph in graphs.items():
        graph.validate()
        for node in sorted(graph.nodes, key=lambda n: n.node_id):
            rows.append([len(rows), dataset, "node", node.node_id, node.t, node.z, node.y, node.x, -1, -1])
        for source, target in graph.edges:
            rows.append([len(rows), dataset, "edge", -1, -1, -1, -1, -1, source, target])

    output = Path(output_csv)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(HEADER)
        writer.writerows(rows)
    return output

