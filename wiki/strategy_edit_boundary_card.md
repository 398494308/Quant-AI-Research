# 策略编辑边界卡

来源：`wiki/strategy_edit_boundary_card.md`。这是 planner、reviewer、edit worker、repair worker 共用的编辑权限边界。

## 可改
- `PARAMS`: 只改既有 key 的值。
- `EXIT_PARAMS`: 只改当前开放的既有 key；单个连续值可以配合 `exit_range_scan` 轻量预筛。
- `FACTOR_SLOT_PARAMS`: 只改既有 slot 的数值，不改 slot 名称或顺序。
- 固定 `_slot_*()`：只改函数体，不改名字、签名或数量。

## 锁死
- `_strategy_core()`、`strategy()`、`strategy_decision()`、候选生成顺序、slot 名称 / 数量 / 签名。
- 新 helper、新 top-level 常量、新 `PARAMS` key、新 `EXIT_PARAMS` key、新 slot 名称。
- 固定执行层口径：`leverage`、`position_fraction`、`position_size_min`、`position_size_max`、`max_concurrent_positions`、`pyramid_enabled`、`pyramid_max_times`、`pyramid_size_ratio`、`tp1_close_fraction`、`breakout_tp1_close_fraction`、`short_breakdown_tp1_close_fraction`、`short_trend_tp1_close_fraction`。
- `short` 入口相关恢复、放宽或新增，只能保留为退出 / 风控安全层，不作为入场目标。

## 锁区 -> 可改
{{LOCKED_REGION_GUIDANCE}}

## 锁区想法翻译规则
- 想法点名 locked helper 时，`change_plan` 必须同时写出对应 editable 落点。
- 只写 locked、不写 editable，视为无效 brief。
- 需要新因子时，只能放进现有 `_slot_*()` 槽，不新增 helper / slot / key。
