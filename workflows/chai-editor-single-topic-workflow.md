# 柴主编 AI 单热点日更工作流（执行入口）

版本：2026-10-03
状态：V2.2；内容规则以 `docs/端到端流程.md` 为准。

## 事实源

- 内容与证据：[端到端流程](../docs/端到端流程.md)。
- 尺寸、安全区与编码：`chai-editor-single-topic-config.json`。
- 复盘：复制 `chai-editor-performance-template.md` 为每期 `performance-record.md`。
- 发布：[三平台手册](chai-platform-publish-playbook.md)，页面状态优先于适配器状态。
- 可迁移流程包：[入口](chai-daily-kit/README.md)。

## 硬约束

- **不自动发布**：只制作时交发布包；用户明确授权当期发布后，准备草稿、回读同一任务、提交一次、核对平台作品。
- **不覆盖**：项目、候选、成片、发布包使用独立目录；旧已发布产物保留。
- 生产前运行 `python3 scripts/validate_chai_editor_contract.py`；失败保存 `production-blocker.md` 并修复。

## 当前入口

选题与源健康：`bash scripts/daily_topics.sh --hours 48 --limit 12`；规则见 [新闻雷达手册](chai-news-radar-workflow.md)。

```bash
python3 scripts/validate_chai_editor_contract.py
python3 scripts/chai_xhs_copy_check.py <发布包目录>/publish-copy.md
python3 scripts/chai_release_preflight.py <发布包目录> --ffprobe <ffprobe路径>
```

预检需要 `release-spec.json`，字段示例见流程包。离线 PASS 不等于内容/听审/平台发布 PASS。

`chai_pipeline.py all/verify` 只用于兼容原工程，不作为新工程统一创意入口。
`chai_publish_mcp.py <包> --only <平台> --keep-open` 为本机旧草稿准备入口；禁用 `--auto-submit`、`--submit`、`--schedule`，因为它们可能绕过封面核对或重新建立任务。恢复在原 group 中完成；准备入口不负责平台端最终验收。


## 生产工具边界 · 用户2026-10-03最新决定

日更恢复此前已验证的 MiniMax 配音、词级时间轴、HyperFrames 合成/导出与 MultiPost 发布流程，优先复用已有日更工程。柴主编品牌、证据、文案、封面、质检与平台核对仍沿用现行要求。EP.233 的 ChatCut 试验不替代日更生产线。ChatCut 用于单独的数字人介绍等业务，不自动迁移日更或改动既有生产线。
