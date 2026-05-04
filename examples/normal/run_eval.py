#!/usr/bin/env python3
"""
规则引擎评估示例 (Rule-Based Evaluation)
=========================================

本示例展示如何使用 prompt-git-manager 的 Python API 进行纯规则评估（无需 LLM）。

评估原理：
----------
规则引擎评估通过以下步骤比较两个 prompt 版本的质量差异：

1. 渲染 (Rendering)
   - 使用 rule_based_render() 将 prompt 模板与数据集变量组合
   - 替换 {{variable}} 占位符为实际值

2. 关键词匹配 (Keyword Matching)
   - extract_keywords() 提取期望输出中的关键词
   - keyword_match() 计算关键词覆盖率
   - 匹配阈值: 0.5 (50% 关键词命中即视为匹配)

3. 文本相似度 (Text Similarity)
   - compute_similarity() 使用 SequenceMatcher 计算文本相似度
   - 相似度阈值: 0.7 (70% 相似度即视为匹配)

4. Token 估算 (Token Estimation)
   - estimate_tokens() 估算输出的 token 数量
   - 支持 CJK 字符的特殊处理

5. 综合评分 (Overall Scoring)
   - accuracy: 匹配样本数 / 总样本数
   - consistency: 新旧版本匹配率的一致性
   - accuracy_delta: 新版本准确率 - 旧版本准确率
   - passed: accuracy_delta >= -threshold

使用场景：
----------
- 无需 API Key，完全离线运行
- 适合快速验证 prompt 变更的影响
- 适合 CI/CD 流水线中的自动化检查
- 适合大规模数据集的批量评估

运行方式：
----------
    cd examples/normal
    python run_eval.py
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from promptgit.schema import PromptTemplate
from promptgit.evaluator import (
    load_dataset,
    evaluate_prompts,
    rule_based_render,
    extract_keywords,
    keyword_based_evaluate,
    compute_similarity,
    estimate_tokens,
)


def main():
    # =========================================================================
    # 第 1 步：加载数据集
    # =========================================================================
    # 数据集格式: JSONL (每行一个 JSON 对象)
    # 必需字段: input, expected_output
    # 可选字段: metadata (用于分类和过滤)
    print("=" * 70)
    print("第 1 步：加载数据集")
    print("=" * 70)

    dataset_path = Path(__file__).parent.parent / "datasets" / "qa_dataset.jsonl"
    dataset = load_dataset(dataset_path)

    print(f"  数据集路径: {dataset_path}")
    print(f"  样本数量: {len(dataset)}")
    print()
    print("  数据集内容预览:")
    for i, sample in enumerate(dataset[:3]):
        print(f"    [{i+1}] Q: {sample.input}")
        print(f"        A: {sample.expected_output}")
        print(f"        分类: {sample.metadata.get('category', 'N/A')}")
        print(f"        难度: {sample.metadata.get('difficulty', 'N/A')}")
        print()

    # =========================================================================
    # 第 2 步：加载 Prompt 模板
    # =========================================================================
    # Prompt 模板格式: YAML
    # 必需字段: name, system_prompt, user_template
    # 可选字段: version, variables, constraints, metadata
    print("=" * 70)
    print("第 2 步：加载 Prompt 模板")
    print("=" * 70)

    prompts_dir = Path(__file__).parent.parent / "prompts"
    prompt_files = sorted(prompts_dir.glob("*.yaml"))

    templates = {}
    for pf in prompt_files:
        template = PromptTemplate.from_yaml(pf)
        templates[pf.stem] = template
        print(f"  已加载: {pf.name}")
        print(f"    名称: {template.name}")
        print(f"    版本: {template.version}")
        print(f"    变量: {list(template.variables.keys())}")
        print()

    # =========================================================================
    # 第 3 步：理解评估原理 - 渲染
    # =========================================================================
    # rule_based_render() 是评估的核心：
    #   1. 读取 user_template
    #   2. 将 {{variable}} 替换为实际值
    #   3. 返回渲染后的文本
    #
    # 注意：规则引擎不做真正的 LLM 调用，只是文本替换
    # 这样可以在不调用 LLM 的情况下，验证 prompt 模板的正确性
    print("=" * 70)
    print("第 3 步：理解评估原理 - 渲染")
    print("=" * 70)

    # 选择第一个模板进行演示
    demo_template = list(templates.values())[0]
    sample = dataset[0]

    print(f"  演示模板: {demo_template.name}")
    print(f"  演示样本: {sample.input}")
    print()

    # 渲染过程
    rendered = rule_based_render(demo_template, {"question": sample.input})
    print("  渲染结果:")
    print(f"    {rendered[:200]}...")
    print()

    # =========================================================================
    # 第 4 步：理解评估原理 - 关键词匹配
    # =========================================================================
    # extract_keywords() 提取文本中的关键词
    #   - 转换为小写
    #   - 移除标点符号
    #   - 过滤停用词 (the, is, a, etc.)
    #   - 返回关键词集合
    #
    # keyword_match() 计算两个文本的关键词匹配率
    #   - 匹配率 = 交集大小 / 期望关键词数量
    #   - 匹配阈值: 0.5 (50%)
    print("=" * 70)
    print("第 4 步：理解评估原理 - 关键词匹配")
    print("=" * 70)

    expected = sample.expected_output
    generated = rendered  # 规则引擎：输出 = 渲染后的模板

    expected_keywords = extract_keywords(expected)
    generated_keywords = extract_keywords(generated)

    print(f"  期望输出: {expected}")
    print(f"  生成输出: {generated[:100]}...")
    print()
    print(f"  期望关键词: {expected_keywords}")
    print(f"  生成关键词: {generated_keywords}")
    print()

    # keyword_based_evaluate() 返回 (simulated_output, is_match)
    _, is_match = keyword_based_evaluate(generated, expected)
    print(f"  关键词匹配: {'✓ 通过' if is_match else '✗ 未通过'}")
    print()

    # =========================================================================
    # 第 5 步：理解评估原理 - 文本相似度
    # =========================================================================
    # compute_similarity() 使用 Python 的 SequenceMatcher 计算文本相似度
    #   - 基于最长公共子序列 (LCS) 算法
    #   - 返回 0.0 到 1.0 之间的浮点数
    #   - 相似度阈值: 0.7 (70%)
    print("=" * 70)
    print("第 5 步：理解评估原理 - 文本相似度")
    print("=" * 70)

    similarity = compute_similarity(expected, generated)
    print(f"  文本相似度: {similarity:.1%}")
    print(f"  相似度阈值: 70%")
    print(f"  相似度结果: {'✓ 通过' if similarity >= 0.7 else '✗ 未通过'}")
    print()

    # =========================================================================
    # 第 6 步：理解评估原理 - Token 估算
    # =========================================================================
    # estimate_tokens() 估算文本的 token 数量
    #   - 英文: 按空格分词，每个词约 1-2 tokens
    #   - CJK 字符: 每个字符约 2 tokens
    #   - 标点符号: 约 1 token
    print("=" * 70)
    print("第 6 步：理解评估原理 - Token 估算")
    print("=" * 70)

    old_tokens = estimate_tokens(expected)
    new_tokens = estimate_tokens(generated)
    token_delta = new_tokens - old_tokens

    print(f"  期望输出 Token 数: {old_tokens}")
    print(f"  生成输出 Token 数: {new_tokens}")
    print(f"  Token 差异: {token_delta:+d}")
    print()

    # =========================================================================
    # 第 7 步：执行完整评估
    # =========================================================================
    # evaluate_prompts() 是完整的评估函数，它会：
    #   1. 对数据集中的每个样本，渲染新旧两个模板
    #   2. 计算关键词匹配和文本相似度
    #   3. 统计准确率、Token 成本和一致性
    #   4. 判断是否通过阈值检查
    #
    # 返回 EvalResult 对象，包含：
    #   - total_samples: 总样本数
    #   - accuracy_old: 旧模板准确率
    #   - accuracy_new: 新模板准确率
    #   - accuracy_delta: 准确率变化
    #   - token_cost_old: 旧模板 Token 成本
    #   - token_cost_new: 新模板 Token 成本
    #   - token_cost_delta: Token 成本变化率
    #   - consistency_score: 一致性评分
    #   - passed: 是否通过阈值检查
    #   - threshold: 阈值设置
    #   - details: 每个样本的详细结果
    print("=" * 70)
    print("第 7 步：执行完整评估")
    print("=" * 70)

    # 构建评估变量映射
    # 注意：数据集的 input 字段需要映射到 prompt 模板的变量
    # 这里我们使用 input 作为 question 变量的值
    eval_variables = {}
    for sample in dataset:
        eval_variables[sample.input] = {"question": sample.input}

    # 评估每个模板（与自身比较，验证模板的一致性）
    print()
    print("  评估结果:")
    print("  " + "-" * 66)
    print(f"  {'模板':<25} {'准确率':>8} {'Token':>8} {'一致性':>8} {'状态':>8}")
    print("  " + "-" * 66)

    for name, template in templates.items():
        result = evaluate_prompts(
            old_template=template,
            new_template=template,
            dataset=dataset,
            threshold=0.05,  # 允许 5% 的准确率下降
        )

        status = "✓ PASS" if result.passed else "✗ FAIL"
        print(
            f"  {name:<25} "
            f"{result.accuracy_new:>7.1%} "
            f"{result.token_cost_new:>7d} "
            f"{result.consistency_score:>7.1%} "
            f"{status:>8}"
        )

    print("  " + "-" * 66)
    print()

    # =========================================================================
    # 第 8 步：详细结果分析
    # =========================================================================
    # 每个样本的详细结果包含：
    #   - input: 输入文本
    #   - expected: 期望输出
    #   - old_output: 旧模板渲染结果
    #   - new_output: 新模板渲染结果
    #   - old_match: 旧模板是否匹配
    #   - new_match: 新模板是否匹配
    #   - similarity_delta: 相似度变化
    print("=" * 70)
    print("第 8 步：详细结果分析")
    print("=" * 70)

    # 选择一个模板进行详细分析
    demo_name = list(templates.keys())[0]
    demo_template = templates[demo_name]

    result = evaluate_prompts(
        old_template=demo_template,
        new_template=demo_template,
        dataset=dataset,
        threshold=0.05,
    )

    print(f"\n  模板: {demo_name}")
    print(f"  总样本数: {result.total_samples}")
    print(f"  准确率: {result.accuracy_new:.1%}")
    print(f"  Token 成本: {result.token_cost_new}")
    print(f"  一致性: {result.consistency_score:.1%}")
    print(f"  是否通过: {'是' if result.passed else '否'}")
    print()

    print("  前 5 个样本的详细结果:")
    print("  " + "-" * 66)

    for i, detail in enumerate(result.details[:5]):
        match_status = "✓" if detail.new_match else "✗"
        print(f"  [{i+1}] 输入: {detail.input}")
        print(f"      期望: {detail.expected}")
        print(f"      实际: {detail.new_output}")
        print(f"      匹配: {match_status} (相似度: {detail.similarity_delta:.1%})")
        print()

    # =========================================================================
    # 第 9 步：评估结果解读
    # =========================================================================
    print("=" * 70)
    print("第 9 步：评估结果解读")
    print("=" * 70)
    print("""
  评估指标说明：
  ┌─────────────────┬────────────────────────────────────────────┐
  │ 指标             │ 说明                                       │
  ├─────────────────┼────────────────────────────────────────────┤
  │ accuracy        │ 匹配样本数 / 总样本数                       │
  │                 │ 匹配条件: 关键词匹配率 >= 50%               │
  │                 │ 或文本相似度 >= 70%                         │
  ├─────────────────┼────────────────────────────────────────────┤
  │ token_cost      │ 所有样本输出的 token 数总和                 │
  │                 │ 用于评估 prompt 的成本效率                  │
  ├─────────────────┼────────────────────────────────────────────┤
  │ consistency     │ 新旧版本匹配率的一致性                      │
  │                 │ 1.0 = 完全一致，0.0 = 完全不同              │
  ├─────────────────┼────────────────────────────────────────────┤
  │ accuracy_delta  │ 新版本准确率 - 旧版本准确率                 │
  │                 │ 正值 = 改进，负值 = 退化                    │
  ├─────────────────┼────────────────────────────────────────────┤
  │ passed          │ accuracy_delta >= -threshold                │
  │                 │ 即准确率下降不超过阈值                       │
  └─────────────────┴────────────────────────────────────────────┘

  评估流程图：
  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
  │ 加载数据集   │───>│ 渲染模板     │───>│ 计算指标     │
  │ (JSONL)      │    │ (变量替换)   │    │ (匹配/相似)  │
  └──────────────┘    └──────────────┘    └──────────────┘
                                                │
                                                v
                                         ┌──────────────┐
                                         │ 判断是否通过 │
                                         │ (阈值检查)   │
                                         └──────────────┘
    """)

    print("=" * 70)
    print("评估完成！")
    print("=" * 70)
    print()
    print("下一步:")
    print("  - 查看 examples/llm_enhanced/ 了解 LLM 增强评估")
    print("  - 查看 examples/llm_as_judge/ 了解 LLM-as-judge 评估")
    print("  - 修改 prompt 模板后重新运行本脚本观察指标变化")
    print()


if __name__ == "__main__":
    main()
