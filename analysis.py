#!/usr/bin/env python3
"""
Association-rule mining for the accidental drug related deaths dataset.

This script implements BOTH Apriori and FP-Growth from scratch (pure Python,
no external dependencies) so the workflow is reproducible in restricted
environments. It also exports frequent itemsets and association rules for each
algorithm, and writes a concise comparison report.
"""

from __future__ import annotations

import csv
import itertools
import math
import os
import time
import tracemalloc
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Dict, FrozenSet, Iterable, List, Optional, Sequence, Set, Tuple

# -----------------------------
# Configuration section
# -----------------------------
# The input dataset required by the assignment.
DATASET_PATH = "Accidental_Drug_Related_Deaths.csv"

# Output folder for generated CSV/markdown artifacts.
OUTPUT_DIR = "outputs"

# Minimum support and confidence thresholds used for both algorithms.
# Support is interpreted as fraction of total transactions.
MIN_SUPPORT = 0.03
MIN_CONFIDENCE = 0.35

# Drug indicator columns in the source dataset. Each row becomes one transaction
# containing the substances flagged as present.
DRUG_COLUMNS = [
    "Heroin",
    "Heroin death certificate (DC)",
    "Cocaine",
    "Fentanyl",
    "Fentanyl Analogue",
    "Oxycodone",
    "Oxymorphone",
    "Ethanol",
    "Hydrocodone",
    "Benzodiazepine",
    "Methadone",
    "Meth/Amphetamine",
    "Amphet",
    "Tramad",
    "Hydromorphone",
    "Morphine (Not Heroin)",
    "Xylazine",
    "Gabapentin",
    "Opiate NOS",
    "Heroin/Morph/Codeine",
    "Other Opioid",
    "Any Opioid",
    "Other",
]


# -----------------------------
# Utility and data-loading helpers
# -----------------------------
def normalize_presence(value: str) -> bool:
    """Return True when a cell indicates the substance is present.

    The source data uses mostly "Y" flags, with occasional text in "Other"-style
    fields. We therefore mark values as present whenever they are non-empty and
    not explicit negative placeholders.
    """

    if value is None:
        return False
    text = str(value).strip().lower()
    if text in {"", "n", "no", "0", "nan", "none"}:
        return False
    return True


def load_transactions(path: str, columns: Sequence[str]) -> List[FrozenSet[str]]:
    """Load CSV rows and convert each row into a transaction itemset.

    Each item in a transaction is the drug column name where presence is True.
    Rows with no positive drug indicator are skipped.
    """

    transactions: List[FrozenSet[str]] = []
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        missing = [col for col in columns if col not in reader.fieldnames]
        if missing:
            raise ValueError(f"Missing required drug columns: {missing}")

        for row in reader:
            basket = frozenset(col for col in columns if normalize_presence(row.get(col, "")))
            if basket:
                transactions.append(basket)

    return transactions


def support_count(transactions: Sequence[FrozenSet[str]], itemset: FrozenSet[str]) -> int:
    """Count transactions containing the given itemset."""

    return sum(1 for tx in transactions if itemset.issubset(tx))


def generate_rules(
    frequent_itemsets: Dict[FrozenSet[str], float],
    min_confidence: float,
) -> List[Tuple[Tuple[str, ...], Tuple[str, ...], float, float, float]]:
    """Generate association rules from frequent itemsets.

    Returns tuples of (antecedent, consequent, support, confidence, lift).
    """

    rules = []
    for itemset, sup in frequent_itemsets.items():
        if len(itemset) < 2:
            continue
        for r in range(1, len(itemset)):
            for antecedent in itertools.combinations(sorted(itemset), r):
                antecedent_fs = frozenset(antecedent)
                consequent_fs = itemset - antecedent_fs

                ante_sup = frequent_itemsets.get(antecedent_fs)
                cons_sup = frequent_itemsets.get(consequent_fs)
                if not ante_sup or not cons_sup:
                    continue

                confidence = sup / ante_sup
                if confidence < min_confidence:
                    continue

                lift = confidence / cons_sup if cons_sup > 0 else math.inf
                rules.append(
                    (
                        tuple(sorted(antecedent_fs)),
                        tuple(sorted(consequent_fs)),
                        sup,
                        confidence,
                        lift,
                    )
                )

    rules.sort(key=lambda x: (x[3], x[4], x[2]), reverse=True)
    return rules


