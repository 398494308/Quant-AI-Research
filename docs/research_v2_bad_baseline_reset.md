# Research V2 Bad Baseline Reset

这份文档记录“重新从很差但 gate 通过的基底开始”的默认策略。目的不是选一个好策略，而是避免研究器在高分局部平台上继续做小幅抖动。

## v26 选基底原则

v26 的主评分是活跃度调整后的稳健时间块收益，所以烂基底也应按这个口径选择。不要再按旧的 capture 倍率或固定趋势段主分选基底。

优先选择同时满足这些条件的历史候选：

- gate 能通过，没有爆仓和严重费用失真。
- `main_score`、`robust_time_score`、`train_robust_block_score`、`validation_robust_block_score` 都偏低，给研究器留出明显增长空间。
- 交易量不要太低：非加仓开仓频率最好接近 `10-15` 笔/月，低频会通过 activity multiplier 折扣正收益。
- 策略结构不要太复杂，避免新 session 被一大堆旧分支锁住。
- 不选择靠单一大行情或单边暴利撑起来的候选。

## 历史候选

历史第 30 轮 `planner_040` 的 `bc1b...` source 已在 `2026-05-12 23:22`（Asia/Shanghai）迁移到固定因子槽结构，并被替换为当前 active champion。迁移版保留旧普通回测入口的交易行为口径，同时锁住主框架，让研究器只改参数和固定 slot。

| 项目 | 值 |
| --- | --- |
| candidate | `planner_040` |
| iteration | `30` |
| original code hash | `bc1b2137aba6bb103357ac12394825cc1739b6e4f8c96c2e5831c32192468e6f` |
| structured code hash | `660e09d6e45e3ac676d54fcbd912853705eac2e9b0deffab3fdf63b9b9581409` |
| source snapshot | `backups/research_v2_round_artifacts/sources/bc/bc1b2137aba6bb103357ac12394825cc1739b6e4f8c96c2e5831c32192468e6f.py` |
| v26 gate | 通过 |
| promotion_score | `-0.3568` |
| main_score / robust_time_score | `-0.0815 / -0.0680` |
| train/val robust block | `0.0383 / -0.1732` |
| train/val activity multiplier | `0.9720 / 1.0000` |
| benchmark_hurdle_score | `0.0136` |
| drawdown / robustness / idle penalty | `0.1753 / 0.0000 / 0.1000` |
| capture_score / capture_core_score | `0.0273 / 0.0138` |
| train / val 非加仓开仓 | `254 / 233` |

保留它作为候选的原因：

- 已知能跑完整评估并通过基础 gate。
- gate 通过，且固定框架已锁住，适合作为结构化研究起点。
- v26 下重算后仍应保留明显增长空间。
- 交易量明显偏低时，后续研究应优先在固定 slot 内提高有效交易覆盖，而不是新增平行路径刷数量。

它不是永久指定基底。如果后续又进入局部平台，可以重新从历史记录里找更差的 gate 通过候选。

## 重置流程

1. 停止研究器。
2. 选择一个 v26 下低分但 gate 通过的 source snapshot。
3. 将 source snapshot 写入 `src/strategy_macd_aggressive.py`。
4. 按当前固定因子槽结构迁移，不改主框架。
5. 用 `--reset-champion --no-optimize` 重建 active reference。
6. 重置 stage/session。
7. 启动研究器。
8. 更新本文档和 `config/research_v2_operator_focus.md`，写明新基底 hash 和选择理由。

## 评分检查

重置后至少确认这些指标：

- `score_regime` 必须是 `robust_block_v26_activity_mean`。
- `promotion_score` 低，且主要增长空间来自 `main_score`。
- `train_robust_block_score` 和 `validation_robust_block_score` 都不高。
- `benchmark_hurdle_score` 没有异常放大。
- `drawdown_penalty_score`、`robustness_penalty_score`、`trade_idle_penalty` 不应单项压过主分太多。
- `capture_score` 和 `capture_core` 只作为诊断参考，不作为选基底主理由。

## 注意

- `test` 只做人工只读观察，不进入 planner prompt、评分或晋升。
- 不要把“test 差”写进方向卡让模型直接优化 test。
- 重新换基底后，文档和 `operator_focus` 必须同步改成新的 active reference 状态。
