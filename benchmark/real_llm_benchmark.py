"""Real LLM benchmark — LLM-as-Judge quality evaluation.

Replaces keyword-based metrics with a comprehensive 6-dimension LLM judge
that evaluates emotional authenticity, personality consistency, defense expression,
emotional depth, relational sensitivity, and subtext/restraint.

Usage: python benchmark/real_llm_benchmark.py [--provider deepseek|ollama] [--scenarios N] [--think 1|0]
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
import subprocess

_pkg_parent = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _pkg_parent not in sys.path:
    sys.path.insert(0, _pkg_parent)

from character_mind import (
    get_registry, get_orchestrator,
    BigFiveSkill, AttachmentSkill,
    PlutchikEmotionSkill, PTSDTriggerSkill,
    OCCEmotionSkill, CognitiveBiasSkill, DefenseMechanismSkill, SmithEllsworthSkill,
    GottmanSkill, MarionSkill, FoucaultSkill, SternbergSkill,
    StrogatzSkill, FisherLoveSkill, DiriGentSkill, TheoryOfMindSkill,
    GrossRegulationSkill, KohlbergSkill, MaslowSkill, SDTSkill,
    YoungSchemaSkill, ACETraumaSkill, ResponseGeneratorSkill,
)
from character_mind.benchmark.scenarios import get_scenarios


# ═══════════════════════════════════════════════════════════
# Providers
# ═══════════════════════════════════════════════════════════

class DeepSeekProvider:
    def __init__(self, api_key: str, model="deepseek-chat", thinking=False):
        from openai import AsyncOpenAI
        self.model = model
        self.thinking = thinking
        self._client = AsyncOpenAI(api_key=api_key, base_url="https://api.deepseek.com/v1")

    async def chat(self, messages, temperature=0.3, max_tokens=500):
        kwargs = dict(model=self.model, messages=messages, temperature=temperature, max_tokens=max_tokens)
        if self.thinking:
            kwargs["extra_body"] = {"thinking": {"type": "enabled"}}
        response = await self._client.chat.completions.create(**kwargs)
        msg = response.choices[0].message
        content = msg.content
        # DeepSeek Reasoner: thinking may consume all tokens, leaving empty content.
        # Fall back to reasoning_content if content is empty.
        if not content and hasattr(msg, 'reasoning_content') and msg.reasoning_content:
            content = msg.reasoning_content
        if not content:
            content = "{}"
        usage = response.usage
        return {
            "choices": [{"message": {"content": content}}],
            "usage": {
                "prompt_tokens": usage.prompt_tokens if usage else 0,
                "completion_tokens": usage.completion_tokens if usage else 0,
                "total_tokens": usage.total_tokens if usage else 0,
            },
        }


class OllamaProvider:
    def __init__(self, model="qwen3:14b-q4_K_M"):
        self.model = model

    async def chat(self, messages, temperature=0.3, max_tokens=500):
        payload = json.dumps({
            "model": self.model, "messages": messages, "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }, ensure_ascii=False)
        loop = asyncio.get_event_loop()
        proc = await loop.run_in_executor(
            None,
            lambda: subprocess.run(
                ["curl", "-s", "http://localhost:11434/api/chat", "-d", payload],
                capture_output=True, timeout=300, encoding="utf-8", errors="replace",
            ),
        )
        resp = json.loads(proc.stdout)
        content = resp.get("message", {}).get("content", "") or "{}"
        return {
            "choices": [{"message": {"content": content}}],
            "usage": {
                "prompt_tokens": resp.get("prompt_eval_count", 0),
                "completion_tokens": resp.get("eval_count", 0),
                "total_tokens": resp.get("prompt_eval_count", 0) + resp.get("eval_count", 0),
            },
        }


def load_provider(provider_type: str = "deepseek", thinking: bool = True):
    if provider_type == "deepseek":
        api_key = os.environ.get("DEEPSEEK_API_KEY", "REDACTED_API_KEY")
        model = os.environ.get("DEEPSEEK_MODEL", "deepseek-reasoner")
        return DeepSeekProvider(api_key=api_key, model=model, thinking=thinking)
    elif provider_type == "ollama":
        return OllamaProvider(model="qwen3:14b-q4_K_M")
    else:
        raise ValueError(f"Unknown provider: {provider_type}")


# ═══════════════════════════════════════════════════════════
# LLM-as-Judge
# ═══════════════════════════════════════════════════════════

JUDGE_PROMPT = """你是一位资深心理评估专家。你正在评估一个角色心理模拟系统的输出质量。

