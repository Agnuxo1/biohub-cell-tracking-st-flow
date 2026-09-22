import csv

from biohub_stflow.link import link_framewise_hungarian, physical_distance_um
from biohub_stflow.model import Candidate
from biohub_stflow.submission import HEADER, write_submission


def test_anisotropic_distance_is_physical():
    a = Candidate(1, 0, 10, 10, 10)
    b = Candidate(2, 1, 11, 10, 10)
    c = Candidate(3, 1, 10, 13, 10)
    spacing = (1.625, 0.40625, 0.40625)
    assert physical_distance_um(a, b, spacing) > physical_distance_um(a, c, spacing)


def test_link_and_submission(tmp_path):
    spacing = (1.625, 0.40625, 0.40625)
    candidates = [
        Candidate(1, 0, 10, 10, 10),
        Candidate(2, 1, 10, 11, 10),
        Candidate(3, 2, 10, 12, 10),
    ]
    graph = link_framewise_hungarian(candidates, spacing, gate_um=7.0)
    assert graph.edges == [(1, 2), (2, 3)]
    output = write_submission({"synthetic": graph}, tmp_path / "submission.csv")
    with output.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))
    assert rows[0] == HEADER
    assert [row[0] for row in rows[1:]] == ["0", "1", "2", "3", "4"]
    assert rows[-1][-2:] == ["2", "3"]
