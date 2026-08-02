# RNG and Seed Policy

- Synthetic MATLAB/PlatEMO-style optimizer runs use the MATLAB `mcg16807` stream unless a runner manifest explicitly states otherwise.
- Python real-market configured ECMADE-MOO uses `numpy.random.default_rng(cfg.seed)`.
- The default optimizer seed rule is `seed = run_index`.
- The formal selector seed is `20260717`.
- Selector seed and optimizer seed are distinct and must both be reported for ablation experiments.
- Train/validation/test split must be read from `data/synthetic/split_manifest.csv`; scripts must not re-split instances independently.
