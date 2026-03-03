# Apriori vs FP-Growth: Summary of Observations

- Transactions analyzed: **11932**
- Minimum support: **0.03**
- Minimum confidence: **0.35**

## Frequent Itemsets and Rules

- Apriori frequent itemsets: **108**
- FP-Growth frequent itemsets: **108**
- Apriori association rules: **216**
- FP-Growth association rules: **216**

## Performance Comparison

- Apriori runtime: **0.1676 s**
- FP-Growth runtime: **0.1182 s**
- Apriori peak memory (tracemalloc): **52.49 KB**
- FP-Growth peak memory (tracemalloc): **381.87 KB**

## Top Apriori Rules

1. {Heroin death certificate (DC)} -> {Heroin, Heroin/Morph/Codeine} (support=0.0620, confidence=1.0000, lift=5.7283)
2. {Any Opioid, Heroin death certificate (DC)} -> {Heroin, Heroin/Morph/Codeine} (support=0.0619, confidence=1.0000, lift=5.7283)
3. {Heroin death certificate (DC)} -> {Heroin/Morph/Codeine} (support=0.0620, confidence=1.0000, lift=5.4187)
4. {Heroin, Heroin death certificate (DC)} -> {Heroin/Morph/Codeine} (support=0.0620, confidence=1.0000, lift=5.4187)
5. {Any Opioid, Heroin death certificate (DC)} -> {Heroin/Morph/Codeine} (support=0.0619, confidence=1.0000, lift=5.4187)
6. {Any Opioid, Heroin, Heroin death certificate (DC)} -> {Heroin/Morph/Codeine} (support=0.0619, confidence=1.0000, lift=5.4187)
7. {Heroin death certificate (DC)} -> {Heroin} (support=0.0620, confidence=1.0000, lift=3.3348)
8. {Heroin death certificate (DC), Heroin/Morph/Codeine} -> {Heroin} (support=0.0620, confidence=1.0000, lift=3.3348)
9. {Any Opioid, Heroin death certificate (DC)} -> {Heroin} (support=0.0619, confidence=1.0000, lift=3.3348)
10. {Any Opioid, Heroin death certificate (DC), Heroin/Morph/Codeine} -> {Heroin} (support=0.0619, confidence=1.0000, lift=3.3348)

## Top FP-Growth Rules

1. {Heroin death certificate (DC)} -> {Heroin, Heroin/Morph/Codeine} (support=0.0620, confidence=1.0000, lift=5.7283)
2. {Any Opioid, Heroin death certificate (DC)} -> {Heroin, Heroin/Morph/Codeine} (support=0.0619, confidence=1.0000, lift=5.7283)
3. {Heroin death certificate (DC)} -> {Heroin/Morph/Codeine} (support=0.0620, confidence=1.0000, lift=5.4187)
4. {Heroin, Heroin death certificate (DC)} -> {Heroin/Morph/Codeine} (support=0.0620, confidence=1.0000, lift=5.4187)
5. {Any Opioid, Heroin death certificate (DC)} -> {Heroin/Morph/Codeine} (support=0.0619, confidence=1.0000, lift=5.4187)
6. {Any Opioid, Heroin, Heroin death certificate (DC)} -> {Heroin/Morph/Codeine} (support=0.0619, confidence=1.0000, lift=5.4187)
7. {Heroin death certificate (DC)} -> {Heroin} (support=0.0620, confidence=1.0000, lift=3.3348)
8. {Heroin death certificate (DC), Heroin/Morph/Codeine} -> {Heroin} (support=0.0620, confidence=1.0000, lift=3.3348)
9. {Any Opioid, Heroin death certificate (DC)} -> {Heroin} (support=0.0619, confidence=1.0000, lift=3.3348)
10. {Any Opioid, Heroin death certificate (DC), Heroin/Morph/Codeine} -> {Heroin} (support=0.0619, confidence=1.0000, lift=3.3348)

## Recommendations / Conclusions

1. Both algorithms should return equivalent frequent patterns when support thresholds match. If counts differ, check preprocessing or threshold rounding.
2. For larger datasets, FP-Growth is often preferable because it avoids candidate explosion by using the FP-tree representation.
3. Apriori remains valuable for teaching and interpretability, especially when candidate generation/pruning logic needs to be explicit in documentation.
