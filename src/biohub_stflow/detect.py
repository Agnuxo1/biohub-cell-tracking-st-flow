from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
from scipy import ndimage

from .model import Candidate


DEFAULT_VOXEL_SIZE_UM = (1.625, 0.40625, 0.40625)


@dataclass(frozen=True)
class DetectorConfig:
    sigmas_um: tuple[float, ...] = (0.75, 1.10, 1.55)
    percentile_low: float = 1.0
    percentile_high: float = 99.5
    mad_threshold: float = 3.0
    nms_radius_um: float = 1.8
    temporal_window: int = 1
    min_temporal_support: float = 0.25
    max_candidates_per_frame: int = 2500


def normalize_volume(
    volume: np.ndarray,
    percentile_low: float = 1.0,
    percentile_high: float = 99.5,
) -> np.ndarray:
    """Robustly scale one timepoint to float32 in [0, 1]."""

    array = np.asarray(volume)
    if array.ndim != 3:
        raise ValueError(f"expected a 3D timepoint, got shape {array.shape}")
    values = array.astype(np.float32, copy=False)
    low, high = np.percentile(values, (percentile_low, percentile_high))
    if not np.isfinite(low) or not np.isfinite(high) or high <= low:
        return np.zeros_like(values, dtype=np.float32)
    return np.clip((values - low) / (high - low), 0.0, 1.0).astype(np.float32, copy=False)


def _filter_size(radius_um: float, voxel_size_um: tuple[float, float, float]) -> tuple[int, int, int]:
    sizes = []
    for spacing in voxel_size_um:
        radius_voxels = max(1, int(np.ceil(radius_um / spacing)))
        sizes.append(2 * radius_voxels + 1)
    return tuple(sizes)  # type: ignore[return-value]


def _dog_response(
    normalized: np.ndarray,
    sigma_um: float,
    voxel_size_um: tuple[float, float, float],
) -> np.ndarray:
    sigma = tuple(float(sigma_um) / float(spacing) for spacing in voxel_size_um)
    broad_sigma = tuple(value * 1.6 for value in sigma)
    narrow = ndimage.gaussian_filter(normalized, sigma=sigma, mode="nearest")
    broad = ndimage.gaussian_filter(normalized, sigma=broad_sigma, mode="nearest")
    return np.maximum(narrow - broad, 0.0).astype(np.float32, copy=False)


def _local_temporal_support(
    candidate_coords: np.ndarray,
    neighbor: np.ndarray | None,
    voxel_size_um: tuple[float, float, float],
    gate_um: float,
) -> np.ndarray:
    if neighbor is None or len(candidate_coords) == 0:
        return np.zeros(len(candidate_coords), dtype=np.float32)
    size = _filter_size(gate_um, voxel_size_um)
    maxima = ndimage.maximum_filter(neighbor, size=size, mode="nearest")
    coords = tuple(candidate_coords[:, axis] for axis in range(3))
    return maxima[coords].astype(np.float32, copy=False)


def detect_timepoint(
    volume: np.ndarray,
    t: int,
    voxel_size_um: tuple[float, float, float] = DEFAULT_VOXEL_SIZE_UM,
    config: DetectorConfig = DetectorConfig(),
    previous: np.ndarray | None = None,
    following: np.ndarray | None = None,
    next_node_id: int = 1,
) -> list[Candidate]:
    """Detect bright cell-like peaks while preserving physical anisotropy."""

    normalized = normalize_volume(volume, config.percentile_low, config.percentile_high)
    responses = [_dog_response(normalized, sigma, voxel_size_um) for sigma in config.sigmas_um]
    response_stack = np.stack(responses, axis=0)
    best_scale_index = np.argmax(response_stack, axis=0)
    response = np.max(response_stack, axis=0)

    median = float(np.median(response))
    mad = float(np.median(np.abs(response - median)))
    threshold = median + config.mad_threshold * max(mad, 1e-6)
    local_max = ndimage.maximum_filter(
        response,
        size=_filter_size(config.nms_radius_um, voxel_size_um),
        mode="nearest",
    )
    mask = (response == local_max) & (response >= threshold)
    coords = np.argwhere(mask)
    if len(coords) == 0:
        return []

    supports = []
    for neighbor in (previous, following):
        supports.append(_local_temporal_support(coords, neighbor, voxel_size_um, gate_um=7.0))
    temporal_support = np.mean(np.stack(supports), axis=0) if supports else np.zeros(len(coords))

    keep = temporal_support >= config.min_temporal_support
    # At movie boundaries only one neighbor exists; do not suppress a valid peak merely because
    # the absent side contributes zero.
    neighbor_count = int(previous is not None) + int(following is not None)
    if neighbor_count == 0:
        keep = np.ones(len(coords), dtype=bool)
    elif neighbor_count == 1:
        keep = temporal_support * 2.0 >= config.min_temporal_support
    coords = coords[keep]
    temporal_support = temporal_support[keep]
    if len(coords) == 0:
        return []

    values = response[tuple(coords[:, axis] for axis in range(3))]
    intensity = normalized[tuple(coords[:, axis] for axis in range(3))]
    scales = np.asarray(config.sigmas_um, dtype=np.float32)[best_scale_index[tuple(coords[:, axis] for axis in range(3))]]
    order = np.argsort(values)[::-1][: config.max_candidates_per_frame]

    candidates: list[Candidate] = []
    for offset in order:
        z, y, x = (int(value) for value in coords[offset])
        spatial = float(values[offset])
        temporal = float(temporal_support[offset])
        score = float(np.clip(0.7 * spatial + 0.3 * temporal, 0.0, 1.0))
        candidates.append(
            Candidate(
                node_id=next_node_id + len(candidates),
                t=int(t),
                z=z,
                y=y,
                x=x,
                score=score,
                response=spatial,
                intensity=float(intensity[offset]),
                temporal_support=temporal,
                scale_um=float(scales[offset]),
            )
        )
    return candidates


def detect_sequence(
    volume: np.ndarray | Iterable[np.ndarray],
    voxel_size_um: tuple[float, float, float] = DEFAULT_VOXEL_SIZE_UM,
    config: DetectorConfig = DetectorConfig(),
) -> list[Candidate]:
    """Detect a whole `(T, Z, Y, X)` sequence with a bounded temporal window."""

    sequence = volume if isinstance(volume, np.ndarray) else list(volume)
    if len(sequence) == 0:
        return []
    if np.asarray(sequence).ndim != 4:
        raise ValueError("expected a 4D sequence with shape (T, Z, Y, X)")

    normalized = [normalize_volume(frame, config.percentile_low, config.percentile_high) for frame in sequence]
    candidates: list[Candidate] = []
    next_id = 1
    for t, frame in enumerate(sequence):
        previous = normalized[t - 1] if t > 0 and config.temporal_window else None
        following = normalized[t + 1] if t + 1 < len(normalized) and config.temporal_window else None
        found = detect_timepoint(
            frame,
            t=t,
            voxel_size_um=voxel_size_um,
            config=config,
            previous=previous,
            following=following,
            next_node_id=next_id,
        )
        candidates.extend(found)
        next_id += len(found)
    return candidates

