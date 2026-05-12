# MACD Aggressive Current State

这份文档只描述当前主线的运行状态、评分口径和人工介入边界。

## 当前快照

`2026-05-12 09:43:57`（Asia/Shanghai）已切到 `v24` 评分，并用历史第 30 轮 `planner_040` 的很差但 gate 通过版本重建 champion、重置 stage/session。这个基底的目标不是直接可用，而是给研究器留出明显增长空间，避免继续围绕旧高收益局部平台微调。

当前策略源码位置：

- [src/strategy_macd_aggressive.py](../src/strategy_macd_aggressive.py)
- [backups/strategy_macd_aggressive_v2_best.py](../backups/strategy_macd_aggressive_v2_best.py)

当前运行态：

| 项目 | 状态 |
| --- | --- |
| 研究器 | v24 基底已重建，stage/session 已重置 |
| active reference | champion |
| reference hash | `bc1b2137aba6bb103357ac12394825cc1739b6e4f8c96c2e5831c32192468e6f` |
| 来源 | 历史第 30 轮 `planner_040` |
| score regime | `trend_capture_v24_multiplicative_capture_core` |
| gate | 通过 |
| quality_score | -0.0424 |
| promotion_score | -0.3267 |
| capture_score / capture_core_score | 0.0374 / 0.0056 |
| period_capture_score / side_capture_score / side_multiplier | 0.0116 / 0.0430 / 0.4803 |
| timed_return_score / adjusted_timed_return_score | 0.2515 / 0.0629 |
| capture_return_multiplier | 0.2500 |
| drawdown_penalty_score / robustness_penalty_score / trade_activity_penalty | 0.2003 / 0.0000 / 0.1578 |
| train/val clean 抓取分 | -0.0424 / 0.1173 |
| train/val capture gap | 0.1597 |
| bull/bear capture gap | 0.0225 |
| train clean 趋势段 | 67 段，多 36 / 空 31 |
| val clean 趋势段 | 50 段，多 28 / 空 22 |
| selection 多/空捕获 | 0.0543 / 0.0317 |
| train+val 期间收益 | 54.06% |
| val 期间收益 | 18.90% |
| train/val 非加仓开仓 | 336 / 268 |
| train/val 月非加仓开仓 | 约 18.6 / 22.3 |
| Sharpe(train / val / train+val) | 0.59 / 0.58 / 0.58 |
| test capture / return / 平仓 | -0.0430 / -13.25% / 44 |
| 策略复杂度 | `hard_cap` 诊断态；复杂度只提示，不做自动拒收 |

说明：

- v24 的主变化是 `capture_core` 改为乘法结构：train/val 平衡是主体，多空偏科只作为乘数打折。
- 当前 champion 分数很低，`capture_core=0.0056`，正收益补充分只释放 `25%`。研究器应优先找到连续 train/val 趋势捕获的结构性提升。
- 当前基底交易量充足，不需要再把第一优先级放在“补交易量”；核心短板是 train 捕获为负、整体 capture 很低。
- `test` 是人工盲测观察，不进入 prompt、方向卡、评分或晋升；planner / reviewer 也不接收 demo 可用性判断。
- Funding 覆盖仍为 `0%`，这是数据源缺口；后续是否进入 demo run 由人工单独决定，不作为研究器优化目标。
- Fear & Greed 情绪数据作为可选 `market_state` 输入暴露给策略；它不进入评分、gate 或强制优化目标。

## 数据与窗口

- 标的：`OKX BTC-USDT-SWAP`
- 事实层：`15m`
- 确认层：`1h / 4h`，由 `15m` 聚合得到
- 执行价：优先使用 `1m`
- 情绪：Fear & Greed 日频数据，只作为策略可选环境信息
- `train`：`2023-07-01` 到 `2024-12-31`
- `val`：`2025-01-01` 到 `2025-12-31`
- `test`：`2026-01-01` 到 `2026-04-30`
- `train` 滚动窗口：`28` 天，步长 `21` 天
- `val` 分块：`4` 个连续时间块

## v24 Capture 与收益合成

趋势候选段只从已有 4h 趋势路径里切，不新增回测。切段规则固定，研究器不会在普通策略修改轮次里改这套 capture 数据源。

候选趋势阈值：

