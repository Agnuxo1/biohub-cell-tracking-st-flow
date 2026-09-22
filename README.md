# ST-Flow: reproducible 3D+time cell tracking

![ST-Flow header](assets/header.png)

ST-Flow is an open-source, competition-ready baseline for [Biohub – Cell Tracking During Development](https://www.kaggle.com/competitions/biohub-cell-tracking-during-development). It converts OME-Zarr fluorescence volumes into a physically constrained tracking graph with cell centroids, temporal edges, and conservative division events.

![Tracking pipeline](assets/pipeline.png)

## Why this baseline is useful

- Lazy OME-Zarr access keeps memory bounded on long 3D+time videos.
- Anisotropic multi-scale DoG/LoG detection respects voxel spacing.
- Candidate consensus across neighbouring frames suppresses unstable detections.
- Costs are expressed in micrometres and gated by plausible motion.
- Sparse Hungarian linking is a deterministic fallback when global min-cost flow is unavailable.
- Division edges are added only when geometry and temporal evidence agree.

![Scale-aware detection](assets/scale-aware-detection.png)

## Pipeline

```text
OME-Zarr -> physical normalization -> multi-scale candidates
    -> temporal consensus -> sparse gated linking -> division filter
    -> invariant checks -> submission.csv
```

![Temporal links](assets/temporal-links.png)

## Reproduce locally

```powershell
cd biohub-cell-tracking-st-flow
$env:PYTHONPATH="$PWD/src"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
python -m pytest tests -q --basetemp .pytest_tmp
python -m compileall -q src tests
```

The design is documented in [docs/PIPELINE_DESIGN.md](docs/PIPELINE_DESIGN.md) and [configs/default.yaml](configs/default.yaml). Competition data are intentionally excluded; download them only through Kaggle and keep them outside version control.

## Scientific and competition limits

This is an engineering baseline, not a biological validation study. Public scores are not evidence of biological validity. Local tests verify file contracts and graph invariants only. Follow the competition rules and data-access restrictions before submitting.

## License

MIT. See [LICENSE](LICENSE). Dataset terms remain those of the competition sponsor.
