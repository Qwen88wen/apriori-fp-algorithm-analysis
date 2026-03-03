# 新手手把手：自己一行一行敲出 `analysis.py` 并运行

> 目标：你不需要“复制粘贴就完事”，而是能边敲边懂。  
> 方式：按“代码块 + 每行意思”来输入。

---

## 0) 先准备环境

在仓库根目录执行：

```bash
python --version
python analysis.py
```

- 第一句确认 Python 可用。
- 第二句是最终运行命令（你敲完代码后再执行）。

---

## 1) 新建文件并写文件头

先新建 `analysis.py`，输入下面代码：

```python
#!/usr/bin/env python3
"""
Association-rule mining for the accidental drug related deaths dataset.
"""
```

每行意思：
- `#!/usr/bin/env python3`：告诉系统用 Python3 解释器执行这个脚本。
- `""" ... """`：文件级注释（docstring），说明脚本作用。

---

## 2) 输入导入（import）

```python
from __future__ import annotations

import csv
import itertools
import math
import os
import time
import tracemalloc
from collections import Counter
from dataclasses import dataclass
from typing import Dict, FrozenSet, List, Optional, Sequence, Set, Tuple
```

每行意思：
- `from __future__ import annotations`：让类型注解按字符串延迟解析，避免前向引用问题。
- `import csv`：读取/写入 CSV。
- `import itertools`：组合枚举（生成规则时要用）。
- `import math`：`ceil`、`inf` 等数学函数。
- `import os`：路径拼接、目录创建。
- `import time`：统计运行时间。
- `import tracemalloc`：统计 Python 内存峰值。
- `from collections import Counter`：计数器，统计项出现次数。
- `from dataclasses import dataclass`：定义 FP 树节点结构。
- `from typing ...`：类型提示，帮助你读懂函数输入输出。

---

## 3) 输入配置区（你最常改的地方）

```python
DATASET_PATH = "Accidental_Drug_Related_Deaths.csv"
OUTPUT_DIR = "outputs"

MIN_SUPPORT = 0.03
MIN_CONFIDENCE = 0.35

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
```

每行意思（重点）：
- `DATASET_PATH`：输入数据文件路径。
- `OUTPUT_DIR`：结果输出目录。
- `MIN_SUPPORT`：最小支持度阈值（越大，频繁项越少）。
- `MIN_CONFIDENCE`：最小置信度阈值（越大，规则越少）。
- `DRUG_COLUMNS`：哪些列当作“事务里的 item”。

---

## 4) 预处理函数：把一行 CSV 变成一条事务

```python
def normalize_presence(value: str) -> bool:
    if value is None:
        return False
    text = str(value).strip().lower()
    if text in {"", "n", "no", "0", "nan", "none"}:
        return False
    return True
```

每行意思：
- `def normalize_presence...`：定义“该值是否表示药物存在”。
- `if value is None`：空值直接当不存在。
- `str(value).strip().lower()`：统一成“去空格+小写”便于比较。
- `if text in {...}`：把常见否定值统一归为不存在。
- `return True`：其他非空值都算存在。

继续输入：

```python
def load_transactions(path: str, columns: Sequence[str]) -> List[FrozenSet[str]]:
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
```

每行意思：
- `load_transactions`：读取 CSV，输出事务列表。
- `transactions = []`：准备存每条事务。
- `with open(...)`：打开文件；`utf-8-sig` 兼容 BOM。
- `DictReader`：每行按“列名->值”读取。
- `missing = ...`：检查必须列是否存在。
- `raise ValueError`：缺列就立刻报错，防止错算。
- `for row in reader`：逐行处理。
- `basket = frozenset(...)`：从药物列里挑出“存在”的项，组成不可变集合。
- `if basket`：空事务不要。
- `transactions.append`：存起来。
- `return transactions`：把所有事务返回。

---

## 5) 通用函数：支持度计数 + 规则生成

```python
def support_count(transactions: Sequence[FrozenSet[str]], itemset: FrozenSet[str]) -> int:
    return sum(1 for tx in transactions if itemset.issubset(tx))
```

每行意思：
- 统计“有多少条事务包含该项集”。

```python
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
                rules.append((
                    tuple(sorted(antecedent_fs)),
                    tuple(sorted(consequent_fs)),
                    sup,
                    confidence,
                    lift,
                ))

    rules.sort(key=lambda x: (x[3], x[4], x[2]), reverse=True)
    return rules
```

每行意思（核心概念）：
- 枚举每个频繁项集的所有非空真子集作为前件（antecedent）。
- 后件（consequent）= 原项集 - 前件。
- `confidence = support(X∪Y)/support(X)`。
- `lift = confidence / support(Y)`。
- 只保留 `confidence >= min_confidence` 的规则。
- 最后按 `(confidence, lift, support)` 从高到低排序。

---

## 6) Apriori：候选生成 + 剪枝

```python
def apriori(transactions: Sequence[FrozenSet[str]], min_support: float) -> Dict[FrozenSet[str], float]:
    n = len(transactions)
    min_count = math.ceil(min_support * n)

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
```

