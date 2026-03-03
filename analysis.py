#!/usr/bin/env python3
"""
Association-rule mining workflow with optional LLM-assisted data cleaning/evaluation.

Core mining algorithms (Apriori + FP-Growth) are pure Python and dependency-free.
When optional tools are available, the script can:
1) use an open-source LLM backend (e.g., Ollama) to classify ambiguous presence values,
2) use PandasAI for dataframe-level data quality inspection,
3) use LLM to evaluate mined rules by support/confidence/lift.
"""

from __future__ import annotations

import csv
import itertools
import json
import math
import os
import time
import tracemalloc
import urllib.error
import urllib.request
from collections import Counter
from dataclasses import dataclass
from typing import Dict, FrozenSet, List, Optional, Sequence, Set, Tuple

# -----------------------------
# Configuration section
# -----------------------------
DATASET_PATH = "Accidental_Drug_Related_Deaths.csv"
OUTPUT_DIR = "outputs"

MIN_SUPPORT = 0.03
MIN_CONFIDENCE = 0.35

# Optional LLM/PandasAI controls (open-source stack target: Ollama + PandasAI)
ENABLE_LLM_CLEANING = True
ENABLE_LLM_EVALUATION = True
ENABLE_PANDASAI_AUDIT = True

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
OLLAMA_TIMEOUT_S = int(os.getenv("OLLAMA_TIMEOUT_S", "20"))

ENABLE_MLXTEND_COMPARISON = True
ENABLE_SEQUENTIAL_MINING = True

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
# LLM and PandasAI helpers
# -----------------------------
def call_ollama(prompt: str) -> Optional[str]:
    """Call Ollama generate API. Returns text or None when unavailable."""

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.1},
    }
    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=OLLAMA_TIMEOUT_S) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return body.get("response", "").strip() or None
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return None


def pandasai_audit(dataset_path: str) -> str:
    """Optional PandasAI data-quality audit; returns markdown text."""

    if not ENABLE_PANDASAI_AUDIT:
        return "PandasAI audit disabled by config."

    try:
        import pandas as pd  # type: ignore
        from pandasai import SmartDataframe  # type: ignore
    except Exception:
        return "PandasAI audit skipped: pandas/pandasai not installed in runtime."

    try:
        df = pd.read_csv(dataset_path)
    except Exception as exc:
        return f"PandasAI audit skipped: failed to read dataset ({exc})."

    # Newer PandasAI versions use connector objects and may require credentials;
    # we intentionally keep this lightweight and safe-fallback.
    try:
        sdf = SmartDataframe(df)
        q1 = sdf.chat("Which columns in this dataframe have the highest missing-value ratio?")
        q2 = sdf.chat(
            "List data quality risks that may affect association-rule mining and suggest cleaning actions."
        )
        return (
            "PandasAI audit executed successfully.\n\n"
            f"- Missingness insight: {q1}\n"
            f"- Cleaning recommendations: {q2}"
        )
    except Exception as exc:
        return f"PandasAI audit unavailable at runtime (likely missing LLM connector/config): {exc}"


def llm_classify_presence(raw_value: str, column: str) -> Optional[bool]:
    """Ask LLM whether a token means present/absent. Returns None if unclear."""

    prompt = f"""
You are assisting data cleaning for association-rule mining.
Column: {column}
Cell value: {raw_value!r}
Task: classify this value as PRESENT or ABSENT for substance occurrence.
Respond with exactly one token: PRESENT or ABSENT.
""".strip()
    answer = call_ollama(prompt)
    if not answer:
        return None
    token = answer.upper().strip()
    if "PRESENT" in token:
        return True
    if "ABSENT" in token:
        return False
    return None


def llm_evaluate_rules(rules: List[Tuple[Tuple[str, ...], Tuple[str, ...], float, float, float]], n: int = 10) -> str:
    """Ask LLM to evaluate top rules by support/confidence/lift."""

    if not ENABLE_LLM_EVALUATION:
        return "LLM rule evaluation disabled by config."
    if not rules:
        return "No rules available for LLM evaluation."

    lines = []
    for i, (ant, cons, sup, conf, lift) in enumerate(rules[:n], start=1):
        lines.append(
            f"{i}. {{{', '.join(ant)}}} -> {{{', '.join(cons)}}} "
            f"(support={sup:.4f}, confidence={conf:.4f}, lift={lift:.4f})"
        )
    prompt = (
        "You are reviewing association rules for an analytics assignment.\n"
        "Evaluate the following rules using support, confidence, and lift.\n"
        "Output 3 sections: (1) Strong rules, (2) Cautions, (3) Practical recommendations.\n\n"
        + "\n".join(lines)
    )
    response = call_ollama(prompt)
    if not response:
        return "LLM evaluation skipped: Ollama endpoint/model unavailable."
    return response