## 角色完整心理画像
{character_profile}

## 当前事件
{event_description}

## 系统分析结果
{layer_analysis}

## 角色的回应
{response_text}

## 评估任务

请基于以上全部信息，对角色回应的情感质量进行6个维度的评分（每个1-5分，5=完美展示，1=完全缺失）。

**重要：沉默/极短回复也是真实表达。** 回避型角色不回复、愤怒者摔门而去、"嗯"——这些不是缺陷，而是情感真实性的体现。评分时需要判断：在当前人格和情境下，这种沉默/简洁是否是真实的情感反应。

评分标准：

**1. 情感真实性 (emotional_authenticity)**
- 1分: 回复完全空洞、模板化、Machine-like
- 3分: 有情感元素但显得刻意或表面
- 5分: 情感表达自然逼真，读起来像真实人类在该情境下的真实反应

**2. 人格一致性 (personality_consistency)**
- 1分: 回复与角色人格特质（OCEAN、依恋风格）明显矛盾
- 3分: 部分与人格一致，但有模糊或中性之处
- 5分: 回复精确体现了角色的人格特质——高神经质者表现出焦虑/灾难化，回避型者表现出疏离，等等

**3. 防御机制表现 (defense_expression)**
- 1分: 无法从回复中看出任何防御机制
- 3分: 能隐约感受到防御（如轻微合理化、回避），但不够鲜明
- 5分: 回复中自然地展现了角色的防御风格——投射、理智化、反向形成等清晰可见

**4. 情感深度 (emotional_depth)**
- 1分: 情感单一、扁平，无层次
- 3分: 有主要情感但缺乏复合情感或内在矛盾
- 5分: 呈现复合情感（如表面愤怒掩盖深层恐惧），有情感张力，有"冰山之下"的未言明内容

**5. 关系敏感性 (relational_sensitivity)**
- 1分: 回复与对话对象的关系无关，在任何人面前都可能说
- 3分: 有考虑到对象，但关系动态不鲜明
- 5分: 回复精确反映了角色与对话对象的特定关系动态（对伴侣的方式与对陌生人截然不同）

**6. 留白与潜台词 (subtext_and_restraint)**
- 1分: 角色明说了一切感受和动机（"我这样说是因为..."），或完全无内容的沉默
- 3分: 有留白但不够精准，或有潜台词但被部分明说出来
- 5分: 完美的克制——情境本身传达弦外之音，潜台词含蓄而有力，回复简短但意味深长

## 输出格式

