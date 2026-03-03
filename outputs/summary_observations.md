# Apriori vs FP-Growth: Summary of Observations

- Transactions analyzed: **10764**
- Minimum support: **0.03**
- Minimum confidence: **0.35**

## LLM + PandasAI Data Cleaning/Evaluation Notes

- LLM cleaning: LLM cleaning enabled. Learned 0 token classifications via Ollama model 'llama3.1:8b' (if endpoint available).
- PandasAI audit: PandasAI audit skipped: pandas/pandasai not installed in runtime.

## Frequent Itemsets and Rules

- Apriori frequent itemsets: **119**
- FP-Growth frequent itemsets: **119**
- Apriori association rules: **255**
- FP-Growth association rules: **255**

## Performance Comparison

- Apriori runtime: **0.2113 s**
- FP-Growth runtime: **0.1475 s**
- Apriori peak memory (tracemalloc): **55.52 KB**
- FP-Growth peak memory (tracemalloc): **359.72 KB**

## Top Apriori Rules

1. {Heroin death certificate (DC)} -> {Heroin, Heroin/Morph/Codeine} (support=0.0687, confidence=1.0000, lift=5.1675)
2. {Any Opioid, Heroin death certificate (DC)} -> {Heroin, Heroin/Morph/Codeine} (support=0.0686, confidence=1.0000, lift=5.1675)
3. {Heroin death certificate (DC)} -> {Heroin/Morph/Codeine} (support=0.0687, confidence=1.0000, lift=4.8883)
4. {Heroin, Heroin death certificate (DC)} -> {Heroin/Morph/Codeine} (support=0.0687, confidence=1.0000, lift=4.8883)
5. {Any Opioid, Heroin death certificate (DC)} -> {Heroin/Morph/Codeine} (support=0.0686, confidence=1.0000, lift=4.8883)
6. {Any Opioid, Heroin, Heroin death certificate (DC)} -> {Heroin/Morph/Codeine} (support=0.0686, confidence=1.0000, lift=4.8883)
7. {Heroin death certificate (DC)} -> {Heroin} (support=0.0687, confidence=1.0000, lift=3.3243)
8. {Heroin death certificate (DC), Heroin/Morph/Codeine} -> {Heroin} (support=0.0687, confidence=1.0000, lift=3.3243)
9. {Any Opioid, Heroin death certificate (DC)} -> {Heroin} (support=0.0686, confidence=1.0000, lift=3.3243)
10. {Any Opioid, Heroin death certificate (DC), Heroin/Morph/Codeine} -> {Heroin} (support=0.0686, confidence=1.0000, lift=3.3243)

## Top FP-Growth Rules

1. {Heroin death certificate (DC)} -> {Heroin, Heroin/Morph/Codeine} (support=0.0687, confidence=1.0000, lift=5.1675)
2. {Any Opioid, Heroin death certificate (DC)} -> {Heroin, Heroin/Morph/Codeine} (support=0.0686, confidence=1.0000, lift=5.1675)
3. {Heroin death certificate (DC)} -> {Heroin/Morph/Codeine} (support=0.0687, confidence=1.0000, lift=4.8883)
4. {Heroin, Heroin death certificate (DC)} -> {Heroin/Morph/Codeine} (support=0.0687, confidence=1.0000, lift=4.8883)
5. {Any Opioid, Heroin death certificate (DC)} -> {Heroin/Morph/Codeine} (support=0.0686, confidence=1.0000, lift=4.8883)
6. {Any Opioid, Heroin, Heroin death certificate (DC)} -> {Heroin/Morph/Codeine} (support=0.0686, confidence=1.0000, lift=4.8883)
7. {Heroin death certificate (DC)} -> {Heroin} (support=0.0687, confidence=1.0000, lift=3.3243)
8. {Heroin death certificate (DC), Heroin/Morph/Codeine} -> {Heroin} (support=0.0687, confidence=1.0000, lift=3.3243)
9. {Any Opioid, Heroin death certificate (DC)} -> {Heroin} (support=0.0686, confidence=1.0000, lift=3.3243)
10. {Any Opioid, Heroin death certificate (DC), Heroin/Morph/Codeine} -> {Heroin} (support=0.0686, confidence=1.0000, lift=3.3243)

## LLM-based Rule Evaluation

LLM evaluation skipped: Ollama endpoint/model unavailable.

## Handcrafted vs mlxtend Comparison

mlxtend comparison skipped: pandas/mlxtend not installed in runtime.

## Sequential Pattern Mining (Self-explore)

Sequential mining skipped: prefixspan not installed in runtime.
