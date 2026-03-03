# REPORT — Apriori 与 FP-Growth 实验报告

> 数据集：`Accidental_Drug_Related_Deaths.csv`
> 
> 代码主文件：`analysis.py`

## Step 1 — Preprocessing（数据预处理）

### 目标
将原始 CSV 的每行死亡记录，转换为「事务（transaction）」：事务内元素为药物特征列中被标记为存在的项。

### 实现要点
1. 使用 `csv.DictReader` 读取数据。
2. 对每个药物列执行 presence 归一化（`normalize_presence`）：
   - 空值 / `N` / `No` / `0` / `none` 视为缺失。
   - 其余非空值视为存在。
3. 若该行无任一药物被标记，则该事务跳过。

### 代码截图（分段）
> 说明：当前执行环境的浏览器截图工具崩溃（Chromium SIGSEGV），无法自动导出 PNG。以下先给出对应行号与代码片段；如你需要，我可以在你本地/可用浏览器环境补齐真实 PNG 并替换。

**预处理段（`analysis.py` L66–L110）**

```python
# -----------------------------
# Utility and data-loading helpers
# -----------------------------
def normalize_presence(value: str) -> bool:
    ...

def load_transactions(path: str, columns: Sequence[str]) -> List[FrozenSet[str]]:
    ...
```

---

## Step 2 — Apriori（频繁项集挖掘）

### 目标
用 Apriori 找到满足最小支持度的频繁项集。

### 实现要点
1. 先统计 1-项集（`L1`）。
2. 通过自连接生成候选 `Ck`。
3. 进行 Apriori 剪枝：候选项的所有 `k-1` 子集必须都在 `Lk-1`。
4. 统计支持度并保留频繁项。

### 代码截图（分段）
**Apriori 段（`analysis.py` L155–L204）**

```python
def apriori(transactions: Sequence[FrozenSet[str]], min_support: float) -> Dict[FrozenSet[str], float]:
    ...
```

---

## Step 3 — FP-Growth（频繁项集挖掘）

### 目标
用 FP-tree 与条件模式基递归挖掘频繁项集。

### 实现要点
1. 构建 `FPNode` / `FPTree`。
2. 首次扫描得到全局频次，并过滤低频项。
3. 事务按频次排序插入 FP-tree。
4. 基于 header table 提取条件模式基，递归构建条件树挖掘模式。

### 代码截图（分段）
**FP 段（`analysis.py` L206–L347）**

```python
@dataclass
class FPNode:
    ...

class FPTree:
    ...

def fp_growth(...):
    ...
```

---

## Step 4 — Rule Generation（规则生成）

### 目标
从频繁项集中生成关联规则，计算 support / confidence / lift。

### 实现要点
1. 枚举每个频繁项集的非空真子集作为 antecedent。
2. consequent = itemset - antecedent。
3. 用支持度计算 confidence 与 lift。
4. 按 confidence / lift 排序。

### 代码截图（分段）
**规则段（`analysis.py` L113–L152）**

```python
def generate_rules(...):
    ...
```

---

## Step 5 — Main Pipeline（主流程）

### 目标
统一执行：读取事务 → 两算法挖掘 → 规则生成 → 输出 CSV/MD。

### 实现要点
1. `main()` 中调用 `load_transactions`。
2. 分别执行 `apriori()` 与 `fp_growth()`。
3. 分别导出 itemsets 与 rules。
4. 导出 `summary_observations.md` 对比结果。

### 代码截图（分段）
**主流程段（`analysis.py` L439–L497）**

```python
def main() -> None:
    ...
```

---

## Step 6 — 对比分析（Apriori vs FP-Growth）

基于当前默认阈值：
- `MIN_SUPPORT = 0.03`
- `MIN_CONFIDENCE = 0.35`

运行结果摘要：
- 两种算法频繁项集数量一致（108）。
- 两种算法规则数量一致（216）。
- 运行时间 FP-Growth 略快。

详见：`outputs/summary_observations.md`。

---

## 预期输出 + 可能问题

### 预期输出
1. `outputs/apriori_itemsets.csv`
2. `outputs/apriori_rules.csv`
3. `outputs/fp_growth_itemsets.csv`
4. `outputs/fp_growth_rules.csv`
5. `outputs/summary_observations.md`

### 可能问题（及排查）
1. **阈值太高，规则很少或没有规则**
   - 现象：`rules.csv` 行数很少。
   - 排查：降低 `MIN_SUPPORT` 或 `MIN_CONFIDENCE` 后重跑。

