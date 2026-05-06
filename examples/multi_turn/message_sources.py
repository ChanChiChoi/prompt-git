#!/usr/bin/env python3
"""
消息来源的三种组合场景演示
==========================

本示例演示模板级 messages 和样本级 messages 的三种组合：

  场景 A：模板有 messages + 样本有 messages → 样本覆盖模板
  场景 B：模板有 messages + 样本无 messages → 使用模板默认
  场景 C：模板无 messages + 样本有 messages → 仅用样本历史

运行方式：
    cd examples/multi_turn
    python message_sources.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from promptgit.schema import PromptTemplate
from promptgit.evaluator import load_dataset, rule_based_render


def print_rendered(title: str, rendered: str):
    """格式化打印渲染结果"""
    print(f"  {title}")
    print("  " + "-" * 66)
    for line in rendered.split("\n\n"):
        print(f"  {line}")
    print("  " + "-" * 66)
    print()


def main():
    prompts_dir = Path(__file__).parent.parent / "prompts"
    datasets_dir = Path(__file__).parent.parent / "datasets"

    # =========================================================================
    # 场景 A：模板有 messages + 样本有 messages → 样本覆盖模板
    # =========================================================================
    print("=" * 70)
    print("场景 A：模板有 messages + 样本有 messages → 样本覆盖模板")
    print("=" * 70)
    print()
    print("  当模板和样本都定义了 messages 时，使用样本的，忽略模板的。")
    print("  适用于：每个样本需要完全不同的对话历史。")
    print()

    template_a = PromptTemplate.from_yaml(prompts_dir / "tutoring_multi_turn.yaml")
    dataset_a = load_dataset(datasets_dir / "tutoring_dataset_with_messages.jsonl")

    print(f"  模板: {template_a.name}")
    print(f"  模板 messages 轮次: {len(template_a.messages)}")
    for msg in template_a.messages:
        print(f"    [{msg['role']}] {msg['content']}")
    print()

    sample = dataset_a[0]
    print(f"  样本 input: {sample.input}")
    print(f"  样本 messages 轮次: {len(sample.messages)}")
    for msg in sample.messages:
        print(f"    [{msg['role']}] {msg['content'][:60]}...")
    print()

    # 渲染：样本 messages 覆盖模板 messages
    variables = {
        "topic": sample.metadata.get("topic", "Python"),
        "current_question": sample.input,
    }
    rendered = rule_based_render(template_a, variables, sample_messages=sample.messages)
    print_rendered("渲染结果（使用样本 messages，模板 messages 被忽略）:", rendered)

    print("  最终 LLM 收到的消息：")
    print("  " + "-" * 66)
    for i, line in enumerate(rendered.split("\n\n")):
        if i == 0:
            print(f"  {line}  ← 来自模板 system_prompt")
        elif i < len(sample.messages) + 1:
            print(f"  {line}  ← 来自样本 messages")
        else:
            print(f"  {line}  ← 来自样本 input")
    print("  " + "-" * 66)
    print()

    # =========================================================================
    # 场景 B：模板有 messages + 样本无 messages → 使用模板默认
    # =========================================================================
    print("=" * 70)
    print("场景 B：模板有 messages + 样本无 messages → 使用模板默认")
    print("=" * 70)
    print()
    print("  样本没有定义 messages 时，使用模板的 messages 作为默认对话历史。")
    print("  适用于：所有样本共享相同的对话结构，通过变量切换主题。")
    print()

    template_b = PromptTemplate.from_yaml(prompts_dir / "tutoring_multi_turn.yaml")
    dataset_b = load_dataset(datasets_dir / "tutoring_dataset_no_messages.jsonl")

    print(f"  模板: {template_b.name}")
    print(f"  模板 messages 轮次: {len(template_b.messages)}")
    for msg in template_b.messages:
        print(f"    [{msg['role']}] {msg['content']}")
    print()

    sample_b = dataset_b[0]
    print(f"  样本 input: {sample_b.input}")
    print(f"  样本 messages: {sample_b.messages}  (空列表，无样本级消息)")
    print()

    # 渲染：使用模板 messages（sample_messages=None）
    variables_b = {
        "topic": sample_b.metadata.get("topic", "Python"),
        "current_question": sample_b.input,
    }
    rendered_b = rule_based_render(template_b, variables_b)
    print_rendered("渲染结果（使用模板 messages，变量被替换）:", rendered_b)

    print("  最终 LLM 收到的消息：")
    print("  " + "-" * 66)
    for i, line in enumerate(rendered_b.split("\n\n")):
        if i == 0:
            print(f"  {line}  ← 来自模板 system_prompt")
        elif i < len(template_b.messages) + 1:
            print(f"  {line}  ← 来自模板 messages（{{{{topic}}}} 已替换为 {sample_b.metadata.get('topic')}）")
        else:
            print(f"  {line}  ← 来自样本 input")
    print("  " + "-" * 66)
    print()

    # 对比不同样本使用模板 messages 的效果
    print("  不同样本使用同一模板 messages，通过变量适配：")
    print()
    for i, s in enumerate(dataset_b[:3]):
        v = {"topic": s.metadata.get("topic", "Python"), "current_question": s.input}
        r = rule_based_render(template_b, v)
        # 只显示 user 和 assistant 消息部分
        parts = r.split("\n\n")
        print(f"    样本 {i+1}（topic={s.metadata.get('topic')}）:")
        for p in parts[1:]:  # 跳过 system
            print(f"      {p[:70]}...")
        print()

    # =========================================================================
    # 场景 C：模板无 messages + 样本有 messages → 仅用样本历史
    # =========================================================================
    print("=" * 70)
    print("场景 C：模板无 messages + 样本有 messages → 仅用样本历史")
    print("=" * 70)
    print()
    print("  模板是单轮的，但样本自带对话历史。")
    print("  适用于：部分样本需要多轮上下文，部分不需要，灵活混合。")
    print()

    template_c = PromptTemplate.from_yaml(prompts_dir / "tutor_no_messages.yaml")
    dataset_c_mixed = load_dataset(datasets_dir / "tutoring_dataset_with_messages.jsonl")
    dataset_c_plain = load_dataset(datasets_dir / "tutoring_dataset_no_messages.jsonl")

    print(f"  模板: {template_c.name}")
    print(f"  模板 messages: {template_c.messages}  (空列表，单轮模板)")
    print()

    # 样本 1：有 messages
    sample_c1 = dataset_c_mixed[0]
    variables_c1 = {"current_question": sample_c1.input}
    rendered_c1 = rule_based_render(template_c, variables_c1, sample_messages=sample_c1.messages)

    print(f"  样本 1（有 messages）: {sample_c1.input}")
    print(f"  样本 messages 轮次: {len(sample_c1.messages)}")
    print_rendered("渲染结果（使用样本 messages）:", rendered_c1)

    # 样本 2：无 messages
    sample_c2 = dataset_c_plain[0]
    variables_c2 = {"current_question": sample_c2.input}
    rendered_c2 = rule_based_render(template_c, variables_c2)

    print(f"  样本 2（无 messages）: {sample_c2.input}")
    print(f"  样本 messages: {sample_c2.messages}  (空列表)")
    print_rendered("渲染结果（单轮，无历史）:", rendered_c2)

    # =========================================================================
    # 总结
    # =========================================================================
    print("=" * 70)
    print("总结：消息来源优先级")
    print("=" * 70)
    print("""
  ┌─────────────────┬─────────────────┬────────────────────────────────┐
  │ 模板 messages   │ 样本 messages   │ 最终使用                       │
  ├─────────────────┼─────────────────┼────────────────────────────────┤
  │ 有              │ 有              │ 样本的（覆盖模板）             │
  │ 有              │ 无              │ 模板的（变量被替换）           │
  │ 无              │ 有              │ 样本的                         │
  │ 无              │ 无              │ 无（单轮模式）                 │
  └─────────────────┴─────────────────┴────────────────────────────────┘

  使用建议：

  ┌─────────────────────────────────────────────────────────────────┐
  │ 所有样本共享相同对话结构 → 只在模板定义 messages，样本不定义    │
  │ 每个样本有不同对话历史   → 在样本中定义 messages，模板可不定义  │
  │ 混合场景                 → 部分样本定义 messages，部分不定义    │
  └─────────────────────────────────────────────────────────────────┘
    """)

    print("=" * 70)
    print("演示完成！")
    print("=" * 70)
    print()


if __name__ == "__main__":
    main()
