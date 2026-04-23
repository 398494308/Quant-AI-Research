# real-money-test

这是本仓库内自洽的 `freqtrade` dry-run / live 壳子。

它的定位很明确：

- 继续复用 `src/strategy_macd_aggressive.py` 和 `src/freqtrade_macd_aggressive.py`
- 用 `freqtrade` 负责交易所接入、下单、持仓、重启、日志
- 不再默认继承外部仓库配置

## 当前目录

- `config.base.json`
  基础 `freqtrade` 配置，不含敏感信息
- `build_runtime_config.py`
  生成运行时配置，优先读取本地环境变量或 `config/secrets.env` 里的 OKX 凭证
- `strategies/MacdAggressiveStrategy.py`
  `freqtrade` 策略入口
- `start_dry_run.sh`
  启动 dry-run
- `start_live.sh`
  启动 live，必须显式确认风险
- `manage.sh`
  统一入口，支持 `start/stop/restart/status/log`
- `daily_report.py`
  汇总权益、持仓和近 24h 表现，并发送 Discord
- `report.env.example`
  日报频道配置样板
- `systemd/freqtrade-macd-aggressive-dryrun.service.example`
  systemd 示例

## 凭证来源

运行时配置的凭证优先级：

1. 环境变量
   - `OKX_API_KEY`
   - `OKX_API_SECRET`
   - `OKX_API_PASSWORD`
2. `config/secrets.env`
3. 你手动传入的 `--source-config`

如果以上都没有，`build_runtime_config.py` 会直接报错，不会再去引用外部仓库。

## 先跑 dry-run

```bash
bash real-money-test/manage.sh start
```

查看日志：

```bash
bash real-money-test/manage.sh log
```

查看状态：

```bash
bash real-money-test/manage.sh status
```

停止：

```bash
bash real-money-test/manage.sh stop
```

## live 启动

只有在确认 dry-run 稳定后才运行：

```bash
export I_UNDERSTAND_LIVE_RISK=YES
bash real-money-test/start_live.sh
```

## 当前实现状态

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
- 验证 Discord / cron / systemd / restart 行为

不要把 dry-run 的单段收益直接当成 future live 收益。
