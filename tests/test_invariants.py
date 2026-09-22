import csv

import pytest

from biohub_stflow.link import link_framewise_hungarian, physical_distance_um
from biohub_stflow.model import Candidate, TrackGraph
from biohub_stflow.submission import HEADER, write_submission


SPACING = (1.625, 0.40625, 0.40625)


def test_candidate_coordinates_convert_to_um():
    node = Candidate(1, 0, 2, 4, 8)
    assert node.xyz_um(SPACING) == (3.25, 1.625, 3.25)


def test_distance_is_zero_for_same_coordinate():
    node = Candidate(1, 0, 2, 4, 8)
    assert physical_distance_um(node, node, SPACING) == 0.0


def test_gate_rejects_distant_assignment():
    candidates = [Candidate(1, 0, 2, 4, 8), Candidate(2, 1, 2, 30, 8)]
    graph = link_framewise_hungarian(candidates, SPACING, gate_um=7.0)
    assert graph.edges == []


def test_missing_next_frame_has_no_edge():
    graph = link_framewise_hungarian([Candidate(1, 4, 2, 4, 8)], SPACING)
    assert graph.edges == []


def test_duplicate_node_ids_are_rejected():
    graph = TrackGraph([Candidate(1, 0, 0, 0, 0), Candidate(1, 1, 0, 0, 0)])
    with pytest.raises(ValueError, match="unique"):
        graph.validate()


def test_unknown_edge_node_is_rejected():
    graph = TrackGraph([Candidate(1, 0, 0, 0, 0)], [(1, 2)])
    with pytest.raises(ValueError, match="unknown"):
        graph.validate()


def test_backward_edge_is_rejected():
    graph = TrackGraph(
        [Candidate(1, 1, 0, 0, 0), Candidate(2, 0, 0, 0, 0)],
        [(1, 2)],
    )
    with pytest.raises(ValueError, match="forward"):
        graph.validate()


def test_empty_submission_contains_header(tmp_path):
    output = write_submission({"empty": TrackGraph()}, tmp_path / "submission.csv")
    with output.open(newline="", encoding="utf-8") as handle:
        assert list(csv.reader(handle)) == [HEADER]


def test_edge_rows_use_official_sentinels(tmp_path):
    graph = TrackGraph(
        [Candidate(1, 0, 0, 0, 0), Candidate(2, 1, 0, 0, 0)],
        [(1, 2)],
    )
    output = write_submission({"dataset_a": graph}, tmp_path / "submission.csv")
    with output.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))
    assert rows[-1][2] == "edge"
    assert rows[-1][3:8] == ["-1", "-1", "-1", "-1", "-1"]
    assert rows[-1][8:] == ["1", "2"]

