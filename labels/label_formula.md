# Label Formula

## Experiment B LabelScore

For each `instance x theta` group, aggregate run-level metrics and rank theta candidates within the same instance/K comparison group.

- Higher is better: HV, PF_Overlap.
- Lower is better: IGD, PF_Drift, Runtime.
- Ties use average rank.
- Lower LabelScore is better when using the average of ranks.

## Experiment C C_LabelScore

The formal stability-aware selector target is:

```text
C_LabelScore = -0.2 * rank_HV
             - 0.2 * rank_IGD
             - 0.3 * rank_PF_Overlap
             - 0.3 * rank_PF_Drift
```

Because smaller metric ranks are better, a larger `C_LabelScore` indicates a better stability-aware theta. `C_ThetaRank` is assigned by sorting `C_LabelScore` descending within each comparison group.

## Leakage Rule

Test instances must not appear in selector training labels. The split authority is `data/synthetic/split_manifest.csv`.
