# Research V2 Bad Baseline Reset

这份文档记录“重新从很差但 gate 通过的基底开始”的默认策略。目的不是选一个好策略，而是避免研究器在高分局部平台上继续做小幅抖动。

## 默认烂基底

优先使用历史第 30 轮 `planner_040`。

| 项目 | 值 |
| --- | --- |
| candidate | `planner_040` |
| iteration | `30` |
| code hash | `bc1b2137aba6bb103357ac12394825cc1739b6e4f8c96c2e5831c32192468e6f` |
| source snapshot | `backups/research_v2_round_artifacts/sources/bc/bc1b2137aba6bb103357ac12394825cc1739b6e4f8c96c2e5831c32192468e6f.py` |
| gate | 通过 |
| promotion_score | `-0.3267` |
| capture_core_score | `0.0056` |
| capture_score | `0.037` |
| selection return | `54.1%` |
| validation return | `18.9%` |
| train / val 非加仓开仓 | `336 / 268` |

选择原因：

- gate 能通过，说明它不是完全坏掉的策略。
- 收益和 capture 都很低，研究器有足够增长空间。
- 交易量足够，不会把研究方向重新拉回“先补交易量”。
- 它比当前高收益 champion 更适合作为重启基底，因为高收益 champion 容易让研究器在局部高分区域做微调。

重置时的默认动作：

1. 停止研究器。
2. 将上面的 source snapshot 写入 `src/strategy_macd_aggressive.py`。
3. 用 `--reset-champion --no-optimize` 重建 active reference。
4. 重置 stage/session。
5. 启动研究器。

最近一次执行：`2026-05-12 09:43:57`（Asia/Shanghai）已按该流程重建为 active champion，并重置 stage/session。

## Capture 分数白话解释

`capture_score` 可以理解成：市场给了几段明显趋势，策略在这些趋势里到底有没有跟上。

例子：

- 市场上涨一大段，策略也赚到钱：加分。
- 市场下跌一大段，策略靠空头赚到钱：加分。
- 市场有大趋势，但策略没赚到，或者反而亏钱：低分或负分。
- 只靠震荡里偶然赚钱，不会显著提高 capture。

现在的普通 `capture_score` 是 train 和 val 的平均趋势抓取表现。问题是它可能掩盖偏科：比如多头抓得还行，空头很差，平均后看起来还能接受。

`capture_core` 是更严格的版本：

- 先看 train 和 val 是否都能抓到趋势。
- 再看 bull 和 bear 是否都能抓到趋势。
- 如果某一边明显弱，就不能只靠强的一边把总分抬高。

通俗说：

`capture_score` 问的是“整体抓趋势像不像样”。
`capture_core` 问的是“是不是 train/val、多/空都像样”。

## 当前 capture_core 结构

旧加权平均结构容易稀释弱项。当前已改成乘法结构：

```text
period_score = balance(train_capture, validation_capture)
side_score = balance(bull_capture, bear_capture)

side_multiplier =
  side_score <= 0.02: 0.35
  0.02 ~ 0.10: smoothstep 平滑到 1.00
  > 0.10: 1.00

capture_core = period_score * side_multiplier
```

这样做的含义：

- train/val 都不错，但多空偏科严重，收益项仍会被打折。
- 多头很强、空头很弱时，不能继续靠多头收益把 promotion 顶上去。
- 不是额外 soft gate，而是主分计算方式本身更偏向泛化。
- 该基底在 v24 下 `period_score=0.0116`、`side_score=0.0430`、`side_multiplier=0.4803`，所以 `capture_core=0.0056`，增长空间很大。

## 最小可调单位硬规则

目标是禁止微调，不是强迫每次都做极端大跳。默认使用“中等步长”。

当前规则：

- 普通百分比参数：单次改动至少 `8%` 相对变化，且至少 `2.0` 个绝对点。
- 大数值百分比参数，例如 `trailing_activation_pct`、`tp1_pnl_pct`：单次改动至少 `8%` 相对变化。
- 小比例参数，例如 `take_profit=0.04`、费率、buffer：单次改动至少 `10%` 相对变化，且至少 `0.002` 绝对值。
- bars/lookback/hold 类整数参数：单次改动至少 `15%`，且至少 `4` 根。
- 0 到 1 之间的阈值，例如 ratio、score、close_pos：单次改动至少 `0.01`，或至少 `8%` 相对变化，取较大者。
- `exit_range_scan` 产生的候选点也必须满足最小步长；不满足则不扫描。

当前仍配合行为变化检查：

- smoke 后核心行为必须明显变化。
- 至少满足以下之一：
  - 非加仓开仓数变化 `>= 8`。
  - path pass 或 final veto pass 变化 `>= 3%`。
  - long/short 其中一侧开仓变化 `>= 5%`。

这条规则的目标是拦住“源码有 diff，但交易路径几乎没变”的候选。

## 注意

- `test` 仍然只做人工只读观察，不进入 planner prompt、评分或晋升。
- 不要把“test 差”写进方向卡让模型直接优化 test。
- 如果重新换基底，文档和 `operator_focus` 要同步改成新的 active reference 状态。
