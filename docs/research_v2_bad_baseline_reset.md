# Research V2 Bad Baseline Reset

这份文档记录“重新从很差但 gate 通过的基底开始”的默认策略。目的不是选一个好策略，而是避免研究器在高分局部平台上继续做小幅抖动。

## v29 选基底原则

v29 的主评分拆成 `return_score + holding_time_score - penalty_score`。烂基底也应按这个口径选择：收益主分要低但能完整评估，持仓覆盖至少过 gate，费用、回撤和过拟合不能失真。当前阶段是 `long-only / flat` 硬 gate：val 与 train+val 的 short 非加仓开仓数都必须为 `0`。不要再按旧的 capture 倍率、月开仓倍率或固定趋势段主分选基底。

优先选择同时满足这些条件的历史候选：

- gate 能通过，没有爆仓、严重费用失真或过拟合失真。
- 启用 long-only gate 后，候选必须满足 val 与 train+val short 非加仓开仓数为 `0`；short 入场权限关闭。
- `return_score`、`robust_time_score`、`train_robust_block_score`、`validation_robust_block_score` 都偏低，给研究器留出明显增长空间。
- 持仓覆盖不能太低：train/val 持仓覆盖低于 `5%` 会直接 gate fail。非加仓开仓频率最好有可观察样本，但只做诊断，不作为主分或硬 gate。
- 仓位规则固定为 BTC 20x 保证金口径：首仓当前净值 `10%` 保证金，每次加仓新增当时净值 `5%` 保证金，加仓作用在同一笔 trade 上；半退关闭，只能完整退出。不要用调仓位比例、加仓比例、半退比例、并发仓数或单仓上下限来选择基底。
- 策略结构不要太复杂，避免新 session 被一大堆旧分支锁住。
- 不选择靠单一大行情或单边暴利撑起来的候选。

## 历史候选

当前使用 `2026-05-18` 手搓 long-only 低分基底。它不是优秀策略，只是为了让研究器从一个过 gate、结构清晰、可删弱留强的起点重新搜索。主线是价格结构向上释放、EMA 区域回踩再站上、强趋势二次加速；ADX/ATR/CHOP、成交量和 flow 只做辅助，MACD 后置确认。short 退出和风控代码保留，short 入场关闭。仓位口径已更新为首仓 10% 保证金、每次加仓 5% 保证金、半退关闭。

| 项目 | 值 |
| --- | --- |
| candidate | manual low-score long-only baseline |
| iteration | manual reset on `2026-05-18` |
| code hash | `6e38eb4ea3568f20cfecc0d74229fc2301ebfc7b38c301c8daa1b07814cfa7ca` |
| structured snapshot | `src/strategy_macd_aggressive.py` / `backups/strategy_macd_aggressive_v2_best.py` |
| v29 gate | 通过 |
| promotion_score | `-0.9135` |
| return_score / robust_time_score | `-0.4195 / -0.4059` |
| train/val robust block | `-0.1274 / -0.6843` |
| benchmark_hurdle_score | `0.0136` |
| holding_time_score / penalty_score | `0.0000 / 0.4941` |
| drawdown / robustness / fee / overfit penalty | `0.4329 / 0.0032 / 0.0580 / 0.0000` |
| capture_score / capture_core_score | `-0.0329 / -0.0115` |
| train / val 非加仓开仓 | `314 / 168` |
| train / val 月非加仓开仓 | `17.38 / 14.01` |
| train / val 持仓覆盖 | `20.69% / 20.27%` |
| long-only gate | train+val 与 val short 非加仓开仓数均为 `0` |

保留它作为候选的原因：

- 已知能跑完整评估并通过基础 gate 与 long-only gate。
- 固定框架已锁住，适合作为结构化研究起点；后续候选必须保持 short 新开仓为 0 才能成为 champion。
- 分数足够低，主要增长空间来自交易质量、费用拖累、回撤和 val 弱块，而不是继续刷交易数量。
- 结构保持简单：三条 long 路径加一个 long veto，给 planner 在固定 slot 内删弱留强、重排阈值和改退出留出空间。

它不是永久指定基底。如果后续又进入局部平台，可以重新从历史记录里找更差的 gate 通过候选。

## 重置流程

1. 停止研究器。
2. 选择一个 v29 下低分但 gate 通过的 source snapshot。
3. 将 source snapshot 写入 `src/strategy_macd_aggressive.py`。
4. 按当前固定因子槽结构迁移，不改主框架。
5. 用 `--reset-champion --no-optimize` 重建 active reference。
6. 重置 stage/session。
7. 启动研究器。
8. 更新本文档和 `config/research_v2_operator_focus.md`，写明新基底 hash 和选择理由。

## 评分检查

重置后至少确认这些指标：

- `score_regime` 必须是 `robust_block_v29_return_holding_penalty`。
- `promotion_score` 低，且主要增长空间来自 `return_score`、持仓覆盖和惩罚项。
- `train_robust_block_score` 和 `validation_robust_block_score` 都不高。
- `benchmark_hurdle_score` 没有异常放大。
- `drawdown_penalty_score`、`robustness_penalty_score`、`fee_drag_penalty_score`、`overfit_penalty_score` 不应单项异常压过主分太多。
- `capture_score` 和 `capture_core` 只作为诊断参考，不作为选基底主理由。

## 注意

- `test` 只做人工只读观察，不进入 planner prompt、评分或晋升。
- 不要把“test 差”写进方向卡让模型直接优化 test。
- 重新换基底后，文档和 `operator_focus` 必须同步改成新的 active reference 状态。
