# MACD Aggressive Current State

这份文档只描述当前主线的运行状态、评分口径和人工介入边界。

## 当前快照

截至 `2026-05-15`（Asia/Shanghai），策略已完成结构化重构：迁移后保留原策略行为口径，同时新增固定因子槽和硬框架校验。研究器现在额外带一个周期性结构自检修复轮，用于定期整理明显局部过拟合或结构膨胀。低活跃度已经改为硬 gate，避免长期空仓策略成为研究目标。

当前策略源码位置：

- [src/strategy_macd_aggressive.py](../src/strategy_macd_aggressive.py)
- [backups/strategy_macd_aggressive_v2_best.py](../backups/strategy_macd_aggressive_v2_best.py)

当前运行态：

| 项目 | 状态 |
| --- | --- |
| 研究器 | 已以 `planner_040` 结构化差基底重置并重启 |
| score regime | `robust_block_v28_activity_drawdown_allowance` |
| active reference | champion |
| reference hash | `660e09d6e45e3ac676d54fcbd912853705eac2e9b0deffab3fdf63b9b9581409` |
| 来源 | `planner_040` structured bad-baseline reset |
| gate | 通过 |
| quality_score | `0.0180` |
| promotion_score | `-0.1417` |
| main_score / robust_time_score | `-0.0912 / -0.0776` |
| raw robust_time_score | `-0.0674` |
| train/val robust block | `0.0383 / -0.1732` |
| train/val activity multiplier | `0.4695 / 0.6750` |
| benchmark_hurdle_score | `0.0136` |
| drawdown / robustness / allowance / activity | `0.0505 / 0.0000 / 0.3717 / 0.5723` |
| capture_score / capture_core_score | `0.0273 / 0.0138` |
| train/val 非加仓开仓 | `254 / 233` |
| train/val 月非加仓开仓 | `14.06 / 19.43` |
| train/val 持仓覆盖 | `8.82% / 10.69%` |
| val path return | `-30.19%` |
| worst drawdown / fee drag | `31.34% / 3.43%` |
| test / demo | 只做人工只读观察，不进入 prompt、评分或晋升 |
| Sharpe | 只做人工筛选和通知展示，不进入主评分 |
| capture | 只做趋势诊断，不进入主评分，不再给收益做倍率 |
| regime scorecard | 只做解释工具，不做 gate |

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
- v28 稳健主分时间块：`28` 天窗口，`14` 天步长
- walk-forward 诊断使用每个 train 窗口的 robust block 分；提前淘汰复用已完成窗口结果，不再额外重跑累计 train 区间。

## 策略结构

当前策略采用固定框架：

```text
build_context -> classify_regime -> evaluate_factor_slots
              -> build_long/short_candidates
              -> select_candidate -> strategy output
```

可调边界：

- 可改：`PARAMS` 既有 key 的值、开放的 `EXIT_PARAMS` 值、`FACTOR_SLOT_PARAMS` 数值、固定 `_slot_*()` 函数体。
- 不可改：`_strategy_core()` 编排、候选生成顺序、slot 名称/数量/签名、`strategy()` / `strategy_decision()` 入口、固定仓位和杠杆安全项。
- 新因子必须放进现有 slot；不能新增 top-level helper、常量或新的 `PARAMS` / `EXIT_PARAMS` key。
- 普通回测入口 `strategy()` 保留旧行为口径：长侧优先，长侧没有才看空侧；`strategy_decision()` 用结构化候选强度比较。

## v28 主评分

v28 不再把固定单边趋势段 capture 当成主目标。主目标是：多数时间块平均表现要好，同时有效活跃度不能低到只靠少数交易撑起收益。

主分：

```text
train_robust_block_score = 0.60 * mean(block_returns)
                         + 0.25 * median(block_returns)
                         + 0.15 * p25(block_returns)

validation_robust_block_score 同上

train_activity_multiplier = train_entry_activity_multiplier
                          * train_exposure_multiplier

train_adjusted = min(train_robust_block_score, 0)
               + max(train_robust_block_score, 0) * train_activity_multiplier

validation_activity_multiplier = validation_entry_activity_multiplier
                               * validation_exposure_multiplier

validation_adjusted = min(validation_robust_block_score, 0)
                    + max(validation_robust_block_score, 0) * validation_activity_multiplier

robust_time_score = 0.50 * train_adjusted
                  + 0.50 * validation_adjusted

benchmark_hurdle_score = max(0, buy_hold_robust_score) * 0.25

main_score = robust_time_score - benchmark_hurdle_score
```

晋级分：

```text
promotion_score = main_score
                - drawdown_penalty_score
                - robustness_penalty_score
```

回撤惩罚：

```text
drawdown_risk_allowance = 0.20 + 0.30 * activity_multiplier

drawdown_penalty_score =
    0.10 * max(drawdown_risk_score - drawdown_risk_allowance, 0)
  + 1.00 * max(drawdown_risk_score - 1.25, 0)
```

含义：

- `mean` 代表整体时间块平均收益，是 v28 主方向。
- `median` 代表大多数时间块表现。
- `p25` 代表偏差但常见的弱块表现。
- `min` 只做诊断，不进入主分，避免单个坏块把研究器引向“少交易少亏”的局部解。
- 有效活跃度先过硬 gate：train/val 月非加仓开仓都必须至少 `5` 笔/月，持仓覆盖都必须至少 `5%`；低于这条线直接不合格。过 gate 后，活跃度倍率继续只折扣正收益，负收益不打折。
- buy&hold 只在自身稳健分为正时形成轻量扣分，避免研究器只学到“顺市场裸多”。
- 回撤惩罚只扣超过有效活跃度容忍线的部分；严重回撤仍重罚。鲁棒性惩罚是轻量软约束。

