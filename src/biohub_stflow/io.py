from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import numpy as np

from .detect import DEFAULT_VOXEL_SIZE_UM


@dataclass
class OmeZarrVolume:
    """Lazy OME-Zarr volume wrapper; the Zarr dependency stays optional locally."""

    array: object
    voxel_size_um: tuple[float, float, float] = DEFAULT_VOXEL_SIZE_UM

    @property
    def shape(self) -> tuple[int, ...]:
        return tuple(int(value) for value in self.array.shape)  # type: ignore[attr-defined]

    def read_timepoint(self, t: int) -> np.ndarray:
        if t < 0 or t >= self.shape[0]:
            raise IndexError(f"timepoint {t} outside [0, {self.shape[0]})")
        return np.asarray(self.array[t])  # type: ignore[index]

    def iter_timepoints(self) -> Iterator[np.ndarray]:
        for t in range(self.shape[0]):
            yield self.read_timepoint(t)


def open_ome_zarr(path: str | Path, voxel_size_um: tuple[float, float, float] = DEFAULT_VOXEL_SIZE_UM) -> OmeZarrVolume:
    """Open the competition's array at group path `0` without loading it into RAM."""

    try:
        import zarr
    except ImportError as exc:  # pragma: no cover - exercised only in minimal local envs
        raise RuntimeError("zarr is required to open OME-Zarr; attach it to the Kaggle notebook") from exc

    root = zarr.open_group(str(path), mode="r")
    array = root["0"]
    if len(array.shape) != 4:
        raise ValueError(f"expected a 4D OME-Zarr array at {path!s}, got {array.shape}")
    return OmeZarrVolume(array=array, voxel_size_um=voxel_size_um)

