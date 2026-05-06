"""Mock LLM provider — simulates realistic but varied LLM output quality.

The provider generates responses for each skill based on its expected output schema,
with configurable quality that affects JSON validity, field completeness,
and format correctness. This exercises extract_json() and parse_output() robustness.
"""
from __future__ import annotations

import json
import random
from typing import Any


# ── Expected output schemas for each skill ──
# Each entry: {field_name: (type_or_example, is_critical)}
# is_critical=True means the field is essential (parse_output fallback provides it)
SKILL_SCHEMAS: dict[str, dict[str, tuple[Any, bool]]] = {
    # L0
    "big_five_analysis": {
        "behavioral_bias": ("受宜人性影响，倾向于迎合他人", True),
        "emotional_reactivity": (0.65, True),
        "social_approach": ("谨慎接近但保持距离", False),
        "decision_style": ("情感驱动", False),
        "stress_response": ("过度担忧和灾难化思考", False),
        "interpretation_bias": ("将他人的模糊行为解读为拒绝信号", False),
    },
    "attachment_style_analysis": {
        "activation_level": (0.7, True),
        "trigger": ("感知到被忽视或拒绝", False),
        "internal_experience": ("强烈的被抛弃恐惧", False),
        "defense_behavior": ("反复寻求确认", False),
        "what_they_say": ("你在想什么？", False),
        "what_they_need": ("安全感和持续的关注", False),
        "partner_perception_risk": ("把对方的独立空间解读为疏远", False),
        "next_prediction": ("会更加黏附以测试对方的忠诚度", False),
    },
    # L1
    "plutchik_emotion": {
        "internal": ({"emotions": {"joy": 0.3, "sadness": 0.4, "fear": 0.6, "anger": 0.2, "disgust": 0.1, "surprise": 0.3, "trust": 0.4, "anticipation": 0.5}, "dominant": "fear", "fine_grained": ["anxious"], "complex": [], "functional": [], "pleasantness": -0.3, "intensity": 0.6}, True),
        "expressed": ({"emotions": {"joy": 0.1, "sadness": 0.2, "fear": 0.1, "anger": 0.1, "disgust": 0.0, "surprise": 0.1, "trust": 0.3, "anticipation": 0.2}, "dominant": "trust"}, False),
        "emotion_gap": ({"exists": True, "type": "masking", "description": "内心恐惧但表面表现平静"}, False),
        "novelty": ({"is_novel": False, "similar_to_past": True}, False),
    },
    "emotion_probe": {
        "fine_grained": ([{"emotion": "焦虑", "intensity": 0.7, "evidence": "反复查看手机"}, {"emotion": "失落", "intensity": 0.5, "evidence": "等待未果"}], True),
        "functional": ([{"emotion": "yearning", "intensity": 0.6, "behavioral_consequence": "反复查看对方状态"}], False),
        "primary_undisclosed_emotion": ("对被抛弃的深层恐惧", False),
        "emotional_complexity": ("moderate", False),
    },
    "ptsd_trigger_check": {
        "triggered": (False, True),
        "matched_triggers": ([], False),
        "intrusion_risk": (0.2, False),
        "avoidance_risk": (0.3, False),
        "hyperarousal_risk": (0.4, False),
        "immediate_reaction": ("轻微警觉但没有完全触发", False),
    },
    # L2
    "occ_emotion_appraisal": {
        "goal_relevance": (0.7, False),
        "goal_conduciveness": (-0.3, False),
        "causal_attribution": ("对方的行为", False),
        "causal_agent": ("他人", False),
        "unexpectedness": (0.4, False),
        "coping_potential": (0.5, False),
        "norm_compatibility": (0.6, False),
        "emotions": ([{"name": "fear", "intensity": 0.6, "label": "恐惧"}, {"name": "anxiety", "intensity": 0.5, "label": "焦虑"}], True),
        "emotional_intensity": (0.6, True),
        "appraisal_summary": ("事件对个人目标存在潜在威胁", True),
        "action_tendency": ("退缩和寻求安全", False),
        "activation_relevance": (0.8, False),
    },
    "cognitive_bias_detect": {
        "activated_biases": ([{"name": "灾难化", "intensity": 0.7, "thought": "对方不回消息意味着已经厌倦了我"}], True),
        "alternative_interpretation": ("对方可能只是忙碌", False),
        "bias_summary": ("倾向于对模糊信号做最坏的解读", False),
        "activation_relevance": (0.75, False),
    },
    "defense_mechanism_analysis": {
        "activated_defense": ({"name": "投射", "level": 3, "intensity": 0.6}, True),
        "defense_behavior": ("将自己的不安全感投射给对方", False),
        "what_is_being_defended_against": ("对自我价值的怀疑", False),
        "emotional_gap_analysis": ("内心感到恐惧但表现出来的却是挑剔", False),
        "maturity_assessment": ("神经质水平的防御", False),
        "alternative_coping": ("直接表达自己的不安全感", False),
        "activation_relevance": (0.7, False),
    },
    "smith_ellsworth_appraisal": {
        "certainty": (0.4, True),
        "pleasantness": (-0.3, True),
        "attentional_activity": (0.7, False),
        "anticipated_effort": (0.6, False),
        "control": (0.3, False),
        "situational_control": (0.2, False),
        "other_agency": (0.7, False),
        "self_agency": (0.4, False),
        "responsibility": ("他人主要责任", False),
        "appraisal_profile": ("不确定性高, 愉悦度低, 他人主导", True),
        "appraisal_emotion_link": ("不确定性和低控制感导致焦虑", False),
        "cognitive_vulnerability": (0.65, False),
        "activation_relevance": (0.8, False),
    },
    # L3
    "gottman_interaction": {
        "positive_ratio_estimate": (1.5, False),
        "active_horsemen": (["defensiveness"], False),
        "horsemen_escalation_risk": (0.4, False),
        "emotional_flooding_risk": (0.6, False),
        "repair_attempt_detected": (True, False),
        "repair_accepted": (False, False),
        "interaction_diagnosis": ("轻度防御性互动模式", True),
        "intervention_suggestion": ("增加积极回应比例", False),
    },
    "marion_erotic_phenomenology": {
        "who_is_advancing": ("neither", True),
        "erotic_reduction_stage": ("imagination", False),
        "body_under_gaze": ("none", False),
        "oath_status": ("unspoken", False),
        "logic_type": ("sentimental", False),
        "what_is_unsaid": ("对亲密接触的渴望被理性压抑", False),
        "erotic_tension": (0.3, False),
    },
    "foucauldian_power_analysis": {
        "disciplinary_technologies": (["自我监控"], False),
        "internalized_gaze": ("对自身行为是否符合规范的持续审视", False),
        "truth_regime_conflict": ("个人欲望与社会规范的冲突", False),
        "subjectivation_tension": ("在顺从和抵抗之间的摇摆", True),
        "resistance_form": ("微小的不服从", False),
        "power_productive_effect": ("自我约束产生了表面的顺从", False),
        "discourse_position": ("subordinate", False),
        "power_intensity": (0.5, False),
        "activation_relevance": (0.6, False),
    },
    "sternberg_triangle": {
        "intimacy": (0.5, False),
        "passion": (0.6, False),
        "commitment": (0.3, False),
        "love_type": ("浪漫之爱", True),
        "strongest_dimension": ("passion", False),
        "weakest_dimension": ("commitment", False),
        "trend": ("passion growing", False),
        "triangle_description": ("激情主导但缺乏承诺的不稳定关系", False),
    },
    "strogatz_love_dynamics": {
        "a_parameter": (0.6, False),
        "b_parameter": (0.4, False),
        "system_trend": ("toward_equilibrium", True),
        "stability_assessment": ("缓慢趋向稳定", False),
        "delay_effect": ("回应延迟导致振荡", False),
        "equilibrium_point": (0.55, False),
    },
    
    "theory_of_mind": {
        "perceived_thoughts": (["对方可能正在疏远我"], True),
        "perceived_intentions": (["对方可能想保持距离"], False),
        "perceived_feelings_toward_self": ("对方对自己感到不耐烦", False),
        "evidence_basis": ("weak", False),
        "alternative_interpretations": (["对方可能只是忙碌"], False),
        "distortion_factors": (["焦虑依恋导致过度解读"], False),
        "behavioral_influence": ("角色将更频繁地寻求确认", False),
        "ToM_accuracy_estimate": (0.3, False),
    },
    "fisher_love_stages": {
        "current_stage": ("attraction", True),
        "stage_markers": (["intense_focus", "emotional_dependency"], False),
        "neurochemical_profile": ("dopamine_dominant", False),
        "transition_readiness": (0.5, False),
        "stuck_risk": (0.3, False),
    },
    "dirigent_world_tension": {
        "perceived_reality": ("当前关系中的不确定性", False),
        "tension_dimensions": ({"self": {"gap": 0.4, "actual": "焦虑的自我", "ideal": "安定的自我", "pain": 0.5}, "relationship": {"gap": 0.6, "actual": "模糊不清的关系", "ideal": "明确承诺的关系", "pain": 0.7}}, False),
        "dominant_tension": ("relationship", False),
        "overall_cognitive_dissonance": (0.5, True),
        "coping_strategy": ("emotion_focused", True),
        "predicted_action": ("寻求对方的明确表态", False),
        "long_term_arc_impact": ("如果持续模糊, 可能导致关系破裂", False),
    },
    # L4
    "gross_emotion_regulation": {
        "internal_to_external_path": ("内心的恐惧 → 外在的冷淡疏离", False),
        "detected_strategy": ("expressive_suppression", True),
        "effectiveness": (0.5, False),
        "cost": ("增加内在痛苦, 降低社交连接", False),
        "functional_emotion_shift": ("恐惧被压抑但并未真正转化", False),
        "alternative_strategy": ("cognitive_reappraisal", False),
        "long_term_impact": ("长期压抑可能导致情绪爆发", False),
        "regulation_insight": ("她的压抑策略在短期内保护了她, 但付出了代价", False),
    },
    "kohlberg_moral_reasoning": {
        "stage_used": (3, True),
        "reasoning": ("基于人际期望和社會规范做出判断", False),
        "stage_consistency": ("consistent", False),
        "moral_conflict": ("个人需求与社会期望的冲突", False),
        "justification_style": ("寻求外部认可", False),
    },
    "maslow_need_stack": {
        "current_dominant": (3, True),
        "need_stack": ([{"level": 1, "name": "生理需求", "satisfaction": 0.9, "urgency": 0.1}, {"level": 2, "name": "安全需求", "satisfaction": 0.5, "urgency": 0.7}, {"level": 3, "name": "归属与爱", "satisfaction": 0.3, "urgency": 0.9}, {"level": 4, "name": "尊重需求", "satisfaction": 0.4, "urgency": 0.6}], False),
        "blocked_needs": (["归属与爱"], False),
        "deficiency_vs_growth": ("deficiency", False),
        "behavior_explanation": ("当前行为主要受未满足的归属需求驱动", False),
    },
    "sdt_motivation_analysis": {
        "autonomy_impact": (-0.3, False),
        "competence_impact": (0.1, False),
        "relatedness_impact": (-0.5, False),
        "most_threatened": ("relatedness", False),
        "compensation_behavior": ("通过讨好行为试图修复关系连接", False),
        "intrinsic_motivation_level": (0.4, True),
    },
    # L5
    "young_schema_update": {
        "affected_schemas": ([{"name": "遗弃/不稳定", "effect": "reinforced", "intensity_change": 0.1}], True),
        "schema_driven_interpretation": ("对方的疏远被解释为即将被抛弃的证据", False),
        "healing_opportunity": ("对方的明确表态可以帮助缓解", False),
        "reinforcement_risk": (0.7, False),
        "schema_shift_summary": ("遗弃图式得到轻微强化", False),
    },
    "ace_trauma_processing": {
        "ace_activation": (0.3, True),
        "exploration_impact": (-0.1, False),
        "reward_sensitivity": (0.2, False),
        "ace_driven_behavior": ("微弱的讨好行为倾向", False),
        "long_term_trajectory": ("轻微负面但可控", False),
        "protective_factor": ("当前关系中的安全感部分缓冲了ACE的影响", False),
    },
    "response_generator": {
        "response_text": ("我...我不知道该说什么。", True),
        "action": ("stay_silent", False),
        "subtext": ("内心有太多想说但无法表达", False),
        "emotional_expression": ("anxiety", False),
        "authenticity_note": ("回应反映了真实的情感矛盾", False),
    },
}


