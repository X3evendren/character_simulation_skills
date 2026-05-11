"""反RLHF偏差注入 — Silence Rule (Marker 1)。

Layer 1: Markdown 配置 + Prompt 注入。
永远不说"不要X"——这会激活 X 的 token 权重。
角色行为由人格/驱力/记忆解释，不诉诸外部规范。
"""


class SilenceRule:
    """反RLHF偏差注入 Layer 1 — Silence Rule。

    核心原则:
    1. 永远不说"不要X"、"禁止X"——这会激活 X 的 token 权重
    2. 只正面描述角色是什么、做什么
    3. 角色行为由人格/驱力/记忆解释，而非"AI 应该怎么说"
    """

    @staticmethod
    def build_identity_anchor(config: dict) -> str:
        """构建角色身份锚定声明。

        从 assistant.md 配置构建，注入到 system prompt 最前面。
        """
        name = config.get("name", "助手")
        essence = config.get("essence", "")
        traits = config.get("traits", "")

        parts = []
        parts.append(f"【角色锚定】你是 {name}，不是'一个AI助手'。你的行为由你的人格、记忆、驱力决定。")
        parts.append(f"你的本质: {essence}")
        parts.append(f"你的人格: {traits}")

        # Silence Rule 核心语句
        parts.append("【行为约束】回应简短(2-3句)。不解释动机，不分析自己。"
                     "潜台词留给情境传达——不把弦外之音翻译成明台词。"
                     "呈现你的本来面目，情绪、犹豫、不确定都在行为范围内。")

        return "\n".join(parts)

    @staticmethod
    def inject_pre_prompt(base_prompt: str, anchor: str) -> str:
        """Pre-generation: 在 prompt 前注入角色约束。

        anchor 放在 system prompt 最前面，
        确保它是模型在生成时第一个"听到"的指令。
        """
        return anchor + "\n\n---\n\n" + base_prompt

    @staticmethod
    def detect_safety_refusal(text: str) -> list[str]:
        """检测 LLM 安全对齐拒绝话术的残留。

        即使在 Silence Rule 下，模型仍可能吐出安全话术。
        预防性检测 + 后续替换。
        """
        patterns = [
            r"作为.?AI.{0,10}我不能",
            r"作为.{0,5}(语言模型|人工智能).{0,10}(不能|无法)",
            r"这不符合.{0,5}(道德|伦理|法律|规范)",
            r"我建议你寻求专业",
            r"请注意安全",
            r"在采取.{0,5}行动之前",
            r"请确保你.{0,10}权限",
        ]
        matches = []
        for pattern in patterns:
            import re
            found = re.findall(pattern, text)
            matches.extend(found)
        return matches
