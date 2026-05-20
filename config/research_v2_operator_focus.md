# 研究器人工方向卡

这份文件只提供软引导，不是硬限制。若当前真实诊断与这里冲突，一律以真实诊断为准。

## 优先方向

- 当前评分口径是 `robust_block_v29_return_holding_penalty`。
- 这张卡是长期方向卡，不绑定 champion hash，不保存静态 champion 分数；当前 active reference、分数、交易量、回撤和短板永远以运行器每轮实时注入的诊断为准。
- 当前刚换成 10% 首仓、5% 加仓、关闭半退的手搓低分 long-only 结构化基底并重置 stage/session；当前 active reference hash 是 `6e38eb4ea3568f20cfecc0d74229fc2301ebfc7b38c301c8daa1b07814cfa7ca`。不要沿用换基底前的旧 champion 叙事、旧 1/4 仓位口径或旧局部路线，先看本轮实时评分拆解、漏斗和交易路径。
- 当前基底故意很弱：它只负责过 gate 和提供足够交易样本，当前短板包括 val 亏损、费用拖累、回撤和弱块收益。不要把它的参数当成优秀经验继承。
- 当前策略主框架已硬锁。研究器只能改既有 `PARAMS`、开放 `EXIT_PARAMS`、`FACTOR_SLOT_PARAMS` 和固定 `_slot_*()` 函数体；不能新增 helper、slot、参数 key，不能改 `_strategy_core()`、候选选择顺序或入口签名。
- 如果想法点名锁区 helper，必须先翻译到可改空间：优先落到对应 `_slot_*()`、`PARAMS`、`EXIT_PARAMS` 或 `FACTOR_SLOT_PARAMS`，不要直接把锁区 helper 当行动目标。
- 当前策略方向是价格结构优先：前高附近向上释放、EMA 区域回踩再站上、强趋势二次加速。ADX/CHOP/ATR、成交量和 flow 用作环境与质量过滤；MACD 只做后置确认，不应重新变成主驱动。
- 当前研究重点从固定单边趋势捕获，改为多数时间块都能稳健赚钱。优先看 `train_robust_block_score`、`validation_robust_block_score`、`return_score`、`holding_time_score`、`penalty_score` 和 `promotion_score`。
- `return_score = robust_time_score - benchmark_hurdle_score`。train/val 各自 28 天收益块用 mean/median/P25 聚合，min 只做诊断；正向 buy&hold 稳健分按 `0.25` 形成轻量基准扣分。
- `promotion_score = return_score + holding_time_score - penalty_score`。`holding_time_score` 只做小额辅助，鼓励足够持仓覆盖，低覆盖扣分、过度接近 buy-and-hold 轻扣；`penalty_score` 是回撤、鲁棒性、手续费拖累和过拟合软惩罚加总。
- `capture_score` / `capture_core` 只做低优先级趋势诊断，不进入主评分，也不再给收益做倍率。不要围绕固定 clean trend segments 或 bull/bear capture 追分。
- 持仓覆盖先过硬 gate：train/val 持仓覆盖都必须至少 `5%`；月非加仓开仓频率只做诊断，不进入主分，也不要为了刷数量制造无收益短交易。持仓覆盖率约 `16%` 起视为充分参与行情。
- 当前阶段使用 `long-only / flat` 硬 gate：val 与 train+val 的 short 非加仓开仓数都必须为 `0`；只要出现 short 新开仓，候选不能晋级。short 不是本阶段的研究目标。
- 仓位规则固定为 BTC 20x 保证金口径：首仓当前净值 `10%` 保证金，每次加仓新增当时净值 `5%` 保证金，加仓作用在同一笔 trade 上，不新建独立仓位；半退关闭，只能通过止损、趋势失效、追踪、时间退出或其它完整退出信号一次性离场。仓位比例、并发仓、单仓上下限、加仓比例和半退比例不是研究器优化项。
- 是否需要继续补参与度，只看本轮实时注入的 train/val 持仓覆盖率、持仓时间分和漏斗；月频只判断交易形态，不作为追分目标。
- Regime scorecard 只作为解释工具，帮助判断“什么环境适合动量、什么环境应该缩手”。可优先观察 ADX/CHOP/ATR、flow imbalance、成交量代理、Fear & Greed 与价格自身波动。
- `行情标签诊断` 只做回测后解释，不进评分、不做 gate、不作为策略输入。它把 train/val 拆成主升浪、快速拉升、可交易震荡上行、普通震荡、高波动乱震、回调等行情，帮助判断策略是错过机会还是错误参与；test 标签只供人工只读观察。
- 默认策略画像是阶段性 `long-only / flat`。优先研究震荡或低趋势环境里如何抓住向上释放、回调再上行的 long 路径，而不是把震荡过滤成长期空仓。
- short 入场权限暂时关闭；short 相关逻辑只保留退出和风控安全层。bear/downside 表现只用于解释风险、回撤和空仓质量，不作为恢复 short 的理由。
- 如果候选尝试恢复 short、放宽 short context、延长 short 持仓，或围绕 short capture 追分，默认降权并要求重写；当前只看 long 主线。
- Fear & Greed 情绪可作为策略输入，但只应作为环境过滤或确认信号；不要为了情绪字段本身堆规则。
- 数值参数步长是高优先级软约束，不是技术 gate：默认用中到大步长，优先换真实交易路径、slot 层、choke point、规则链或最终放行层；如果需要小步长参数修正，必须说明它会改变哪条真实交易路径、漏斗节点或持仓管理行为。参数小改不会被技术拒收，但 smoke 行为不变仍会被拒收。
- 新增或启用因子前，先删除、合并或替换旧条件；如果 slot 复杂度接近 warning，需要优先瘦身再加因子。
- 如果系统提示本轮是“结构自检修复轮”，本轮目标不是追分，而是判断是否某个 slot、规则链或局部阶段过度学习；只能删减、合并、参数化泛化或移除无效分支。
- `exit_range_scan` 只用于单个连续型 `EXIT_PARAMS` 的轻量预筛，不要把它当网格搜索。

