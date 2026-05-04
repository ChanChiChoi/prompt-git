# 发展路线图

> prompt-git-manager 的发展规划

---

## 目录

- [当前版本](#当前版本)
- [短期计划](#短期计划-02x)
- [中期计划](#中期计划-03x)
- [长期愿景](#长期愿景-10)
- [功能投票](#功能投票)

---

## 当前版本

### v0.1.1 (当前)

**核心功能：**
- ✅ `pg init` - 初始化项目
- ✅ `pg add` - 添加 Prompt
- ✅ `pg commit` - 提交变更
- ✅ `pg diff` - 语义 Diff
- ✅ `pg eval` - 数据集评估
- ✅ `pg ci init` - CI 配置生成

**评估能力：**
- ✅ 规则引擎（无 LLM 依赖）
- ✅ 关键词匹配
- ✅ Token 估算
- ✅ 一致性评分

**CI/CD：**
- ✅ GitHub Actions 模板
- ✅ Pre-commit 钩子
- ✅ PyPI 发布流程

---

## 短期计划 (v0.2.x)

### v0.2.0 - LLM 增强评估

**目标：** 支持 LLM 作为评估后端

```
[ ] 集成 LiteLLM
[ ] 支持 OpenAI / Anthropic / 本地模型
[ ] LLM-as-judge 评估模式
[ ] 多模型对比评估
```

**使用场景：**
```bash
# 使用 LLM 评估
pg eval --dataset data.jsonl --provider openai --model gpt-4

# 对比不同模型
pg eval --dataset data.jsonl --compare-models gpt-3.5,gpt-4
```

### v0.2.1 - 增强 Diff

**目标：** 更智能的语义分析

```
[ ] 意图偏移检测
[ ] 上下文感知 Diff
[ ] Diff 可视化报告
[ ] 自定义检测规则
```

### v0.2.2 - 数据集增强

**目标：** 更好的数据集管理

```
[ ] 数据集生成器（从 Prompt 自动生成）
[ ] 数据集验证工具
[ ] 数据集合并/拆分
[ ] 数据集版本管理
```

---

## 中期计划 (v0.3.x)

### v0.3.0 - 多 Prompt 管理

**目标：** 支持 Prompt 链和组合

```
[ ] Prompt 引用和继承
[ ] Prompt 链定义
[ ] 条件分支
[ ] 模板组合
```

**示例：**
```yaml
name: customer-service
extends: base-assistant
chains:
  - name: greeting
    prompt: greeting-prompt
  - name: main
    prompt: main-prompt
  - name: closing
    prompt: closing-prompt
```

### v0.3.1 - 团队协作

**目标：** 更好的团队协作支持

```
[ ] Prompt 锁定机制
[ ] 变更审批流程
[ ] 团队权限管理
[ ] 变更通知
```

### v0.3.2 - 可视化界面

**目标：** Web UI 支持

```
[ ] Prompt 编辑器
[ ] Diff 可视化
[ ] 评估结果仪表盘
[ ] 团队协作界面
```

---

## 长期愿景 (v1.0)

### 核心目标

成为 Prompt 工程的标准工具链：

```
Prompt 开发
    ↓
版本控制 (prompt-git-manager)
    ↓
自动评估
    ↓
CI/CD 集成
    ↓
生产部署
    ↓
监控反馈
```

### v1.0 功能

```
[ ] 完整的 Prompt 生命周期管理
[ ] 多语言/多模态支持
[ ] 企业级安全和权限
[ ] 云服务集成
[ ] 插件生态系统
```

### 生态系统

```
prompt-git-manager (核心)
    ├── prompt-git-lint (代码检查)
    ├── prompt-git-fmt (格式化)
    ├── prompt-git-test (测试框架)
    ├── prompt-git-deploy (部署工具)
    └── prompt-git-monitor (监控)
```

---

## 功能投票

### 如何投票

在 GitHub Issues 中使用标签投票：

- 👍 - 我需要这个功能
- 🎉 - 这个功能很重要
- ❤️ - 我愿意贡献代码

### 待投票功能

| 功能 | Issue | 状态 |
|------|-------|------|
| LLM 评估 | #10 | 待投票 |
| Web UI | #11 | 待投票 |
| 多 Prompt 链 | #12 | 待投票 |
| 数据集生成 | #13 | 待投票 |
| 自定义规则 | #14 | 待投票 |

### 提议新功能

1. 在 GitHub 创建 Issue
2. 使用 `feature-request` 标签
3. 描述使用场景和期望行为
4. 等待社区反馈

---

## 发布计划

| 版本 | 预计时间 | 主题 |
|------|---------|------|
| v0.2.0 | 2024 Q1 | LLM 评估 |
| v0.2.1 | 2024 Q1 | 增强 Diff |
| v0.3.0 | 2024 Q2 | 多 Prompt |
| v0.4.0 | 2024 Q3 | 团队协作 |
| v1.0.0 | 2024 Q4 | 正式版 |

---

## 贡献方式

### 代码贡献

```bash
# 1. Fork 仓库
# 2. 选择一个功能分支
git checkout -b feature/llm-evaluation

# 3. 开发并测试
# 4. 提交 PR
```

### 非代码贡献

- 📝 改进文档
- 🐛 报告 Bug
- 💡 提议功能
- 🧪 编写测试
- 🌍 翻译文档

---

## 相关链接

- [GitHub Issues](https://github.com/ChanChiChoi/prompt-git-manager/issues)
- [GitHub Discussions](https://github.com/ChanChiChoi/prompt-git-manager/discussions)
- [贡献指南](../CONTRIBUTING.md)
- [更新日志](../CHANGELOG.md)
