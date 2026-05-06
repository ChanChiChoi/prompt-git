#!/usr/bin/env python3
"""
多轮对话评估示例 (Multi-Turn Conversation Evaluation)
=====================================================

本示例展示如何使用 prompt-git-manager 评估多轮对话 prompt 模板。

多轮对话与单轮的区别：
------------------------
- 单轮：system_prompt + user_template（一问一答）
- 多轮：system_prompt + messages（历史对话）+ user_template（当前轮次）

消息来源的两个层级：
--------------------
1. 模板级 messages：定义在 YAML 模板中，所有样本共享的对话结构
2. 样本级 messages：定义在数据集 JSONL 中，每个样本独立的对话历史

优先级：样本级 messages 优先于模板级 messages

数据集格式：
-----------
每个样本可包含 messages 字段：
{
    "input": "当前用户问题",
    "expected_output": "期望输出",
    "metadata": {...},
    "messages": [
        {"role": "user", "content": "历史问题"},
        {"role": "assistant", "content": "历史回答"}
    ]
}

评估行为差异：
--------------
1. 规则引擎模式：
   - messages 被渲染为结构化文本：[system] ... [user] ... [assistant] ...
   - 然后进行关键词匹配和相似度计算

2. LLM 增强模式：
   - messages 被构建为完整的 message 列表，直接传入 LLM API
   - LLM 能看到完整的对话历史，生成更准确的输出

3. Diff 检测：
   - 轮次增删 → HIGH 风险
   - 角色变化 → HIGH 风险
   - 内容修改 → MEDIUM 风险

运行方式：
----------
    cd examples/multi_turn
    python run_eval.py

如需 LLM 增强评估：
    export OPENAI_API_KEY=sk-xxx
    python run_eval.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from promptgit.schema import PromptTemplate
from promptgit.evaluator import (
    load_dataset,
    evaluate_prompts,
    rule_based_render,
    extract_keywords,
    compute_similarity,
    estimate_tokens,
)


def main():
    # =========================================================================
    # 第 1 步：加载多轮对话数据集
    # =========================================================================
    print("=" * 70)
    print("第 1 步：加载多轮对话数据集")
    print("=" * 70)

    dataset_path = Path(__file__).parent.parent / "datasets" / "tutoring_dataset.jsonl"
    dataset = load_dataset(dataset_path)

    print(f"  数据集路径: {dataset_path}")
    print(f"  样本数量: {len(dataset)}")
    print()
    print("  数据集内容预览:")
    for i, sample in enumerate(dataset[:3]):
        print(f"    [{i+1}] Q: {sample.input}")
        print(f"        A: {sample.expected_output[:80]}...")
        print(f"        话题: {sample.metadata.get('topic', 'N/A')}")
        print(f"        难度: {sample.metadata.get('difficulty', 'N/A')}")
        print(f"        历史轮次: {len(sample.messages)}")
        if sample.messages:
            for msg in sample.messages:
                print(f"          [{msg['role']}] {msg['content'][:50]}...")
        print()

    # =========================================================================
    # 第 2 步：加载多轮 Prompt 模板
    # =========================================================================
    print("=" * 70)
    print("第 2 步：加载多轮 Prompt 模板")
    print("=" * 70)

    prompts_dir = Path(__file__).parent.parent / "prompts"
    multi_turn_files = [
        f for f in prompts_dir.glob("*.yaml")
        if "multi_turn" in f.stem or "tutoring" in f.stem
    ]

    templates = {}
    for pf in multi_turn_files:
        template = PromptTemplate.from_yaml(pf)
        templates[pf.stem] = template
        print(f"  已加载: {pf.name}")
        print(f"    名称: {template.name}")
        print(f"    版本: {template.version}")
        print(f"    模板 messages 轮次: {len(template.messages)}")
        for j, msg in enumerate(template.messages):
            print(f"      [{j}] {msg['role']}: {msg['content'][:50]}...")
        print()

    if not templates:
        print("  未找到多轮模板，请确认 examples/prompts/ 中存在多轮模板文件")
        return

    # =========================================================================
    # 第 3 步：理解消息来源的优先级
    # =========================================================================
    # 样本级 messages 优先于模板级 messages
    # 这允许每个样本有自己独特的对话历史
    print("=" * 70)
    print("第 3 步：理解消息来源的优先级")
    print("=" * 70)

    demo_template = list(templates.values())[0]
    sample_with_msgs = dataset[0]  # 有样本级 messages
    sample_without_msgs = type(dataset[0])(
        input=dataset[0].input,
        expected_output=dataset[0].expected_output,
        metadata=dataset[0].metadata,
        messages=[],  # 无样本级 messages
    )

    variables = {
        "topic": sample_with_msgs.metadata.get("topic", "Python"),
        "current_question": sample_with_msgs.input,
    }

    # 使用模板级 messages 渲染
    rendered_template = rule_based_render(demo_template, variables, sample_messages=None)

    # 使用样本级 messages 渲染（覆盖模板级）
    rendered_sample = rule_based_render(demo_template, variables, sample_messages=sample_with_msgs.messages)

    print(f"  模板: {demo_template.name}")
    print(f"  样本: {sample_with_msgs.input}")
    print()
    print("  使用模板级 messages 渲染:")
    print("  " + "-" * 66)
    for line in rendered_template.split("\n\n")[:4]:
        print(f"  {line}")
    print("  " + "-" * 66)
    print()
    print("  使用样本级 messages 渲染（覆盖模板级）:")
    print("  " + "-" * 66)
    for line in rendered_sample.split("\n\n")[:4]:
        print(f"  {line}")
    print("  " + "-" * 66)
    print()

    # =========================================================================
    # 第 4 步：理解多轮变量替换
    # =========================================================================
    # messages 中的 {{variable}} 占位符会被替换
    # 与 user_template 使用相同的变量池
    print("=" * 70)
    print("第 4 步：理解多轮变量替换")
    print("=" * 70)

    print("  模板级 messages 中的变量替换示例:")
    for msg in demo_template.messages:
        original = msg["content"]
        # 手动替换演示
        replaced = original
        for var_name, var_value in variables.items():
            replaced = replaced.replace(f"{{{{{var_name}}}}}", str(var_value))
        if "{{" not in original:
            print(f"    [{msg['role']}] {original}")
        else:
            print(f"    [{msg['role']}] 原始: {original}")
            print(f"           替换后: {replaced}")
    print()
    print("  样本级 messages 已经是具体值，无需变量替换:")
    if sample_with_msgs.messages:
        for msg in sample_with_msgs.messages[:2]:
            print(f"    [{msg['role']}] {msg['content'][:60]}...")
    print()

    # =========================================================================
    # 第 5 步：多轮模板的评估
    # =========================================================================
    # evaluate_prompts() 对多轮模板的处理：
    #   1. 检查样本是否有 messages，有则使用样本级，否则使用模板级
    #   2. rule_based_render() 渲染为结构化文本
    #   3. keyword_based_evaluate() 进行关键词匹配
    #   4. 计算 accuracy、token_cost、consistency
    print("=" * 70)
    print("第 5 步：多轮模板的评估")
    print("=" * 70)

    # 构建评估变量
    eval_dataset = []
    for sample in dataset:
        eval_dataset.append(sample)

    # 评估每个模板（与自身比较，验证一致性）
    print()
    print("  评估结果:")
    print("  " + "-" * 66)
    print(f"  {'模板':<25} {'准确率':>8} {'Token':>8} {'一致性':>8} {'状态':>8}")
    print("  " + "-" * 66)

    for name, template in templates.items():
        result = evaluate_prompts(
            old_template=template,
            new_template=template,
            dataset=eval_dataset,
            threshold=0.05,
        )

        status = "PASS" if result.passed else "FAIL"
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
    # 第 6 步：详细结果分析
    # =========================================================================
    print("=" * 70)
    print("第 6 步：详细结果分析")
    print("=" * 70)

    demo_name = list(templates.keys())[0]
    demo_template = templates[demo_name]

    result = evaluate_prompts(
        old_template=demo_template,
        new_template=demo_template,
        dataset=eval_dataset,
        threshold=0.05,
    )

    print(f"\n  模板: {demo_name}")
    print(f"  总样本数: {result.total_samples}")
    print(f"  准确率: {result.accuracy_new:.1%}")
    print(f"  Token 成本: {result.token_cost_new}")
    print(f"  一致性: {result.consistency_score:.1%}")
    print()

    print("  前 5 个样本的详细结果:")
    print("  " + "-" * 66)

    for i, detail in enumerate(result.details[:5]):
        match_status = "MATCH" if detail.new_match else "MISS"
        print(f"  [{i+1}] 输入: {detail.input[:60]}...")
        print(f"      期望: {detail.expected[:60]}...")
        print(f"      实际: {detail.new_output[:60]}...")
        print(f"      状态: {match_status}")
        print()

    # =========================================================================
    # 第 7 步：单轮 vs 多轮对比
    # =========================================================================
    # 多轮模板渲染后包含更多上下文，可能影响匹配结果
    # 这里对比同一个问题在单轮和多轮下的评估差异
    print("=" * 70)
    print("第 7 步：单轮 vs 多轮渲染对比")
    print("=" * 70)

    # 创建单轮版本（去除 messages）
    single_turn_data = {
        "name": "python-tutor-single",
        "version": "1.0.0",
        "system_prompt": demo_template.system_prompt,
        "user_template": demo_template.user_template,
        "variables": demo_template.variables,
        "constraints": demo_template.constraints,
        "metadata": demo_template.metadata,
    }
    single_turn = PromptTemplate.model_validate(single_turn_data)

    sample = eval_dataset[0]
    variables = {
        "topic": sample.metadata.get("topic", "Python"),
        "current_question": sample.input,
    }

    multi_rendered = rule_based_render(demo_template, variables, sample_messages=sample.messages)
    single_rendered = rule_based_render(single_turn, variables)

    print(f"\n  单轮渲染（{estimate_tokens(single_rendered)} tokens）:")
    print(f"  {single_rendered[:150]}...")
    print()
    print(f"  多轮渲染（{estimate_tokens(multi_rendered)} tokens）:")
    print(f"  {multi_rendered[:150]}...")
    print()

    # 对比评估
    multi_result = evaluate_prompts(demo_template, demo_template, eval_dataset)
    single_result = evaluate_prompts(single_turn, single_turn, eval_dataset)

    print("  评估对比:")
    print(f"  {'模式':<12} {'准确率':>8} {'Token':>8} {'一致性':>8}")
    print(f"  {'单轮':<12} {single_result.accuracy_new:>7.1%} {single_result.token_cost_new:>7d} {single_result.consistency_score:>7.1%}")
    print(f"  {'多轮':<12} {multi_result.accuracy_new:>7.1%} {multi_result.token_cost_new:>7d} {multi_result.consistency_score:>7.1%}")
    print()

    # =========================================================================
    # 第 8 步：结果解读
    # =========================================================================
    print("=" * 70)
    print("第 8 步：结果解读")
    print("=" * 70)
    print("""
  多轮对话评估要点：

  ┌─────────────────┬────────────────────────────────────────────┐
  │ 方面             │ 说明                                       │
  ├─────────────────┼────────────────────────────────────────────┤
  │ 消息来源         │ 样本级 messages 优先于模板级 messages       │
  │ 渲染格式         │ [system] [user] [assistant] [user] 结构化  │
  │ 变量替换         │ 模板 messages 和 user_template 共享变量池   │
  │ Token 成本       │ 多轮渲染包含历史，token 数更多              │
  │ LLM 模式        │ messages 直传 API，保留完整对话上下文       │
  │ Diff 风险        │ 轮次增删=HIGH，内容修改=MEDIUM             │
  └─────────────────┴────────────────────────────────────────────┘

  消息来源优先级：

  ┌─────────────────────────────────────────────────────────────┐
  │ 1. 样本级 messages（数据集 JSONL 中的 messages 字段）        │
  │    → 每个样本独立的对话历史，覆盖模板级                      │
  │                                                             │
  │ 2. 模板级 messages（YAML 模板中的 messages 字段）            │
  │    → 所有样本共享的默认对话结构                              │
  │                                                             │
  │ 3. 无 messages（单轮模式）                                   │
  │    → 仅使用 system_prompt + user_template                   │
  └─────────────────────────────────────────────────────────────┘

  LLM 增强模式的优势（多轮场景更明显）：

  ┌─────────────────────────────────────────────────────────────┐
  │ 规则引擎：渲染为文本 → 丢失结构信息，关键词匹配可能不准     │
  │ LLM 模式：messages 直传 → LLM 真正理解对话历史，输出更准确  │
  └─────────────────────────────────────────────────────────────┘

  建议：
  - 多轮对话场景优先使用 LLM 增强评估
  - 规则引擎适合快速验证模板格式是否正确
  - 使用 pg diff 检测 messages 变更的风险等级
  - 使用样本级 messages 为每个样本提供独立的对话上下文
    """)

    print("=" * 70)
    print("评估完成！")
    print("=" * 70)
    print()
    print("下一步:")
    print("  - 设置 OPENAI_API_KEY 使用 LLM 增强评估")
    print("  - 修改数据集中的 messages 观察评估变化")
    print("  - 使用 pg diff 对比不同版本的多轮模板")
    print()


if __name__ == "__main__":
    main()