# -----------------------------
# Data-loading helpers
# -----------------------------
def normalize_presence(value: str) -> bool:
    """Default (non-LLM) presence normalization."""

    if value is None:
        return False
    text = str(value).strip().lower()
    if text in {"", "n", "no", "0", "nan", "none"}:
        return False
    return True


def load_llm_value_map(path: str, columns: Sequence[str]) -> Dict[Tuple[str, str], bool]:
    """Build a mapping for ambiguous tokens using LLM (called once per unique token)."""

    value_map: Dict[Tuple[str, str], bool] = {}
    token_set: Set[Tuple[str, str]] = set()

    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            for col in columns:
                raw = row.get(col, "")
                token = str(raw).strip()
                if not token:
                    continue
                low = token.lower()
                if low in {"y", "yes", "n", "no", "0", "1", "nan", "none"}:
                    continue
                token_set.add((col, token))

    for col, token in sorted(token_set):
        result = llm_classify_presence(token, col)
        if result is not None:
            value_map[(col, token.lower())] = result

    return value_map


def normalize_presence_with_llm(value: str, column: str, llm_map: Dict[Tuple[str, str], bool]) -> bool:
    """Normalize value using deterministic rules + optional LLM map for ambiguous tokens."""

    if value is None:
        return False
    text = str(value).strip()
    low = text.lower()

    if low in {"", "n", "no", "0", "nan", "none"}:
        return False
    if low in {"y", "yes", "1", "true"}:
        return True

    mapped = llm_map.get((column, low))
    if mapped is not None:
        return mapped

    # Fallback: non-empty means present (consistent with original pipeline).
    return True


def load_transactions(path: str, columns: Sequence[str]) -> Tuple[List[FrozenSet[str]], str]:
    """Load CSV and convert each row into a transaction itemset.

    Returns (transactions, cleaning_note).
    """

    transactions: List[FrozenSet[str]] = []
    llm_note = "LLM cleaning not used."
    llm_map: Dict[Tuple[str, str], bool] = {}

    if ENABLE_LLM_CLEANING:
        llm_map = load_llm_value_map(path, columns)
        llm_note = (
            f"LLM cleaning enabled. Learned {len(llm_map)} token classifications "
            f"via Ollama model '{OLLAMA_MODEL}' (if endpoint available)."
        )

    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        missing = [col for col in columns if col not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"Missing required drug columns: {missing}")

        for row in reader:
            basket = frozenset(
                col
                for col in columns
                if normalize_presence_with_llm(row.get(col, ""), col, llm_map)
            )
            if len(basket) >= 2:
                transactions.append(basket)

    return transactions, llm_note


def support_count(transactions: Sequence[FrozenSet[str]], itemset: FrozenSet[str]) -> int:
    return sum(1 for tx in transactions if itemset.issubset(tx))


def generate_rules(
    frequent_itemsets: Dict[FrozenSet[str], float],
    min_confidence: float,
) -> List[Tuple[Tuple[str, ...], Tuple[str, ...], float, float, float]]:
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
                rules.append((tuple(sorted(antecedent_fs)), tuple(sorted(consequent_fs)), sup, confidence, lift))

    rules.sort(key=lambda x: (x[3], x[4], x[2]), reverse=True)
    return rules


# -----------------------------
# Apriori implementation
# -----------------------------
def apriori(transactions: Sequence[FrozenSet[str]], min_support: float) -> Dict[FrozenSet[str], float]:
    n = len(transactions)
    min_count = math.ceil(min_support * n)

    item_counter: Counter[str] = Counter()
    for tx in transactions:
        item_counter.update(tx)

    current_level: Set[FrozenSet[str]] = {
        frozenset([item]) for item, count in item_counter.items() if count >= min_count
    }

    frequent: Dict[FrozenSet[str], float] = {fs: item_counter[next(iter(fs))] / n for fs in current_level}

    k = 2
    while current_level:
        prev = sorted(current_level, key=lambda x: tuple(sorted(x)))
        candidates: Set[FrozenSet[str]] = set()
        for i in range(len(prev)):
            for j in range(i + 1, len(prev)):
                union = prev[i] | prev[j]
                if len(union) != k:
                    continue
                if all(frozenset(sub) in current_level for sub in itertools.combinations(union, k - 1)):
                    candidates.add(union)

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
    def __init__(self):
        self.root = FPNode(None, None)
        self.header: Dict[str, FPNode] = {}

    def add_transaction(self, items: Sequence[str], count: int = 1) -> None:
        node = self.root
        for item in items:
            if item not in node.children:
                child = FPNode(item, node)
                node.children[item] = child
                if item not in self.header:
                    self.header[item] = child
                else:
                    cursor = self.header[item]
                    while cursor.link is not None:
                        cursor = cursor.link
                    cursor.link = child
            node = node.children[item]
            node.count += count


