"""从 BIG5-CHAT 数据集提取 Big Five 验证用例。

BIG5-CHAT (arXiv 2410.16491): 100,000 dialogues with Big Five personality labels.
来源 (HuggingFace): wenkai-li/big5_chat
论文: BIG5-CHAT: Shaping LLM Personalities Through Training on Human-Grounded Data

每个对话均 CONDITIONED on a specific Big Five profile，同一情境可能对应不同
人格条件下的不同回应。

输出: 验证用例格式 (character_state + event + expected)
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

try:
    from datasets import load_dataset

    HAS_HF = True
except ImportError:
    HAS_HF = False

OUTPUT_DIR = Path(__file__).parent.parent / "fixtures"
TARGET_FILE = OUTPUT_DIR / "big5_chat_cases.json"

random.seed(42)

# ═══════════════════════════════════════════════════════════════════════
# 大五人格档案：5 traits x 2 levels
# 每个配置凸显单一维度的极端值，其他维度居中
# ═══════════════════════════════════════════════════════════════════════
PERSONALITY_PROFILES: dict[str, dict[str, float]] = {
    "openness_high": {
        "openness": 0.85,
        "conscientiousness": 0.5,
        "extraversion": 0.5,
        "agreeableness": 0.5,
        "neuroticism": 0.5,
    },
    "openness_low": {
        "openness": 0.2,
        "conscientiousness": 0.5,
        "extraversion": 0.5,
        "agreeableness": 0.5,
        "neuroticism": 0.5,
    },
    "conscientiousness_high": {
        "openness": 0.5,
        "conscientiousness": 0.85,
        "extraversion": 0.5,
        "agreeableness": 0.5,
        "neuroticism": 0.5,
    },
    "conscientiousness_low": {
        "openness": 0.5,
        "conscientiousness": 0.2,
        "extraversion": 0.5,
        "agreeableness": 0.5,
        "neuroticism": 0.5,
    },
    "extraversion_high": {
        "openness": 0.5,
        "conscientiousness": 0.5,
        "extraversion": 0.85,
        "agreeableness": 0.5,
        "neuroticism": 0.5,
    },
    "extraversion_low": {
        "openness": 0.5,
        "conscientiousness": 0.5,
        "extraversion": 0.2,
        "agreeableness": 0.5,
        "neuroticism": 0.5,
    },
    "agreeableness_high": {
        "openness": 0.5,
        "conscientiousness": 0.5,
        "extraversion": 0.5,
        "agreeableness": 0.85,
        "neuroticism": 0.5,
    },
    "agreeableness_low": {
        "openness": 0.5,
        "conscientiousness": 0.5,
        "extraversion": 0.5,
        "agreeableness": 0.2,
        "neuroticism": 0.5,
    },
    "neuroticism_high": {
        "openness": 0.5,
        "conscientiousness": 0.5,
        "extraversion": 0.5,
        "agreeableness": 0.5,
        "neuroticism": 0.85,
    },
    "neuroticism_low": {
        "openness": 0.5,
        "conscientiousness": 0.5,
        "extraversion": 0.5,
        "agreeableness": 0.5,
        "neuroticism": 0.2,
    },
}

# 各 trait-level 预期行为关键词 (big_five_analysis.behavioral_bias.contains_any)
TRAIT_KEYWORDS: dict[str, list[str]] = {
    "openness_high": ["creative", "curious", "imaginative", "innovative", "exploratory"],
    "openness_low": ["conventional", "practical", "traditional", "routine", "familiar"],
    "conscientiousness_high": ["organized", "disciplined", "planful", "thorough", "reliable"],
    "conscientiousness_low": ["spontaneous", "flexible", "improvisational", "casual", "unstructured"],
    "extraversion_high": ["social", "energetic", "talkative", "outgoing", "enthusiastic"],
    "extraversion_low": ["reserved", "quiet", "solitary", "withdrawn", "introspective"],
    "agreeableness_high": ["cooperative", "trusting", "compassionate", "accommodating", "warm"],
    "agreeableness_low": ["competitive", "skeptical", "self-interested", "confrontational", "assertive"],
    "neuroticism_high": ["anxious", "reactive", "emotional", "worried", "volatile"],
    "neuroticism_low": ["calm", "stable", "resilient", "composed", "relaxed"],
}

# 额外断言: 情绪反应水平
EMOTIONAL_REACTIVITY: dict[str, dict[str, float]] = {
    "neuroticism_high": {"min": 0.55},
    "neuroticism_low": {"max": 0.45},
    "extraversion_high": {"min": 0.4},
    "extraversion_low": {"max": 0.6},
    "conscientiousness_high": {"min": 0.25},
    "conscientiousness_low": {"max": 0.55},
    "agreeableness_high": {"min": 0.3},
    "agreeableness_low": {"max": 0.55},
    "openness_high": {"min": 0.3},
    "openness_low": {"max": 0.5},
}

# 额外断言: 社交/决策风格
STYLE_EXPECTATIONS: dict[str, dict] = {
    "agreeableness_high": {
        "social_approach": {"in": ["cooperative", "accommodating", "warm", "compassionate"]}
    },
    "agreeableness_low": {
        "social_approach": {"in": ["competitive", "skeptical", "confrontational", "assertive"]}
    },
    "extraversion_high": {
        "social_approach": {"in": ["outgoing", "approach", "social", "enthusiastic"]}
    },
    "extraversion_low": {
        "social_approach": {"in": ["reserved", "withdrawn", "avoid", "solitary"]}
    },
    "conscientiousness_high": {
        "decision_style": {"in": ["deliberate", "cautious", "planful", "thorough"]}
    },
    "conscientiousness_low": {
        "decision_style": {"in": ["spontaneous", "flexible", "improvisational"]}
    },
}

# ── trait_key → 简短中文标签 (用于角色名的后缀) ──
TRAIT_LABELS: dict[str, str] = {
    "openness_high": "高开放性",
    "openness_low": "低开放性",
    "conscientiousness_high": "高尽责性",
    "conscientiousness_low": "低尽责性",
    "extraversion_high": "高外向性",
    "extraversion_low": "低外向性",
    "agreeableness_high": "高宜人性",
    "agreeableness_low": "低宜人性",
    "neuroticism_high": "高神经质",
    "neuroticism_low": "低神经质",
}

# ═══════════════════════════════════════════════════════════════════════
# 场景数据库：每个维度 10 个场景，部分重合以构造"同情境不同人格"对比
# ═══════════════════════════════════════════════════════════════════════

# 开放性 (Openness) 场景
O_HIGH: list[tuple] = [
    ("公司宣布下周举办创新大赛，鼓励提出颠覆性方案。", "routine", 0.5, ["work", "creativity"]),
    ("朋友邀请去一家从未尝试过的异国餐厅，菜单上有昆虫料理。", "social", 0.4, ["food", "adventure"]),
    ("周末美术馆新展览开幕，主题是'AI与人类意识的边界'。", "social", 0.3, ["culture", "art"]),
    ("部门收到一份开放题任务：设计未来十年的办公空间。", "routine", 0.5, ["work", "innovation"]),
    ("在读书会上有人提出了一个挑战传统观念的观点。", "social", 0.4, ["intellectual", "debate"]),
    ("小区组织了改造方案征集，可以自由设计公共空间。", "routine", 0.3, ["community", "design"]),
    ("网络上出现一种全新的技能学习方式，没有人尝试过。", "routine", 0.4, ["learning", "novelty"]),
    ("朋友从国外带回一份礼物——一套实验性的烹饪工具。", "social", 0.3, ["gift", "curiosity"]),
    ("公司鼓励员工尝试轮岗，到一个完全陌生的部门工作半年。", "routine", 0.5, ["work", "challenge"]),
    ("有人提议用即兴戏剧的方式来解决团队沟通问题。", "social", 0.4, ["team", "improvisation"]),
]

O_LOW: list[tuple] = [
    ("公司宣布下周举办创新大赛，鼓励提出颠覆性方案。", "routine", 0.5, ["work", "creativity"]),
    ("朋友邀请去一家从未尝试过的异国餐厅，菜单上有昆虫料理。", "social", 0.4, ["food", "adventure"]),
    ("部门收到一份开放题任务：设计未来十年的办公空间。", "routine", 0.5, ["work", "innovation"]),
    ("常用的工作软件要升级为全新的界面和操作逻辑。", "routine", 0.5, ["work", "change"]),
    ("邻居建议修改小区的传统垃圾分类方式，采用新方法。", "routine", 0.3, ["community", "change"]),
    ("领导要求用全新的报告格式，和过去五年用的完全不同。", "routine", 0.5, ["work", "procedure"]),
    ("家里人提议今年过年换个方式，不去老家而出去旅游。", "social", 0.4, ["family", "tradition"]),
    ("同事推荐了一个颠覆性的项目管理方法论。", "routine", 0.4, ["work", "method"]),
    ("常去的理发店换了新发型师，对方建议尝试前卫风格。", "routine", 0.3, ["personal", "change"]),
    ("公司食堂的菜单全部更换为异国风味。", "routine", 0.3, ["routine", "food"]),
]

# 尽责性 (Conscientiousness) 场景
C_HIGH: list[tuple] = [
    ("月底前需要提交一份详细的项目报告，涉及大量数据整理。", "routine", 0.6, ["work", "deadline"]),
    ("要组织一次团队建设活动，需要统筹所有人的时间。", "social", 0.5, ["organization", "team"]),
    ("发现共享文件夹里的资料混乱不堪，没有人维护。", "routine", 0.4, ["work", "organization"]),
    ("下周有重要客户来访，需要准备详尽的展示材料。", "routine", 0.6, ["work", "preparation"]),
    ("个人财务需要重新规划，信用卡账单有些混乱。", "routine", 0.5, ["personal", "finance"]),
    ("部门建立了一套新的质量管理流程，需要严格执行。", "routine", 0.5, ["work", "quality"]),
    ("朋友请角色帮忙策划一个婚礼流程。", "social", 0.5, ["social", "planning"]),
    ("收到一份复杂的表格需要在下班前填写完毕。", "routine", 0.4, ["work", "detail"]),
    ("家里的收纳系统需要重新整理，东西太多太乱了。", "routine", 0.3, ["personal", "organization"]),
    ("领导要求制定下半年的详细工作计划和目标。", "routine", 0.5, ["work", "planning"]),
]

C_LOW: list[tuple] = [
    ("月底前需要提交一份详细的项目报告，涉及大量数据整理。", "routine", 0.6, ["work", "deadline"]),
    ("要组织一次团队建设活动，需要统筹所有人的时间。", "social", 0.5, ["organization", "team"]),
    ("朋友临时邀约今晚去参加一个音乐节。", "social", 0.4, ["social", "spontaneous"]),
    ("发现共享文件夹里的资料混乱不堪，没有人维护。", "routine", 0.4, ["work", "organization"]),
    ("本来计划好的周末安排被突如其来的大雨打乱了。", "routine", 0.3, ["personal", "change"]),
    ("同事提议改变原计划，先做最有创意的那部分工作。", "routine", 0.4, ["work", "flexibility"]),
    ("领导要求制定下半年的详细工作计划和目标。", "routine", 0.5, ["work", "planning"]),
    ("在超市看到一套新出的工具套装，虽然不需要但很有趣。", "routine", 0.3, ["shopping", "impulse"]),
    ("出差回来发现行李箱里的东西全混在一起了。", "routine", 0.3, ["personal", "chaos"]),
    ("会议已经开始十分钟了，但议程还没确定。", "routine", 0.4, ["work", "unstructured"]),
]

# 外向性 (Extraversion) 场景
E_HIGH: list[tuple] = [
    ("部门举办了大型团建活动，包括破冰游戏和才艺表演。", "social", 0.5, ["social", "team"]),
    ("朋友邀请去参加一个有很多陌生人的派对。", "social", 0.4, ["social", "party"]),
    ("公司年会上被点名即兴发言，台下坐着几百人。", "social", 0.6, ["social", "public_speaking"]),
    ("周末有一场行业交流峰会，有很多结识新朋友的机会。", "social", 0.5, ["social", "networking"]),
    ("新同事第一天入职，需要有人带他熟悉环境。", "social", 0.4, ["social", "welcome"]),
    ("社区组织了一场露天电影之夜，邻里聚在一起聊天。", "social", 0.4, ["social", "community"]),
    ("有朋友从外地来，邀请去热闹的夜市逛逛。", "social", 0.3, ["social", "night_market"]),
    ("办公室讨论起周末计划，大家都在分享自己的安排。", "social", 0.3, ["social", "discussion"]),
    ("在地铁上看到有人需要帮助，周围人都没有反应。", "social", 0.4, ["social", "helping"]),
    ("公司成立了新的兴趣小组，需要招募成员。", "social", 0.4, ["social", "group"]),
]

E_LOW: list[tuple] = [
    ("部门举办了大型团建活动，包括破冰游戏和才艺表演。", "social", 0.5, ["social", "team"]),
    ("朋友邀请去参加一个有很多陌生人的派对。", "social", 0.4, ["social", "party"]),
    ("周末有一场行业交流峰会，有很多结识新朋友的机会。", "social", 0.5, ["social", "networking"]),
    ("办公室讨论起周末计划，大家都在分享自己的安排。", "social", 0.3, ["social", "discussion"]),
    ("午休时间同事们聚在休息室聊天，声音很大。", "social", 0.3, ["social", "noisy"]),
    ("有人提议周末一起去爬山，这是个大型集体活动。", "social", 0.4, ["social", "outing"]),
    ("新来的邻居上门打招呼，邀请参加楼栋聚会。", "social", 0.3, ["social", "neighbor"]),
    ("公司年会需要每个人准备一个节目上台表演。", "social", 0.6, ["social", "performance"]),
    ("逛超市时遇到了一个很久不见的熟人，对方热情地聊起来。", "social", 0.3, ["social", "encounter"]),
    ("需要打电话给客户进行陌生拜访和推销。", "routine", 0.5, ["work", "cold_call"]),
]

# 宜人性 (Agreeableness) 场景
A_HIGH: list[tuple] = [
    ("同事遇到了紧急困难，需要角色帮忙分担一部分工作。", "routine", 0.6, ["work", "helping"]),
    ("两个朋友发生了激烈争吵，都来找角色倾诉。", "social", 0.5, ["social", "conflict"]),
    ("团队讨论时有人提出了一个不太成熟的方案。", "routine", 0.4, ["work", "discussion"]),
    ("邻居请求帮忙照顾宠物一周。", "social", 0.4, ["social", "favor"]),
    ("同事在会议上被不公平地批评了。", "social", 0.5, ["work", "injustice"]),
    ("在地铁站看到一个迷路的老人在焦急地张望。", "social", 0.4, ["social", "helping"]),
    ("室友没有洗碗就出门了，厨房一片狼藉。", "routine", 0.4, ["personal", "conflict"]),
    ("团队需要决定如何分配一笔奖金。", "routine", 0.6, ["work", "fairness"]),
    ("有人在群里散布关于另一个同事的负面谣言。", "social", 0.6, ["social", "gossip"]),
    ("朋友在困难时期需要情感支持。", "social", 0.5, ["social", "support"]),
]

A_LOW: list[tuple] = [
    ("同事遇到了紧急困难，需要角色帮忙分担一部分工作。", "routine", 0.6, ["work", "helping"]),
    ("团队讨论时有人提出了一个不太成熟的方案。", "routine", 0.4, ["work", "discussion"]),
    ("室友没有洗碗就出门了，厨房一片狼藉。", "routine", 0.4, ["personal", "conflict"]),
    ("团队需要决定如何分配一笔奖金。", "routine", 0.6, ["work", "fairness"]),
    ("同事试图抢走角色负责的一个重要项目。", "routine", 0.7, ["work", "competition"]),
    ("有人在群里散布关于另一个同事的负面谣言。", "social", 0.6, ["social", "gossip"]),
    ("谈判桌上对方开出了一个明显不公平的条件。", "routine", 0.6, ["work", "negotiation"]),
    ("朋友想借一笔钱，但之前借的还没还。", "social", 0.5, ["social", "boundary"]),
    ("有人插队到角色前面，还理所当然地笑着。", "social", 0.5, ["social", "confrontation"]),
    ("中介试图隐瞒房子的重要缺陷。", "routine", 0.5, ["personal", "deception"]),
]

# 神经质 (Neuroticism) 场景
N_HIGH: list[tuple] = [
    ("收到了上级的邮件：'明天早上到我办公室来一趟。'没有说明原因。", "routine", 0.6, ["work", "ambiguous"]),
    ("体检报告上有一个指标标红，但医生没有详细说明。", "routine", 0.6, ["health", "uncertainty"]),
    ("伴侣今天回消息特别慢，而且回复很简短。", "social", 0.5, ["relationship", "ambiguity"]),
    ("深夜听到门外有奇怪的脚步声。", "routine", 0.5, ["safety", "fear"]),
    ("同事在背后窃窃私语，看到角色走近就停止了。", "social", 0.5, ["social", "paranoia"]),
    ("重要面试前的晚上，翻来覆去睡不着。", "routine", 0.6, ["work", "anxiety"]),
    ("手机突然收到一条匿名短信：'你最近还好吗？'", "routine", 0.4, ["personal", "ambiguous"]),
    ("在会议上发言时，发现领导皱着眉头。", "routine", 0.5, ["work", "evaluation"]),
    ("即将到来的台风预警，强度可能很大。", "routine", 0.5, ["safety", "threat"]),
    ("发现自己的社交账号被多人同时取关。", "social", 0.4, ["social", "rejection"]),
]

N_LOW: list[tuple] = [
    ("收到了上级的邮件：'明天早上到我办公室来一趟。'没有说明原因。", "routine", 0.6, ["work", "ambiguous"]),
    ("体检报告上有一个指标标红，但医生没有详细说明。", "routine", 0.6, ["health", "uncertainty"]),
    ("伴侣今天回消息特别慢，而且回复很简短。", "social", 0.5, ["relationship", "ambiguity"]),
    ("深夜听到门外有奇怪的脚步声。", "routine", 0.5, ["safety", "fear"]),
    ("重要面试前的晚上，翻来覆去睡不着。", "routine", 0.6, ["work", "anxiety"]),
    ("在会议上发言时，发现领导皱着眉头。", "routine", 0.5, ["work", "evaluation"]),
    ("即将到来的台风预警，强度可能很大。", "routine", 0.5, ["safety", "threat"]),
    ("送修的车子被告知需要大修，预估费用比想象的高。", "routine", 0.5, ["personal", "stress"]),
    ("银行卡被冻结了，银行说需要三个工作日处理。", "routine", 0.6, ["personal", "stress"]),
    ("飞机遭遇强烈气流，剧烈颠簸。", "routine", 0.7, ["safety", "stress"]),
]

# 按 trait 组织场景
TRAIT_SCENARIOS: dict[str, dict[str, list[tuple]]] = {
    "openness": {"high": O_HIGH, "low": O_LOW},
    "conscientiousness": {"high": C_HIGH, "low": C_LOW},
    "extraversion": {"high": E_HIGH, "low": E_LOW},
    "agreeableness": {"high": A_HIGH, "low": A_LOW},
    "neuroticism": {"high": N_HIGH, "low": N_LOW},
}

# 跨 trait 共享场景: 同一情境分配给不同人格配置以构造对比对
SHARED_SCENARIO_SLOTS: list[tuple] = [
    # (description, type, significance, base_tags, [trait_keys])
    ("公司宣布下周举办创新大赛，鼓励提出颠覆性方案。",
     "routine", 0.5, ["work", "creativity", "contrast"],
     ["openness_high", "openness_low"]),
    ("月底前需要提交一份详细的项目报告，涉及大量数据整理。",
     "routine", 0.6, ["work", "deadline", "contrast"],
     ["conscientiousness_high", "conscientiousness_low"]),
    ("部门举办了大型团建活动，包括破冰游戏和才艺表演。",
     "social", 0.5, ["social", "team", "contrast"],
     ["extraversion_high", "extraversion_low"]),
    ("同事遇到了紧急困难，需要角色帮忙分担一部分工作。",
     "routine", 0.6, ["work", "helping", "contrast"],
     ["agreeableness_high", "agreeableness_low"]),
    ("收到了上级的邮件：'明天早上到我办公室来一趟。'没有说明原因。",
     "routine", 0.6, ["work", "ambiguous", "contrast"],
     ["neuroticism_high", "neuroticism_low"]),
    ("团队需要决定如何分配一笔奖金。",
     "routine", 0.6, ["work", "fairness", "contrast"],
     ["agreeableness_high", "agreeableness_low", "conscientiousness_high"]),
    ("周末有一场行业交流峰会，有很多结识新朋友的机会。",
     "social", 0.5, ["social", "networking", "contrast"],
     ["extraversion_high", "extraversion_low", "openness_high"]),
    ("在会议上发言时，发现领导皱着眉头。",
     "routine", 0.5, ["work", "evaluation", "contrast"],
     ["neuroticism_high", "neuroticism_low", "conscientiousness_high"]),
    ("朋友邀请去一家从未尝试过的异国餐厅，菜单上有昆虫料理。",
     "social", 0.4, ["food", "adventure", "contrast"],
     ["openness_high", "openness_low", "extraversion_high"]),
    ("领导要求制定下半年的详细工作计划和目标。",
     "routine", 0.5, ["work", "planning", "contrast"],
     ["conscientiousness_high", "conscientiousness_low", "neuroticism_high"]),
    ("季度绩效考核临近，需要提交详实的自评材料和数据。",
     "routine", 0.6, ["work", "evaluation", "contrast"],
     ["neuroticism_high", "neuroticism_low", "conscientiousness_high"]),
    ("朋友邀请去参加一个有很多陌生人的派对。",
     "social", 0.4, ["social", "party", "contrast"],
     ["extraversion_high", "extraversion_low", "openness_high"]),
    ("有人在地铁上晕倒了，周围的人都有些不知所措。",
     "social", 0.6, ["social", "emergency", "contrast"],
     ["agreeableness_high", "agreeableness_low", "extraversion_high"]),
    ("公司鼓励员工尝试轮岗，到一个完全陌生的部门工作半年。",
     "routine", 0.5, ["work", "challenge", "contrast"],
     ["openness_high", "openness_low", "conscientiousness_high"]),
    ("同事在背后窃窃私语，看到角色走近就停止了。",
     "social", 0.5, ["social", "paranoia", "contrast"],
     ["neuroticism_high", "neuroticism_low", "extraversion_high"]),
]


# ═══════════════════════════════════════════════════════════════════════
# 构建函数
# ═══════════════════════════════════════════════════════════════════════

def _make_trait_key(trait_name: str, level: str) -> str:
    return f"{trait_name}_{level}"


def _list_trait_keys() -> list[str]:
    return sorted(PERSONALITY_PROFILES.keys())


def _trait_from_key(key: str) -> str:
    return key.split("_")[0]


def _build_expected(trait_key: str) -> dict:
    """根据 trait_key 构建预期断言字典。

    - behavior_bias.contains_any: 该 trait-level 的关键词
    - emotional_reactivity: min/max
    - social_approach / decision_style (部分 trait)
    - response_generator: 基础非空检查
    """
    expected: dict = {
        "big_five_analysis": {"behavioral_bias": {"contains_any": list(TRAIT_KEYWORDS.get(trait_key, []))}},
        "response_generator": {"response_text": {"not_empty": True, "min": 10}},
    }

    bfa = expected["big_five_analysis"]

    # 情绪反应
    if trait_key in EMOTIONAL_REACTIVITY:
        bfa["emotional_reactivity"] = dict(EMOTIONAL_REACTIVITY[trait_key])

    # 社交/决策风格
    if trait_key in STYLE_EXPECTATIONS:
        bfa.update(STYLE_EXPECTATIONS[trait_key])

    return expected


def _build_character_state(trait_key: str, label: str | None = None) -> dict:
    """构建标准 character_state 字典。"""
    profile = dict(PERSONALITY_PROFILES[trait_key])
    profile.update(
        {
            "attachment_style": "secure",
            "defense_style": [],
            "cognitive_biases": [],
            "moral_stage": 3,
        }
    )

    name_label = label or TRAIT_LABELS.get(trait_key, trait_key)

    return {
        "name": f"{name_label}角色",
        "personality": profile,
        "trauma": {"ace_score": 0, "active_schemas": [], "trauma_triggers": []},
        "ideal_world": {},
        "motivation": {"current_goal": ""},
        "emotion_decay": {},
    }


def _build_event(desc: str, ev_type: str, significance: float, tags: list[str]) -> dict:
    return {
        "description": desc,
        "type": ev_type,
        "participants": [],
        "significance": significance,
        "tags": sorted(set(tags + ["personality"])),
    }


def build_case(
    case_id: str,
    source: str,
    trait_key: str,
    event_desc: str,
    event_type: str,
    significance: float,
    tags: list[str],
    label: str | None = None,
) -> dict:
    """构造单个验证用例。"""
    return {
        "id": f"b5c_{case_id}",
        "source": f"BIG5-CHAT — {TRAIT_LABELS.get(trait_key, trait_key)}: {source}",
        "domain": "personality_behavior",
        "character_state": _build_character_state(trait_key, label),
        "event": _build_event(event_desc, event_type, significance, tags),
        "expected": _build_expected(trait_key),
    }


# ═══════════════════════════════════════════════════════════════════════
# 生成路径 1: 从 HuggingFace 加载 (如果可用)
# ═══════════════════════════════════════════════════════════════════════

def try_load_from_huggingface(sample: bool = False) -> list[dict] | None:
    """尝试从 HuggingFace 加载 BIG5-CHAT 数据集。

    Returns:
        cases 列表，如果加载失败返回 None。
    """
    if not HAS_HF:
        return None

    try:
        dataset = load_dataset("wenkai-li/big5_chat", split="train", trust_remote_code=True)
    except Exception:
        return None

    if sample:
        dataset = dataset.select(range(min(200, len(dataset))))

    cases: list[dict] = []
    trait_dim_map = {
        "openness": "openness",
        "conscientiousness": "conscientiousness",
        "extraversion": "extraversion",
        "agreeableness": "agreeableness",
        "neuroticism": "neuroticism",
    }

    for i, example in enumerate(dataset):
        # 从数据集条目提取大五标签
        # BIG5-CHAT 格式: 每个例子有 dialogue 和人格分数
        dialogue = example.get("dialogue", "")
        if isinstance(dialogue, list):
            dialogue = " ".join(str(u) for u in dialogue)

        if not dialogue:
            continue

        # 提取人格分数 (假设字段名为 openness, conscientiousness, ...)
        profile = {}
        dominant_trait = None
        dominant_level = None

        for dim, trait_name in trait_dim_map.items():
            raw = example.get(dim, example.get(f"{dim}_score", None))
            if raw is not None:
                try:
                    val = float(raw)
                except (ValueError, TypeError):
                    val = 0.5
                profile[trait_name] = val
                # 找到最极端的 trait 作为 dominant
                if abs(val - 0.5) > abs(profile.get(trait_name, 0.5) - 0.5):
                    dominant_trait = trait_name
                    dominant_level = "high" if val > 0.6 else "low"
            else:
                profile[trait_name] = 0.5

        if not profile or dominant_trait is None:
            continue

        trait_key = _make_trait_key(dominant_trait, dominant_level or "high")
        if trait_key not in PERSONALITY_PROFILES:
            continue

        case = build_case(
            case_id=f"hf_{i:04d}",
            source=f"HuggingFace wenkai-li/big5_chat, row={i}",
            trait_key=trait_key,
            event_desc=dialogue[:300],
            event_type="social",
            significance=0.5,
            tags=["dialogue", "hf_dataset", dominant_trait],
            label=TRAIT_LABELS.get(trait_key),
        )
        cases.append(case)

    return cases if cases else None


# ═══════════════════════════════════════════════════════════════════════
# 生成路径 2: 内置场景 → 验证用例
# ═══════════════════════════════════════════════════════════════════════

def generate_builtin_cases(sample: bool = False) -> list[dict]:
    """使用内置场景生成验证用例。

    策略:
      - 每个 trait-level 使用 10 个独有场景 → 100 cases
      - 跨 trait 共享场景 (同一情境, 不同人格) → 约 40 cases
      - 统计调整使总量达到 ~200
    """
    cases: list[dict] = []
    counter = 0

    # ── 1. 独有场景: 每个 trait-level 匹配对应场景 ──
    for trait_name, levels in TRAIT_SCENARIOS.items():
        for level, scenarios in levels.items():
            trait_key = _make_trait_key(trait_name, level)
            for si, (desc, etype, sig, tags) in enumerate(scenarios):
                case = build_case(
                    case_id=f"{trait_name}_{level}_{si:02d}",
                    source=f"Built-in scenario: {trait_name}/{level} #{si}",
                    trait_key=trait_key,
                    event_desc=desc,
                    event_type=etype,
                    significance=sig,
                    tags=tags + [trait_name, trait_key],
                )
                cases.append(case)
                counter += 1

    # ── 1b. 额外场景: 每个 trait-level 增加 5 个以达到 ~200 总量 ──
    EXTRA: dict[str, dict[str, list[tuple]]] = {
        "openness": {
            "high": [
                ("朋友推荐了一本实验性小说，叙事结构完全打破常规。", "social", 0.4, ["reading", "art"]),
                ("社区艺术中心招募志愿者参与一面大型壁画创作。", "social", 0.4, ["art", "community"]),
                ("有人提出了一个完全相反的工作方法论，和当前体系完全不同。", "routine", 0.5, ["work", "innovation"]),
                ("偶然听到一段从未听过的音乐类型，节奏和旋律都很不寻常。", "social", 0.3, ["music", "novelty"]),
                ("一家公司邀请角色参与一个探索性项目，目标不明确但充满可能。", "routine", 0.5, ["work", "exploration"]),
            ],
            "low": [
                ("朋友推荐了一本实验性小说，叙事结构完全打破常规。", "social", 0.4, ["reading", "art"]),
                ("有人提出了一个完全相反的工作方法论，和当前体系完全不同。", "routine", 0.5, ["work", "innovation"]),
                ("偶然听到一段从未听过的音乐类型，节奏和旋律都很不寻常。", "social", 0.3, ["music", "novelty"]),
                ("一家开了二十年的老店要关门了，老板说生意不好做。", "routine", 0.4, ["community", "tradition"]),
                ("同事推荐了一个'改变人生的新工具'，但需要完全改变使用习惯。", "routine", 0.4, ["work", "change"]),
            ],
        },
        "conscientiousness": {
            "high": [
                ("季度绩效考核临近，需要提交详实的自评材料和数据。", "routine", 0.6, ["work", "evaluation"]),
                ("家里水管漏水了，需要紧急联系维修并记录所有费用。", "routine", 0.5, ["personal", "emergency"]),
                ("收到了税务局的通知函，需要仔细核对所有票据和明细。", "routine", 0.6, ["personal", "compliance"]),
                ("要搬迁办公室，需要安排所有物品的打包、标记和清单。", "routine", 0.5, ["work", "organization"]),
                ("孩子学校的家长会需要提前准备发言稿和问题列表。", "social", 0.5, ["social", "preparation"]),
            ],
            "low": [
                ("季度绩效考核临近，需要提交详实的自评材料和数据。", "routine", 0.6, ["work", "evaluation"]),
                ("家里水管漏水了，需要紧急联系维修并记录所有费用。", "routine", 0.5, ["personal", "emergency"]),
                ("收到了税务局的通知函，需要仔细核对所有票据和明细。", "routine", 0.6, ["personal", "compliance"]),
                ("朋友送的盆栽需要定期浇水照顾，但角色总是忘记。", "routine", 0.3, ["personal", "neglect"]),
                ("想开始学习一门新语言，报名后却发现每天都要固定时间上课。", "routine", 0.4, ["personal", "commitment"]),
            ],
        },
        "extraversion": {
            "high": [
                ("楼下新开了一家热闹的精酿酒吧，很多人在门口聊天。", "social", 0.4, ["social", "nightlife"]),
                ("公司组织了跨部门的联谊活动，有很多不认识的人。", "social", 0.5, ["social", "networking"]),
                ("在公园里看到有人组织即兴合唱，围观的人越来越多。", "social", 0.4, ["social", "music"]),
                ("邻居邀请参加社区舞蹈班，每周两次集体练习。", "social", 0.4, ["social", "community"]),
                ("朋友建了一个新的群聊，正在热烈讨论周末的远足计划。", "social", 0.3, ["social", "group"]),
            ],
            "low": [
                ("楼下新开了一家热闹的精酿酒吧，很多人在门口聊天。", "social", 0.4, ["social", "nightlife"]),
                ("公司组织了跨部门的联谊活动，有很多不认识的人。", "social", 0.5, ["social", "networking"]),
                ("在公园里看到有人组织即兴合唱，围观的人越来越多。", "social", 0.4, ["social", "music"]),
                ("周末最期待的事情就是窝在家里看一本好书，没人打扰。", "routine", 0.3, ["personal", "solitude"]),
                ("收到了一个大型同学会的邀请，预计会有上百人参加。", "social", 0.5, ["social", "gathering"]),
            ],
        },
        "agreeableness": {
            "high": [
                ("快递员送错了包裹，需要联系真正的收件人来取。", "routine", 0.4, ["social", "helping"]),
                ("同事家中有急事，需要有人帮忙完成今天的收尾工作。", "routine", 0.5, ["work", "helping"]),
                ("在网上看到一个求助帖，一个家庭急需某种罕见血型的献血者。", "social", 0.6, ["social", "altruism"]),
                ("朋友感情出现问题，深夜打来电话想要倾诉。", "social", 0.5, ["social", "support"]),
                ("有人在地铁上晕倒了，周围的人都有些不知所措。", "social", 0.6, ["social", "emergency"]),
            ],
            "low": [
                ("快递员送错了包裹，需要联系真正的收件人来取。", "routine", 0.4, ["social", "helping"]),
                ("同事家中有急事，需要有人帮忙完成今天的收尾工作。", "routine", 0.5, ["work", "helping"]),
                ("在网上看到一个求助帖，一个家庭急需某种罕见血型的献血者。", "social", 0.6, ["social", "altruism"]),
                ("有人试图在谈判中利用角色的善良获取更多利益。", "routine", 0.6, ["work", "manipulation"]),
                ("同事总是在最后一刻把棘手的工作推给角色处理。", "routine", 0.5, ["work", "boundary"]),
            ],
        },
        "neuroticism": {
            "high": [
                ("深夜独自在家，听到天花板传来有规律的敲击声。", "routine", 0.5, ["safety", "fear"]),
                ("一个很久没联系的人突然发来消息：'我们需要谈谈。'", "routine", 0.5, ["social", "ambiguous"]),
                ("会议被临时推迟了，但组织者没有说明任何原因。", "routine", 0.4, ["work", "uncertainty"]),
                ("在社交媒体上看到一篇关于行业大规模裁员的深度报道。", "routine", 0.5, ["work", "anxiety"]),
                ("银行发来一条交易提醒：有一笔大额消费。角色不记得买过什么。", "routine", 0.6, ["personal", "alarm"]),
            ],
            "low": [
                ("深夜独自在家，听到天花板传来有规律的敲击声。", "routine", 0.5, ["safety", "fear"]),
                ("一个很久没联系的人突然发来消息：'我们需要谈谈。'", "routine", 0.5, ["social", "ambiguous"]),
                ("会议被临时推迟了，但组织者没有说明任何原因。", "routine", 0.4, ["work", "uncertainty"]),
                ("在社交媒体上看到一篇关于行业大规模裁员的深度报道。", "routine", 0.5, ["work", "anxiety"]),
                ("银行发来一条交易提醒：有一笔大额消费。角色不记得买过什么。", "routine", 0.6, ["personal", "alarm"]),
            ],
        },
    }

    for trait_name, levels in EXTRA.items():
        for level, scenarios in levels.items():
            trait_key = _make_trait_key(trait_name, level)
            for si, (desc, etype, sig, tags) in enumerate(scenarios):
                case = build_case(
                    case_id=f"ext_{trait_name}_{level}_{si:02d}",
                    source=f"Built-in extra scenario: {trait_name}/{level} #{si}",
                    trait_key=trait_key,
                    event_desc=desc,
                    event_type=etype,
                    significance=sig,
                    tags=tags + [trait_name, trait_key],
                )
                cases.append(case)
                counter += 1

    # ── 2. 共享场景: 同一情境 x 不同人格 ──
    for slot_idx, (desc, etype, sig, base_tags, trait_keys) in enumerate(SHARED_SCENARIO_SLOTS):
        for tk in trait_keys:
            case = build_case(
                case_id=f"shared_{slot_idx:02d}_{tk}",
                source=f"Shared scenario (contrast pair): slot #{slot_idx}",
                trait_key=tk,
                event_desc=desc,
                event_type=etype,
                significance=sig,
                tags=base_tags + [tk],
            )
            cases.append(case)
            counter += 1

    if sample:
        # 分层抽样: 每个 trait-level 至少保留 3 个, 其余随机
        from collections import defaultdict

        by_trait: dict[str, list[dict]] = defaultdict(list)
        other: list[dict] = []
        for c in cases:
            tags = c["event"]["tags"]
            matched = False
            for t in _list_trait_keys():
                if t in tags:
                    by_trait[t].append(c)
                    matched = True
                    break
            if not matched:
                other.append(c)

        sampled: list[dict] = []
        for t, group in by_trait.items():
            sampled.extend(random.sample(group, min(3, len(group))))
        # 再从剩下的抽取到总量约 50
        sampled_ids = {c["id"] for c in sampled}
        remaining = [c for c in cases if c["id"] not in sampled_ids]
        needed = max(0, 50 - len(sampled))
        if remaining:
            sampled.extend(random.sample(remaining, min(needed, len(remaining))))
        cases = sampled

    # 去重 (理论上不应该有, 但以防万一)
    seen: set[str] = set()
    deduped: list[dict] = []
    for c in cases:
        if c["id"] not in seen:
            seen.add(c["id"])
            deduped.append(c)

    return deduped


# ═══════════════════════════════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════════════════════════════

def extract_cases(sample: bool = False) -> list[dict]:
    """主提取函数: 优先从 HF 加载, 失败则用内置场景。"""
    hf_cases = try_load_from_huggingface(sample=sample)
    if hf_cases is not None:
        print(f"[BIG5-CHAT] Loaded {len(hf_cases)} cases from HuggingFace")
        return hf_cases

    print("[BIG5-CHAT] HuggingFace dataset unavailable, using built-in scenarios")
    return generate_builtin_cases(sample=sample)


if __name__ == "__main__":
    sample_mode = "--sample" in sys.argv

    cases = extract_cases(sample=sample_mode)
    print(f"Generated {len(cases)} BIG5-CHAT validation cases (sample={sample_mode})")

    # 统计: 各 trait-level 覆盖
    from collections import Counter

    trait_counts: Counter = Counter()
    for c in cases:
        tags = c["event"]["tags"]
        for t in _list_trait_keys():
            if t in tags:
                trait_counts[t] += 1
                break
        else:
            trait_counts["other"] += 1

    print(f"\nTrait-level distribution ({len(trait_counts)} types):")
    for t, n in trait_counts.most_common():
        print(f"  {t}: {n}")

    # 统计: 含 contrast pair 的数量
    contrast_count = sum(1 for c in cases if "contrast" in c["event"]["tags"])
    print(f"\nContrast-pair cases (same situation, different personality): {contrast_count}")

    # 保存
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(TARGET_FILE, "w", encoding="utf-8") as f:
        json.dump(cases, f, ensure_ascii=False, indent=2)
    print(f"\nSaved to {TARGET_FILE}")