## Gate

当前 gate 保留安全和明显失真类限制：

- 爆仓数量必须为 `0`。
- 手续费拖累不能超过 `MACD_V2_MAX_FEE_DRAG_PCT`。
- train+val 严重集中度过拟合仍会直接淘汰。
- train/val 月非加仓开仓频率任一低于 `5` 笔/月直接失败。
- train/val 持仓覆盖任一低于 `5%` 直接失败。

以下内容只做诊断，不再作为硬 gate：

- capture / capture_core。
- val 趋势命中率。
- 多空趋势捕获。
- val 趋势分块。
- 交易数量本身。

晋升规则没有改变：候选必须先过 gate；已有 champion 时，`promotion_score` 必须严格高于当前 active reference，才会刷新 champion。取消的是额外晋级边际，不是取消“更高分才替换”。

结构自检修复轮是唯一例外：它由周期计数排队，不是 planner 主动选择的模式。自检轮候选仍必须通过源码校验、smoke、完整评估和现有 gate；通过后跳过 `promotion_score` 比较，直接替换 active reference，并在 journal 标记 `reference_update_kind=structural_audit_replace`。

## 结构自检修复

触发条件改为定期整理：

- 自上次 champion 刷新或结构自检尝试后，普通轮累计完成 `15` 次 full eval / duplicate-result eval。
- champion 刷新会重置计数；结构自检轮无论成功或失败，也会重置计数。
- 复杂度增长和同一 slot / cluster 连续失败只做诊断，不再直接排队自检。

自检轮只做删减和泛化：

- planner 用独立短 session，不沿用普通持久 session。
- 任务是检查是否某个 slot、规则链或局部阶段过度学习。
- 允许删窄条件、合并重复条件、参数化泛化或移除无效分支。
- 不允许新增复杂分支；改动后 `lines / bool_ops / ifs` 净复杂度不得增加。
- 自检轮失败后不连环触发，直接回到当前 active reference 继续普通研究。

## 交易活跃度

交易频率按非加仓开仓数计算，加仓不计入。

- 目标区间：约 `10-15` 笔/月。
- `8-9` 笔/月偏少。
- `7` 笔/月以下开始明显负面。
- `5` 笔/月以下不可接受。

交易量不足和持仓覆盖不足先触发硬 gate，再通过 `activity_multiplier` 折扣正收益：

```text
entry_activity_multiplier:
0/月  -> 0.00
5/月  -> 0.10
7/月  -> 0.35
10/月 -> 0.70
15/月及以上 -> 1.00

exposure_multiplier:
0%  -> 0.00
5%  -> 0.25
8%  -> 0.45
12% -> 0.75
16%及以上 -> 1.00

activity_multiplier = entry_activity_multiplier * exposure_multiplier
```

持仓覆盖率按“至少有一个仓位存在的时间 / 区间总时间”计算；多仓重叠只算一次，不会因为并行仓位重复加总。目的不是刷交易数，而是避免“开仓数够但大部分时间空仓”的局部解。

## Regime Scorecard

Regime scorecard 是解释工具，用来帮助 planner 判断动量在什么环境有效，不直接进评分或 gate。

当前只复用回测已有轻量数据，不额外接重型外部源：

- ADX / CHOP / ATR ratio。
- flow imbalance、成交量代理、taker buy ratio。
- Fear & Greed：`sentiment`、`fear_greed_value`、`fear_greed_ema7`、`fear_greed_delta1/3/7`。
- 价格自身波动和 daily equity path。

它的用途是回答：

- 趋势强、波动扩张时，动量规则是否更容易赚钱。
- 震荡、低流量或情绪极端时，策略是否应该缩手。
- train 和 val 的好坏块是否来自相同市场环境。

## 鲁棒性

鲁棒性只做轻量软惩罚，不额外回测。它复用已有 train/val 稳健收益块和 Ulcer 统计，检查两侧分布是否离谱：

- train/val 稳健收益块中心差异。
- train/val 分布宽度差异。
- val 是否落到 train 的宽分布包络之外。
- train/val Ulcer 比是否严重失衡。

阈值设得较宽，只在差异很大时明显扣分。它不是用来强行追求稳定曲线，而是拦住“train/val 明显不是同一种策略表现”的情况。

## Capture 诊断

capture 仍保留，因为它能解释策略是否真正抓到了明显趋势，但它不再决定主分。

- 趋势段仍使用固定 clean trend segments。
- train/val 抓取分仍是“段等权均分 50% + 原权重均分 50%”。
- bull 和 bear 都只奖励账户正收益。
- `capture_core` 只提示 train/val 或多空是否偏科。

如果 capture 很低但稳健时间块表现好，候选仍可晋升；如果 capture 很高但多数时间块表现差，主分不会被 capture 拉起来。

## 多空画像

当前研究画像默认允许 `long / flat`。`short` 不是必须对称参与的主引擎，只作为高置信辅助。

- short 占比和多空 capture 只做诊断，不进入评分或 gate。
- 如果 short 不能改善整体 train/val 稳健收益、回撤或 val 弱块，planner 可以主动收窄 short。
- reviewer 会打回只因为 bear capture 弱就机械扩大 short、放宽 short context 或延长 short exit 的方案。

## 人工边界

- 不把 test 或 demo 判断写入 planner prompt。
- 不让 planner 直接优化 test。
- demo 是否值得跑，由人工基于 test、图表、实盘壳子和风险承受单独判断。
- Funding 覆盖仍是数据源缺口；最终实盘前用长时间 demo run 验证。
