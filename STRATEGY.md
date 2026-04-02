# 激进版 MACD 趋势策略

## 策略定位

这是当前 `test2` 仓库实际运行的激进型 BTCUSDT 永续合约趋势研究版本。它的目标不是做低波动权益曲线，而是在可接受高回撤和一定爆仓风险的前提下，尽量放大趋势段收益。

- 标的：`BTCUSDT` 永续合约
- 执行周期：15 分钟
- 过滤周期：1 小时 + 4 小时
- 默认杠杆：`15x`
- 最大并发：`5`
- 当前研究循环间隔：`60` 秒

## 当前真实信号

当前 `src/strategy_macd_aggressive.py` 实际只输出两个信号：

1. `long_breakout`
   15 分钟、1 小时、4 小时三周期共振向上后，价格向上突破近期高点时开多。
2. `short_breakdown`
   三周期共振向下后，价格向下跌破近期低点时开空。

说明：

- 回测引擎仍保留了按信号差异化退出的扩展接口。
- 但当前版本没有启用 `long_pullback` 和 `short_bounce_fail` 入场逻辑，文档与评估应以这两个有效信号为准。

## 入场逻辑

策略使用三层过滤：

1. 15 分钟执行层
   通过 EMA 结构、MACD 方向、ADX 强度确认短线趋势。
2. 1 小时趋势层
   用 EMA 锚点、EMA 结构、MACD 方向和 ADX 确认主趋势。
3. 4 小时环境层
   进一步确认大级别方向，减少逆势追单。

触发条件还会叠加：

- 近端突破 / 跌破窗口
- K 线实体占比
- 收盘位置
- 成交量相对均量
- RSI 区间
- MACD 柱值阈值

## 当前核心优化参数

系统已把 AI 可调参数压缩到 12 个，避免大规模自由调参导致过拟合。

### 入场 6 个

- `macd_fast = 5`
- `macd_slow = 16`
- `macd_signal = 3`
- `hourly_adx_min = 12.8`
- `breakout_lookback = 21`
- `breakdown_lookback = 26`

### 出场 6 个

- `leverage = 15`
- `position_fraction = 0.19`
- `stop_atr_mult = 3.0`
- `stop_max_loss_pct = 53.0`
- `tp1_pnl_pct = 46.0`
- `trailing_activation_pct = 88.0`

除了这 12 个核心参数，其他参数在自动研究循环中默认固定不动。

## 退出与风控

当前退出系统以“高杠杆、宽止盈、允许利润奔跑”为主，包含以下组件：

- 固定 ATR 止损
- 单笔最大亏损上限
- 首次止盈 `TP1`
- 追踪止盈激活与回撤退出
- 保本移动止损
- 动态持仓时长
- 趋势失效退出
- 金字塔加仓
- 手续费与资金费率计入收益

当前默认风险参数：

- 杠杆：`15x`
- 单仓保证金占比：`19%`
- 单仓最小保证金：`5000 USDT`
- 单仓最大保证金：`30000 USDT`
- 最大并发仓位：`5`
- 最大允许单笔亏损：`53%`
- 默认 TP1：`46%`
- 默认 trailing 激活：`88%`
- 允许金字塔加仓，最多 `3` 次

## 数据窗口

当前研究循环不再按自然月切分，而是按连续 `20` 天时间块顺序切分：

```text
训练:
前 5 个时间块

验证:
接下来的 2 个时间块

影子测试:
最后 2 个时间块
```

这样做的原因是避免自然月边界对结果造成过大影响，同时让样本数明显多于按月切分。
影子测试只用于外层拦截，不参与给优化模型的反馈。

## 当前评分方式

研究循环的最终选优，已经不再直接使用单窗口回测结果中的内部 `result["score"]`。当前采用两层外部评分：

```python
selection_score =
    train_avg * 0.35
  + val_avg * 0.65
  - max(0, train_avg - val_avg) * 0.90
  - val_std * 0.18
  - max(0, -worst_val_return) * 0.35
  - max(0, train_std - max(10, val_std + 6)) * 0.05
  - max(0, worst_drawdown - 55) * 0.22
  - liquidations * 1.5

promotion_score =
    selection_score
  - max(0, val_avg - test_avg) * 0.15
  - max(0, -test_avg) * 0.10
```

设计含义：

