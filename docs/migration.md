# 迁移指南

> 从其他工具迁移到 prompt-git-manager

---

## 目录

- [从 LangChain 迁移](#从-langchain-迁移)
- [从 Langfuse 迁移](#从-langfuse-迁移)
- [从 OpenAI Prompts 迁移](#从-openai-prompts-迁移)
- [从手动管理迁移](#从手动管理迁移)
- [迁移检查清单](#迁移检查清单)

---

## 从 LangChain 迁移

### LangChain Prompt 格式

```python
# LangChain 方式
from langchain.prompts import PromptTemplate

prompt = PromptTemplate(
    input_variables=["question"],
    template="Answer the question: {question}"
)
```

### prompt-git-manager 格式

```yaml
# prompt-git-manager 方式
name: qa-prompt
version: "1.0.0"
system_prompt: "You are a helpful assistant."
user_template: "Answer the question: {{question}}"
variables:
  question:
    type: string
    description: "User's question"
```

### 迁移步骤

1. **提取 Prompt 内容**
   ```python
   # 从 LangChain 提取
   template = prompt.template
   input_vars = prompt.input_variables
   ```

2. **转换为 YAML**
   ```yaml
   name: extracted-prompt
   version: "1.0.0"
   system_prompt: "..."
   user_template: "..."  # 将 {var} 改为 {{var}}
   variables:
     var:
       type: string
   ```

3. **添加元数据**
   ```yaml
   metadata:
     source: langchain
     migrated_at: "2026-05-04"
   ```

### 格式差异

| 特性 | LangChain | prompt-git-manager |
|------|-----------|-------------------|
| 变量语法 | `{var}` | `{{var}}` |
| 存储方式 | Python 代码 | YAML 文件 |
| 版本控制 | Git（代码） | Git（专用） |
| 评估 | 自定义 | 内置 |

---

## 从 Langfuse 迁移

### Langfuse Prompt 格式

```python
# Langfuse 方式
from langfuse import Langfuse

langfuse = Langfuse()
prompt = langfuse.get_prompt("my-prompt")
```

### 迁移步骤

1. **导出 Langfuse Prompts**
   ```python
   from langfuse import Langfuse
   
   langfuse = Langfuse()
   
   # 获取所有 prompts
   prompts = langfuse.client.prompts.list()
   
   # 导出为 YAML
   for prompt in prompts:
       yaml_content = convert_to_yaml(prompt)
       save_yaml(f"{prompt.name}.yaml", yaml_content)
   ```

2. **转换格式**
   ```python
   def convert_to_yaml(langfuse_prompt):
       return {
           "name": langfuse_prompt.name,
           "version": str(langfuse_prompt.version),
           "system_prompt": langfuse_prompt.prompt[0]["content"],
           "user_template": langfuse_prompt.prompt[1]["content"],
           "variables": extract_variables(langfuse_prompt),
           "metadata": {
               "source": "langfuse",
               "langfuse_id": langfuse_prompt.id
           }
       }
   ```

3. **导入到 prompt-git-manager**
   ```bash
   # 添加所有导出的 prompts
   for file in exported/*.yaml; do
       pg add "$file"
   done
   
   pg commit -m "Migrate from Langfuse"
   ```

### 功能对应

| Langfuse 功能 | prompt-git-manager 对应 |
|--------------|----------------------|
| Prompt 管理 | `pg add/commit/diff` |
| 版本控制 | Git 原生版本 |
| 评估 | `pg eval` |
| 监控 | 外部集成 |

---

## 从 OpenAI Prompts 迁移

### OpenAI Prompt 格式

```python
# OpenAI 方式
messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": f"Answer: {question}"}
]
```

### 迁移步骤

1. **提取 System Prompt**
   ```python
   system_msg = [m for m in messages if m["role"] == "system"][0]["content"]
   ```

2. **提取 User Template**
   ```python
   user_msg = [m for m in messages if m["role"] == "user"][0]["content"]
   # 将 f-string 变量转换为 {{var}}
   template = user_msg.replace("{question}", "{{question}}")
   ```

3. **创建 YAML**
   ```yaml
   name: openai-prompt
   version: "1.0.0"
   system_prompt: "..."
   user_template: "..."
   variables:
     question:
       type: string
   metadata:
     source: openai
   ```

### 格式对比

```python
# OpenAI 原格式
messages = [
    {"role": "system", "content": "You are a coder."},
    {"role": "user", "content": f"Write {language} code for: {task}"}
]

# prompt-git-manager 格式
"""
name: code-writer
system_prompt: "You are a coder."
user_template: "Write {{language}} code for: {{task}}"
variables:
  language:
    type: string
    default: "python"
  task:
    type: string
"""
```

---

## 从手动管理迁移

### 常见手动管理方式

```
prompts/
├── v1_customer_service.txt
├── v2_customer_service.txt
├── v3_customer_service_final.txt
├── v3_customer_service_final_v2.txt
└── customer_service_backup.txt
```

### 迁移步骤

1. **整理现有 Prompt**
   ```bash
   # 创建目录
   mkdir -p migrated
   
   # 识别最新版本
   # 通常是文件名最新的或内容最完整的
   cp prompts/v3_customer_service_final_v2.txt migrated/customer_service.yaml
   ```

2. **转换为结构化格式**
   ```yaml
   # migrated/customer_service.yaml
   name: customer-service
   version: "1.0.0"
   system_prompt: |
     [从 txt 文件中提取系统提示部分]
   user_template: |
     [从 txt 文件中提取用户模板部分]
   variables:
     # 识别并定义变量
   constraints:
     # 识别并定义约束
   metadata:
     source: manual_migration
     original_file: "v3_customer_service_final_v2.txt"
   ```

3. **初始化并导入**
   ```bash
   # 初始化
   pg init
   
   # 添加所有迁移的 prompts
   pg add migrated/customer_service.yaml
   
   # 提交
   pg commit -m "Migrate from manual management"
   ```

4. **创建基线数据集**
   ```bash
   # 从现有测试用例中提取
   cat > fixtures/dataset.jsonl << 'EOF'
   {"input": "常见问题1", "expected_output": "标准答案1"}
   {"input": "常见问题2", "expected_output": "标准答案2"}
   EOF
   ```

5. **运行基线评估**
   ```bash
   pg eval --dataset fixtures/dataset.jsonl --threshold 0.05
   ```

### 迁移收益

| 方面 | 手动管理 | prompt-git-manager |
|------|---------|-------------------|
| 版本控制 | 文件名后缀 | Git 原生 |
| 变更追踪 | 无法追踪 | 语义 Diff |
| 质量保证 | 无 | 自动评估 |
| 团队协作 | 复制粘贴 | Git 工作流 |
| 回滚能力 | 找备份 | `git checkout` |

---

## 迁移检查清单

### 迁移前

- [ ] 盘点现有 Prompt 数量
- [ ] 识别最新版本
- [ ] 记录依赖关系
- [ ] 备份原始文件

### 格式转换

- [ ] 提取 system_prompt
- [ ] 提取 user_template
- [ ] 识别变量（`{var}` → `{{var}}`）
- [ ] 定义变量类型和默认值
- [ ] 提取约束
- [ ] 添加元数据

### 导入验证

- [ ] 运行 `pg add` 验证格式
- [ ] 运行 `pg diff --semantic` 检查
- [ ] 运行 `pg eval` 评估基线
- [ ] 检查所有变量替换正常

### 团队过渡

- [ ] 培训团队使用 CLI
- [ ] 设置 CI/CD 集成
- [ ] 建立 Code Review 流程
- [ ] 更新文档

### 生产部署

- [ ] 在测试环境验证
- [ ] 逐步切换流量
- [ ] 监控评估指标
- [ ] 保留回滚方案

---

## 迁移脚本示例

### 批量转换脚本

```python
#!/usr/bin/env python3
"""批量迁移脚本示例"""

import os
import re
import yaml
from pathlib import Path

def convert_txt_to_yaml(txt_path: Path) -> dict:
    """将 txt prompt 转换为 YAML 格式"""
    content = txt_path.read_text()
    
    # 简单分离 system 和 user 部分
    parts = content.split("---")
    system_prompt = parts[0].strip() if len(parts) > 0 else ""
    user_template = parts[1].strip() if len(parts) > 1 else content
    
    # 提取变量
    variables = {}
    var_pattern = r"\{(\w+)\}"
    for var in re.findall(var_pattern, user_template):
        variables[var] = {"type": "string", "default": ""}
        user_template = user_template.replace(f"{{{var}}}", f"{{{{{var}}}}}")
    
    return {
        "name": txt_path.stem,
        "version": "1.0.0",
        "system_prompt": system_prompt,
        "user_template": user_template,
        "variables": variables,
        "metadata": {
            "source": "migration",
            "original_file": txt_path.name
        }
    }

def migrate_directory(input_dir: Path, output_dir: Path):
    """迁移整个目录"""
    output_dir.mkdir(exist_ok=True)
    
    for txt_file in input_dir.glob("*.txt"):
        yaml_data = convert_txt_to_yaml(txt_file)
        yaml_path = output_dir / f"{txt_file.stem}.yaml"
        
        with open(yaml_path, "w") as f:
            yaml.dump(yaml_data, f, default_flow_style=False, allow_unicode=True)
        
        print(f"Converted: {txt_file.name} → {yaml_path.name}")

if __name__ == "__main__":
    migrate_directory(
        input_dir=Path("old_prompts"),
        output_dir=Path("migrated_prompts")
    )
```

### 使用方法

```bash
# 1. 运行迁移脚本
python migrate.py

# 2. 验证转换结果
for file in migrated_prompts/*.yaml; do
    pg add "$file" --dry-run
done

# 3. 批量导入
for file in migrated_prompts/*.yaml; do
    pg add "$file"
done

# 4. 提交
pg commit -m "Migrate prompts from legacy system"
```

---

## 常见问题

### Q: 变量语法不同怎么办？

**A:** 使用批量替换：
```bash
# 将 {var} 替换为 {{var}}
sed -i 's/{\(\w+\)}/{{\1}}/g' *.yaml
```

### Q: 如何保留历史版本？

**A:** 按时间顺序导入：
```bash
# 导入 v1
cp v1.yaml .prompts/
pg commit -m "Import v1"

# 导入 v2
cp v2.yaml .prompts/
pg commit -m "Import v2"

# 最终版本已在 HEAD
```

### Q: 如何验证迁移正确？

**A:** 运行评估：
```bash
# 创建测试数据集
cat > fixtures/test.jsonl << 'EOF'
{"input": "测试问题", "expected_output": "期望答案"}
EOF

# 评估
pg eval --dataset fixtures/test.jsonl --threshold 0.05
```

---

## 相关文档

- [快速开始](quickstart.md) - 5 分钟上手
- [Prompt Schema](prompt-schema.md) - 文件格式
- [数据集指南](dataset-guide.md) - 创建数据集
- [最佳实践](best-practices.md) - 使用建议
