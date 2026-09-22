import numpy as np

from biohub_stflow.detect import DetectorConfig, detect_sequence, normalize_volume
from biohub_stflow.pipeline import run_deterministic_baseline


SPACING = (1.625, 0.40625, 0.40625)


def _moving_spot_movie() -> np.ndarray:
    movie = np.full((4, 16, 32, 32), 10.0, dtype=np.float32)
    zz, yy, xx = np.indices(movie.shape[1:], dtype=np.float32)
    for t in range(movie.shape[0]):
        spot = 5000.0 * np.exp(
            -(
                ((zz - 8.0) / 1.2) ** 2
                + ((yy - (10.0 + t)) / 2.0) ** 2
                + ((xx - (12.0 + t)) / 2.0) ** 2
            )
            / 2.0
        )
        movie[t] += spot
    return movie


def _detector_config() -> DetectorConfig:
    return DetectorConfig(
        sigmas_um=(0.75, 1.10),
        percentile_low=0.0,
        percentile_high=99.5,
        mad_threshold=1.0,
        nms_radius_um=1.8,
        temporal_window=1,
        min_temporal_support=0.0,
        max_candidates_per_frame=100,
    )


def test_normalize_constant_volume_is_zero():
    normalized = normalize_volume(np.full((3, 4, 5), 7.0, dtype=np.uint16))
    assert normalized.dtype == np.float32
    assert np.array_equal(normalized, np.zeros_like(normalized))


def test_detector_assigns_unique_ids_across_timepoints():
    candidates = detect_sequence(_moving_spot_movie(), SPACING, _detector_config())
    assert len(candidates) == 4
    assert [candidate.t for candidate in candidates] == [0, 1, 2, 3]
    assert [candidate.node_id for candidate in candidates] == [1, 2, 3, 4]


def test_deterministic_baseline_links_synthetic_motion():
    graph = run_deterministic_baseline(
        _moving_spot_movie(),
        voxel_size_um=SPACING,
        detector_config=_detector_config(),
        gate_um=8.0,
    )
    assert len(graph.nodes) == 4
    assert graph.edges == [(1, 2), (2, 3), (3, 4)]
    graph.validate()
