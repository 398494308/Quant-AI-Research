# DeepSeek Planner Experiment

这份 clone 用于做 `planner-only` 的 DeepSeek 对照实验。

## 当前接法

- `planner`：走 DeepSeek 官方兼容 API
- `reviewer / edit_worker / repair_worker / summary_worker`：继续走原来的 `codex exec`
- `base_url`：`https://api.deepseek.com`
- `model`：`deepseek-v4-pro`
- `thinking`：`enabled`
- `reasoning_effort`：`max`

## 当前观察

截至 `2026-04-26` 的运行观察，当前观察是：

- `GPT` 更适合固定框架、规则严密、执行链稳定的角色，例如 `reviewer / edit_worker / repair_worker / summary_worker`
- `DeepSeek` 在发散找方向、提出新假设、快速换研究层级这类 `planner` 任务里，当前表现更好

这只是当前仓库、当前评分口径和当前实验流程下的结论，不把它外推成所有任务的一般结论。

## 关键说明

### 1. 只换 planner

通过 `config/secrets.env` 中的 `MACD_V2_PLANNER_PROVIDER=deepseek` 控制。

只有 `session_kind=planner` 时才会切到 DeepSeek，其余角色不变。

### 2. AGENTS 规则仍然生效

原来的 `Codex CLI` 会天然读取工作区里的 `AGENTS.md`。

DeepSeek API 不会自动读取本地文件，所以实验接法里会把工作区 `AGENTS.md`
的全文显式注入到 `planner` 的 system prompt 中，确保原有 `apply on planner`
的规则继续成立。

### 3. planner 仍有持久 session

DeepSeek 没有直接复用 Codex 的 session 机制。

这个实验里，`planner` 的多轮上下文会写到工作区本地历史文件：

- `state/research_macd_aggressive_v2_agent_workspace/.deepseek_planner_session_*.json`

它仍然受当前 `active reference + stage` 作用域约束；stage 重开或 champion 刷新时，
本地 planner session 才会重置。

补充两点：

- 同一 stage 内，即使出现 reviewer 打回、`behavioral_noop`、同轮重生或方向切换，也不会自动重置 planner session。
- 本地 session 默认只保留最近 `12` 条非 system 历史消息，目标是保留失败记忆，但压掉长尾原始对话。

### 4. planner reasoning 会额外落本地 trace

为了方便回看每一轮 `planner` 是否真的换了想法、有没有吸收 `reviewer` 的反馈，
实验接法会额外写一份 append-only trace：

- `state/research_macd_aggressive_v2_agent_workspace/.deepseek_planner_trace_*.jsonl`

每一行记录一轮 planner 调用，包含：

- 当前轮收到的 `prompt`
- DeepSeek 返回的最终 `assistant_content`
- DeepSeek 返回的 `assistant_reasoning_content`

这个 trace 只用于观测，不会把旧的 `reasoning_content` 再喂回模型，因此不会改变原有研究流程。
本地 session history 现在也不会再持久化 `reasoning_content`，避免无效膨胀。

### 5. prompt 结构没变，只做压缩

这轮实验没有改研究器角色分工、SOP 或 prompt 分层架构，只做了减重：

- 压缩 planner / reviewer / repair 的重复规则文本
- 把人工卡、reviewer 卡和 front memory 改成更短的摘要块
- 保留原有“先复盘失败证据，再决定继续还是转向”的工作方式

### 6. telemetry 现在区分原始 prompt 和真实发送上下文

模型调用日志仍保留原来的 `prompt_chars / system_prompt_chars / estimated_prompt_tokens`，
同时新增真实发送口径，例如：

- `system_prompt_chars_sent`
- `history_message_chars_sent`
- `history_message_count_sent`
- `total_message_chars_sent`
- `estimated_prompt_tokens_sent`

这样可以直接看出内联 `AGENTS.md` 和持久 session 历史到底把 planner 上下文推高了多少。

## 运行层补充

这份实验 clone 近期还补了 3 个和 `planner` 接法正交的轻优化，目标只是减重，不改原有研究结构：

- 回测 `prepared context` 增加进程内小缓存，避免同参数重复准备
- active reference 的 base smoke 行为增加单份缓存，同时把 candidate 的 smoke 与行为采样合并成一次
- 非持久 `Codex` 文本 phase 遇到瞬态失败时，先立刻短重试 `1` 次，再回到原来的外层恢复逻辑

这些改动不会改变 `planner-only` DeepSeek 实验的 session 作用域、prompt 结构或评分口径。

## 推荐启动前动作

因为这是从主仓拷出来的实验 clone，建议首次启动前先做一次 stage reset：

```bash
bash scripts/reset_research_macd_aggressive_v2_stage.sh
```

这样可以保留当前参考点，但清掉从主仓复制过来的 live session、wiki 前台记忆和候选残留，
避免 A/B 实验互相污染。