- 初始趋势：`max(3.0%, 2.3 * ATR ratio)`
- 成段趋势：`max(3.5%, 2.7 * ATR ratio)`
- 反转确认：`max(1.8%, 1.5 * ATR ratio)`
- 最短段长：`3` 根 4h K 线

clean 过滤：

- `trend_efficiency >= 0.30`
- `directional_bar_ratio >= 0.60`

原始单段分数：

`period_score = 0.70 * trend_capture_score + 0.30 * return_score`

连续趋势抓取主分：

`train_capture_score = 0.50 * train_equal_capture_score + 0.50 * train_weighted_capture_score`

`val_capture_score = 0.50 * val_equal_capture_score + 0.50 * val_weighted_capture_score`

`capture_score = 0.50 * train_capture_score + 0.50 * val_capture_score`

`capture_core`：

`period_capture_score = balance(train_capture_score, val_capture_score)`

`side_capture_score = balance(selection_bull_capture_score, selection_bear_capture_score)`

```text
side_multiplier =
  0.35                                      if side_capture_score <= 0.02
  0.35 + 0.65 * smoothstep((side - 0.02) / 0.08)  if 0.02 < side_capture_score < 0.10
  1.00                                      if side_capture_score >= 0.10
```

`capture_core = period_capture_score * side_multiplier`

`balance(left, right)` 在差距 `<=0.08` 时近似取平均；差距从 `0.08` 到 `0.24` 之间平滑转向弱项；差距 `>=0.24` 时弱项权重达到 `0.65`。

收益补充分会按 `capture_core` 连续调整：

- `capture_core <= 0.03`：`capture_return_multiplier = 0.25`
- `0.03 < capture_core <= 0.12`：`0.25 + 0.75 * smoothstep((capture_core - 0.03) / 0.09)`
- `capture_core > 0.12`：`1.00 + 0.45 * (1.00 - exp(-(capture_core - 0.12) / 0.20))`

`adjusted_timed_return_score = timed_return_score * capture_return_multiplier`（仅当 `timed_return_score >= 0`）

`timed_return_score < 0` 时不打折，亏损按原值进入评分，避免低 capture 把负收益“折轻”。

Sharpe 不进入主评分，只保留原始 `train / val / train+val / test` 数值，供人工筛选和复核使用。

## 交易活跃度

交易数使用非加仓开仓数，不使用平仓数。加仓只改变已有 position 的规模，不计入活跃度，也不占用 `max_concurrent_positions`。

`train_trade_activity_shortfall = clamp(max(180 - train_entry_trades, 0) / 180, 0.0, 1.0)`

`val_trade_activity_shortfall = clamp(max(120 - validation_entry_trades, 0) / 120, 0.0, 1.0)`

`trade_count_penalty = 0.15 * (0.50 * train_trade_activity_shortfall + 0.50 * val_trade_activity_shortfall)`

最长无新开仓上限约 `7` 天；趋势机会覆盖惩罚复用已有 clean trend 段命中率。三项活跃度惩罚合计上限为 `0.35`。

## 晋级分

`promotion_score = 0.50 * adjusted_timed_return_score - drawdown_penalty_score - robustness_penalty_score - trade_activity_penalty`

候选必须先过 `gate`，并且 `promotion_score` 严格高于当前 active reference，才有资格刷新 champion。

## 最小改动硬规则

为避免研究器在同一局部平台做近邻微调，候选相对 active reference 的 `PARAMS` / `EXIT_PARAMS` 数值改动必须达到中等步长：

- bars / lookback / hold / period 类整数参数：至少约 `15%`，且不少于 `4` 根。
- 0 到 1 的 ratio / fraction / confirmation 类阈值：至少 `0.01` 或 `8%`，取较大者。
- 小比例参数：至少 `10%`，且不少于 `0.002`。
- 其他百分比参数：至少 `8%`，且不少于 `2` 个绝对点。
- `exit_range_scan` 的显式值和自动值也必须满足同一最小步长。

这不是 soft constraint；低于最小步长会直接技术拒收。

## 鲁棒性软惩罚

`robustness_penalty_score` 不做硬 gate，也不新增回测。它只复用已有结果：

- `train_window_scores`：现有 train rolling window 的 `period_score`
- `validation_block_scores`：现有 val 分块 `period_score`
- `train_ulcer_pct / validation_ulcer_pct`：现有固定窗口回撤风险里的 blended Ulcer

当前总上限为 `0.15`。它只用来识别 train/val 分布差异是否离谱，不能压过主评分。