# -----------------------------
# Apriori implementation
# -----------------------------
def apriori(transactions: Sequence[FrozenSet[str]], min_support: float) -> Dict[FrozenSet[str], float]:
    """Mine frequent itemsets using the Apriori algorithm."""

    n = len(transactions)
    min_count = math.ceil(min_support * n)

    # L1: frequent 1-itemsets
    item_counter: Counter[str] = Counter()
    for tx in transactions:
        item_counter.update(tx)

    current_level: Set[FrozenSet[str]] = {
        frozenset([item]) for item, count in item_counter.items() if count >= min_count
    }

    frequent: Dict[FrozenSet[str], float] = {
        fs: item_counter[next(iter(fs))] / n for fs in current_level
    }

    k = 2
    while current_level:
        # Candidate generation (self-join of Lk-1)
        prev = sorted(current_level, key=lambda x: tuple(sorted(x)))
        candidates: Set[FrozenSet[str]] = set()
        for i in range(len(prev)):
            for j in range(i + 1, len(prev)):
                union = prev[i] | prev[j]
                if len(union) != k:
                    continue

                # Apriori pruning: all (k-1)-subsets of candidate must be frequent.
                if all(frozenset(sub) in current_level for sub in itertools.combinations(union, k - 1)):
                    candidates.add(union)

        # Count candidate supports and keep only frequent candidates.
        next_level: Set[FrozenSet[str]] = set()
        for cand in candidates:
            count = support_count(transactions, cand)
            if count >= min_count:
                next_level.add(cand)
                frequent[cand] = count / n

        current_level = next_level
        k += 1

    return frequent


# -----------------------------
# FP-Growth implementation
# -----------------------------
@dataclass
class FPNode:
    """Node in an FP-tree."""

    item: Optional[str]
    count: int
    parent: Optional["FPNode"]
    children: Dict[str, "FPNode"]
    link: Optional["FPNode"]

    def __init__(self, item: Optional[str], parent: Optional["FPNode"]):
        self.item = item
        self.count = 0
        self.parent = parent
        self.children = {}
        self.link = None


class FPTree:
    """Compact tree structure used by FP-Growth."""

    def __init__(self):
        self.root = FPNode(None, None)
        self.header: Dict[str, FPNode] = {}

    def add_transaction(self, items: Sequence[str], count: int = 1) -> None:
        node = self.root
        for item in items:
            if item not in node.children:
                child = FPNode(item, node)
                node.children[item] = child

                # Maintain linked-list in header table for quick conditional pattern extraction.
                if item not in self.header:
                    self.header[item] = child
                else:
                    cursor = self.header[item]
                    while cursor.link is not None:
                        cursor = cursor.link
                    cursor.link = child
            node = node.children[item]
            node.count += count


def build_fp_tree(
    transactions: Sequence[FrozenSet[str]],
    min_count: int,
) -> Tuple[FPTree, Dict[str, int]]:
    """Build an FP-tree and return it with global frequent-item counts."""

    freq_counter: Counter[str] = Counter()
    for tx in transactions:
        freq_counter.update(tx)

    # Keep only globally frequent items.
    freq_items = {item: cnt for item, cnt in freq_counter.items() if cnt >= min_count}
    tree = FPTree()

    for tx in transactions:
        filtered = [item for item in tx if item in freq_items]
        if not filtered:
            continue

        # Sort by descending support, then lexicographically for deterministic output.
        filtered.sort(key=lambda x: (-freq_items[x], x))
        tree.add_transaction(filtered)

    return tree, freq_items


def mine_conditional_pattern_base(node: FPNode) -> List[Tuple[List[str], int]]:
    """Extract prefix paths ending at linked nodes for one item."""

    base: List[Tuple[List[str], int]] = []
    cursor = node
    while cursor is not None:
        path: List[str] = []
        parent = cursor.parent
        while parent is not None and parent.item is not None:
            path.append(parent.item)
            parent = parent.parent
        if path:
            base.append((list(reversed(path)), cursor.count))
        cursor = cursor.link
    return base


