# MACD Aggressive Current State

这份文档只描述当前主线的运行状态、评分口径和人工介入边界。

## 当前快照

截至 `2026-05-18`（Asia/Shanghai），策略已完成结构化重构，并阶段性切到 `long-only / flat` 研究口径。当前 gate 保留最低持仓覆盖要求，月开仓数只做诊断；long-only 硬 gate 要求 val 与 train+val 的 short 非加仓开仓数都为 `0`。short 退出和风控代码保留，只作为历史或异常持仓安全层，不再作为入场研究路径。

当前策略源码位置：

- [src/strategy_macd_aggressive.py](../src/strategy_macd_aggressive.py)
- [backups/strategy_macd_aggressive_v2_best.py](../backups/strategy_macd_aggressive_v2_best.py)

当前运行态：

| 项目 | 状态 |
| --- | --- |
| 研究器 | 10% 首仓、5% 加仓、关闭半退的手搓低分 long-only 基底已重建为 active reference，准备从干净 stage/session 重新启动 |
| score regime | `robust_block_v29_return_holding_penalty` |
| active reference | champion / working reference |
| reference hash | `6e38eb4ea3568f20cfecc0d74229fc2301ebfc7b38c301c8daa1b07814cfa7ca` |
| 来源 | 手搓结构化低分基底：价格结构优先，flow/趋势质量辅助，MACD 后置确认 |
| gate | long-only gate 启用：val 与 train+val short 非加仓开仓必须为 `0` |
| quality_score | `-0.1274` |
| promotion_score | `-0.9135` |
| return_score / robust_time_score | `-0.4195 / -0.4059` |
| raw robust_time_score | `-0.4059` |
| train/val robust block | `-0.1274 / -0.6843` |
| benchmark_hurdle_score | `0.0136` |
| holding_time_score / penalty_score | `0.0000 / 0.4941` |
| drawdown / robustness / fee / overfit penalty | `0.4329 / 0.0032 / 0.0580 / 0.0000` |
| capture_score / capture_core_score | `-0.0329 / -0.0115` |
| train/val 非加仓开仓 | `314 / 168` |
| long-only gate | `val` 与 `train+val` short 非加仓开仓数都必须为 `0` |
| train/val 月非加仓开仓 | `17.38 / 14.01` |
| train/val 持仓覆盖 | `20.69% / 20.27%` |
| val path return | `-72.23%` |
| worst drawdown / fee drag | `77.96% / 8.14%` |
| test / demo | 只做人工只读观察，不进入 prompt、评分或晋升 |
| freqtrade 适配层 | long-only；`can_short=False`，不再发出 `enter_short` |
| Sharpe | 只做人工筛选和通知展示，不进入主评分 |
| capture | 只做趋势诊断，不进入主评分，不再给收益做倍率 |
| regime scorecard | 只做解释工具，不做 gate |
| 行情标签诊断 | 回测后解释层，不进入评分或 gate；train/val 给 planner，test 只人工看 |

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
- v29 稳健主分时间块：`28` 天窗口，`14` 天步长
- walk-forward 保留为轻量早停和诊断：使用每个 train 窗口的 robust block 分观察训练期稳定性，提前淘汰复用已完成窗口结果，不再额外重跑累计 train 区间。它不再承担旧 capture 保护职责。

## 策略结构

当前策略采用固定框架：

```text
build_context -> classify_regime -> evaluate_factor_slots
              -> build_long_candidate
              -> select_long_candidate -> strategy output
```

可调边界：

- 可改：`PARAMS` 既有 key 的值、开放的 `EXIT_PARAMS` 值、`FACTOR_SLOT_PARAMS` 数值、固定 `_slot_*()` 函数体。
- 不可改：`_strategy_core()` 编排、候选生成顺序、slot 名称/数量/签名、`strategy()` / `strategy_decision()` 入口、固定仓位和杠杆安全项。
- planner / reviewer / worker 若点名锁区 helper，必须把想法翻译到可改空间：对应 `_slot_*()`、`PARAMS`、`EXIT_PARAMS` 或 `FACTOR_SLOT_PARAMS`。系统会先拦住只写锁区、不写落点的 brief。
- 新因子必须放进现有 slot；不能新增 top-level helper、常量或新的 `PARAMS` / `EXIT_PARAMS` key。
- 当前运行入口只允许 long 候选入场；short 候选构建函数返回空。short 退出、止损和异常持仓处理函数保留，避免未来恢复或历史持仓处理时丢失安全层。

