#!/usr/bin/env python3
"""
LLM-as-Judge 评估示例 (LLM-as-Judge Evaluation)
=================================================

本示例展示如何使用 prompt-git-manager 的 Python API 进行 LLM-as-Judge 评估。

评估原理：
----------
LLM-as-Judge 评估使用一个独立的 LLM 作为评判者，对输出质量进行评分：

1. LLM 生成 (LLM Generation)
   - 使用生成模型 (如 gpt-3.5-turbo) 生成输出
   - 与 LLM 增强评估相同的生成过程

2. Judge 评分 (Judge Scoring)
   - 使用独立的评判模型 (如 gpt-4) 对输出评分
   - Judge 模型接收: 输入问题、期望输出、实际输出
   - Judge 模型返回: 0-1 分数和评分理由
   - 评分阈值: 0.7 (70 分以上视为通过)

3. 独立 Judge 模型 (Independent Judge)
   - 生成模型和评判模型可以不同
   - 推荐: 小模型生成，大模型评判
   - 例如: gpt-3.5-turbo 生成，gpt-4 评判
   - 这样既节省成本，又保证评判质量

4. 综合评分 (Overall Scoring)
   - accuracy: Judge 评分 >= 0.7 的样本比例
   - judge_results: 每个样本的 Judge 评分详情
   - 其他指标与 LLM 增强评估相同

使用场景：
----------
- 需要最准确的评估结果
- 需要评估输出质量而非仅文本相似度
- 需要理解 LLM 为什么给出某个评分
- 适合重要 prompt 变更的最终验证

运行方式：
----------
    cd examples/llm_as_judge
    export OPENAI_API_KEY=sk-xxx
    python run_eval.py
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from promptgit.schema import PromptTemplate
from promptgit.evaluator import load_dataset, compute_similarity
from promptgit.llm_evaluator import (
    get_llm_config,
    llm_generate_output,
    llm_judge_evaluate,
    evaluate_prompts_with_llm,
    compare_models,
)


def main():
    # =========================================================================
    # 第 1 步：加载数据集
    # =========================================================================
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
        print()

    # =========================================================================
    # 第 2 步：加载 Prompt 模板
    # =========================================================================
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
        print()

    # =========================================================================
    # 第 3 步：配置 LLM
    # =========================================================================
    # LLM-as-Judge 需要两个配置:
    #   1. 生成模型 (gen_config): 用于生成输出
    #   2. 评判模型 (judge_config): 用于评分
    #
    # 推荐配置:
    #   - 生成模型: gpt-3.5-turbo (成本低，速度快)
    #   - 评判模型: gpt-4 (质量高，评判准确)
    #
    # 也可以使用相同的模型，但独立模型通常效果更好
    print("=" * 70)
    print("第 3 步：配置 LLM")
    print("=" * 70)

    # 检查 API Key
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("  ⚠️  未设置 OPENAI_API_KEY 环境变量")
        print("  请设置后重新运行: export OPENAI_API_KEY=sk-xxx")
        print()
        print("  其他提供商的环境变量:")
        print("    - ANTHROPIC_API_KEY: Anthropic Claude")
        print("    - AZURE_API_KEY: Azure OpenAI")
        print()

        # 演示配置创建（不实际调用 LLM）
        gen_config = get_llm_config("openai", "gpt-3.5-turbo")
        judge_config = get_llm_config("openai", "gpt-4")

        print("  配置示例 (独立 Judge 模型):")
        print(f"    生成模型:")
        print(f"      提供商: {gen_config.provider}")
        print(f"      模型: {gen_config.model}")
        print(f"    评判模型:")
        print(f"      提供商: {judge_config.provider}")
        print(f"      模型: {judge_config.model}")
        print()

        # 演示跨提供商配置
        gen_config = get_llm_config("anthropic", "claude-3-haiku-20240307")
        judge_config = get_llm_config("openai", "gpt-4")

        print("  配置示例 (跨提供商):")
        print(f"    生成模型:")
        print(f"      提供商: {gen_config.provider}")
        print(f"      模型: {gen_config.model}")
        print(f"    评判模型:")
        print(f"      提供商: {judge_config.provider}")
        print(f"      模型: {judge_config.model}")
        print()

        # 演示本地模型配置
        gen_config = get_llm_config("ollama", "llama2")
        judge_config = get_llm_config("openai", "gpt-4")

        print("  配置示例 (本地 + 云端):")
        print(f"    生成模型 (本地):")
        print(f"      提供商: {gen_config.provider}")
        print(f"      模型: {gen_config.model}")
        print(f"      API Base: {gen_config.api_base}")
        print(f"    评判模型 (云端):")
        print(f"      提供商: {judge_config.provider}")
        print(f"      模型: {judge_config.model}")
        print()

        print("=" * 70)
        print("演示结束（需要 API Key 才能实际运行 LLM-as-Judge 评估）")
        print("=" * 70)
        return

    # 创建 LLM 配置
    # 生成模型: gpt-3.5-turbo (成本低，速度快)
    gen_config = get_llm_config("openai", "gpt-3.5-turbo")

    # 评判模型: gpt-4 (质量高，评判准确)
    judge_config = get_llm_config("openai", "gpt-4")

    print(f"  LLM 配置 (独立 Judge 模型):")
    print(f"    生成模型:")
    print(f"      提供商: {gen_config.provider}")
    print(f"      模型: {gen_config.model}")
    print(f"    评判模型:")
    print(f"      提供商: {judge_config.provider}")
    print(f"      模型: {judge_config.model}")
    print()

    # =========================================================================
    # 第 4 步：理解评估原理 - LLM 生成
    # =========================================================================
    # 与 LLM 增强评估相同的生成过程
    # 使用生成模型 (gpt-3.5-turbo) 生成输出
    print("=" * 70)
    print("第 4 步：理解评估原理 - LLM 生成")
    print("=" * 70)

    demo_template = list(templates.values())[0]
    sample = dataset[0]

    print(f"  演示模板: {demo_template.name}")
    print(f"  演示样本: {sample.input}")
    print()

    # 调用 LLM 生成输出
    print("  调用生成模型 (gpt-3.5-turbo) 生成输出...")
    llm_output = llm_generate_output(gen_config, demo_template, {"question": sample.input})

    print(f"  LLM 输出:")
    print(f"    {llm_output[:200]}...")
    print()

    # =========================================================================
    # 第 5 步：理解评估原理 - Judge 评分
    # =========================================================================
    # llm_judge_evaluate() 是 Judge 评估的核心:
    #   1. 构建评判 prompt (包含输入、期望输出、实际输出)
    #   2. 调用评判模型 (gpt-4) 进行评分
    #   3. 解析 JSON 响应，提取分数和理由
    #
    # Judge 评分标准:
    #   - 0.0-0.3: 差 (输出与期望严重不符)
    #   - 0.3-0.5: 一般 (输出部分正确，但有明显问题)
    #   - 0.5-0.7: 良好 (输出基本正确，但有改进空间)
    #   - 0.7-1.0: 优秀 (输出与期望高度一致)
    #
    # 评分阈值: 0.7 (70 分以上视为通过)
    print("=" * 70)
    print("第 5 步：理解评估原理 - Judge 评分")
    print("=" * 70)

    expected = sample.expected_output

    print(f"  期望输出: {expected}")
    print(f"  LLM 输出: {llm_output[:100]}...")
    print()

    # 调用 Judge 评分
    print("  调用评判模型 (gpt-4) 进行评分...")
    judge_result = llm_judge_evaluate(judge_config, sample.input, expected, llm_output)

    print(f"  Judge 评分结果:")
    print(f"    分数: {judge_result.score:.2f} (范围: 0.0-1.0)")
    print(f"    阈值: 0.70")
    print(f"    结果: {'✓ 通过' if judge_result.score >= 0.7 else '✗ 未通过'}")
    print(f"    理由: {judge_result.reasoning}")
    print()

    # =========================================================================
    # 第 6 步：执行完整评估 (LLM-as-Judge)
    # =========================================================================
    # evaluate_prompts_with_llm() 使用 use_judge=True 启用 Judge 模式
    # 它会:
    #   1. 对数据集中的每个样本，调用生成模型生成输出
    #   2. 调用评判模型对每个输出进行评分
    #   3. 统计评分结果，计算准确率
    #   4. 判断是否通过阈值检查
    #
    # 参数:
    #   - old_template: 旧版本模板
    #   - new_template: 新版本模板
    #   - dataset: 数据集
    #   - llm_config: 生成模型配置
    #   - threshold: 阈值 (默认 0.05)
    #   - use_judge: 是否使用 Judge (True)
    #   - judge_config: Judge 模型配置 (可选，不传则使用同一个模型)
    print("=" * 70)
    print("第 6 步：执行完整评估 (LLM-as-Judge)")
    print("=" * 70)

    print("  开始 LLM-as-Judge 评估...")
    print("  (这可能需要几分钟时间，取决于数据集大小和 LLM 响应速度)")
    print()

    result = evaluate_prompts_with_llm(
        old_template=list(templates.values())[0],
        new_template=list(templates.values())[0],
        dataset=dataset,
        llm_config=gen_config,
        threshold=0.05,
        use_judge=True,  # 启用 Judge 模式
        judge_config=judge_config,  # 使用独立的 Judge 模型
    )

    print(f"  评估结果:")
    print(f"    总样本数: {result.total_samples}")
    print(f"    准确率 (旧): {result.accuracy_old:.1%}")
    print(f"    准确率 (新): {result.accuracy_new:.1%}")
    print(f"    准确率变化: {result.accuracy_delta:+.1%}")
    print(f"    一致性: {result.consistency_score:.1%}")
    print(f"    是否通过: {'是' if result.passed else '否'}")
    print()

    # =========================================================================
    # 第 7 步：Judge 评分详情
    # =========================================================================
    # judge_results 包含每个样本的 Judge 评分详情:
    #   - score: 评分 (0.0-1.0)
    #   - reasoning: 评分理由
    #   - raw_response: Judge 的原始响应 (JSON)
    print("=" * 70)
    print("第 7 步：Judge 评分详情")
    print("=" * 70)

    print("  前 5 个样本的 Judge 评分:")
    print("  " + "-" * 66)

    for i, detail in enumerate(result.details[:5]):
        judge = result.judge_results[i] if i < len(result.judge_results) else None
        match_status = "✓" if detail.new_match else "✗"

        print(f"  [{i+1}] 输入: {detail.input}")
        print(f"      期望: {detail.expected}")
        print(f"      LLM 输出: {detail.new_output[:100]}...")
        print(f"      匹配: {match_status}")

        if judge:
            print(f"      Judge 分数: {judge.score:.2f}")
            print(f"      Judge 理由: {judge.reasoning[:100]}...")
        print()

    # =========================================================================
    # 第 8 步：模型对比 (compare_models)
    # =========================================================================
    # compare_models() 对比两个模型在同一数据集上的表现
    # 支持:
    #   - 同提供商对比: gpt-3.5-turbo vs gpt-4
    #   - 跨提供商对比: openai:gpt-4 vs anthropic:claude-3-opus
    #
    # 返回 LLMCompareResult 列表，包含:
    #   - model_a: 模型 A 名称
    #   - model_b: 模型 B 名称
    #   - score_a: 模型 A 评分
    #   - score_b: 模型 B 评分
    #   - winner: 获胜者 (a/b/tie)
    #   - reasoning: 评判理由
    print("=" * 70)
    print("第 8 步：模型对比 (compare_models)")
    print("=" * 70)

    print("  对比 gpt-3.5-turbo 和 gpt-4 的表现...")
    print("  (这可能需要几分钟时间)")
    print()

    # 同提供商对比
    config_a = get_llm_config("openai", "gpt-3.5-turbo")
    config_b = get_llm_config("openai", "gpt-4")

    compare_results = compare_models(
        template=list(templates.values())[0],
        dataset=dataset,
        config_a=config_a,
        config_b=config_b,
    )

    print("  模型对比结果:")
    print("  " + "-" * 66)
    print(f"  {'样本':<20} {'gpt-3.5-turbo':>12} {'gpt-4':>12} {'获胜者':>8}")
    print("  " + "-" * 66)

    for i, cr in enumerate(compare_results[:5]):
        print(
            f"  [{i+1}] {cr.winner:>8} "
            f"{cr.score_a:>11.2f} "
            f"{cr.score_b:>11.2f} "
            f"{cr.winner:>8}"
        )

    print("  " + "-" * 66)
    print()

    # 统计获胜次数
    wins_a = sum(1 for cr in compare_results if cr.winner == "a")
    wins_b = sum(1 for cr in compare_results if cr.winner == "b")
    ties = sum(1 for cr in compare_results if cr.winner == "tie")

    print(f"  总计:")
    print(f"    gpt-3.5-turbo 获胜: {wins_a} 次")
    print(f"    gpt-4 获胜: {wins_b} 次")
    print(f"    平局: {ties} 次")
    print()

    # =========================================================================
    # 第 9 步：评估结果解读
    # =========================================================================
    print("=" * 70)
    print("第 9 步：评估结果解读")
    print("=" * 70)
    print("""
  LLM-as-Judge 评估 vs 其他评估方式:

  ┌─────────────────┬──────────────┬──────────────┬──────────────┐
  │ 特性             │ 规则引擎     │ LLM 增强     │ LLM-as-Judge │
  ├─────────────────┼──────────────┼──────────────┼──────────────┤
  │ 输出来源         │ 模板渲染     │ LLM 生成     │ LLM 生成     │
  │ 评分方式         │ 关键词匹配   │ 文本相似度   │ Judge 评分   │
  │ API Key          │ 不需要       │ 需要         │ 需要 (x2)    │
  │ 运行速度         │ 快           │ 中           │ 慢           │
  │ 评估准确性       │ 低           │ 中           │ 高           │
  │ 评分可解释性     │ 无           │ 无           │ 有 (理由)    │
  │ 适用场景         │ 快速验证     │ 精确评估     │ 最终验证     │
  │ 成本             │ 免费         │ 低           │ 高           │
  └─────────────────┴──────────────┴──────────────┴──────────────┘

  Judge 评分流程:
  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
  │ 生成模型     │───>│ 构建评判     │───>│ 评判模型     │
  │ (gpt-3.5)    │    │ Prompt       │    │ (gpt-4)      │
  └──────────────┘    └──────────────┘    └──────────────┘
                                                │
                                                v
                                         ┌──────────────┐
                                         │ 解析评分     │
                                         │ (JSON)       │
                                         └──────────────┘

  独立 Judge 模型的优势:
  ┌─────────────────────────────────────────────────────────────┐
  │ 1. 成本优化: 小模型生成 (gpt-3.5-turbo) + 大模型评判 (gpt-4) │
  │ 2. 质量保证: 大模型评判更准确                                 │
  │ 3. 灵活性: 可以混合不同提供商的模型                          │
  │ 4. 可解释性: Judge 提供评分理由                               │
  └─────────────────────────────────────────────────────────────┘
    """)

    print("=" * 70)
    print("评估完成！")
    print("=" * 70)
    print()
    print("总结:")
    print("  - 规则引擎: 快速验证，无需 API Key")
    print("  - LLM 增强: 精确评估，需要 API Key")
    print("  - LLM-as-Judge: 最终验证，需要 API Key，评分可解释")
    print()
    print("下一步:")
    print("  - 尝试不同的生成/评判模型组合")
    print("  - 使用跨提供商模型对比 (如 OpenAI vs Anthropic)")
    print("  - 修改 prompt 模板后重新运行观察指标变化")
    print()


if __name__ == "__main__":
    main()
