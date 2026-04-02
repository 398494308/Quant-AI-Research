# 激进版 MACD 当前设定

## 定位

- 面向高风险、高回报场景
- 目标是提升趋势段收益弹性，而不是做平滑曲线
- 接受较高回撤，但研究循环会限制极端坏解进入最优基底

## 当前运行参数

- 杠杆：`15x`
- 最大并发：`5`
- 单仓保证金占比：`19%`
- 单仓最小保证金：`5000 USDT`
- 单仓最大保证金：`30000 USDT`
- 默认 TP1：`46%`
- trailing 激活：`88%`
- 最大亏损上限：`53%`

## 当前有效信号

- `long_breakout`
- `short_breakdown`

当前实现没有启用 `long_pullback` 和 `short_bounce_fail` 入场。

## 当前 12 个核心优化参数

入场参数：

- `macd_fast = 5`
- `macd_slow = 16`
- `macd_signal = 3`
- `hourly_adx_min = 12.8`
- `breakout_lookback = 21`
- `breakdown_lookback = 26`

出场参数：

- `leverage = 15`
- `position_fraction = 0.19`
- `stop_atr_mult = 3.0`
- `stop_max_loss_pct = 53.0`
- `tp1_pnl_pct = 46.0`
- `trailing_activation_pct = 88.0`

## 研究循环约束

- 每轮默认最多改动 `6` 个键
- 单键步长通常不超过当前值 `15%`
- 连续 `6` 轮通过但未刷新最优时，自动放宽到 `8` 个键和 `22%` 步长
- 研究循环间隔：`60` 秒
- 提供商故障恢复冷却：`60` 秒
- 普通失败冷却：`60` 秒

## 重复方向防护

- accepted / rejected 各保留最近 `16` 条方向记忆
- AI 提案在回测前先查重
- 如果命中精确重复或方向重复，会提示“这个方向已经重复过了，可能没有重复探索价值”
- 最多重规划 `2` 次，仍重复则直接跳过本轮
