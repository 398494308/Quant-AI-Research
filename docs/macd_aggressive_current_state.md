# MACD Aggressive Current State

## 当前主线

- 仓库：`test3`
- 研究器：`scripts/research_macd_aggressive_v2.py`
- 策略：`src/strategy_macd_aggressive.py`
- 回测器：`src/backtest_macd_aggressive.py`
- 当前评分口径：`trend_capture_v6`
- 当前事实源：`15m`
- `1h` / `4h` 只是由 `15m` 聚合出来的确认层
- 成交量维度除了总量，还包含 `trade_count`、`taker_buy_volume`、`taker_sell_volume`

## 最新手工基底

- 更新时间：`2026-04-19`
- 当前已持久化到：
  - `src/strategy_macd_aggressive.py`
  - `backups/strategy_macd_aggressive_v2_best.py`
  - `state/research_macd_aggressive_v2_best.json`
- 当前 `baseline` 评估结果：
  - train 均值分：`0.2737`
  - train 中位分：`0.1526`
  - train 波动：`0.4144`
  - val 趋势分：`0.1549`
  - val 收益分：`0.0071`
  - val 多头捕获：`-0.0527`
  - val 空头捕获：`0.3558`
  - val 命中率：`39.29%`
  - 总交易数：`322`
- 当前 gate 仍未通过，原因是：
  - val 多头捕获略低于线

这版新基底的手工方向不是“继续堆更多 long”，而是：

- 保留原主吸收型 long 路径
- 给 long 加入更强的 flow / chop 环境过滤
- 保留 short 主框架不大动
- 用更干净的历史重新起跑，让研究器围绕这个基底继续找 gate 内解

## 当前时间切分

- `train`
  `2023-07-01` 到 `2024-12-31`

- `val`
  `2025-01-01` 到 `2025-12-31`

- `test`
  `2026-01-01` 到 `2026-03-31`

当前默认是：

- `28` 天 train 窗口
- `21` 天步长
- `train` 内做 walk-forward
- `val` 和 `test` 都是单段连续窗口

## 当前评分结构

单段分数：

- `period_score = 0.70 * trend_capture_score + 0.30 * return_score`

研究器主分：

- `quality_score`
  train 滚动窗口的均值分

- `promotion_score`
  val 单段连续分；只有先过 gate，才会拿它和当前 `champion` 比较

test 验收：

- `test` 只在新 `champion` 时评估
- `test` 不参与 `quality_score`
- `test` 不参与 `promotion_score`
- `test` 不会进入 prompt 和记忆表

## 当前 gate

主 gate 现在重点看：

- train 滚动均值分
- train 滚动中位分
- val 命中率
- val 趋势捕获分
- train 与 val 的分差
- val 多头捕获
- val 空头捕获
- val 分块最差块和负分块数量
- 手续费拖累

这些现在只做诊断，不再直接卡 gate：

- train 滚动波动
- train 盈利窗口占比
- val 趋势段数
- val 分块波动
- val 多空交易支持

过拟合集中度仍会诊断，但只有严重集中度会直接触发 gate veto；高风险轮次会继续在 journal 里降权。

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
- val 聚合诊断可见
- 当多空捕获明显失衡时，prompt 会追加“软偏置”提示，优先把探索预算投向更弱的一侧，而不是硬性锁死只看单边
- `test` 完全不可见
- 最近轮次拆成“核心指标表 + 元信息摘要”
- journal 里新增 `方向冷却表（系统硬约束）`
- 防重复规则只保留一份，不再多处复写
- `edited_regions` 最多 `1-3` 个，系统会用真实 diff / AST 派生的 `system signature` 复核
- prompt 里的可编辑区域已收紧到当前策略文件真实存在的 `6` 个区域

## 当前 Discord 口径

Discord 现在只保留：

- `数据范围`
- `本轮窗口`
- `train+val期间收益`
- `val期间收益`
- 新 `champion` 时额外播报 `test期间收益`
- `train+val交易数量`
- 新 `champion` 时额外播报 `test交易数量`
- `val多/空捕获`
- `最大回撤/手续费拖累`

## 当前运行保护

- `smoke` 先跑少量窗口
- `smoke` 通过后，还会比对候选和当前参考在 smoke 窗口里的行为指纹
- 如果收益、交易数、信号统计、退出原因和交易摘要完全一致，会按 `behavioral_noop` 直接跳过完整评估
- 候选报错时会在同一轮 repair
- 同簇低变化近邻会在评估前被系统拦截，不再白跑 `smoke/full eval`
- 被探索硬约束拦截后，会在同一轮里强制重生候选方向
- 同一方向簇再次触发该机制后，会进入短期冷却锁
- 冷却锁采用 `3 -> 6 -> 10` 轮递增
- 低变化近邻判定会同时看真实 diff、参数族变化和 AST 派生结构签名
- `duplicate source / duplicate hash / empty diff / behavioral_noop` 会写入 journal
- `exploration_blocked` 表示候选在评估前就被系统探索硬约束拒收
- heartbeat 会写出当前阶段和窗口名
- provider timeout 默认 `600s`

## 当前需要注意

- 这是一次新的评分 regime 切换，旧 `trend_capture_v4` 历史不会再作为主参考。
- 新 regime 下的 `champion / baseline` 会在研究器下一次初始化或下一轮运行后重新沉淀。
- 如果本地价格 CSV 还是旧格式，需要先重新运行 `python3 scripts/download_aggressive_data.py`，生成带 flow 列的新 `15m/1h/4h/1m` 数据。
- `scripts/research_macd_aggressive_v2.py` 的启动路径会把 `src/strategy_macd_aggressive.py` 从已保存 best 恢复回来。
- 所以如果只是想安全评估当前 `src`，不要直接跑 `--no-optimize`，请用下面这段：

```bash
python3 - <<'PY'
from pathlib import Path
import sys, importlib
sys.path.insert(0, str(Path('.').resolve()))
sys.path.insert(0, str(Path('src').resolve()))

import strategy_macd_aggressive as sm
import scripts.research_macd_aggressive_v2 as rs

importlib.reload(sm)
rs.strategy_module = sm
report = rs.evaluate_current_strategy()
print(report.summary_text)
PY
```

- 本轮已在 `2026-04-19` 做过一次彻底历史清理：
  - `state/research_macd_aggressive_v2_journal.jsonl` 已清空
  - `state/research_macd_aggressive_v2_journal.compact.json` 已清空
  - 原文件已按时间戳归档