def build_conditional_tree(
    pattern_base: List[Tuple[List[str], int]],
    min_count: int,
) -> Tuple[FPTree, Dict[str, int]]:
    """Create conditional FP-tree from a pattern base."""

    counter: Counter[str] = Counter()
    for path, count in pattern_base:
        for item in path:
            counter[item] += count

    freq_items = {item: cnt for item, cnt in counter.items() if cnt >= min_count}
    tree = FPTree()

    for path, count in pattern_base:
        filtered = [item for item in path if item in freq_items]
        if not filtered:
            continue
        filtered.sort(key=lambda x: (-freq_items[x], x))
        tree.add_transaction(filtered, count)

    return tree, freq_items


def fp_growth(transactions: Sequence[FrozenSet[str]], min_support: float) -> Dict[FrozenSet[str], float]:
    """Mine frequent itemsets using FP-Growth recursion."""

    n = len(transactions)
    min_count = math.ceil(min_support * n)
    tree, freq_items = build_fp_tree(transactions, min_count)

    frequent: Dict[FrozenSet[str], float] = {}

    def recurse(current_tree: FPTree, current_freq: Dict[str, int], suffix: FrozenSet[str]) -> None:
        # Process items from low frequency to high frequency.
        items = sorted(current_freq.items(), key=lambda kv: (kv[1], kv[0]))
        for item, count in items:
            new_pattern = frozenset(set(suffix) | {item})
            frequent[new_pattern] = count / n

            node = current_tree.header.get(item)
            if node is None:
                continue

            pattern_base = mine_conditional_pattern_base(node)
            cond_tree, cond_freq = build_conditional_tree(pattern_base, min_count)
            if cond_freq:
                recurse(cond_tree, cond_freq, new_pattern)

    recurse(tree, freq_items, frozenset())
    return frequent


# -----------------------------
# Output helpers
# -----------------------------
def ensure_output_dir() -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def write_itemsets_csv(path: str, itemsets: Dict[FrozenSet[str], float]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["itemset", "size", "support"])
        for fs, sup in sorted(itemsets.items(), key=lambda x: (len(x[0]), x[1], sorted(x[0])), reverse=False):
            writer.writerow(["; ".join(sorted(fs)), len(fs), f"{sup:.6f}"])


def write_rules_csv(path: str, rules: List[Tuple[Tuple[str, ...], Tuple[str, ...], float, float, float]]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["antecedent", "consequent", "support", "confidence", "lift"])
        for ant, cons, sup, conf, lift in rules:
            writer.writerow([
                "; ".join(ant),
                "; ".join(cons),
                f"{sup:.6f}",
                f"{conf:.6f}",
                f"{lift:.6f}",
            ])


def top_n_rules_text(rules: List[Tuple[Tuple[str, ...], Tuple[str, ...], float, float, float]], n: int = 10) -> str:
    lines = []
    for idx, (ant, cons, sup, conf, lift) in enumerate(rules[:n], start=1):
        lines.append(
            f"{idx}. {{{', '.join(ant)}}} -> {{{', '.join(cons)}}} "
            f"(support={sup:.4f}, confidence={conf:.4f}, lift={lift:.4f})"
        )
    return "\n".join(lines) if lines else "No rules met the confidence threshold."


