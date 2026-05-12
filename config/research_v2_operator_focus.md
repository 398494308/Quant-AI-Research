# 研究器人工方向卡

这份文件只提供软引导，不是硬限制。若当前真实诊断与这里冲突，一律以真实诊断为准。

## 优先方向

- 当前评分口径是 `trend_capture_v24_multiplicative_capture_core`。
- 当前 active reference 是历史第 30 轮 `planner_040` 重建出来的低分 champion，hash `bc1b2137aba6bb103357ac12394825cc1739b6e4f8c96c2e5831c32192468e6f`。
- 当前基底 gate 通过，但分数很低：`promotion_score=-0.3267`，`capture_score=0.0374`，`capture_core=0.0056`，`capture_return_multiplier=0.25`。
- 当前交易量已经足够：train/val 非加仓开仓约 `336/268`，月频约 `18.6/22.3`。不要把主要预算浪费在刷交易量。
- 当前核心短板是趋势捕获质量：train capture 为负，val capture 也不高；多空侧相对均衡但都弱。优先找能同时提高 train/val 连续趋势捕获的结构性规则。
- `capture_core = period_capture * side_multiplier`：period 看 train/val 是否都抓到，side 只在 bull/bear 偏弱时打折。不能只靠收益或单边强项刷新 champion。
- 收益补充分按 `capture_core` 连续调整：`0.03` 以下只释放 `25%`，`0.12` 附近回到 `1` 倍，超过后继续加成但边际递减。
- 数值参数有最小步长硬规则：`PARAMS` / `EXIT_PARAMS` 相对 active reference 改动太小会被拒收；bars/lookback/hold/period 类至少约 `15%` 且不少于 `4` 根，0 到 1 阈值至少 `0.01` 或 `8%`，小比例至少 `10%` 且不少于 `0.002`，其他百分比至少 `8%` 且不少于 `2` 点。
- `exit_range_scan` 只用于单个连续型 `EXIT_PARAMS` 的轻量预筛，扫描点也必须满足同一最小步长。
- Fear & Greed 情绪可作为策略输入，但只应作为环境过滤或确认信号；不要为了情绪字段本身堆规则。
- 策略复杂度当前是 `hard_cap` 诊断态；复杂度只提示，不自动拒收。后续应优先改旧逻辑、删旧条件、复用现有 helper，避免继续堆大块条件。

## 降权方向

- 降权只在旧路径上做近邻阈值拨动；这类改动现在大概率会被最小步长规则或行为检查拦住。
- 降权主要研究 `EXIT_PARAMS`、trailing、profit protect、holding time 这类纯退出微调；只有真实诊断明确说明主堵点在退出层时才继续。
- 降权把“提高 capture”理解成单纯放松所有入场 gate。需要提高真实趋势机会覆盖，同时控制手续费拖累和回撤。
- 降权主要让 train 或 val 其中一边变热、另一边继续很弱的方案。
- 降权主要强化单边收益、但 bull/bear 或 train/val 平衡没有改善的方案。
- 降权只增加局部分支、但不明显改变最终交易路径的改动。

## 默认动作

- 默认先看真实漏斗，找到限制有效入场的 choke point，再决定改哪一层。
- 默认优先解决 train capture 为负、连续趋势段命中不足、趋势跟随启动太慢或过早退出的问题。
- 默认把每轮改动做成一个可证伪假设：改哪条路径、期望增加哪些趋势段命中、预期 train/val 哪个指标变化。
- 若 smoke 行为不变，下一轮优先换机制层、换 choke point 或换最终交易路径，不要继续在同一层横移。
- 若要调整参数，必须用中等步长；小幅微调不是有效研究动作。
