# MACD Aggressive Current State

## 当前主线

- 仓库：`test3`
- 研究器：`scripts/research_macd_aggressive_v2.py`
- 策略：`src/strategy_macd_aggressive.py`
- 回测器：`src/backtest_macd_aggressive.py`
- 当前评分口径：`trend_capture_v5`

## 当前时间切分

- `development`
  `2023-07-01` 到 `2024-12-31`

- `validation`
  `2025-01-01` 到 `2025-12-31`

- `test`
  `2026-01-01` 到 `2026-03-31`

当前默认是：

- `28` 天开发窗口
- `21` 天步长
- `development` 内做 walk-forward
- `validation` 和 `test` 都是单段连续窗口

## 当前评分结构

单段分数：

- `period_score = 0.70 * trend_capture_score + 0.30 * return_score`

研究器主分：

- `quality_score`
  开发期滚动窗口的均值分

- `promotion_score`
  验证集单段连续分

隐藏验收：

- hidden `test` 只在新 best 时评估
- hidden `test` 不参与 `quality_score`
- hidden `test` 不参与 `promotion_score`
- hidden `test` 不会进入 prompt 和记忆表

## 当前 gate

主 gate 现在重点看：

- 开发期滚动均值分
- 开发期滚动中位分
- 开发期滚动波动
- 开发期盈利窗口占比
- 验证集趋势段数
- 验证集命中率
- 验证集趋势捕获分
- 开发期与验证集的分差
- 验证集多头捕获
- 验证集空头捕获
- 验证分块稳健性
- 手续费拖累
- 验证期多空交易支持

过拟合集中度仍会诊断，但现在主要用于提示和历史降权参考。

## 当前 prompt 结构

当前 prompt 顺序：

1. 策略目标
2. 思考框架
3. 当前诊断
4. 记忆使用规则
5. 历史研究记忆
6. 探索与防重复规则
7. 硬约束
8. 输出要求

当前 prompt 的关键点：

- 不再内嵌完整策略源码
- memory rule 与 journal 相邻
- validation 聚合诊断可见
- hidden test 完全不可见
- 最近轮次拆成“核心指标表 + 元信息摘要”
- 防重复规则只保留一份，不再多处复写

## 当前 Discord 口径

Discord 现在优先播报：

- `选择期连续收益`
- `验证连续收益`
- 新 best 时额外播报 `隐藏测试连续收益`

然后再播报：

- 开发滚动分
- 验证晋级分
- 开发/验证分差
- 验证到来/陪跑/掉头
- 验证多/空捕获
- 验证命中率/趋势段
- 验证多/空平仓数
- 验证三分块稳健性
- 选择期连续诊断

## 当前运行保护

- `smoke` 先跑少量窗口
- 候选报错时会在同一轮 repair
- `duplicate source / duplicate hash / empty diff` 会写入 journal
- heartbeat 会写出当前阶段和窗口名
- provider timeout 默认 `600s`

## 当前需要注意

- 这是一次新的评分 regime 切换，旧 `trend_capture_v4` 历史不会再作为主参考。
- 新 regime 下的 best 会在研究器下一次初始化或下一轮运行后重新沉淀。
- 如果要看现在的真实基线，请直接跑：

```bash
python3 scripts/research_macd_aggressive_v2.py --no-optimize
```
