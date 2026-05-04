# 贡献指南 / Contributing Guide

感谢你对 prompt-git-manager 的关注！欢迎贡献代码、报告问题或改进文档。

---

## 目录

- [开发环境](#开发环境)
- [项目结构](#项目结构)
- [代码规范](#代码规范)
- [提交规范](#提交规范)
- [Pull Request 流程](#pull-request-流程)
- [Issue 指南](#issue-指南)
- [文档贡献](#文档贡献)

---

## 开发环境

### 前置条件

- Python 3.10+
- Git
- uv（推荐）

### 搭建开发环境

```bash
# 1. Fork 并克隆仓库
git clone https://github.com/YOUR_USERNAME/prompt-git-manager.git
cd prompt-git-manager

# 2. 创建虚拟环境
uv venv .venv
source .venv/bin/activate  # Linux/macOS
# 或 .venv\Scripts\activate  # Windows

# 3. 安装开发依赖
uv sync --extra dev

# 4. 运行测试
uv run pytest

# 5. 验证安装
pg --version
```

### IDE 配置

**VS Code 推荐设置：**
```json
{
  "python.defaultInterpreterPath": ".venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": false,
  "python.linting.ruffEnabled": true,
  "python.formatting.provider": "none",
  "python.formatting.ruffEnabled": true
}
```

---

## 项目结构

```
prompt-git-manager/
├── src/promptgit/           # 源代码
│   ├── __init__.py          # 版本号
│   ├── cli.py               # CLI 入口
│   ├── schema.py            # 数据模型
│   ├── diff_engine.py       # Diff 引擎
│   ├── evaluator.py         # 评估器
│   ├── ci_gen.py            # CI 生成器
│   ├── ci_guard.py          # CI 拦截
│   └── utils.py             # 工具函数
├── tests/                   # 测试代码
├── docs/                    # 文档
├── examples/                # 示例
├── fixtures/                # 测试数据
└── .github/workflows/       # CI 配置
```

### 模块职责

| 模块 | 职责 | 修改频率 |
|------|------|---------|
| cli.py | 用户交互 | 中 |
| schema.py | 数据验证 | 低 |
| diff_engine.py | Diff 算法 | 中 |
| evaluator.py | 评估逻辑 | 中 |
| ci_gen.py | YAML 生成 | 低 |
| utils.py | 工具函数 | 低 |

---

## 代码规范

### Python 风格

- 遵循 PEP 8
- 使用类型注解（Type Hints）
- 使用 Pydantic 进行数据验证
- 函数和类必须有 docstring

### 命名规范

```python
# 模块名：小写下划线
diff_engine.py

# 类名：大驼峰
class PromptTemplate:
    pass

# 函数名：小写下划线
def compute_diff():
    pass

# 常量：大写下划线
ERR_SUCCESS = 0

# 私有成员：单下划线前缀
def _internal_function():
    pass
```

### Docstring 格式

```python
def function_name(arg1: str, arg2: int) -> bool:
    """Short description of the function.

    Longer description if needed.

    Args:
        arg1: Description of arg1.
        arg2: Description of arg2.

    Returns:
        Description of return value.

    Raises:
        ValueError: When something is invalid.
    """
    pass
```

### 类型注解

```python
from typing import Optional, Any
from pathlib import Path

def process(
    name: str,
    path: Path,
    config: Optional[dict[str, Any]] = None
) -> list[str]:
    pass
```

### 代码检查

```bash
# 类型检查
uv run mypy src/

# Lint 检查
uv run ruff check src/

# 代码格式化
uv run ruff format src/
```

---

## 提交规范

### Commit Message 格式

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### Type 类型

| Type | 说明 | 示例 |
|------|------|------|
| feat | 新功能 | `feat(eval): add LLM evaluation` |
| fix | Bug 修复 | `fix(diff): handle empty constraints` |
| docs | 文档更新 | `docs: add quickstart guide` |
| style | 代码格式 | `style: fix indentation` |
| refactor | 重构 | `refactor: extract diff logic` |
| test | 测试 | `test: add edge case tests` |
| chore | 构建/工具 | `chore: update dependencies` |

### 示例

```bash
# 简单提交
git commit -m "feat: add semantic diff"

# 带作用域
git commit -m "fix(eval): handle empty dataset"

# 带详细说明
git commit -m "feat(diff): add risk level detection

- Detect variable changes
- Detect constraint changes
- Detect tone shifts

Closes #123"
```

---

## Pull Request 流程

### 1. 创建分支

```bash
# 从 main 创建功能分支
git checkout main
git pull origin main
git checkout -b feature/your-feature
```

分支命名：
- `feature/xxx` - 新功能
- `fix/xxx` - Bug 修复
- `docs/xxx` - 文档更新
- `refactor/xxx` - 重构

### 2. 开发和测试

```bash
# 编写代码
vim src/promptgit/your_module.py

# 运行测试
uv run pytest tests/ -v

# 运行特定测试
uv run pytest tests/test_your_module.py -v
```

### 3. 提交代码

```bash
git add .
git commit -m "feat: your feature description"
```

### 4. 推送并创建 PR

```bash
git push origin feature/your-feature
gh pr create --title "feat: your feature" --body "Description"
```

### 5. PR 模板

```markdown
## 描述
简要描述这个 PR 的目的

## 变更类型
- [ ] 新功能
- [ ] Bug 修复
- [ ] 文档更新
- [ ] 重构

## 测试
- [ ] 添加了新测试
- [ ] 所有测试通过
- [ ] 覆盖率未下降

## 检查清单
- [ ] 代码遵循项目规范
- [ ] 更新了相关文档
- [ ] 更新了 CHANGELOG.md
```

### 6. 代码审查

- 至少需要一个维护者审查
- 确保所有 CI 检查通过
- 解决所有审查意见

---

## Issue 指南

### Bug 报告

```markdown
## Bug 描述
清晰描述遇到的问题

## 复现步骤
1. 运行 `pg init`
2. 运行 `pg add test.yaml`
3. 看到错误

## 期望行为
描述你期望的正确行为

## 实际行为
描述实际发生的情况

## 环境信息
- OS: macOS 14.0
- Python: 3.11.0
- prompt-git-manager: 0.1.0
```

### 功能请求

```markdown
## 功能描述
清晰描述你想要的功能

## 使用场景
描述这个功能的使用场景

## 建议实现
如果有想法，描述建议的实现方式
```

---

## 文档贡献

### 文档结构

```
docs/
├── index.md              # 文档目录
├── quickstart.md         # 快速开始
├── cli_reference.md      # CLI 参考
├── prompt-schema.md      # Prompt 规范
├── dataset-guide.md      # 数据集指南
├── configuration.md      # 配置详解
├── python-api.md         # Python API
├── architecture.md       # 架构文档
├── best-practices.md     # 最佳实践
├── migration.md          # 迁移指南
├── roadmap.md            # 路线图
└── TROUBLESHOOTING.md    # 故障排除
```

### 文档规范

- 使用 Markdown 格式
- 包含代码示例
- 中英文之间加空格
- 使用表格整理信息
- 提供目录导航

### 预览文档

```bash
# 使用 VS Code 预览
code docs/quickstart.md

# 或使用 grip 本地预览
pip install grip
grip docs/quickstart.md
```

---

## 发布流程

### 版本号规范

遵循 Semantic Versioning：
- `MAJOR.MINOR.PATCH`
- `0.1.0` → `0.2.0` (新功能) → `0.2.1` (修复) → `1.0.0` (正式版)

### 发布步骤

```bash
# 1. 更新版本号
./scripts/bump_version.sh patch  # 或 minor, major

# 2. 更新 CHANGELOG.md
vim CHANGELOG.md

# 3. 提交并推送
git add .
git commit -m "chore: release v0.1.1"
git push origin main --tags

# 4. 创建 GitHub Release
gh release create v0.1.1 --title "v0.1.1" --notes "See CHANGELOG.md"
```

---

## 获取帮助

- [GitHub Discussions](https://github.com/ChanChiChoi/prompt-git-manager/discussions)
- [GitHub Issues](https://github.com/ChanChiChoi/prompt-git-manager/issues)

---

## 行为准则

- 尊重所有参与者
- 接受建设性批评
- 专注于对社区最有利的事情
- 对他人表示同理心

---

感谢你的贡献！🎉
