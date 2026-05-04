# prompt-git MVP Spec
## 目标
零侵入、Git 原生的 Prompt 版本控制与 CI 防退化工具，专注开发时工作流，不依赖外部数据库或 Web UI。

## 核心命令
- `pg init`：初始化 `.prompts/` 目录与元数据
- `pg add <file>`：将 Prompt 文件纳入版本追踪（YAML/JSON/MD）
- `pg commit -m "msg"`：记录变更快照，生成结构化日志
- `pg diff [--semantic]`：对比当前与 HEAD，输出变量/约束/意图变更摘要
- `pg eval --dataset <file.jsonl> [--threshold 0.05]`：跑历史数据集，拦截退化 PR
- `pg ci init`：生成 `.github/workflows/prompt-guard.yml` 与 pre-commit 钩子

## 输入/输出
- 输入：`.prompts/*.yaml`、`datasets/*.jsonl`、Git 仓库
- 输出：CLI 报告、JSON 评测结果、CI YAML、Markdown Changelog

## 成功标准（验收）
1. 支持 `pip install` 或 `uv run` 直接运行
2. `pg diff` 能正确识别 3 类变更：变量替换、约束增删、意图偏移
3. `pg eval` 输出 `accuracy_delta`、`cost_delta`、`consistency_score`
4. CI 流程在 PR 阶段自动运行，失败则 Comment 警告
5. 单元测试覆盖率 ≥ 80%，含 20+ 边界用例
6. README 含架构图、安装、示例、性能对比表