def write_summary_report(
    path: str,
    n_transactions: int,
    apriori_itemsets: Dict[FrozenSet[str], float],
    fp_itemsets: Dict[FrozenSet[str], float],
    apriori_rules: List[Tuple[Tuple[str, ...], Tuple[str, ...], float, float, float]],
    fp_rules: List[Tuple[Tuple[str, ...], Tuple[str, ...], float, float, float]],
    apriori_runtime: float,
    fp_runtime: float,
    apriori_peak_kb: float,
    fp_peak_kb: float,
) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("# Apriori vs FP-Growth: Summary of Observations\n\n")
        fh.write(f"- Transactions analyzed: **{n_transactions}**\n")
        fh.write(f"- Minimum support: **{MIN_SUPPORT:.2f}**\n")
        fh.write(f"- Minimum confidence: **{MIN_CONFIDENCE:.2f}**\n\n")

        fh.write("## Frequent Itemsets and Rules\n\n")
        fh.write(f"- Apriori frequent itemsets: **{len(apriori_itemsets)}**\n")
        fh.write(f"- FP-Growth frequent itemsets: **{len(fp_itemsets)}**\n")
        fh.write(f"- Apriori association rules: **{len(apriori_rules)}**\n")
        fh.write(f"- FP-Growth association rules: **{len(fp_rules)}**\n\n")

        fh.write("## Performance Comparison\n\n")
        fh.write(f"- Apriori runtime: **{apriori_runtime:.4f} s**\n")
        fh.write(f"- FP-Growth runtime: **{fp_runtime:.4f} s**\n")
        fh.write(f"- Apriori peak memory (tracemalloc): **{apriori_peak_kb:.2f} KB**\n")
        fh.write(f"- FP-Growth peak memory (tracemalloc): **{fp_peak_kb:.2f} KB**\n\n")

        fh.write("## Top Apriori Rules\n\n")
        fh.write(top_n_rules_text(apriori_rules, n=10) + "\n\n")

        fh.write("## Top FP-Growth Rules\n\n")
        fh.write(top_n_rules_text(fp_rules, n=10) + "\n\n")

        fh.write("## Recommendations / Conclusions\n\n")
        fh.write(
            "1. Both algorithms should return equivalent frequent patterns when support thresholds match. "
            "If counts differ, check preprocessing or threshold rounding.\n"
        )
        fh.write(
            "2. For larger datasets, FP-Growth is often preferable because it avoids candidate explosion by using "
            "the FP-tree representation.\n"
        )
        fh.write(
            "3. Apriori remains valuable for teaching and interpretability, especially when candidate generation/pruning "
            "logic needs to be explicit in documentation.\n"
        )


# -----------------------------
# Main execution pipeline
# -----------------------------
def run_with_profile(fn, *args):
    """Run function while capturing runtime and peak memory in KB."""

    tracemalloc.start()
    start = time.perf_counter()
    result = fn(*args)
    runtime = time.perf_counter() - start
    _current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return result, runtime, peak / 1024.0


def main() -> None:
    ensure_output_dir()

    transactions = load_transactions(DATASET_PATH, DRUG_COLUMNS)
    if not transactions:
        raise RuntimeError("No transactions were extracted from the dataset.")

    apriori_itemsets, apriori_runtime, apriori_peak_kb = run_with_profile(apriori, transactions, MIN_SUPPORT)
    fp_itemsets, fp_runtime, fp_peak_kb = run_with_profile(fp_growth, transactions, MIN_SUPPORT)

    # Generate rules from each frequent-itemset dictionary.
    apriori_rules = generate_rules(apriori_itemsets, MIN_CONFIDENCE)
    fp_rules = generate_rules(fp_itemsets, MIN_CONFIDENCE)

    # Export detailed machine-readable outputs.
    write_itemsets_csv(os.path.join(OUTPUT_DIR, "apriori_itemsets.csv"), apriori_itemsets)
    write_itemsets_csv(os.path.join(OUTPUT_DIR, "fp_growth_itemsets.csv"), fp_itemsets)
    write_rules_csv(os.path.join(OUTPUT_DIR, "apriori_rules.csv"), apriori_rules)
    write_rules_csv(os.path.join(OUTPUT_DIR, "fp_growth_rules.csv"), fp_rules)

    # Export concise narrative report for assignment summary section.
    write_summary_report(
        path=os.path.join(OUTPUT_DIR, "summary_observations.md"),
        n_transactions=len(transactions),
        apriori_itemsets=apriori_itemsets,
        fp_itemsets=fp_itemsets,
        apriori_rules=apriori_rules,
        fp_rules=fp_rules,
        apriori_runtime=apriori_runtime,
        fp_runtime=fp_runtime,
        apriori_peak_kb=apriori_peak_kb,
        fp_peak_kb=fp_peak_kb,
    )

    # Console summary to quickly validate execution.
    print("Association analysis complete.")
    print(f"Transactions: {len(transactions)}")
    print(f"Apriori -> itemsets: {len(apriori_itemsets)}, rules: {len(apriori_rules)}, runtime: {apriori_runtime:.4f}s")
    print(f"FP-Growth -> itemsets: {len(fp_itemsets)}, rules: {len(fp_rules)}, runtime: {fp_runtime:.4f}s")
    print(f"Outputs written to: {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