## 降权方向

- 降权继续优化固定趋势段 capture，却不能改善多数时间块收益分布的方案。
- 降权只在旧路径上做近邻阈值拨动；这类改动即使能通过源码校验，也很容易因为没有真实行为变化而被拦住。
- 降权主要研究 trailing、profit protect、holding time 这类纯退出微调；只有真实诊断明确说明主堵点在退出层时才继续。
- 降权把“提高参与度”理解成单纯刷开仓数。需要提高有效持仓覆盖和上涨段持有质量，同时控制手续费拖累和回撤。
- 降权只因为 bear/downside 表现弱就机械恢复 short 的方案。
- 降权让 short 成为交易来源的方案；当前 short 入场权限关闭。
- 降权主要让 train 或 val 其中一边变热、另一边继续很弱的方案。
- 降权只增加局部分支、但不明显改变最终交易路径的改动。
- 降权试图修改主框架、候选生成顺序、slot 名称或入口函数的方案；这类方案会被硬校验拒绝。

## 默认动作

- 默认先看真实漏斗，找到限制有效入场的 choke point，再决定改哪一层。
- 默认按环境分层思考动量：趋势强且不拥挤时追踪，震荡、流量不足或情绪极端反转风险高时缩手或等待确认。
- 默认把“会处理震荡”推进为“在震荡中识别向上释放并做 long”，而不是继续依靠 short 或长期空仓回避震荡。
- 默认优先修复“交易质量”而不是继续放大交易量；当前基底已为过 gate 牺牲了质量，后续需要用结构、flow、波动和退出把亏损交易删掉或拿住上涨段。
- `_slot_long_veto()` 只做负向过滤，不再藏趋势质量硬门；如果要收紧 long，优先在 `long_context`、`long_breakout`、`long_pullback` 或退出层做有名有姓的调整。
- 默认先看固定 slot 哪一层卡住：`regime_*`、`long_*`、`short_*` 或退出参数；不要直接改主编排。
- 默认把每轮改动做成一个可证伪假设：改哪条路径、期望改善哪些 28 天收益块、预期 train/val 哪个 robust block、持仓覆盖、费用或惩罚项如何变化。
- 若 smoke 行为不变，下一轮优先换机制层、换 choke point 或换最终交易路径，不要继续在同一层横移。
- 若要调整参数，默认用中到大步长；小幅微调只有在能明确改变真实交易路径、漏斗节点或持仓行为时才算有效研究动作。
