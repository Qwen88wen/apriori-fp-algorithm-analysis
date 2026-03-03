# Apriori and FP-Growth Analysis (Assignment Workflow)

This repository contains a complete Python workflow to run association analysis on:

- `Accidental_Drug_Related_Deaths.csv`

The script implements both algorithms from scratch:

1. Apriori (with candidate generation and Apriori pruning)
2. FP-Growth (with FP-tree + conditional pattern bases)

## How to run

```bash
python analysis.py
```

## What the script produces

All artifacts are written to `outputs/`:

- `apriori_itemsets.csv` – frequent itemsets mined by Apriori
- `apriori_rules.csv` – association rules generated from Apriori itemsets
- `fp_growth_itemsets.csv` – frequent itemsets mined by FP-Growth
- `fp_growth_rules.csv` – association rules generated from FP-Growth itemsets
- `summary_observations.md` – concise comparison, top rules, and conclusions

## Notes

- Input transactions are derived from drug indicator columns in the dataset.
- A transaction is one death record with all positively flagged substances.
- Default thresholds in `analysis.py`:
  - `MIN_SUPPORT = 0.03`
  - `MIN_CONFIDENCE = 0.35`

You can adjust those constants at the top of the script if your instructor requests different thresholds.


## Beginner guide

- See `BEGINNER_STEP_BY_STEP.md` for a hand-holding, line-by-line coding and run walkthrough.