2. **脏值导致事务为空**
   - 现象：有效事务数偏低，甚至报错 `No transactions were extracted...`。
   - 排查：检查 `normalize_presence` 是否覆盖数据中的实际标记形式。

3. **字段名不匹配**
   - 现象：报错 `Missing required drug columns`。
   - 排查：核对 CSV 列名是否被修改、是否有前后空格或编码问题。

4. **两算法结果不一致**
   - 现象：频繁项集数量不同。
   - 排查：支持度阈值取整逻辑、预处理一致性、排序/过滤逻辑是否一致。

---

## 什么是 inline comments（你问的第 4 点）

`inline comments` 指的是 **代码评审时直接挂在某一行 diff 上的评论**，不是总评。

- 位置：PR 的 “Files changed” 页面某一行旁边。
- 作用：指出某行代码的具体问题或改法。
- 修复方式：逐条引用该 comment，对应改代码，然后在 PR 回复“已修复 + 说明改动点”。

如果你把这些 inline comments 贴给我（或给我截图），我可以逐条修复并再次提交。

---

## 附录 A：所有运行的代码（每条附 1 行 justification）

> 说明：这里列的是完成本作业交付所需、且可复现的运行命令。

1. `python analysis.py`
   - justification：执行完整主流程（预处理、Apriori、FP-Growth、规则生成、导出结果），生成 `outputs/*`。

2. `python - <<'PY' ...`（对比 `outputs/apriori_itemsets.csv` 与 `outputs/fp_growth_itemsets.csv`）
   - justification：验证两算法在同阈值下得到的频繁项集是否一致，确保实现正确性与可比性。

3. `python - <<'PY' ...`（读取 `Accidental_Drug_Related_Deaths.csv` 并检查列名）
   - justification：确认输入字段完整且与 `DRUG_COLUMNS` 对齐，避免运行时 `Missing required drug columns`。

---

## 附录 B：Apriori / FP-Growth 必备知识点清单

### B1. 共同基础（两者都需要）
1. **事务数据库（Transaction DB）**：每条记录是一个 itemset。
2. **支持度（Support）**：`support(X) = count(X) / N`。
3. **置信度（Confidence）**：`confidence(X→Y) = support(X∪Y) / support(X)`。
4. **提升度（Lift）**：`lift(X→Y) = confidence(X→Y) / support(Y)`。
5. **最小支持度 / 最小置信度阈值** 的意义及影响（阈值越高，规则越少）。
6. **组合爆炸风险** 与复杂度意识（尤其高维 item 情况）。

### B2. Apriori 专项
1. **Apriori 性质（反单调性）**：若项集频繁，则其所有子集必频繁。
2. **候选生成（Join）**：由 `L(k-1)` 连接得到 `Ck`。
3. **候选剪枝（Prune）**：若候选某个 `(k-1)` 子集不在 `L(k-1)`，可直接剪掉。
4. **逐层扫描数据库**：每层需统计候选支持度。
5. **性能瓶颈**：候选数爆炸、重复扫描 I/O 成本高。

### B3. FP-Growth 专项
1. **FP-tree 结构**：压缩事务前缀路径，减少显式候选生成。
2. **Header table + node-link**：快速定位同名 item 的所有节点。
3. **条件模式基（Conditional Pattern Base）**：某 item 的前缀路径集合。
4. **条件 FP-tree**：基于条件模式基递归挖掘频繁模式。
5. **性能特点**：通常在大数据/高频共现下优于 Apriori；但树构建与递归也有内存开销。

---

## 附录 C：Preprocessing 做了什么，为什么这么做

### C1. 做了什么
1. **固定输入列集合**：只选药物相关指标列（`DRUG_COLUMNS`）。
2. **presence 归一化**：将 `""/N/No/0/none` 统一视作不存在，其他非空值视作存在。
3. **按行构造事务**：把每一行中的“存在药物列名”组成一个事务 `frozenset`。
4. **过滤空事务**：若该行没有任何药物标记，则不参与频繁项挖掘。
5. **字段完整性校验**：启动时先检查所需列是否都在 CSV 中。

### C2. 为什么这么做
1. **统一语义，降低噪声**：原始数据可能包含空白/大小写/不同否定写法，不归一化会导致误判支持度。
2. **把表格转为算法可用形态**：Apriori / FP-Growth 输入应是事务集合，而非宽表原始行。
3. **避免无信息记录干扰**：空事务会稀释支持度分母并引入无意义样本。
4. **提前失败，提升可维护性**：缺列立即报错比中途 silent failure 更容易定位问题。
5. **保证两算法输入一致**：只有预处理一致，Apriori 与 FP 的结果比较才公平可信。
