# Apriori and FP-Growth Analysis (Assignment Workflow)

This repository contains a complete Python workflow to run association analysis on:

- `Accidental_Drug_Related_Deaths.csv`

The script implements both algorithms from scratch:

1. Apriori (with candidate generation and Apriori pruning)
2. FP-Growth (with FP-tree + conditional pattern bases)

And includes optional LLM-assisted workflow requested by assignment guidance:

- LLM-assisted data cleaning token classification (Ollama API)
- PandasAI dataframe quality audit (when pandas/pandasai is available)
- LLM-based evaluation of mined association rules
- mlxtend off-the-shelf comparison (apriori + fpgrowth + association_rules, when installed)
- sequential pattern self-explore via PrefixSpan (when installed)

## How to run

```bash
python analysis.py
```

## Optional LLM configuration (Ollama)

Set environment variables before running:

```bash
export OLLAMA_URL="http://localhost:11434/api/generate"
export OLLAMA_MODEL="llama3.1:8b"
export OLLAMA_TIMEOUT_S="20"
python analysis.py
```

If Ollama or PandasAI is not available, the script automatically falls back and still completes the standard Apriori/FP-Growth mining.

## What the script produces

All artifacts are written to `outputs/`:

- `apriori_itemsets.csv` – frequent itemsets mined by Apriori
- `apriori_rules.csv` – association rules generated from Apriori itemsets
- `fp_growth_itemsets.csv` – frequent itemsets mined by FP-Growth
- `fp_growth_rules.csv` – association rules generated from FP-Growth itemsets
- `summary_observations.md` – comparison + LLM/PandasAI notes + top rules

## Notes

- Input transactions are derived from drug indicator columns in the dataset.
- A transaction is one death record with all positively flagged substances.
- Transactions with less than 2 items are removed during cleaning.
- Default thresholds in `analysis.py`:
  - `MIN_SUPPORT = 0.03`
  - `MIN_CONFIDENCE = 0.35`

## Beginner guide

- See `BEGINNER_STEP_BY_STEP.md` for a hand-holding, line-by-line coding and run walkthrough.
