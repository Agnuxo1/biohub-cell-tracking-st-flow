# ST-Flow: reproducible 3D+time cell tracking

![ST-Flow: reproducible 3D+time cell tracking: Physically constrained 3D + time cell tracking. Illustrative cover, not data.](docs/science-figures/header.gif)

**Project citation:** [Francisco Angulo de Lafuente](https://orcid.org/0009-0001-1634-7063) · [CITATION.cff](CITATION.cff) · [Software metadata](codemeta.json).


![ST-Flow header](assets/header.png)

ST-Flow is an open-source, competition-ready baseline for [Biohub – Cell Tracking During Development](https://www.kaggle.com/competitions/biohub-cell-tracking-during-development). It converts OME-Zarr fluorescence volumes into a physically constrained tracking graph with cell centroids, temporal edges, and conservative division events.

![Tracking pipeline](assets/pipeline.png)

## Why this baseline is useful

![Use physical space for association: Lazy read — Chunk OME-Zarr; Scale-aware spots — Respect voxel spacing; Frame consensus — Suppress transients; Motion gate — Cost in micrometres](docs/science-figures/01.gif)

*Figure 1. Use physical space for association.*

- Lazy OME-Zarr access keeps memory bounded on long 3D+time videos.
- Anisotropic multi-scale DoG/LoG detection respects voxel spacing.
- Candidate consensus across neighbouring frames suppresses unstable detections.
- Costs are expressed in micrometres and gated by plausible motion.
- Sparse Hungarian linking is a deterministic fallback when global min-cost flow is unavailable.
- Division edges are added only when geometry and temporal evidence agree.

![Scale-aware detection](assets/scale-aware-detection.png)

## Pipeline

![From volumes to a lineage graph: Image volumes — 3D plus time; Candidates — Anisotropic detection; Temporal edges — Sparse gated links; Division filter — Check graph invariants](docs/science-figures/02.gif)

*Figure 2. From volumes to a lineage graph.*

```text
OME-Zarr -> physical normalization -> multi-scale candidates
    -> temporal consensus -> sparse gated linking -> division filter
    -> invariant checks -> submission.csv
```

![Temporal links](assets/temporal-links.png)

## Reproduce locally

![Offline checks before competition data: Configure — Pin paths; Run tests — Graph contracts; Provide data — External data root; Record run — Config plus hashes](docs/science-figures/03.gif)

*Figure 3. Offline checks before competition data.*

```powershell
cd biohub-cell-tracking-st-flow
$env:PYTHONPATH="$PWD/src"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
python -m pytest tests -q --basetemp .pytest_tmp
python -m compileall -q src tests
```

The design is documented in [docs/PIPELINE_DESIGN.md](docs/PIPELINE_DESIGN.md) and [configs/default.yaml](configs/default.yaml). Competition data are intentionally excluded; download them only through Kaggle and keep them outside version control.

## Scientific and competition limits

![What the validation supports: Unit checks — File and graph rules; Challenge score — Benchmark evidence; Biological validation — Requires separate study](docs/science-figures/04.gif)

*Figure 4. What the validation supports.*

This is an engineering baseline, not a biological validation study. Public scores are not evidence of biological validity. Local tests verify file contracts and graph invariants only. Follow the competition rules and data-access restrictions before submitting.

## License

![Reuse and citation: Original code — MIT notice applies; Competition data — Keep sponsor terms; Cite the work — Use CITATION.cff](docs/science-figures/05.gif)

*Figure 5. Reuse and citation.*

MIT. See [LICENSE](LICENSE). Dataset terms remain those of the competition sponsor.

## Bibliography and research directions

![How the references inform follow-up: Primary sources — Resolve DOI or arXiv ID; Study design — Predefine comparisons; Evidence to report — Separate hypotheses and results](docs/science-figures/06.gif)

*Figure 6. How the references inform follow-up.*

The following primary sources inform proposed checks. Their text, code, figures, and data are not included in this documentation update.

- [Ulman et al. (2017), An objective comparison of cell-tracking algorithms](https://doi.org/10.1038/nmeth.4473). Audit detection and tracking errors separately, especially around division events.
- [Maška et al. (2023), The Cell Tracking Challenge: 10 years of objective benchmarking](https://doi.org/10.1038/s41592-023-01879-y). Report transfer and failure modes by sequence or acquisition condition rather than pooling all videos.

**Attribution and reuse.** Please credit [Francisco Angulo de Lafuente](https://orcid.org/0009-0001-1634-7063) in academic and software reuse and do not present this work as your own. When distributing copies or substantial portions of the original MIT software, preserve the copyright and permission notice. Upstream material keeps its own terms. [License](LICENSE) · [Figure provenance](docs/science-figures/PROVENANCE.md).

<!-- research-provenance: project=biohub-cell-tracking-st-flow; date=2026-11-04; author=Francisco Angulo de Lafuente; orcid=https://orcid.org/0009-0001-1634-7063; original-software-license=MIT -->