当前手搓基底的入场方向：

- `long_breakout`：前高附近或直接突破时的向上释放，价格结构和 K 线接受度先成立，flow/ADX/多周期 EMA 只做质量确认。
- `long_pullback`：价格在 15m EMA 区域或前高附近回踩后重新站上，允许弱通过，给 planner 留出删弱留强的空间。
- `long_reaccel`：已有趋势中的二次加速，只作为窄路径保留。
- `long_veto`：只做负向过滤，不再包含隐藏趋势质量硬门。
- MACD 不再是主驱动，只要求不明显反向；后续不要把研究重心重新拉回 MACD 阈值堆叠。

## v29 主评分

v29 不再把固定单边趋势段 capture 当成主目标。主目标是：多数时间块平均表现要好，同时用持仓覆盖确认策略确实参与了行情。

主分：

```text
train_robust_block_score = 0.60 * mean(block_returns)
                         + 0.25 * median(block_returns)
                         + 0.15 * p25(block_returns)

validation_robust_block_score 同上

robust_time_score = 0.50 * train_robust_block_score
                  + 0.50 * validation_robust_block_score

benchmark_hurdle_score = max(0, buy_hold_robust_score) * 0.25

return_score = robust_time_score - benchmark_hurdle_score
```

晋级分：

```text
holding_time_score = small_bonus_or_penalty_from_position_exposure

penalty_score = drawdown_penalty_score
              + robustness_penalty_score
              + fee_drag_penalty_score
              + overfit_penalty_score

promotion_score = return_score + holding_time_score - penalty_score
```

回撤惩罚：

```text
drawdown_risk_allowance = 0.20 + 0.30 * exposure_multiplier

drawdown_penalty_score =
    0.10 * max(drawdown_risk_score - drawdown_risk_allowance, 0)
  + 1.00 * max(drawdown_risk_score - 1.25, 0)
```

含义：

- `mean` 代表整体时间块平均收益，是 v29 主方向。
- `median` 代表大多数时间块表现。
- `p25` 代表偏差但常见的弱块表现。
- `min` 只做诊断，不进入主分，避免单个坏块把研究器引向“少交易少亏”的局部解。
- 持仓覆盖先过硬 gate：train/val 持仓覆盖都必须至少 `5%`；低于这条线直接不合格。月开仓数只做诊断，不进入主分。
- buy&hold 只在自身稳健分为正时形成轻量扣分，避免研究器只学到“顺市场裸多”。
- 回撤惩罚只扣超过持仓覆盖容忍线的部分；严重回撤仍重罚。鲁棒性、费用和过拟合惩罚都是轻量软约束。

## Gate

当前 gate 保留安全和明显失真类限制：

- 爆仓数量必须为 `0`。
- 手续费拖累不能超过 `MACD_V2_MAX_FEE_DRAG_PCT`。
- train+val 严重集中度过拟合仍会直接淘汰。
- train/val 持仓覆盖任一低于 `5%` 直接失败。
- 启用 `MACD_V2_ENFORCE_LONG_ONLY_GATE=1` 后，val short 非加仓开仓数大于 `0` 会失败。
- 启用 `MACD_V2_ENFORCE_LONG_ONLY_GATE=1` 后，train+val short 非加仓开仓数大于 `0` 会失败。

以下内容只做诊断，不再作为硬 gate：

- capture / capture_core。
- val 趋势命中率。
- 多空趋势捕获。
- val 趋势分块。
- 交易数量本身。
- 月非加仓开仓频率。

当前默认画像是阶段性 `long-only / flat` BTC 上涨捕获器，不是多空均衡器。研究重点是 long 在震荡或低趋势环境里识别向上释放、EMA 区域回踩再站上、趋势二次加速，并在趋势仍有效时拿住；不要因为 bear capture 弱就恢复 short。

