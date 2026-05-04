#!/usr/bin/env python3
"""
LLM 增强评估示例 (LLM-Enhanced Evaluation)
============================================

本示例展示如何使用 prompt-git-manager 的 Python API 进行 LLM 增强评估。

评估原理：
----------
LLM 增强评估在规则引擎的基础上，使用 LLM 生成真实的输出：

1. LLM 配置 (LLM Config)
   - 支持多种提供商: OpenAI, Anthropic, Azure, Ollama, vLLM, SGLang
   - 通过 get_llm_config() 创建配置对象
   - 自动设置 API Base（本地模型）和 API Key（环境变量）

2. LLM 生成 (LLM Generation)
   - llm_generate_output() 调用 LLM 生成输出
   - 将 system_prompt 和渲染后的 user_template 发送给 LLM
   - 返回 LLM 的响应文本

3. 相似度匹配 (Similarity Matching)
   - 与规则引擎相同，使用 compute_similarity() 计算相似度
   - 但匹配的是 LLM 的真实输出，而非模板渲染结果
   - 更准确地反映 prompt 变更对实际输出的影响

4. 综合评分 (Overall Scoring)
   - 与规则引擎相同的评分逻辑
   - 但基于 LLM 输出计算，更有实际意义

使用场景：
----------
- 需要评估 prompt 变更对 LLM 实际输出的影响
- 需要更准确的评估结果（比规则引擎更接近真实场景）
- 支持多种 LLM 提供商
- 适合中等规模数据集的评估

运行方式：
----------
    cd examples/llm_enhanced
    export OPENAI_API_KEY=sk-xxx  # 或其他提供商的 API Key
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
    evaluate_prompts_with_llm,
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
    # get_llm_config() 创建 LLM 配置对象
    # 支持的提供商:
    #   - openai: OpenAI API (需要 OPENAI_API_KEY)
    #   - anthropic: Anthropic API (需要 ANTHROPIC_API_KEY)
    #   - azure: Azure OpenAI (需要 AZURE_API_KEY)
    #   - ollama: 本地 Ollama (默认 http://localhost:11434)
    #   - vllm: 本地 vLLM (默认 http://localhost:8000/v1)
    #   - sglang: 本地 SGLang (默认 http://localhost:30000/v1)
    #
    # 本地模型自动设置 api_base，无需手动配置
    # 云提供商从环境变量读取 API Key
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
        print("    - OLLAMA_API_KEY: Ollama (可选)")
        print()
        print("  本地模型无需 API Key，但需要启动对应服务:")
        print("    - Ollama: ollama serve")
        print("    - vLLM: python -m vllm.entrypoints.openai.api_server")
        print("    - SGLang: python -m sglang.launch_server")
        print()

        # 使用模拟模式继续演示
        print("  本示例将使用模拟数据继续演示评估流程...")
        print("  实际运行时，请设置有效的 API Key")
        print()

        # 演示配置创建（不实际调用 LLM）
        config = get_llm_config("openai", "gpt-3.5-turbo")
        print(f"  配置示例 (OpenAI):")
        print(f"    提供商: {config.provider}")
        print(f"    模型: {config.model}")
        print(f"    API Base: {config.api_base or '默认'}")
        print(f"    温度: {config.temperature}")
        print(f"    最大 Token: {config.max_tokens}")
        print()

        config = get_llm_config("ollama", "llama2")
        print(f"  配置示例 (Ollama 本地):")
        print(f"    提供商: {config.provider}")
        print(f"    模型: {config.model}")
        print(f"    API Base: {config.api_base}")
        print()

        config = get_llm_config("vllm", "meta-llama/Llama-2-7b-chat-hf")
        print(f"  配置示例 (vLLM 本地):")
        print(f"    提供商: {config.provider}")
        print(f"    模型: {config.model}")
        print(f"    API Base: {config.api_base}")
        print()

        print("=" * 70)
        print("演示结束（需要 API Key 才能实际运行 LLM 评估）")
        print("=" * 70)
        return

    # 创建 LLM 配置
    config = get_llm_config("openai", "gpt-3.5-turbo")

    print(f"  LLM 配置:")
    print(f"    提供商: {config.provider}")
    print(f"    模型: {config.model}")
    print(f"    API Base: {config.api_base or '默认 (api.openai.com)'}")
    print(f"    温度: {config.temperature}")
    print(f"    最大 Token: {config.max_tokens}")
    print()

    # =========================================================================
    # 第 4 步：理解评估原理 - LLM 生成
    # =========================================================================
    # llm_generate_output() 是 LLM 评估的核心：
    #   1. 构建完整的 prompt (system + user)
    #   2. 调用 LLM API 生成输出
    #   3. 返回 LLM 的响应文本
    #
    # 与规则引擎的区别:
    #   - 规则引擎: 输出 = 模板渲染结果 (文本替换)
    #   - LLM 增强: 输出 = LLM 的真实响应 (更有意义)
    print("=" * 70)
    print("第 4 步：理解评估原理 - LLM 生成")
    print("=" * 70)

    demo_template = list(templates.values())[0]
    sample = dataset[0]

    print(f"  演示模板: {demo_template.name}")
    print(f"  演示样本: {sample.input}")
    print()

    # 渲染模板
    from promptgit.evaluator import rule_based_render

    rendered = rule_based_render(demo_template, {"question": sample.input})
    print(f"  渲染后的 Prompt:")
    print(f"    System: {demo_template.system_prompt[:100]}...")
    print(f"    User: {rendered[:100]}...")
    print()

    # 调用 LLM 生成输出
    print("  调用 LLM 生成输出...")
    llm_output = llm_generate_output(config, demo_template, {"question": sample.input})

    print(f"  LLM 输出:")
    print(f"    {llm_output[:200]}...")
    print()

    # =========================================================================
    # 第 5 步：理解评估原理 - 相似度匹配
    # =========================================================================
    # 与规则引擎相同的相似度计算，但匹配的是 LLM 的真实输出
    # 这样可以评估 prompt 变更对 LLM 实际行为的影响
    print("=" * 70)
    print("第 5 步：理解评估原理 - 相似度匹配")
    print("=" * 70)

    expected = sample.expected_output
    similarity = compute_similarity(expected, llm_output)

    print(f"  期望输出: {expected}")
    print(f"  LLM 输出: {llm_output[:100]}...")
    print()
    print(f"  文本相似度: {similarity:.1%}")
    print(f"  相似度阈值: 70%")
    print(f"  匹配结果: {'✓ 通过' if similarity >= 0.7 else '✗ 未通过'}")
    print()

    # =========================================================================
    # 第 6 步：执行完整评估
    # =========================================================================
    # evaluate_prompts_with_llm() 是完整的 LLM 评估函数
    # 它会:
    #   1. 对数据集中的每个样本，调用 LLM 生成输出
    #   2. 计算相似度和准确率
    #   3. 统计 Token 成本和一致性
    #   4. 判断是否通过阈值检查
    #
    # 参数:
    #   - old_template: 旧版本模板
    #   - new_template: 新版本模板
    #   - dataset: 数据集
    #   - llm_config: LLM 配置
    #   - threshold: 阈值 (默认 0.05)
    #   - use_judge: 是否使用 LLM-as-judge (默认 False)
    #   - judge_config: Judge 模型配置 (可选)
    print("=" * 70)
    print("第 6 步：执行完整评估")
    print("=" * 70)

    print("  开始 LLM 增强评估...")
    print("  (这可能需要几分钟时间，取决于数据集大小和 LLM 响应速度)")
    print()

    result = evaluate_prompts_with_llm(
        old_template=list(templates.values())[0],
        new_template=list(templates.values())[0],
        dataset=dataset,
        llm_config=config,
        threshold=0.05,
        use_judge=False,  # 不使用 judge，仅使用相似度匹配
    )

    print(f"  评估结果:")
    print(f"    总样本数: {result.total_samples}")
    print(f"    准确率 (旧): {result.accuracy_old:.1%}")
    print(f"    准确率 (新): {result.accuracy_new:.1%}")
    print(f"    准确率变化: {result.accuracy_delta:+.1%}")
    print(f"    Token 成本 (旧): {result.token_cost_old}")
    print(f"    Token 成本 (新): {result.token_cost_new}")
    print(f"    一致性: {result.consistency_score:.1%}")
    print(f"    是否通过: {'是' if result.passed else '否'}")
    print()

    # =========================================================================
    # 第 7 步：详细结果分析
    # =========================================================================
    print("=" * 70)
    print("第 7 步：详细结果分析")
    print("=" * 70)

    print("  前 5 个样本的详细结果:")
    print("  " + "-" * 66)

    for i, detail in enumerate(result.details[:5]):
        match_status = "✓" if detail.new_match else "✗"
        print(f"  [{i+1}] 输入: {detail.input}")
        print(f"      期望: {detail.expected}")
        print(f"      LLM 输出: {detail.new_output[:100]}...")
        print(f"      匹配: {match_status} (相似度: {detail.similarity_delta:.1%})")
        print()

    # =========================================================================
    # 第 8 步：评估结果解读
    # =========================================================================
    print("=" * 70)
    print("第 8 步：评估结果解读")
    print("=" * 70)
    print("""
  LLM 增强评估 vs 规则引擎评估:

  ┌─────────────────┬────────────────────┬────────────────────┐
  │ 特性             │ 规则引擎           │ LLM 增强           │
  ├─────────────────┼────────────────────┼────────────────────┤
  │ 输出来源         │ 模板渲染 (文本替换) │ LLM 真实输出       │
  │ API Key          │ 不需要             │ 需要               │
  │ 运行速度         │ 快 (毫秒级)        │ 慢 (秒级/样本)     │
  │ 评估准确性       │ 低 (仅文本匹配)    │ 高 (真实输出)      │
  │ 适用场景         │ 快速验证/CI        │ 精确评估/开发      │
  │ 成本             │ 免费               │ 按 API 调用计费    │
  └─────────────────┴────────────────────┴────────────────────┘

  评估流程图:
  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
  │ 加载数据集   │───>│ 调用 LLM     │───>│ 计算相似度   │
  │ (JSONL)      │    │ (生成输出)   │    │ (匹配期望)   │
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
    print("  - 查看 examples/llm_as_judge/ 了解 LLM-as-judge 评估")
    print("  - 尝试不同的 LLM 提供商和模型")
    print("  - 修改 prompt 模板后重新运行观察指标变化")
    print()


if __name__ == "__main__":
    main()
