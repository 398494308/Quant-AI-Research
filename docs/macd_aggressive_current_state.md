# MACD Aggressive Current State

这份文档只描述当前主线的运行状态、评分口径和人工介入边界。

## 当前快照

`2026-05-09 23:08:49`（Asia/Shanghai）已把评分口径切到 `trend_capture_v20_clean_trend_segments`，并按 v20 重算当前 active reference。随后已重置 stage/session 并重新启动研究器；当前研究器已进入新 stage 的第 1 轮 planner。

当前策略源码位置：

- [src/strategy_macd_aggressive.py](../src/strategy_macd_aggressive.py)
- [backups/strategy_macd_aggressive_v2_best.py](../backups/strategy_macd_aggressive_v2_best.py)

当前运行态：

| 项目 | 状态 |
| --- | --- |
| 研究器 | 运行中，`model_planner` |
| active reference | baseline |
| reference hash | `4570043420edaa10227897a2e03576176892efd306228fca170daf54188b9d5f` |
| score regime | `trend_capture_v20_clean_trend_segments` |
| state 写回 | 已按 v20 写回 |
| gate | 未通过：`val空头捕获偏低(-0.01)` |
| quality_score | 0.0442 |
| promotion_score | 0.7008 |
| capture_score / timed_return_score | 0.0939 / 2.4338 |
| drawdown_risk_score / drawdown_penalty_score / robustness_penalty_score | 0.8953 / 0.1791 / 0.0000 |
| train/val clean 抓取分 | 0.0442 / 0.1436 |
| train clean 趋势段 | 67 段，多 36 / 空 31 |
| val clean 趋势段 | 50 段，多 28 / 空 22 |
| val 多/空捕获 | 0.3296 / -0.0078 |
| train+val 期间收益 | 1598.32% |
| val 期间收益 | 535.67% |
| train/val 非加仓开仓 | 238 / 161 |
| train/val 月非加仓开仓 | 13.17 / 13.43 |
| Sharpe(train / val / train+val) | 1.88 / 2.35 / 1.70 |
| val 12 月覆盖 | 已覆盖到 2025-12-22 |

说明：

- v20 的目标是把 capture 数据源固定成更干净的单边趋势段，减少震荡段进入评分。
- 研究器不会在策略修改轮次里改这套切段规则；后续候选都按当前代码里的固定规则评估。
- 当前 baseline 按 v20 仍未过 gate，主要问题是 val 空头 clean 趋势捕获略低；新 stage 会围绕新评分继续探索。
- Funding 覆盖仍为 `0%`，这是数据源缺口；最终实盘前用长时间 demo run 兜底观察，不把它硬塞进当前研究评分。

## 数据与窗口

- 标的：`OKX BTC-USDT-SWAP`
- 事实层：`15m`
- 确认层：`1h / 4h`，由 `15m` 聚合得到
- 执行价：优先使用 `1m`
- `train`：`2023-07-01` 到 `2024-12-31`
- `val`：`2025-01-01` 到 `2025-12-31`
- `test`：`2026-01-01` 到 `2026-04-30`
- `train` 滚动窗口：`28` 天，步长 `21` 天
- `val` 分块：`4` 个连续时间块

## v20 Capture 切段

趋势候选段只从已有 4h 趋势路径里切，不新增回测。

候选趋势阈值：

- 初始趋势：`max(3.0%, 2.3 * ATR ratio)`
- 成段趋势：`max(3.5%, 2.7 * ATR ratio)`
- 反转确认：`max(1.8%, 1.5 * ATR ratio)`
- 最短段长：`3` 根 4h K 线

候选段还必须通过两个 clean 过滤：

`trend_efficiency = abs(log(end_price / start_price)) / sum(abs(4h_log_return))`

`directional_bar_ratio = 顺趋势方向的非零 4h K 线数 / 非零 4h K 线总数`

当前阈值：

- `trend_efficiency >= 0.30`
- `directional_bar_ratio >= 0.60`

这两个指标都只复用已有价格路径。前者过滤来回震荡但首尾有位移的段，后者过滤多数 K 线逆着趋势方向走的段。

## 评分公式

原始单段分数：

`period_score = 0.70 * trend_capture_score + 0.30 * return_score`

单段捕获比：

`capture_ratio = clamp(strategy_return / abs(market_return), -1.0, 3.0)`

这里 `strategy_return` 是账户收益方向，bull 和 bear 都必须账户赚钱才是正捕获；`direction` 只用于分段归类，不反转收益符号。

连续趋势抓取主分：

`train_capture_score = 0.50 * train_equal_capture_score + 0.50 * train_weighted_capture_score`

`val_capture_score = 0.50 * val_equal_capture_score + 0.50 * val_weighted_capture_score`

`capture_score = 0.50 * train_capture_score + 0.50 * val_capture_score`

主评分使用连续 `train / val` 数据源：`train` 从已有 `train+val` 连续回测按 `val` 起点切出，`val` 使用连续 validation 结果。`train` walk-forward 仍保留用于窗口诊断、鲁棒性和早停。

收益补充分：

`timed_return_score = 0.50 * train_timed_return_score + 0.50 * val_timed_return_score`

Sharpe 不进入主评分，只保留原始 `train / val / train+val / test` 数值，供人工筛选和复核使用。

交易活跃度惩罚：

`train_trade_activity_shortfall = clamp(max(180 - train_entry_trades, 0) / 180, 0.0, 1.0)`

`val_trade_activity_shortfall = clamp(max(120 - validation_entry_trades, 0) / 120, 0.0, 1.0)`