planner 默认用中到大步长探索：优先换真实交易路径、slot 层、choke point、规则链或最终放行层。小幅阈值修正只有在能明确改变真实交易路径、漏斗节点或持仓行为时才算有效研究动作。

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

## 持仓覆盖与交易频率

交易频率按非加仓开仓数计算，加仓不计入。

- 目标区间可参考约 `10-15` 笔/月。
- 当前月开仓数只做诊断，不进入主分，也不是硬 gate。
- 不要为了刷交易次数制造无收益短交易。

持仓覆盖是当前参与度主指标：

```text
exposure_multiplier:
0%  -> 0.00
5%  -> 0.25
8%  -> 0.45
12% -> 0.75
16%及以上 -> 1.00
```

持仓覆盖率按“至少有一个仓位存在的时间 / 区间总时间”计算；多仓重叠只算一次，不会因为并行仓位重复加总。目的不是刷交易数，而是避免“开仓数够但大部分时间空仓”的局部解。

## Regime Scorecard

Regime scorecard 是解释工具，用来帮助 planner 判断动量在什么环境有效，不直接进评分或 gate。

`行情标签诊断` 是更宽的回测解释层，也不进入 `promotion_score`、gate 或策略输入。它基于回测后的日线 equity curve 和市场 close，结合 ADX、CHOP、ATR、方向效率、段内回撤和单日贡献，把 train/val 拆成主升浪、快速拉升、可交易震荡上行、普通震荡、高波动乱震、脉冲回落、普通回调、大幅回调、阴跌等标签。planner 只看到 train/val 的标签表现和当前 stage 的标签短板历史；test 标签只用于人工只读观察。

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

capture 仍保留，因为它能解释策略是否真正抓到了明显趋势，但它不再决定主分，也不作为 planner 默认施力方向。

- 趋势段仍使用固定 clean trend segments，仅用于解释。
- train/val 抓取分仍是“段等权均分 50% + 原权重均分 50%”，只做兼容展示。
- bull 和 bear 都只奖励账户正收益。
- `capture_core` 只提示 train/val 或多空是否偏科。

如果 capture 很低但稳健时间块表现好，候选仍可晋升；如果 capture 很高但多数时间块表现差，主分不会被 capture 拉起来。

过拟合保护现在以稳健收益块分布、正收益集中度和覆盖率为主；capture 落差和多空 capture 偏科只做提示，不再直接构成淘汰理由。

## 多空画像

当前研究画像是阶段性 `long-only / flat`。

- short 入场权限关闭；val 与 train+val short 非加仓开仓数必须为 `0`。
- short 占比和多空 capture 只做诊断，不进入主评分。
- short 退出和风控代码保留，只用于安全处理历史或异常 short 持仓。
- reviewer 会打回恢复 short、放宽 short context 或延长 short 持仓来追分的方案。

## 仓位规则

当前仓位规则固定在执行层，不再作为研究器自由参数。

- 标的是 BTC-USDT-SWAP，杠杆固定 `20x`。
- 仓位金额使用保证金口径，不是名义价值口径；名义仓位约为保证金的 `20` 倍。
- 首仓保证金 = 当前账户净值的 `10%`。
- 加仓仍作用在同一笔 trade 上，每次新增当时账户净值的 `5%` 保证金。例如本金 `10`，首仓 `1.0`；第一次加仓再加 `0.5`。如果账户净值涨到 `20`，下一次加仓再加 `1.0`。
- 半退关闭；策略只能通过止损、趋势失效、追踪、时间退出或其它完整退出信号一次性离场。
- `position_fraction`、`position_size_min`、`position_size_max`、`max_concurrent_positions`、`pyramid_size_ratio` 和各类 `tp1_close_fraction` 不再让研究器调。回撤控制由评分机制和退出逻辑承担。

## 人工边界

- 不把 test 或 demo 判断写入 planner prompt。
- 不让 planner 直接优化 test。
- demo 是否值得跑，由人工基于 test、图表、实盘壳子和风险承受单独判断。
- Funding 覆盖仍是数据源缺口；最终实盘前用长时间 demo run 验证。