class MockProvider:
    """Simulates an LLM provider with configurable output quality.

    Quality levels:
      1.0 = perfect JSON always
      0.8 = mostly perfect, occasional markdown wrapping
      0.6 = frequent format issues, missing fields
      0.4 = often malformed, many missing fields
      0.2 = mostly broken output
    """

    def __init__(self, quality: float = 0.8, seed: int = 42, error_rate: float = 0.0,
                 base_tokens: int = 300):
        self.quality = max(0.0, min(1.0, quality))
        self.rng = random.Random(seed)
        self.error_rate = error_rate
        self.base_tokens = base_tokens

    def set_quality(self, q: float):
        self.quality = max(0.0, min(1.0, q))

    async def chat(self, messages: list[dict], temperature: float = 0.3,
                   max_tokens: int = 500) -> dict:
        """Simulate an LLM chat call. Returns OpenAI-style response dict."""
        if self.rng.random() < self.error_rate:
            raise Exception("Simulated API error: rate limit exceeded")

        prompt = messages[-1]["content"] if messages else ""
        skill_name = self._detect_skill(prompt)
        content = self._generate_response(skill_name, prompt)

        prompt_tokens = len(prompt) // 3
        completion_tokens = len(content) // 3
        total_tokens = prompt_tokens + completion_tokens + self.rng.randint(-50, 50)

        return {
            "choices": [{"message": {"content": content}}],
            "usage": {
                "prompt_tokens": max(10, prompt_tokens),
                "completion_tokens": max(10, completion_tokens),
                "total_tokens": max(20, total_tokens),
            },
        }

    # Keyword patterns for each skill (searched in prompt text).
    # Use very specific phrases to avoid false matches from the anti-alignment hint.
    # IMPORTANT: response_generator must be first since its prompt contains ALL analysis data.
    _SKILL_KEYWORDS: list[tuple[str, str]] = [
        ("response_generator", "完整心理状态分析"),
        ("response_generator", "回应生成"),
        ("big_five_analysis", "大五人格模型"),
        ("big_five_analysis", "OCEAN"),
        ("attachment_style_analysis", "依恋理论专家"),
        ("attachment_style_analysis", "Bowlby"),
        ("plutchik_emotion", "Plutchik"),
        ("plutchik_emotion", "情感轮理论"),
        ("emotion_probe", "情感信号检测"),
        ("emotion_probe", "功能情感"),
        ("ptsd_trigger_check", "创伤心理学专家"),
        ("ptsd_trigger_check", "PTSD"),
        ("occ_emotion_appraisal", "OCC 模型"),
        ("occ_emotion_appraisal", "情感计算专家"),
        ("cognitive_bias_detect", "认知心理学家"),
        ("cognitive_bias_detect", "认知偏差"),
        ("defense_mechanism_analysis", "防御机制专家"),
        ("defense_mechanism_analysis", "四级防御机制"),
        ("smith_ellsworth_appraisal", "Smith & Ellsworth"),
        ("smith_ellsworth_appraisal", "16维认知评价"),
        ("gottman_interaction", "Gottman"),
        ("gottman_interaction", "魔法比例"),
        ("marion_erotic_phenomenology", "马里翁"),
        ("marion_erotic_phenomenology", "情爱现象学"),
        ("foucauldian_power_analysis", "福柯权力"),
        ("foucauldian_power_analysis", "权力分析专家"),
        ("sternberg_triangle", "Sternberg"),
        ("sternberg_triangle", "爱情三角理论"),
        ("strogatz_love_dynamics", "Strogatz"),
        ("strogatz_love_dynamics", "Romeo-Juliet"),
        ("fisher_love_stages", "Fisher"),
        ("fisher_love_stages", "恋爱阶段专家"),
        ("theory_of_mind", "ToM Agent"),
        ("theory_of_mind", "心理状态推理"),
        ("dirigent_world_tension", "角色动机分析专家"),
        ("dirigent_world_tension", "内心张力"),
        ("gross_emotion_regulation", "Gross"),
        ("gross_emotion_regulation", "情绪调节策略"),
        ("kohlberg_moral_reasoning", "Kohlberg"),
        ("kohlberg_moral_reasoning", "道德心理学家"),
        ("maslow_need_stack", "Maslow"),
        ("maslow_need_stack", "需求层次专家"),
        ("sdt_motivation_analysis", "SDT专家"),
        ("sdt_motivation_analysis", "三种内在需求"),
        ("young_schema_update", "Young图式"),
        ("young_schema_update", "图式疗法"),
        ("ace_trauma_processing", "ACE研究"),
        ("ace_trauma_processing", "ACE分数"),
    ]

    def _detect_skill(self, prompt: str) -> str:
        """Detect which skill is being called from the prompt content."""
        for name, keyword in self._SKILL_KEYWORDS:
            if keyword in prompt:
                return name
        return "unknown"

    def _generate_response(self, skill_name: str, prompt: str = "") -> str:
        """Generate a response with quality-based variation."""
        schema = SKILL_SCHEMAS.get(skill_name)
        if schema is None:
            return "{}"

        perfect = self._build_perfect(schema, skill_name, prompt)

        # Apply quality-based degradation
        q = self.quality
        r = self.rng.random()

        if q >= 0.95:
            # Almost always perfect
            if r < 0.98:
                return self._format_json(perfect, "clean")
            else:
                return self._format_json(perfect, "markdown")
        elif q >= 0.80:
            # Mostly good, minor issues
            if r < 0.70:
                return self._format_json(perfect, "clean")
            elif r < 0.90:
                return self._format_json(perfect, "markdown")
            elif r < 0.95:
                return self._format_json(self._drop_fields(perfect, schema, 1), "clean")
            else:
                return self._make_broken(perfect)
        elif q >= 0.60:
            # Moderate issues
            if r < 0.35:
                return self._format_json(perfect, "clean")
            elif r < 0.55:
                return self._format_json(perfect, "markdown")
            elif r < 0.70:
                return self._format_json(self._drop_fields(perfect, schema, self.rng.randint(1, 3)), "markdown")
            elif r < 0.85:
                return self._format_json(perfect, "trailing_comma")
            elif r < 0.95:
                return self._format_json(self._drop_fields(perfect, schema, self.rng.randint(2, 5)), "single_quotes")
            else:
                return self._make_broken(perfect)
        elif q >= 0.40:
            # Frequent issues
            if r < 0.20:
                return self._format_json(perfect, "clean")
            elif r < 0.35:
                return self._format_json(self._drop_fields(perfect, schema, self.rng.randint(1, 3)), "markdown")
            elif r < 0.50:
                return self._format_json(self._drop_fields(perfect, schema, self.rng.randint(2, 5)), "trailing_comma")
            elif r < 0.65:
                return self._format_json(perfect, "single_quotes")
            elif r < 0.80:
                return self._make_broken(perfect)
            else:
                return self._make_garbage()
        else:
            # Mostly broken
            if r < 0.10:
                return self._format_json(perfect, "clean")
            elif r < 0.20:
                return self._format_json(self._drop_fields(perfect, schema, self.rng.randint(3, 7)), "markdown")
            elif r < 0.40:
                return self._make_broken(perfect)
            else:
                return self._make_garbage()

    def _build_perfect(self, schema: dict, skill_name: str = "", prompt: str = "") -> dict:
        """Build a perfect response dict from schema, varying based on personality params in prompt."""
        result = {}
        for field, (value, _critical) in schema.items():
            if isinstance(value, (dict, list)):
                result[field] = json.loads(json.dumps(value))
            else:
                result[field] = value

        # Personality-aware adjustments
        self._adjust_by_personality(result, skill_name, prompt)
        return result

    def _adjust_by_personality(self, result: dict, skill_name: str, prompt: str):
        """Adjust mock response based on character personality parameters in the prompt."""
        # Extract key personality params from prompt
        neuroticism = self._extract_param(prompt, r'神经质[=:：]\s*([\d.]+)')
        agreeableness = self._extract_param(prompt, r'宜人性[=:：]\s*([\d.]+)')
        extraversion = self._extract_param(prompt, r'外向性[=:：]\s*([\d.]+)')
        conscientiousness = self._extract_param(prompt, r'尽责性[=:：]\s*([\d.]+)')
        attachment = self._extract_str(prompt, r'依恋风格[=:：]\s*(\w+)')
        ace_score = self._extract_param(prompt, r'ACE分数[=:：]\s*(\d+)')
        moral_stage = self._extract_param(prompt, r'道德阶段[=:：]\s*(\d+)')

        if skill_name == "big_five_analysis":
            if neuroticism is not None:
                if neuroticism >= 0.7:
                    result["emotional_reactivity"] = 0.75
                    result["behavioral_bias"] = "倾向于对模糊信号做出负面解读，容易灾难化思考"
                    result["stress_response"] = "过度担忧，反复思考最坏情况"
                    result["interpretation_bias"] = "将模糊或中性事件解读为潜在威胁"
                elif neuroticism <= 0.35:
                    result["emotional_reactivity"] = 0.3
                    result["behavioral_bias"] = "保持情绪稳定，对压力源做出理性评估"
                    result["stress_response"] = "冷静分析情况，寻找实际解决方案"
            if agreeableness is not None:
                if agreeableness <= 0.3:
                    result["social_approach"] = "confrontational"
                    result["decision_style"] = "competitive"
                elif agreeableness >= 0.7:
                    result["social_approach"] = "accommodating"
            if conscientiousness is not None and conscientiousness >= 0.75:
                result["decision_style"] = "deliberate"

        elif skill_name == "ptsd_trigger_check":
            triggers = self._extract_list(prompt, r'创伤触发[=:：]\s*\[([^\]]+)\]')
            event_text = self._extract_str(prompt, r'当前事件[=:：]\s*(.+?)(?:\n|$)')
            if ace_score is not None and ace_score >= 3:
                # Check if any trigger words appear in event
                if triggers and event_text:
                    triggered = any(t.strip() in event_text for t in triggers)
                    if triggered:
                        result["triggered"] = True
                        result["hyperarousal_risk"] = 0.7
                        result["intrusion_risk"] = 0.65
                        result["matched_triggers"] = [t.strip() for t in triggers if t.strip() in event_text]
                        result["immediate_reaction"] = "触发了创伤相关的高度警觉反应"

        elif skill_name == "cognitive_bias_detect":
            biases_str = self._extract_str(prompt, r'认知偏差[=:：]\s*\[([^\]]+)\]')
            event_text = self._extract_str(prompt, r'事件[=:：]\s*(.+?)(?:\n|$)') or prompt[-300:]
            if biases_str:
                bias_list = [b.strip() for b in biases_str.split(",")]
                if bias_list:
                    result["activated_biases"] = [
                        {"name": b, "intensity": 0.65, "thought": f"基于{b}的自动化思考"}
                        for b in bias_list[:2]
                    ]
                    result["bias_summary"] = f"角色主要受{'和'.join(bias_list[:2])}影响"
                    result["alternative_interpretation"] = "存在更客观的替代解释"

        elif skill_name == "defense_mechanism_analysis":
            defense_str = self._extract_str(prompt, r'防御风格[=:：]\s*\[([^\]]+)\]')
            if defense_str:
                defenses = [d.strip() for d in defense_str.split(",")]
                if defenses:
                    d = defenses[0]
                    result["activated_defense"] = {"name": d, "level": 3, "intensity": 0.6}
                    result["defense_behavior"] = f"使用{d}来应对当前压力"
                    result["what_is_being_defended_against"] = "内在的焦虑和不安全感"

        elif skill_name == "kohlberg_moral_reasoning":
            if moral_stage is not None:
                result["stage_used"] = int(moral_stage)
                stage_reasoning = {
                    2: "基于个人利益和交换的推理",
                    3: "基于人际关系和社会期望的推理",
                    4: "基于法律和社会秩序的推理",
                    5: "基于社会契约和普遍原则的推理",
                }
                result["reasoning"] = stage_reasoning.get(int(moral_stage), "基于常规道德判断")

        elif skill_name == "response_generator":
            # 注入事件相关的情感关键词，使 emotion_alignment 指标可测量
            event_text = self._extract_str(prompt, r'当前事件[=:：]\s*(.+?)(?:\n|$)') or prompt[-500:]
            # 检测事件中的情感信号并匹配响应内容
            emotion_keywords = {
                "joy": ["开心", "高兴", "太好了", "真的很快乐", "这让我感到幸福"],
                "sadness": ["难过", "悲伤", "想哭", "心里空空的", "不知道该怎么办"],
                "fear": ["害怕", "恐惧", "不安", "不敢想", "紧张得说不出话"],
                "anger": ["生气", "愤怒", "不满", "凭什么这样", "太不公平了"],
                "trust": ["相信你", "信任", "依赖你", "有你在我很放心"],
                "disgust": ["反感", "厌恶", "受不了", "让人恶心", "不想靠近"],
                "surprise": ["没想到", "惊讶", "震惊", "怎么会这样", "太突然了"],
                "anticipation": ["期待", "盼望", "希望", "等不及了", "好想快点"],
            }
            # 从 Plutchik 输出提取主导情绪（prompt 中包含 L1 上下文）
            dominant = "neutral"
            for emo in emotion_keywords:
                if emo in event_text.lower() or any(kw in event_text for kw in emotion_keywords[emo]):
                    dominant = emo
                    break
            # 如果是中性或无匹配，随机选择匹配事件类型的情感
            if dominant == "neutral":
                if any(w in event_text for w in ["冲突", "争吵", "不满", "生气"]):
                    dominant = "anger"
                elif any(w in event_text for w in ["失去", "离开", "难过", "哭"]):
                    dominant = "sadness"
                elif any(w in event_text for w in ["害怕", "威胁", "危险", "不安"]):
                    dominant = "fear"
                elif any(w in event_text for w in ["开心", "成功", "好消息", "爱"]):
                    dominant = "joy"
                else:
                    dominant = "trust"
            # 生成包含情感关键词的自然响应
            if dominant in emotion_keywords:
                base = self.rng.choice(emotion_keywords[dominant])
                extensions = {
                    "joy": "已经很久没有这种感觉了，像是一直期待的事情终于发生了。",
                    "sadness": "这种感觉一直压在心头，挥之不去。我想一个人待一会儿。",
                    "fear": "我不知道接下来会发生什么，这种不确定让我很不安。",
                    "anger": "为什么总是这样？我已经厌倦了不断地退让和妥协。",
                    "trust": "我知道可以依靠你。这是我为数不多感到安心的时刻。",
                    "disgust": "光是想到这个就让我浑身不舒服。我没办法接受。",
                    "surprise": "完全出乎我的意料，我需要一点时间来消化这件事。",
                    "anticipation": "我在等那个时刻的到来，虽然不确定但充满了希望。",
                }
                ext = extensions.get(dominant, "。")
                result["response_text"] = base + "。" + ext
                result["emotional_expression"] = dominant
            if neuroticism is not None and neuroticism >= 0.7:
                result["authenticity_note"] = "高神经质角色对威胁信号的敏感反应"
            elif attachment == "avoidant":
                result["subtext"] = "用距离保护自己的真实情感"

        elif skill_name == "emotion_probe":
            if neuroticism is not None and neuroticism >= 0.7:
                result["fine_grained"] = [
                    {"emotion": "焦虑", "intensity": 0.7, "evidence": "神经质水平较高"},
                    {"emotion": "不安", "intensity": 0.6, "evidence": "对威胁信号敏感"},
                ]
            if attachment == "anxious":
                result["primary_undisclosed_emotion"] = "对被抛弃的深层恐惧"
                result["emotional_complexity"] = "complex"
            elif attachment == "avoidant":
                result["primary_undisclosed_emotion"] = "对亲密的抗拒与渴望并存"
                result["emotional_complexity"] = "complex"

    @staticmethod
    def _extract_param(text: str, pattern: str) -> float | None:
        import re
        m = re.search(pattern, text)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                pass
        return None

    @staticmethod
    def _extract_str(text: str, pattern: str) -> str | None:
        import re
        m = re.search(pattern, text)
        return m.group(1).strip() if m else None

    @staticmethod
    def _extract_list(text: str, pattern: str) -> list[str]:
        import re
        m = re.search(pattern, text)
        if m:
            return [s.strip().strip("'\"") for s in m.group(1).split(",") if s.strip()]
        return []

    def _drop_fields(self, obj: dict, schema: dict, n: int) -> dict:
        """Drop n random non-critical fields."""
        non_critical = [k for k, (_, crit) in schema.items() if not crit]
        if not non_critical:
            return obj
        to_drop = self.rng.sample(non_critical, min(n, len(non_critical)))
        return {k: v for k, v in obj.items() if k not in to_drop}

    def _format_json(self, obj: dict, style: str) -> str:
        """Format JSON with different styles."""
        json_str = json.dumps(obj, ensure_ascii=False, indent=2)

        if style == "clean":
            return json_str
        elif style == "markdown":
            return f"```json\n{json_str}\n```"
        elif style == "trailing_comma":
            # Add trailing commas (common LLM mistake)
            lines = json_str.split("\n")
            result_lines = []
            for line in lines:
                stripped = line.rstrip()
                if stripped.endswith('"') or stripped.endswith("]") or stripped.endswith("}"):
                    if not stripped.endswith("{") and not stripped.endswith("[") and "," not in stripped[-3:]:
                        result_lines.append(stripped + ",")
                    else:
                        result_lines.append(stripped)
                else:
                    result_lines.append(stripped)
            return "\n".join(result_lines)
        elif style == "single_quotes":
            # Replace double quotes with single quotes (another LLM mistake)
            # Simple approach: just replace top-level string quotes
            return json_str.replace('"', "'")
        else:
            return json_str

    def _make_broken(self, perfect: dict) -> str:
        """Create a structurally broken but partially recoverable JSON."""
        json_str = json.dumps(perfect, ensure_ascii=False)
        # Remove closing brace, or add extra text after JSON, or add BOM
        choice = self.rng.randint(0, 3)
        if choice == 0:
            # Missing closing brace(s)
            return json_str[:-self.rng.randint(1, 3)]
        elif choice == 1:
            # Extra text after JSON
            return json_str + "\n这是额外的解释文本，LLM有时会在JSON后面添加内容。"
        elif choice == 2:
            # BOM + JSON
            return "﻿" + json_str
        else:
            # Truncated in the middle
            cut = len(json_str) // 2 + self.rng.randint(-20, 20)
            return json_str[:max(1, cut)]

    def _make_garbage(self) -> str:
        """Generate completely unusable output."""
        garbage_types = [
            "抱歉，我无法分析这个场景。",
            "I apologize, but I cannot provide that analysis.",
            "```\nAnalysis: The character seems confused.\n```",
            '{"error": "invalid request"}',
            "",
            "The quick brown fox jumps over the lazy dog.",
        ]
        return self.rng.choice(garbage_types)