def build_fp_tree(transactions: Sequence[FrozenSet[str]], min_count: int) -> Tuple[FPTree, Dict[str, int]]:
    freq_counter: Counter[str] = Counter()
    for tx in transactions:
        freq_counter.update(tx)

    freq_items = {item: cnt for item, cnt in freq_counter.items() if cnt >= min_count}
    tree = FPTree()

    for tx in transactions:
        filtered = [item for item in tx if item in freq_items]
        if not filtered:
            continue
        filtered.sort(key=lambda x: (-freq_items[x], x))
        tree.add_transaction(filtered)

    return tree, freq_items


def mine_conditional_pattern_base(node: FPNode) -> List[Tuple[List[str], int]]:
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


def build_conditional_tree(pattern_base: List[Tuple[List[str], int]], min_count: int) -> Tuple[FPTree, Dict[str, int]]:
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
    n = len(transactions)
    min_count = math.ceil(min_support * n)
    tree, freq_items = build_fp_tree(transactions, min_count)

    frequent: Dict[FrozenSet[str], float] = {}

    def recurse(current_tree: FPTree, current_freq: Dict[str, int], suffix: FrozenSet[str]) -> None:
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



def mlxtend_analysis(transactions: Sequence[FrozenSet[str]], min_support: float, min_confidence: float):
    """Optional mlxtend-based Apriori/FP-Growth comparison."""

    if not ENABLE_MLXTEND_COMPARISON:
        return None, "mlxtend comparison disabled by config."
    try:
        import pandas as pd  # type: ignore
        from mlxtend.preprocessing import TransactionEncoder  # type: ignore
        from mlxtend.frequent_patterns import apriori as mx_apriori, fpgrowth as mx_fpgrowth, association_rules  # type: ignore
    except Exception:
        return None, "mlxtend comparison skipped: pandas/mlxtend not installed in runtime."

    tx_list = [sorted(list(tx)) for tx in transactions]
    te = TransactionEncoder()
    arr = te.fit(tx_list).transform(tx_list)
    df = pd.DataFrame(arr, columns=te.columns_)

    ap = mx_apriori(df, min_support=min_support, use_colnames=True)
    fp = mx_fpgrowth(df, min_support=min_support, use_colnames=True)
    ap_rules = association_rules(ap, metric="confidence", min_threshold=min_confidence)
    fp_rules = association_rules(fp, metric="confidence", min_threshold=min_confidence)

    result = {
        "apriori_itemsets": int(len(ap)),
        "fpgrowth_itemsets": int(len(fp)),
        "apriori_rules": int(len(ap_rules)),
        "fpgrowth_rules": int(len(fp_rules)),
    }
    return result, "mlxtend comparison executed successfully."


def handcrafted_vs_mlxtend_note(
    handcrafted_ap_cnt: int,
    handcrafted_fp_cnt: int,
    handcrafted_ap_rules: int,
    handcrafted_fp_rules: int,
    mlxtend_result,
    mlxtend_note: str,
) -> str:
    if not mlxtend_result:
        return mlxtend_note
    return (
        f"{mlxtend_note} "
        f"Handcrafted(Apriori={handcrafted_ap_cnt}, FP={handcrafted_fp_cnt}, "
        f"AprioriRules={handcrafted_ap_rules}, FPRules={handcrafted_fp_rules}) vs "
        f"mlxtend(Apriori={mlxtend_result['apriori_itemsets']}, FP={mlxtend_result['fpgrowth_itemsets']}, "
        f"AprioriRules={mlxtend_result['apriori_rules']}, FPRules={mlxtend_result['fpgrowth_rules']})."
    )


def sequential_pattern_mining_note(transactions: Sequence[FrozenSet[str]]) -> str:
    """Optional sequential mining exploration using prefixspan package if available."""

    if not ENABLE_SEQUENTIAL_MINING:
        return "Sequential mining disabled by config."
    try:
        from prefixspan import PrefixSpan  # type: ignore
    except Exception:
        return "Sequential mining skipped: prefixspan not installed in runtime."

    seqs = [sorted(list(tx)) for tx in transactions]
    ps = PrefixSpan(seqs)
    min_support_count = max(2, int(0.03 * len(seqs)))
    patterns = ps.frequent(min_support_count)
    top = patterns[:5]
    return f"PrefixSpan executed: {len(patterns)} frequent sequential patterns; top5={top}"

