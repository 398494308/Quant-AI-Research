# MACD Aggressive Current State

这份文档只描述当前主线的运行状态、评分口径和人工介入边界。

## 当前快照

`2026-05-10 13:20:27`（Asia/Shanghai）已把 active reference 手工降温为 `manual.cooldown_maxpos2_trigger8`。这次换基底把 `max_concurrent_positions` 从 `4` 降到 `2`，把 `position_fraction` 从 `0.17` 降到 `0.14`，并把 `pyramid_trigger_pnl` 从 `3.588` 提高到 `8.0`；目的不是得到好策略，而是把过高收益基底降到更容易突破的水平，让后续候选优先围绕 `capture_score` 做真实改进。

当前策略源码位置：

- [src/strategy_macd_aggressive.py](../src/strategy_macd_aggressive.py)
- [backups/strategy_macd_aggressive_v2_best.py](../backups/strategy_macd_aggressive_v2_best.py)

当前运行态：

| 项目 | 状态 |
| --- | --- |
| 研究器 | 运行中，正在按新 active reference 初始化 |
| active reference | champion |
| reference hash | `65980c622eb9821b7599560e8a54ea605752e2ef827c88e227673f6e711c7cee` |
| score regime | `trend_capture_v21_capture_adjusted_return` |
| state 写回 | 已按新基底写回，stage/session 已重置 |
| gate | 通过 |
| quality_score | 0.0342 |
| promotion_score | 0.1936 |
| capture_score / timed_return_score | 0.0978 / 1.2267 |
| drawdown_risk_score / drawdown_penalty_score / robustness_penalty_score | 1.0288 / 0.2058 / 0.0000 |
| train/val clean 抓取分 | 0.0342 / 0.1615 |
| train clean 趋势段 | 67 段，多 36 / 空 31 |
| val clean 趋势段 | 50 段，多 28 / 空 22 |
| val 多/空捕获 | 0.3349 / 0.0116 |
| train+val 期间收益 | 857.19% |
| val 期间收益 | 54.36% |
| train/val 非加仓开仓 | 193 / 152 |
| train/val 月非加仓开仓 | 约 10.7 / 12.7 |
| Sharpe(val / train+val) | 0.98 / 1.95 |
| test capture / return / 平仓 | -0.0995 / -35.69% / 26 |
| val 12 月覆盖 | 已覆盖到 2025-12-22 |

说明：

- v21 沿用 v20 的 clean trend capture 数据源，并增加 capture-adjusted return：低 capture 策略不能再只靠高收益顶分。
- 研究器不会在策略修改轮次里改这套切段规则；后续候选都按当前代码里的固定规则评估。
- 当前 champion 是人工降温基底，`promotion_score` 明显低于上一版高 return champion；它用于降低收益项门槛，让研究器优先寻找 capture 的结构性提升。
- 该基底不是好策略：`test` 仍明显失败，特别是 test capture 为负。`test` 是人工盲测观察，不进入 prompt、方向卡、评分或晋升；planner / reviewer 也不接收 demo 可用性判断。
- Funding 覆盖仍为 `0%`，这是数据源缺口；后续是否进入 demo run 由人工单独决定，不作为研究器优化目标。
- Fear & Greed 情绪数据现在作为可选 `market_state` 输入暴露给策略；它不进入评分、gate 或强制优化目标。

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

## v21 Capture 切段

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

人工盲测观察也使用同一混合口径，但该结果不回喂模型：

`test_trend_capture_score = 0.50 * test_equal_capture_score + 0.50 * test_weighted_capture_score`

收益补充分：

`timed_return_score = 0.50 * train_timed_return_score + 0.50 * val_timed_return_score`

收益补充分会按 `capture_score` 平滑打折：

`capture_return_multiplier = 0.50 + 0.50 * smoothstep(clamp((capture_score - 0.05) / 0.15, 0.0, 1.0))`

`adjusted_timed_return_score = timed_return_score * capture_return_multiplier`

含义：

- `capture_score <= 0.05`：收益补充分只算 `50%`
- `capture_score >= 0.20`：收益补充分正常全算
- 中间平滑过渡，避免硬断崖

Sharpe 不进入主评分，只保留原始 `train / val / train+val / test` 数值，供人工筛选和复核使用。

交易活跃度惩罚：

`train_trade_activity_shortfall = clamp(max(180 - train_entry_trades, 0) / 180, 0.0, 1.0)`

`val_trade_activity_shortfall = clamp(max(120 - validation_entry_trades, 0) / 120, 0.0, 1.0)`

`trade_count_penalty = 0.15 * (0.50 * train_trade_activity_shortfall + 0.50 * val_trade_activity_shortfall)`

`trade_idle_penalty = 0.10 * (0.50 * train_idle_shortfall + 0.50 * val_idle_shortfall)`

趋势机会覆盖惩罚复用已有 clean trend 段命中率：

`train_participation_shortfall = clamp((0.22 - train_segment_hit_rate) / 0.10, 0.0, 1.0)`

`val_participation_shortfall = clamp((0.25 - validation_segment_hit_rate) / 0.10, 0.0, 1.0)`

`trend_participation_penalty = 0.10 * (0.50 * train_participation_shortfall + 0.50 * val_participation_shortfall)`

`trade_activity_penalty = min(0.35, trade_count_penalty + trade_idle_penalty + trend_participation_penalty)`

交易数使用非加仓开仓数，不使用平仓数；加仓只改变已有 position 的规模，不计入活跃度，也不占用 `max_concurrent_positions`。

回撤惩罚：

`drawdown_risk_score = 0.50 * train_drawdown_risk_score + 0.50 * val_drawdown_risk_score`

`drawdown_penalty_score = 0.20 * drawdown_risk_score + 1.00 * max(drawdown_risk_score - 1.25, 0.0)`

`drawdown_risk_score` 复用已有日收益路径，按固定窗口计算 Ulcer 风格回撤深度和持续时间，不新增回测。

晋级分：

`promotion_score = 0.60 * capture_score + 0.40 * adjusted_timed_return_score - drawdown_penalty_score - robustness_penalty_score - trade_activity_penalty`

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

- 当前基底 `max_concurrent_positions = 2`，统计独立 position；研究器仍可在允许范围内探索这个参数。
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
8. 新 champion 同步跑 `test`；图表优先复用刚完成评估里的 `validation` 与 `train+val` 结果，不重复回测；随后 Discord 和 `champion_history` 归档，然后重置 stage/session。
9. 人工 `--reset-champion --no-optimize` 重建基底时，也会重算当前源码自己的 `test` 指标，避免沿用旧 champion 的观察值。

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