每行意思（新手重点）：
- `min_count = ceil(min_support * n)`：把比例阈值变成最少出现次数。
- 先做 `L1`（频繁 1 项集）。
- 再循环生成 `k` 项候选。
- `all(...subset in current_level...)`：Apriori 剪枝（反单调性）。
- 候选支持度够才进入下一层。
- 没有新频繁项时退出。

---

## 7) FP-Growth：建树 + 递归挖掘

先输入节点和树：

```python
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
```

每行意思：
- `FPNode`：树节点（item 名、计数、父子关系、同名链表 link）。
- `FPTree.root`：虚根节点。
- `header`：记录每个 item 在树中的首节点，方便走 link。
- `add_transaction`：把事务按顺序插入树，重叠前缀共享路径并累加计数。

再输入建树与递归：

```python
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
```

每行意思（核心）：
- 先全局统计，过滤不频繁项。
- 把每条事务按“频次高→低”排序后插入 FP-tree。
- 对每个 item 提取条件模式基，再建条件树，递归挖掘。
- 最终得到所有频繁项集（无需显式候选爆炸）。

---

## 8) 输出函数（把结果写成作业文件）

```python
def ensure_output_dir() -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
```
- 创建 `outputs/` 文件夹，已存在就不报错。

```python
def write_itemsets_csv(path: str, itemsets: Dict[FrozenSet[str], float]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["itemset", "size", "support"])
        for fs, sup in sorted(itemsets.items(), key=lambda x: (len(x[0]), x[1], sorted(x[0])), reverse=False):
            writer.writerow(["; ".join(sorted(fs)), len(fs), f"{sup:.6f}"])
```
- 写频繁项集 CSV（项集、大小、支持度）。

```python
def write_rules_csv(path: str, rules):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["antecedent", "consequent", "support", "confidence", "lift"])
        for ant, cons, sup, conf, lift in rules:
            writer.writerow(["; ".join(ant), "; ".join(cons), f"{sup:.6f}", f"{conf:.6f}", f"{lift:.6f}"])
```
- 写规则 CSV（前件、后件、支持度、置信度、提升度）。

---

## 9) 主流程（把所有步骤串起来）

```python
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

    transactions = load_transactions(DATASET_PATH, DRUG_COLUMNS)
    if not transactions:
        raise RuntimeError("No transactions were extracted from the dataset.")

    apriori_itemsets, apriori_runtime, apriori_peak_kb = run_with_profile(apriori, transactions, MIN_SUPPORT)
    fp_itemsets, fp_runtime, fp_peak_kb = run_with_profile(fp_growth, transactions, MIN_SUPPORT)

    apriori_rules = generate_rules(apriori_itemsets, MIN_CONFIDENCE)
    fp_rules = generate_rules(fp_itemsets, MIN_CONFIDENCE)

    write_itemsets_csv(os.path.join(OUTPUT_DIR, "apriori_itemsets.csv"), apriori_itemsets)
    write_itemsets_csv(os.path.join(OUTPUT_DIR, "fp_growth_itemsets.csv"), fp_itemsets)
    write_rules_csv(os.path.join(OUTPUT_DIR, "apriori_rules.csv"), apriori_rules)
    write_rules_csv(os.path.join(OUTPUT_DIR, "fp_growth_rules.csv"), fp_rules)

    print("Association analysis complete.")
    print(f"Transactions: {len(transactions)}")
    print(f"Apriori -> itemsets: {len(apriori_itemsets)}, rules: {len(apriori_rules)}, runtime: {apriori_runtime:.4f}s")
    print(f"FP-Growth -> itemsets: {len(fp_itemsets)}, rules: {len(fp_rules)}, runtime: {fp_runtime:.4f}s")
    print(f"Outputs written to: {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
```

每行意思（你真正执行时会发生什么）：
- 先建输出目录。
- 读取 CSV 生成事务。
- 分别跑 Apriori、FP-Growth，并记录时间/内存。
- 从两边频繁项集生成规则。
- 导出四个 CSV。
- 打印总结信息。
- `if __name__ == "__main__"`：保证这个脚本直接运行时才执行 `main()`。

---

## 10) 运行与结果检查（你要自己做）

执行：

```bash
python analysis.py
```

你应该看到类似输出：
- `Transactions: 11932`
- `Apriori -> itemsets: 108, rules: 216`
- `FP-Growth -> itemsets: 108, rules: 216`

再看文件夹：

```bash
ls outputs
```

应该有：
- `apriori_itemsets.csv`
- `apriori_rules.csv`
- `fp_growth_itemsets.csv`
- `fp_growth_rules.csv`
- `summary_observations.md`

---

## 11) 新手最容易错的 5 个点

1. **文件名写错**：`DATASET_PATH` 要和实际 CSV 名称完全一致。  
2. **列名改动**：CSV 表头变了会触发 `Missing required drug columns`。  
3. **缩进错误**：Python 必须对齐（建议 4 空格，不要 Tab）。  
4. **阈值设太高**：规则太少不是报错，是参数结果。  
5. **在错误目录运行**：要在仓库根目录执行 `python analysis.py`。

---

如果你愿意，我下一步可以给你一份“**纯手打训练版**”（更短代码，先只实现 Apriori，再逐步加 FP-Growth）。