- 训练和验证一起决定主选优分，但验证权重更高。
- 训练明显强于验证时，直接按过拟合差惩罚。
- 验证集波动越大、最差验证月越差，扣分越重。
- 回撤超过 `55%` 后开始软惩罚。
- 爆仓次数直接扣分。
- 影子测试只在晋级层参与，避免 AI 直接围绕最新时间块反复磨分。

## 当前 Gate

候选参数只有同时满足以下条件，才有资格成为“最优基底”：

- 总交易数 `>= 30`
- 训练集交易数 `>= 15`
- 验证集交易数 `>= 8`
- 影子测试交易数 `>= 8`
- 最大回撤 `<= 65%`
- 爆仓次数 `<= 10`
- 过拟合差 `train_avg - val_avg <= 25`
- 验证集平均收益 `> 0`
- 影子测试平均收益 `>= 0`
- 杠杆 `>= 14x`
- `tp1_pnl_pct >= 42`
- `验证均值 - 影测均值 <= 28`
- 新冠军的影测收益不能比当前最优基底差超过 `6` 分

只有 `Gate 通过` 且 `promotion_score` 高于当前最优，新的参数才会被正式保留。

## 防重复探索机制

当前重复探索拦截已经前移到回测前，流程如下：

1. AI 基于当前最优参数和历史结果提出候选参数。
2. 系统只保留局部微调：
   - 默认最多改 `6` 个键
   - 单键改动通常不超过当前值的 `15%`
3. 系统计算本轮改动签名：
   - 精确签名：具体哪些参数从什么值改到什么值
   - 方向签名：参数是向上还是向下改
4. 若命中最近记忆中的精确重复或方向重复：
   - 不进入回测
   - 直接把“这个方向已经重复过，可能没有重复探索价值”的提醒反馈给 AI
   - 最多重规划 `2` 次
5. 若连续重规划仍重复，本轮直接跳过。

记忆结构：

- `accepted` 最近 16 条
- `rejected` 最近 16 条

这样做的目标是让 AI 在开始新一轮前，先知道某个方向已经试过且效果差，避免浪费回测轮次。

## 平台期增强搜索

如果连续多轮出现“通过 Gate 但没有刷新最优”的情况，优化器会进入增强模式：

- 默认阈值：连续 `6` 轮
- 允许改动数从 `6` 提高到 `8`
- 单键相对步长上限从 `15%` 提高到 `22%`

这样做是为了在局部微调长期无效时，主动扩大一点搜索半径，但仍然保持在受控范围内。

## 自动研究链路

当前整体链路是：

1. 读取当前最优基底参数
2. 汇总最近评估摘要和 accepted / rejected 历史方向
3. 让 AI 只在 12 个核心参数内生成局部新候选
4. 在回测前做重复方向检查
5. 对连续 `20` 天块跑完整回测
6. 只把训练/验证摘要喂给 AI，影子测试结果留在外层
7. 计算 `selection_score`、`promotion_score` 和 Gate
8. 更优则写回为新基底并发 Discord
9. 不够优则回滚代码，并把结果记入坏样本或普通历史记忆

## 关键文件

```text
src/strategy_macd_aggressive.py      入场信号
src/backtest_macd_aggressive.py      回测与退出逻辑
src/openai_strategy_client.py        OpenAI Responses API 客户端
scripts/research_macd_aggressive.py  自动研究循环
docs/program_macd_aggressive.md      给优化器的目标约束
state/optimizer_memory_macd_aggressive.json  历史方向记忆
state/research_macd_aggressive_heartbeat.json  运行心跳
logs/macd_aggressive_research.log    研究日志
```

## 常用命令

单次仅回测当前参数：

```bash
python3 scripts/research_macd_aggressive.py --once --no-optimize
```

单次跑一轮优化：

```bash
python3 scripts/research_macd_aggressive.py --once
```

启动常驻研究循环：

```bash
bash scripts/manage_research_macd_aggressive.sh start
```

查看日志：

```bash
tail -f logs/macd_aggressive_research.log
```

## 结论

这套系统当前已经从“多参数大范围乱搜”收缩到“12 个核心参数的激进型局部优化”。它更适合先在研究环境中持续迭代，再把通过验证、回撤和重复方向筛选后的参数，拿去做下一阶段的实盘测试。

## 免责声明

本策略仅供学习研究使用，不构成投资建议。加密货币交易风险极高，请勿使用超过承受能力的资金。历史回测表现不代表未来收益。

---

**最后更新**: 2026-04-02
**策略版本**: v2.0-aggressive
**优化模型**: GPT-5.4