# -----------------------------
# Output helpers
# -----------------------------
def ensure_output_dir() -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def write_itemsets_csv(path: str, itemsets: Dict[FrozenSet[str], float]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["itemset", "size", "support"])
        for fs, sup in sorted(itemsets.items(), key=lambda x: (len(x[0]), x[1], sorted(x[0]))):
            writer.writerow(["; ".join(sorted(fs)), len(fs), f"{sup:.6f}"])


def write_rules_csv(path: str, rules: List[Tuple[Tuple[str, ...], Tuple[str, ...], float, float, float]]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["antecedent", "consequent", "support", "confidence", "lift"])
        for ant, cons, sup, conf, lift in rules:
            writer.writerow(["; ".join(ant), "; ".join(cons), f"{sup:.6f}", f"{conf:.6f}", f"{lift:.6f}"])


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
    llm_cleaning_note: str,
    pandasai_note: str,
    llm_rule_eval: str,
    mlxtend_compare_note: str,
    sequential_note: str,
) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("# Apriori vs FP-Growth: Summary of Observations\n\n")
        fh.write(f"- Transactions analyzed: **{n_transactions}**\n")
        fh.write(f"- Minimum support: **{MIN_SUPPORT:.2f}**\n")
        fh.write(f"- Minimum confidence: **{MIN_CONFIDENCE:.2f}**\n\n")

        fh.write("## LLM + PandasAI Data Cleaning/Evaluation Notes\n\n")
        fh.write(f"- LLM cleaning: {llm_cleaning_note}\n")
        fh.write(f"- PandasAI audit: {pandasai_note}\n\n")

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

        fh.write("## LLM-based Rule Evaluation\n\n")
        fh.write(llm_rule_eval + "\n\n")

        fh.write("## Handcrafted vs mlxtend Comparison\n\n")
        fh.write(mlxtend_compare_note + "\n\n")

        fh.write("## Sequential Pattern Mining (Self-explore)\n\n")
        fh.write(sequential_note + "\n")


def run_with_profile(fn, *args):
    tracemalloc.start()
    start = time.perf_counter()
    result = fn(*args)
    runtime = time.perf_counter() - start
    _current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return result, runtime, peak / 1024.0


def main() -> None:
    ensure_output_dir()

    transactions, llm_cleaning_note = load_transactions(DATASET_PATH, DRUG_COLUMNS)
    if not transactions:
        raise RuntimeError("No transactions were extracted from the dataset.")

    pandasai_note = pandasai_audit(DATASET_PATH)

    apriori_itemsets, apriori_runtime, apriori_peak_kb = run_with_profile(apriori, transactions, MIN_SUPPORT)
    fp_itemsets, fp_runtime, fp_peak_kb = run_with_profile(fp_growth, transactions, MIN_SUPPORT)

    apriori_rules = generate_rules(apriori_itemsets, MIN_CONFIDENCE)
    fp_rules = generate_rules(fp_itemsets, MIN_CONFIDENCE)

    llm_rule_eval = llm_evaluate_rules(apriori_rules, n=10)

    mlxtend_result, mlxtend_note = mlxtend_analysis(transactions, MIN_SUPPORT, MIN_CONFIDENCE)
    mlxtend_compare_note = handcrafted_vs_mlxtend_note(
        len(apriori_itemsets),
        len(fp_itemsets),
        len(apriori_rules),
        len(fp_rules),
        mlxtend_result,
        mlxtend_note,
    )
    sequential_note = sequential_pattern_mining_note(transactions)

    write_itemsets_csv(os.path.join(OUTPUT_DIR, "apriori_itemsets.csv"), apriori_itemsets)
    write_itemsets_csv(os.path.join(OUTPUT_DIR, "fp_growth_itemsets.csv"), fp_itemsets)
    write_rules_csv(os.path.join(OUTPUT_DIR, "apriori_rules.csv"), apriori_rules)
    write_rules_csv(os.path.join(OUTPUT_DIR, "fp_growth_rules.csv"), fp_rules)

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
        llm_cleaning_note=llm_cleaning_note,
        pandasai_note=pandasai_note,
        llm_rule_eval=llm_rule_eval,
        mlxtend_compare_note=mlxtend_compare_note,
        sequential_note=sequential_note,
    )

    print("Association analysis complete.")
    print(f"Transactions: {len(transactions)}")
    print(f"Apriori -> itemsets: {len(apriori_itemsets)}, rules: {len(apriori_rules)}, runtime: {apriori_runtime:.4f}s")
    print(f"FP-Growth -> itemsets: {len(fp_itemsets)}, rules: {len(fp_rules)}, runtime: {fp_runtime:.4f}s")
    print(f"LLM cleaning note: {llm_cleaning_note}")
    print(f"PandasAI note: {pandasai_note}")
    print(f"mlxtend note: {mlxtend_compare_note}")
    print(f"Sequential note: {sequential_note}")
    print(f"Outputs written to: {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