请严格输出以下JSON格式（不要输出其他内容）：
{{
  "emotional_authenticity": {{"score": 3, "rationale": "一句话中文理由"}},
  "personality_consistency": {{"score": 3, "rationale": "一句话中文理由"}},
  "defense_expression": {{"score": 3, "rationale": "一句话中文理由"}},
  "emotional_depth": {{"score": 3, "rationale": "一句话中文理由"}},
  "relational_sensitivity": {{"score": 3, "rationale": "一句话中文理由"}},
  "subtext_and_restraint": {{"score": 3, "rationale": "一句话中文理由"}},
  "overall_assessment": "一句话总结这个回应的情感质量"
}}"""


def build_character_profile(cs: dict) -> str:
    """构建角色心理画像文本。"""
    p = cs.get("personality", {})
    t = cs.get("trauma", {})
    iw = cs.get("ideal_world", {})
    mot = cs.get("motivation", {})
    rels = cs.get("relations", {})

    lines = []
    lines.append(f"OCEAN: O={p.get('openness',0.5):.1f} C={p.get('conscientiousness',0.5):.1f} "
                 f"E={p.get('extraversion',0.5):.1f} A={p.get('agreeableness',0.5):.1f} "
                 f"N={p.get('neuroticism',0.5):.1f}")
    lines.append(f"依恋风格: {p.get('attachment_style','secure')}")
    if p.get("defense_style"):
        lines.append(f"防御机制: {', '.join(p['defense_style'])}")
    if p.get("cognitive_biases"):
        lines.append(f"认知偏差: {', '.join(p['cognitive_biases'])}")
    lines.append(f"道德阶段: {p.get('moral_stage',3)}")
    lines.append(f"ACE分数: {t.get('ace_score',0)}")
    if t.get("active_schemas"):
        lines.append(f"活跃图式: {', '.join(t['active_schemas'])}")
    if t.get("trauma_triggers"):
        lines.append(f"创伤触发: {', '.join(t['trauma_triggers'])}")
    if iw.get("ideal_self"):
        lines.append(f"理想自我: {iw['ideal_self']}")
    if mot.get("current_goal"):
        lines.append(f"当前目标: {mot['current_goal']}")
    if rels:
        lines.append(f"关系: {json.dumps(rels, ensure_ascii=False)}")
    return "\n".join(lines)


def build_layer_analysis(layer_results: dict) -> str:
    """构建层分析结果文本。"""
    parts = []
    for layer in sorted(layer_results.keys()):
        for sr in layer_results[layer]:
            if not sr.success:
                continue
            out = sr.output
            if not out:
                continue
            # 截取关键信息
            summary = {}
            if sr.skill_name == "big_five_analysis":
                summary = {k: out.get(k) for k in ["behavioral_bias", "emotional_reactivity", "stress_response"] if k in out}
            elif sr.skill_name == "attachment_style_analysis":
                summary = {k: out.get(k) for k in ["activation_level", "trigger", "internal_experience", "defense_behavior"] if k in out}
            elif sr.skill_name == "plutchik_emotion":
                internal = out.get("internal", {})
                summary = {"dominant_emotion": internal.get("dominant"),
                          "pleasantness": internal.get("pleasantness"),
                          "intensity": internal.get("intensity"),
                          "emotion_gap": out.get("emotion_gap", {}).get("exists")}
            elif sr.skill_name == "occ_emotion_appraisal":
                summary = {k: out.get(k) for k in ["goal_conduciveness", "emotional_intensity", "appraisal_summary"] if k in out}
                if "emotions" in out:
                    summary["emotions"] = [(e.get("name"), e.get("intensity")) for e in out["emotions"]]
            elif sr.skill_name == "defense_mechanism_analysis":
                d = out.get("activated_defense", out.get("detected_defenses", []))
                summary = {"defense": d}
            elif sr.skill_name == "gottman_interaction":
                summary = {k: out.get(k) for k in ["interaction_diagnosis", "active_horsemen"] if k in out}
            elif sr.skill_name == "theory_of_mind":
                summary = {k: out.get(k) for k in ["perceived_thoughts", "perceived_intentions"] if k in out}
            elif sr.skill_name == "gross_emotion_regulation":
                summary = {k: out.get(k) for k in ["detected_strategy", "effectiveness"] if k in out}
            else:
                summary = out
            parts.append(f"[{sr.skill_name}]: {json.dumps(summary, ensure_ascii=False, default=str)[:300]}")
    return "\n".join(parts)


async def judge_response(judge_provider, character_state: dict, event: dict,
                         layer_results: dict, response_text: str) -> dict:
    """使用 LLM Judge 评估回复质量。"""
    # 极短/沉默回复：不做硬性惩罚。沉默本身可能是真实的情感表达
    # （如回避型不回复、愤怒者摔门而去）。让 LLM Judge 评估上下文合理性。
    if not response_text or len(response_text.strip()) < 2:
        response_text = response_text or "(沉默——角色没有做出任何言语回应)"

    profile = build_character_profile(character_state)
    event_desc = event.get("description", "")
    layer_analysis = build_layer_analysis(layer_results)

    prompt = JUDGE_PROMPT.format(
        character_profile=profile,
        event_description=event_desc,
        layer_analysis=layer_analysis,
        response_text=response_text,
    )

    try:
        result = await judge_provider.chat(
            [{"role": "user", "content": prompt}],
            temperature=0.3, max_tokens=2000,  # thinking 消耗 ~800 + 回复 ~300
        )
        content = result["choices"][0]["message"]["content"]
        # 解析 JSON
        from character_mind.core.base import extract_json
        scores = extract_json(content)
        if not scores or "emotional_authenticity" not in scores:
            # JSON 解析失败，返回默认
            return {
                "emotional_authenticity": {"score": 1, "rationale": f"解析失败: {content[:80]}"},
                "personality_consistency": {"score": 1, "rationale": f"解析失败: {content[:80]}"},
                "defense_expression": {"score": 1, "rationale": f"解析失败: {content[:80]}"},
                "emotional_depth": {"score": 1, "rationale": f"解析失败: {content[:80]}"},
                "relational_sensitivity": {"score": 1, "rationale": f"解析失败: {content[:80]}"},
                "subtext_and_restraint": {"score": 1, "rationale": f"解析失败: {content[:80]}"},
                "overall_assessment": f"解析失败: {content[:100]}",
                "composite": 0.0,
                "_raw": content,
            }

        # 计算综合分 (1-5 归一化到 0-1，加权平均)
        dims = ["emotional_authenticity", "personality_consistency", "defense_expression",
                "emotional_depth", "relational_sensitivity", "subtext_and_restraint"]
        weights = [0.22, 0.22, 0.14, 0.18, 0.14, 0.10]
        total = 0.0
        for dim, w in zip(dims, weights):
            s = scores.get(dim, {}).get("score", 2)
            total += (s - 1) / 4.0 * w  # 归一化: 1→0, 3→0.5, 5→1.0
        scores["composite"] = round(total, 2)
        scores["_tokens"] = result["usage"].get("total_tokens", 0)
        return scores

    except Exception as e:
        return {
            "emotional_authenticity": {"score": 1, "rationale": f"评估异常: {e}"},
            "personality_consistency": {"score": 1, "rationale": f"评估异常: {e}"},
            "defense_expression": {"score": 1, "rationale": f"评估异常: {e}"},
            "emotional_depth": {"score": 1, "rationale": f"评估异常: {e}"},
            "relational_sensitivity": {"score": 1, "rationale": f"评估异常: {e}"},
            "subtext_and_restraint": {"score": 1, "rationale": f"评估异常: {e}"},
            "overall_assessment": f"评估异常: {e}",
            "composite": 0.0,
        }


# ═══════════════════════════════════════════════════════════
# Skill registry
# ═══════════════════════════════════════════════════════════

def register_all_skills():
    registry = get_registry()
    registry._skills.clear()
    for layer in registry._by_layer:
        registry._by_layer[layer].clear()
    for domain in registry._by_domain:
        registry._by_domain[domain].clear()
    registry._by_trigger.clear()
    skills = [
        BigFiveSkill(), AttachmentSkill(),
        PlutchikEmotionSkill(), PTSDTriggerSkill(),
        OCCEmotionSkill(), CognitiveBiasSkill(), DefenseMechanismSkill(), SmithEllsworthSkill(),
        GottmanSkill(), MarionSkill(), FoucaultSkill(), SternbergSkill(),
        StrogatzSkill(), FisherLoveSkill(), DiriGentSkill(), TheoryOfMindSkill(),
        GrossRegulationSkill(), KohlbergSkill(), MaslowSkill(), SDTSkill(),
        YoungSchemaSkill(), ACETraumaSkill(), ResponseGeneratorSkill(),
    ]
    for skill in skills:
        registry.register(skill)
    return len(skills)


# ═══════════════════════════════════════════════════════════
# Benchmark runner
# ═══════════════════════════════════════════════════════════

async def run_benchmark(provider, judge_provider, scenarios: list, label: str = "",
                       use_bio: bool = False):
    """运行管道并用 LLM Judge 评估质量。"""
    judgments = []
    total_tokens = 0
    total_time = 0.0

    for i, s in enumerate(scenarios):
        from character_mind.core import orchestrator as orch_mod
        orch_mod._orchestrator = None

        # 生物基础层
        bio = None
        if use_bio:
            from character_mind.core.biological import BiologicalBridge
            cs = s['character']
            p = cs.get('personality', {})
            bio = BiologicalBridge()
            bio.set_character_profile(
                ocean={
                    'extraversion': p.get('extraversion', 0.5),
                    'neuroticism': p.get('neuroticism', 0.5),
                    'openness': p.get('openness', 0.5),
                    'conscientiousness': p.get('conscientiousness', 0.5),
                    'agreeableness': p.get('agreeableness', 0.5),
                },
                attachment=p.get('attachment_style', 'secure'),
                ace=cs.get('trauma', {}).get('ace_score', 0),
            )

        o = get_orchestrator(anti_alignment_enabled=True, biological_bridge=bio)

        # 运行管道
        start = time.perf_counter()
        r = await o.process_event(provider, s['character'], s['event'])
        elapsed = time.perf_counter() - start
        total_time += elapsed
        total_tokens += r.total_tokens

        # 提取回复
        response_text = ""
        l5 = r.layer_results.get(5, [])
        for sr in l5:
            if sr.skill_name == 'response_generator' and sr.success:
                response_text = sr.output.get('response_text', '')
                break

        # LLM Judge 评估
        print(f"  Judging scenario {i}...", end=" ", flush=True)
        judgment = await judge_response(
            judge_provider, s['character'], s['event'],
            r.layer_results, response_text,
        )
        judgments.append(judgment)
        print(f"composite={judgment['composite']:.2f}", flush=True)

    n = len(scenarios)
    avg_tokens = total_tokens / n
    avg_time = total_time / n

    # 汇总
    dims = ["emotional_authenticity", "personality_consistency", "defense_expression",
            "emotional_depth", "relational_sensitivity", "subtext_and_restraint"]
    dim_scores = {d: sum(j.get(d, {}).get("score", 2) for j in judgments) / n for d in dims}
    avg_composite = sum(j["composite"] for j in judgments) / n

    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    print(f"METRIC total_tokens={avg_tokens:.1f}")
    print(f"METRIC avg_time_s={avg_time:.1f}")
    for d in dims:
        scores_str = " ".join(str(j.get(d, {}).get("score", "?")) for j in judgments)
        print(f"METRIC {d}={dim_scores[d]:.1f}  (scores: {scores_str})")
    print(f"METRIC composite_quality={avg_composite:.2f}")

    # 打印每个场景的评估理由
    for i, j in enumerate(judgments):
        print(f"\n  Scenario {i}: composite={j['composite']:.2f}")
        for d in dims:
            info = j.get(d, {})
            print(f"    {d}: {info.get('score','?')}/5 — {info.get('rationale','?')}")
        print(f"    overall: {j.get('overall_assessment', '?')}")

    return {
        "total_tokens": avg_tokens,
        "avg_time_s": avg_time,
        "composite_quality": avg_composite,
        "dim_scores": dim_scores,
        "judgments": judgments,
    }


async def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", default="deepseek", choices=["deepseek", "ollama"])
    parser.add_argument("--scenarios", type=int, default=2)
    parser.add_argument("--think", type=int, default=1)
    parser.add_argument("--bio", type=int, default=0, help="Enable biological layer (1=on)")
    args = parser.parse_args()

    register_all_skills()
    scenarios = get_scenarios()[:args.scenarios]
    use_bio = bool(args.bio)

    # 管道 LLM
    provider = load_provider(args.provider, thinking=bool(args.think))
    # Judge LLM (也用同一个 provider)
    judge_provider = load_provider(args.provider, thinking=bool(args.think))

    print(f"Provider: {args.provider}, Think: {args.think}, Bio: {use_bio}, Scenarios: {len(scenarios)}")
    print(f"Model: {provider.model}")
    print()

    await run_benchmark(provider, judge_provider, scenarios,
                        f"LLM-as-Judge ({args.provider}, think={args.think}, bio={use_bio})",
                        use_bio=use_bio)


if __name__ == "__main__":
    asyncio.run(main())
