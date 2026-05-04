# 快速开始 / Quick Start

> 5 分钟上手 prompt-git-manager

---

## 前置条件

- Python 3.10+
- Git
- uv（推荐）或 pip

---

## 1. 安装

```bash
# 使用 uv（推荐）
uv pip install prompt-git-manager

# 或使用 pip
pip install prompt-git-manager

# 验证安装
pg --version
```

---

## 2. 初始化项目

```bash
cd your-project
pg init
```

这将创建：
```
.prompts/
├── config.json      # 项目配置
└── .gitignore       # 忽略临时文件
```

---

## 3. 创建 Prompt 文件

创建一个 YAML 格式的 prompt 文件：

```bash
cat > qa_prompt.yaml << 'EOF'
name: qa-assistant
version: "1.0.0"
system_prompt: "You are a helpful assistant."
user_template: "Answer: {{question}}"
variables:
  question:
    type: string
    default: "What is Python?"
constraints:
  - Be concise
  - Use examples
metadata:
  author: your-name
EOF
```

**必填字段：**
- `name`：Prompt 名称
- `system_prompt`：系统提示词
- `user_template`：用户消息模板（支持 `{{变量}}`）

---

## 4. 添加到版本追踪

```bash
pg add qa_prompt.yaml
```

输出示例：
```
✓ Added qa_prompt.yaml to prompt tracking
┌─────────────┬──────────────────────┐
│ Field       │ Value                │
├─────────────┼──────────────────────┤
│ Name        │ qa-assistant         │
│ Version     │ 1.0.0                │
│ Variables   │ question             │
│ Constraints │ 2                    │
│ Path        │ .prompts/qa_prompt.yaml │
└─────────────┴──────────────────────┘
```

---

## 5. 提交变更

```bash
pg commit -m "Initial QA prompt"
```

这会：
1. 验证所有 prompt 文件
2. 创建 Git 提交
3. 记录提交元数据到 `commits.jsonl`

---

## 6. 查看变更

修改 prompt 后查看差异：

```bash
# 修改 prompt
vim .prompts/qa_prompt.yaml

# 查看语义 diff
pg diff --semantic
```

输出示例：
```
┌─────────────────────────────────────────────────┐
│ Diff: .prompts/qa_prompt.yaml                   │
├──────────────┬──────────────────────────────────┤
│ Risk Level   │ 🟡 MEDIUM                        │
│ Change Type  │ constraint_change                │
│ Summary      │ Added 1 constraint               │
└──────────────┴──────────────────────────────────┘
```

**风险等级：**
- 🟢 **LOW**：小幅变更，无语义影响
- 🟡 **MEDIUM**：约束或语气变更
- 🔴 **HIGH**：角色或变量删除

---

## 7. 数据集评估

创建测试数据集并评估 prompt 效果：

```bash
# 创建数据集
mkdir -p fixtures
cat > fixtures/dataset.jsonl << 'EOF'
{"input": "What is Python?", "expected_output": "Python is a programming language"}
{"input": "What is Git?", "expected_output": "Git is a version control system"}
{"input": "What is AI?", "expected_output": "AI is artificial intelligence"}
EOF

# 运行评估
pg eval --dataset fixtures/dataset.jsonl --threshold 0.05
```

输出示例：
```
┌────────────────────┬────────────────┐
│ Metric             │ Value          │
├────────────────────┼────────────────┤
│ Total Samples      │ 3              │
│ Accuracy (Old)     │ 100.0%         │
│ Accuracy (New)     │ 100.0%         │
│ Accuracy Delta     │ +0.0%          │
│ Token Cost (Old)   │ 45             │
│ Token Cost (New)   │ 52             │
│ Token Cost Delta   │ +15.6%         │
│ Consistency Score  │ 100.0%         │
│ Status             │ ✅ PASSED      │
│ Threshold          │ 5.0%           │
└────────────────────┴────────────────┘
```

---

## 8. CI 集成（可选）

生成 GitHub Actions 配置：

```bash
pg ci init
```

这将创建：
- `.github/workflows/prompt-guard.yml` - PR 检查
- `.github/workflows/publish.yml` - PyPI 发布
- `.pre-commit-config.yaml` - Pre-commit 钩子
- `scripts/bump_version.sh` - 版本管理

---

## 完整工作流示例

```bash
# 1. 初始化
cd my-project
git init
pg init

# 2. 创建 prompt
cat > qa_prompt.yaml << 'EOF'
name: qa-bot
version: "1.0.0"
system_prompt: "You are a helpful QA assistant."
user_template: "Answer: {{question}}"
variables:
  question:
    type: string
    default: "What is Python?"
constraints:
  - Be concise
metadata:
  author: me
EOF

# 3. 添加并提交
pg add qa_prompt.yaml
pg commit -m "Add QA prompt"

# 4. 修改 prompt
sed -i 's/Be concise/Be concise and use examples/' .prompts/qa_prompt.yaml

# 5. 查看变更
pg diff --semantic

# 6. 创建数据集并评估
mkdir -p fixtures
cat > fixtures/dataset.jsonl << 'EOF'
{"input": "What is Python?", "expected_output": "Python is a programming language"}
EOF
pg eval --dataset fixtures/dataset.jsonl --threshold 0.05

# 7. 提交并推送
pg commit -m "Improve QA prompt"
git add .
git commit -m "Add prompt management"
git push
```

---

## 常见问题

### Q: 提示 "Not a git repository"
**A:** 先运行 `git init` 初始化 Git 仓库。

### Q: 提示 "No .prompts/ directory"
**A:** 先运行 `pg init` 初始化 prompt-git-manager。

### Q: 评估失败怎么办？
**A:** 检查输出的准确率变化，如果下降超过阈值，考虑：
1. 回滚变更：`git checkout HEAD~1 .prompts/`
2. 调整阈值：`pg eval --dataset data.jsonl --threshold 0.10`

---

## 下一步

- [CLI 参考文档](cli_reference.md) - 查看所有命令详解
- [架构文档](architecture.md) - 了解内部实现
- [Troubleshooting](TROUBLESHOOTING.md) - 常见问题解决
- [E-commerce 示例](../examples/ecommerce/) - 完整工作流演示
