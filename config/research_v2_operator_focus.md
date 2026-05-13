# 研究器人工方向卡

这份文件只提供软引导，不是硬限制。若当前真实诊断与这里冲突，一律以真实诊断为准。

## 优先方向

- 当前评分口径是 `robust_block_v26_activity_mean`。
- 这张卡是长期方向卡，不绑定 champion hash；当前 prompt 里的 active reference 分数永远以运行器实时注入为准。
- 当前 active reference hash 是 `660e09d6e45e3ac676d54fcbd912853705eac2e9b0deffab3fdf63b9b9581409`；v26 下 `promotion_score=-0.3568`，`main_score=-0.0815`，`train/val robust block=0.0383/-0.1732`。
- 当前策略主框架已硬锁。研究器只能改既有 `PARAMS`、开放 `EXIT_PARAMS`、`FACTOR_SLOT_PARAMS` 和固定 `_slot_*()` 函数体；不能新增 helper、slot、参数 key，不能改 `_strategy_core()`、候选选择顺序或入口签名。
- 当前交易量已经接近或高于目标：train/val 月非加仓开仓约 `14.06/19.43`，activity multiplier 约 `0.972/1.000`。下一步不要继续单纯刷数量，应改善 val 负收益块和回撤。
- 当前研究重点从固定单边趋势捕获，改为多数时间块都能稳健赚钱。优先看 `train_robust_block_score`、`validation_robust_block_score`、`main_score` 和 `promotion_score`。
- `main_score = activity_adjusted_robust_time_score - benchmark_hurdle_score`。train/val 各自 28 天收益块用 mean/median/P25 聚合，min 只做诊断；正收益再按月非加仓开仓频率打倍率。
- `promotion_score = main_score - drawdown_penalty_score - robustness_penalty_score - trade_idle_penalty`。交易数短缺不再重复扣分，趋势机会覆盖短缺只做诊断。
- `capture_score` / `capture_core` 只做趋势诊断，不进入主评分，也不再给收益做倍率。不要围绕固定 clean trend segments 过拟合。
- 交易量目标已经明确：按非加仓开仓数计，目标大约是 `10-15` 笔/月，`7` 笔/月以下偏负面，`5` 笔/月以下不可接受。不要为了刷数量制造无收益短交易。
- Regime scorecard 只作为解释工具，帮助判断“什么环境适合动量、什么环境应该缩手”。可优先观察 ADX/CHOP/ATR、flow imbalance、成交量代理、Fear & Greed 与价格自身波动。
- Fear & Greed 情绪可作为策略输入，但只应作为环境过滤或确认信号；不要为了情绪字段本身堆规则。
- 数值参数步长是高优先级软约束，不是技术 gate：默认避免近邻阈值微调；如果需要小步长参数修正，必须说明它会改变哪条真实交易路径、漏斗节点或持仓管理行为。参数小改不会被技术拒收，但 smoke 行为不变仍会被拒收。
- 新增或启用因子前，先删除、合并或替换旧条件；如果 slot 复杂度接近 warning，需要优先瘦身再加因子。
- 如果系统提示本轮是“结构自检修复轮”，本轮目标不是追分，而是判断是否某个 slot、规则链或局部阶段过度学习；只能删减、合并、参数化泛化或移除无效分支。
- `exit_range_scan` 只用于单个连续型 `EXIT_PARAMS` 的轻量预筛，不要把它当网格搜索。

## 降权方向

- 降权继续优化固定趋势段 capture，却不能改善多数时间块收益分布的方案。
- 降权只在旧路径上做近邻阈值拨动；这类改动即使能通过源码校验，也很容易因为没有真实行为变化而被拦住。
- 降权主要研究 trailing、profit protect、holding time 这类纯退出微调；只有真实诊断明确说明主堵点在退出层时才继续。
- 降权把“提高交易量”理解成单纯放松所有入场 gate。需要提高有效交易覆盖，同时控制手续费拖累和回撤。
- 降权主要让 train 或 val 其中一边变热、另一边继续很弱的方案。
- 降权只增加局部分支、但不明显改变最终交易路径的改动。
- 降权试图修改主框架、候选生成顺序、slot 名称或入口函数的方案；这类方案会被硬校验拒绝。

## 默认动作

- 默认先看真实漏斗，找到限制有效入场的 choke point，再决定改哪一层。
- 默认按环境分层思考动量：趋势强且不拥挤时追踪，震荡、流量不足或情绪极端反转风险高时缩手或等待确认。
- 默认先看固定 slot 哪一层卡住：`regime_*`、`long_*`、`short_*` 或退出参数；不要直接改主编排。
- 默认把每轮改动做成一个可证伪假设：改哪条路径、期望改善哪些 28 天收益块、预期 train/val 哪个指标变化。
- 若 smoke 行为不变，下一轮优先换机制层、换 choke point 或换最终交易路径，不要继续在同一层横移。
- 若要调整参数，必须用中等步长；小幅微调不是有效研究动作。