`trade_count_penalty = 0.20 * (0.50 * train_trade_activity_shortfall + 0.50 * val_trade_activity_shortfall)`

`trade_idle_penalty = 0.15 * (0.50 * train_idle_shortfall + 0.50 * val_idle_shortfall)`

`trade_activity_penalty = trade_count_penalty + trade_idle_penalty`

交易数使用非加仓开仓数，不使用平仓数；加仓只改变已有 position 的规模，不计入活跃度，也不占用 `max_concurrent_positions`。

回撤惩罚：

`drawdown_risk_score = 0.50 * train_drawdown_risk_score + 0.50 * val_drawdown_risk_score`

`drawdown_penalty_score = 0.20 * drawdown_risk_score + 1.00 * max(drawdown_risk_score - 1.25, 0.0)`

`drawdown_risk_score` 复用已有日收益路径，按固定窗口计算 Ulcer 风格回撤深度和持续时间，不新增回测。

晋级分：

`promotion_score = 0.60 * capture_score + 0.40 * timed_return_score - drawdown_penalty_score - robustness_penalty_score - trade_activity_penalty`

候选必须先过 `gate`，并且 `promotion_score` 严格高于当前 active reference，才有资格刷新 champion。

## 鲁棒性软惩罚

`robustness_penalty_score` 不做硬 gate，也不新增回测。它只复用已有结果：

- `train_window_scores`：现有 train rolling window 的 `period_score`
- `validation_block_scores`：现有 val 分块 `period_score`
- `train_ulcer_pct / validation_ulcer_pct`：现有固定窗口回撤风险里的 blended Ulcer

当前计算：

1. 取 `train_window_scores` 的 `median`、`IQR`、`std`。
2. `IQR` 最小按 `0.10` 处理，避免 train 分布过窄导致过度敏感。
3. 取 `validation_block_scores` 的 `median`、`std`。
4. `center_gap_units = abs(val_median - train_median) / train_iqr`
5. `spread_ratio = max(train_std, val_std, 0.10) / min(max(train_std, 0.10), max(val_std, 0.10))`
6. `envelope_overflow_units`：把 `train_median ± 4 * train_iqr` 当宽包络，只看 val 分块跑出包络多少个 IQR。
7. `ulcer_ratio = max(train_ulcer + 1, val_ulcer + 1) / min(train_ulcer + 1, val_ulcer + 1)`

惩罚上限：

- 总上限：`0.15`
- 中位偏离：`2 / 4 / 8` 个 IQR 开始、加重、封顶，组件最多 `0.05`
- 波动比例：`3 / 6 / 10` 倍开始、加重、封顶，组件最多 `0.03`
- 包络溢出：超过宽包络后按 `2 / 5` 个 IQR 加重、封顶，组件最多 `0.03`
- Ulcer 比：`3 / 6 / 10` 倍开始、加重、封顶，组件最多 `0.04`

这个设计刻意很宽：`train` 和 `val` 都可能包含不同行情，不要求两侧谁更好，只在差异非常离谱时软降权。

## 当前 Gate

当前真正参与 gate 的条件：

- `val` 命中率至少 `0.20`
- `val` 趋势捕获分至少 `0.05`
- `train / val` 连续趋势抓取分差不超过 `0.30`
- `val` 多头捕获至少 `0.00`
- `val` 空头捕获至少 `0.00`
- 平均手续费拖累不超过 `11.5%`
- `val` 最差分块至少 `-0.10`
- `val` 负分块最多 `3`
- `train+val` 严重集中度过拟合直接 veto

`train` rolling 均值和中位数只做诊断，不做硬 gate。收益率已经在 `timed_return_score` 中计分，不再在 gate 里重复强约束。

## 多空并行与仓位

- `max_concurrent_positions = 4`，统计独立 position。
- 加仓不新增独立 position，只改变已有 position 的规模。
- 多空可以在总仓位上限内并行存在。
- 现有空仓不会阻止新的多头信号；现有多仓也不会阻止新的空头信号。
- 混合持仓时，信号层按方向扫描所有 position，不再只看 `positions[0]`。

## 研究器流程

当前链路：

1. `planner` 持久 session 写 draft brief。
2. `reviewer` fresh session 审稿，只输出 `PASS / REVISE`。
3. `edit_worker` 只改 [src/strategy_macd_aggressive.py](../src/strategy_macd_aggressive.py)。
4. 主进程检查 diff、smoke、behavioral noop。
5. 可选 `exit_range_scan`：仅单个 `EXIT_PARAMS` 数值键，最多 3 点轻量预筛。
6. 主进程跑完整 `train walk-forward + val`。
7. gate 通过且 `promotion_score` 严格高于当前 active reference，才能刷新 champion。
8. 新 champion 同步跑 `test`、图表、Discord 和 `champion_history` 归档，然后重置 stage/session。

评分阶段只使用已有 `train/val` 评估结果和轻量 `exit_range_scan` 预筛结果。

## 运行与状态

查看状态：

```bash
bash scripts/manage_research_macd_aggressive_v2.sh status
```

停止研究器：

```bash
bash scripts/manage_research_macd_aggressive_v2.sh stop
```

重开 stage/session：

```bash
bash scripts/reset_research_macd_aggressive_v2_stage.sh
```

启动研究器：

```bash
bash scripts/manage_research_macd_aggressive_v2.sh start
```

当前运行状态以 [state/research_macd_aggressive_v2_heartbeat.json](../state/research_macd_aggressive_v2_heartbeat.json) 和管理脚本输出为准。
