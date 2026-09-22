from __future__ import annotations

import numpy as np

from .detect import DEFAULT_VOXEL_SIZE_UM, DetectorConfig, detect_sequence
from .link import link_framewise_hungarian
from .model import TrackGraph


def run_deterministic_baseline(
    volume: np.ndarray,
    voxel_size_um: tuple[float, float, float] = DEFAULT_VOXEL_SIZE_UM,
    detector_config: DetectorConfig = DetectorConfig(),
    gate_um: float = 7.0,
) -> TrackGraph:
    """JEV-selected end-to-end baseline: detect, then physically gated Hungarian linking."""

    candidates = detect_sequence(volume, voxel_size_um=voxel_size_um, config=detector_config)
    return link_framewise_hungarian(candidates, voxel_size_um=voxel_size_um, gate_um=gate_um)

