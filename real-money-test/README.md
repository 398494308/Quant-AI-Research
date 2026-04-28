# real-money-test

这是本仓库内自洽的 `freqtrade` 交易壳子。

当前默认路径已经从本地 `dry-run` 切到 `OKX Demo Trading`：

- `demo`：默认推荐，用 OKX 模拟盘真实走交易所接口
- `dry-run`：代码保留，但不再默认使用
- `live`：只保留显式手动启动

## 当前目录

- `config.base.json`
  基础 `freqtrade` 配置，不含敏感信息
- `build_runtime_config.py`
  生成 `dry-run / demo / live` 三种运行时配置
- `pin_strategy.py`
  把人工指定版本冻结为 `demo` 固定策略副本
- `demo_monitor.py`
  监控 `demo` 进程、heartbeat，并发送关键事件播报
- `daily_report.py`
  生成 Discord 日报卡；`demo` 与旧 `dry-run` 复用同一频道配置
- `install_daily_report_cron.sh`
  安装或移除 `report / monitor` cron
- `manage.sh`
  统一入口，支持 `start/stop/restart/status/log`
- `start_demo.sh`
  启动 OKX Demo Trading
- `start_dry_run.sh`
  启动本地 dry-run，保留兼容
- `start_live.sh`
  启动 live，必须显式确认风险
- `strategies/MacdAggressivePinnedStrategy.py`
  `demo` 专用 `freqtrade` 策略入口，只加载固定副本
- `pinned/demo/`
  当前 `demo` 固定策略副本与元数据

## 凭证隔离

### `demo`

只认以下环境变量，不会回退到 live 凭证：

- `OKX_DEMO_API_KEY`
- `OKX_DEMO_API_SECRET`
- `OKX_DEMO_API_PASSWORD`

### `dry-run / live`

沿用原来的 live 凭证来源：

1. 环境变量
   - `OKX_API_KEY`
   - `OKX_API_SECRET`
   - `OKX_API_PASSWORD`
2. `config/secrets.env`
3. 你手动传入的 `--source-config`

## 推荐流程：OKX Demo

### 1. 固定策略副本

默认把当前 champion 冻结给 demo：

```bash
.venv/bin/python real-money-test/pin_strategy.py \
  --source backups/strategy_macd_aggressive_v2_champion.py
```

如果你想换成人工指定版本，改 `--source` 即可。

### 2. 配置 demo 凭证

写入 `config/secrets.env`：

```bash
OKX_DEMO_API_KEY=...
OKX_DEMO_API_SECRET=...
OKX_DEMO_API_PASSWORD=...
OKX_DEMO_AVAILABLE_CAPITAL=1000
```

其中：

- `OKX_DEMO_AVAILABLE_CAPITAL=1000` 表示这个 bot 只按 `1000 USDT` 资金规模运行
- 启用该项后，运行时会自动改用 `available_capital`，不再继续使用 `tradable_balance_ratio`

### 3. 启动 demo

```bash
bash real-money-test/manage.sh start demo
```

查看状态：

```bash
bash real-money-test/manage.sh status demo
```

查看日志：

```bash
bash real-money-test/manage.sh log demo
```

停止：

```bash
bash real-money-test/manage.sh stop demo
```

### 4. 安装播报

安装 demo 日报：

```bash
bash real-money-test/install_daily_report_cron.sh install demo report
```

安装 demo 健康监控：

```bash
bash real-money-test/install_daily_report_cron.sh install demo monitor
```

移除旧 dry-run 日报：

```bash
bash real-money-test/install_daily_report_cron.sh remove dry-run report
```

## Demo 播报内容

`demo` 日报卡默认包含：

- 运行状态与 heartbeat age
- 固定策略 hash 短码与来源文件
- 账户权益、可用余额、昨日变化、累计变化
- 交易总数、24h 平仓数、24h 胜率、已实现 / 未实现 PnL
- 持仓占用、前 2 笔持仓摘要、`enter_tag`
- 最近 3 笔平仓
- 当前环境、交易对、周期

如果账户私有 API 不可用，卡片会显式标记 `degraded=...`，并自动退回本地估算口径，不会静默伪装成正常账户数据。

关键事件播报包含：

- demo 启动成功
- demo 启动失败
- demo 进程停止
- heartbeat 超阈值
- 异常后恢复健康

## Dry-run 说明

`dry-run` 代码仍保留，主要用途只剩：

- 本地执行链路回归
- 策略适配层对齐检查
- 不接交易所私有账户时的快速排障

它不再作为默认跑法，也不再是默认播报对象。

## Live 说明

只有在确认 `demo` 稳定后才运行：

```bash
export I_UNDERSTAND_LIVE_RISK=YES
bash real-money-test/start_live.sh
```

## 说明

这套壳子当前已经对齐了这些核心行为：

- 主策略参数源
- 入场信号
- 主标签退出语义
- 路径标签 `enter_tag` 透传
- 主要趋势过滤
- ATR 初始止损
- 保本止损
- 追踪止损
- 趋势失效退出
- 时间退出
- `TP1` 分批止盈
- 有限次加仓

它仍然不是自研回测器的逐字段完全镜像，尤其是：

- 回测里的 `1m` 执行价近似 vs 真实成交
- 滑点假设 vs 真实盘口冲击
- 多并发独立仓位 vs freqtrade 的实际持仓结构

所以它的用途应该理解为：

- 验证执行链路
- 验证主标签与路径标签有没有对齐
- 验证持仓管理
- 验证 Discord / cron / restart 行为

不要把单段 `demo` 或 `dry-run` 收益直接当成 future live 收益。
