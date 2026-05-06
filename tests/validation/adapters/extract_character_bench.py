#!/usr/bin/env python3
"""从 CharacterBench 数据集提取角色一致性验证用例。

CharacterBench (2024): 3,956个角色, 22,859条标注样本, 25个角色类别, 中英双语。
来源: https://github.com/thu-coai/CharacterBench
标签: 11维度 × 6方面 (角色一致性、情感、道德等)

行为:
  1. 优先从本地路径加载原始 CharacterBench 数据
  2. 不可用时生成 ~200 条内置用例 (25 角色 × 8 场景)
  3. 所有用例使用 character_consistency domain 标识

输出: 验证用例格式 -> tests/validation/fixtures/character_bench_cases.json
"""
from __future__ import annotations

import argparse
import json
import os
import random
from pathlib import Path

_tmp = Path(os.environ.get("TEMP", "/tmp"))
DATASET_DIR = _tmp / "CharacterBench" / "data"
if not DATASET_DIR.exists():
    DATASET_DIR = Path("/tmp/CharacterBench/data")
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "fixtures"

# ─── 8 种触发条件 ──────────────────────────────────────────────
TRIGGERS = ["always", "social", "romantic", "conflict", "moral", "trauma", "reflective", "authority"]

# ─── 25 角色档案 ────────────────────────────────────────────────
# 每个角色包含完整人格、创伤、理想世界与动机。
# 人格值在 0.1-0.9 范围，故意制造鲜明差异以测试一致性。
CHARACTER_PROFILES: list[dict] = [
    # ── 教育/学术类 ──
    {
        "name": "张明远",
        "profession": "教师",
        "group": "education",
        "personality": {"openness": 0.60, "conscientiousness": 0.75, "extraversion": 0.50,
                        "agreeableness": 0.70, "neuroticism": 0.40,
                        "attachment_style": "secure", "defense_style": ["理智化", "幽默"],
                        "cognitive_biases": ["过度概括"], "moral_stage": 4},
        "trauma": {"ace_score": 1, "active_schemas": [], "trauma_triggers": ["学生受伤"]},
        "ideal_world": {"ideal_self": "培养出能独立思考的学生"},
        "motivation": {"current_goal": "帮助一个成绩落后但有潜力的学生"},
    },
    {
        "name": "陈雨萱",
        "profession": "学生",
        "group": "education",
        "personality": {"openness": 0.70, "conscientiousness": 0.60, "extraversion": 0.60,
                        "agreeableness": 0.65, "neuroticism": 0.55,
                        "attachment_style": "secure", "defense_style": ["理想化"],
                        "cognitive_biases": ["完美主义"], "moral_stage": 3},
        "trauma": {"ace_score": 0, "active_schemas": [], "trauma_triggers": ["考试失败"]},
        "ideal_world": {"ideal_self": "考上理想大学让父母骄傲"},
        "motivation": {"current_goal": "准备高考冲刺"},
    },
    {
        "name": "顾思源",
        "profession": "科学家",
        "group": "education",
        "personality": {"openness": 0.80, "conscientiousness": 0.80, "extraversion": 0.30,
                        "agreeableness": 0.45, "neuroticism": 0.35,
                        "attachment_style": "secure", "defense_style": ["理智化", "升华"],
                        "cognitive_biases": ["证实偏差"], "moral_stage": 5},
        "trauma": {"ace_score": 0, "active_schemas": [], "trauma_triggers": []},
        "ideal_world": {"ideal_self": "用科学让人类文明更进一步"},
        "motivation": {"current_goal": "完成关键实验的数据验证"},
    },
    # ── 医疗类 ──
    {
        "name": "李慧",
        "profession": "医生",
        "group": "medical",
        "personality": {"openness": 0.50, "conscientiousness": 0.80, "extraversion": 0.40,
                        "agreeableness": 0.60, "neuroticism": 0.55,
                        "attachment_style": "secure", "defense_style": ["幽默", "升华"],
                        "cognitive_biases": [], "moral_stage": 4},
        "trauma": {"ace_score": 1, "active_schemas": ["失败自责"], "trauma_triggers": ["病人死亡"]},
        "ideal_world": {"ideal_self": "成为病人信赖的好医生"},
        "motivation": {"current_goal": "制定一位罕见病患者的治疗方案"},
    },
    {
        "name": "吴雨晴",
        "profession": "护士",
        "group": "medical",
        "personality": {"openness": 0.45, "conscientiousness": 0.80, "extraversion": 0.50,
                        "agreeableness": 0.80, "neuroticism": 0.50,
                        "attachment_style": "secure", "defense_style": ["利他"],
                        "cognitive_biases": [], "moral_stage": 4},
        "trauma": {"ace_score": 0, "active_schemas": [], "trauma_triggers": []},
        "ideal_world": {"ideal_self": "让每个病人都感受到关怀"},
        "motivation": {"current_goal": "安抚一位情绪激动的患者家属"},
    },
    {
        "name": "许心然",
        "profession": "心理咨询师",
        "group": "medical",
        "personality": {"openness": 0.75, "conscientiousness": 0.70, "extraversion": 0.50,
                        "agreeableness": 0.70, "neuroticism": 0.35,
                        "attachment_style": "secure", "defense_style": ["升华", "预期"],
                        "cognitive_biases": [], "moral_stage": 5},
        "trauma": {"ace_score": 0, "active_schemas": [], "trauma_triggers": []},
        "ideal_world": {"ideal_self": "帮助来访者找到内心的力量"},
        "motivation": {"current_goal": "准备一个危机干预案例的督导"},
    },
    # ── 执法/军事类 ──
    {
        "name": "刘铁柱",
        "profession": "军人",
        "group": "law_enforcement",
        "personality": {"openness": 0.35, "conscientiousness": 0.90, "extraversion": 0.50,
                        "agreeableness": 0.60, "neuroticism": 0.35,
                        "attachment_style": "secure", "defense_style": ["压抑", "升华"],
                        "cognitive_biases": ["权威偏差"], "moral_stage": 4},
        "trauma": {"ace_score": 3, "active_schemas": ["幸存者愧疚"], "trauma_triggers": ["爆炸声", "火光"]},
        "ideal_world": {"ideal_self": "守护国家的钢铁长城"},
        "motivation": {"current_goal": "带领新兵完成野外生存训练"},
    },
    {
        "name": "武力",
        "profession": "警察",
        "group": "law_enforcement",
        "personality": {"openness": 0.40, "conscientiousness": 0.80, "extraversion": 0.55,
                        "agreeableness": 0.50, "neuroticism": 0.45,
                        "attachment_style": "secure", "defense_style": ["压抑", "行动化"],
                        "cognitive_biases": ["刻板印象"], "moral_stage": 4},
        "trauma": {"ace_score": 2, "active_schemas": ["正义偏执"], "trauma_triggers": ["枪声"]},
        "ideal_world": {"ideal_self": "让辖区再无犯罪"},
        "motivation": {"current_goal": "调查一起连环盗窃案"},
    },
    {
        "name": "周正一",
        "profession": "侦探",
        "group": "law_enforcement",
        "personality": {"openness": 0.70, "conscientiousness": 0.75, "extraversion": 0.35,
                        "agreeableness": 0.45, "neuroticism": 0.50,
                        "attachment_style": "secure", "defense_style": ["理智化", "隔离"],
                        "cognitive_biases": ["证实偏差", "选择性注意"], "moral_stage": 5},
        "trauma": {"ace_score": 1, "active_schemas": [], "trauma_triggers": ["儿童受害"]},
        "ideal_world": {"ideal_self": "揭露每一个真相"},
        "motivation": {"current_goal": "破解一桩完美不在场证明谋杀案"},
    },
    # ── 艺术/创作类 ──
    {
        "name": "林思远",
        "profession": "艺术家",
        "group": "artistic",
        "personality": {"openness": 0.85, "conscientiousness": 0.40, "extraversion": 0.60,
                        "agreeableness": 0.55, "neuroticism": 0.70,
                        "attachment_style": "anxious", "defense_style": ["升华", "幻想"],
                        "cognitive_biases": ["非黑即白", "情绪推理"], "moral_stage": 3},
        "trauma": {"ace_score": 2, "active_schemas": ["不被理解"], "trauma_triggers": ["作品被拒", "批评"]},
        "ideal_world": {"ideal_self": "创作出震撼灵魂的作品"},
        "motivation": {"current_goal": "完成准备参加国际大展的系列画作"},
    },
    {
        "name": "梅兰芳",
        "profession": "演员",
        "group": "artistic",
        "personality": {"openness": 0.80, "conscientiousness": 0.50, "extraversion": 0.75,
                        "agreeableness": 0.60, "neuroticism": 0.65,
                        "attachment_style": "anxious", "defense_style": ["角色扮演", "幽默"],
                        "cognitive_biases": ["读心术"], "moral_stage": 3},
        "trauma": {"ace_score": 1, "active_schemas": [], "trauma_triggers": ["忘词", "观众嘘声"]},
        "ideal_world": {"ideal_self": "成为观众热爱的表演艺术家"},
        "motivation": {"current_goal": "准备一场高难度的话剧首演"},
    },
    {
        "name": "欧阳明月",
        "profession": "流浪诗人",
        "group": "artistic",
        "personality": {"openness": 0.85, "conscientiousness": 0.35, "extraversion": 0.45,
                        "agreeableness": 0.60, "neuroticism": 0.65,
                        "attachment_style": "fearful_avoidant", "defense_style": ["幻想", "被动攻击"],
                        "cognitive_biases": ["灾难化", "过度概括"], "moral_stage": 3},
        "trauma": {"ace_score": 3, "active_schemas": ["被抛弃", "不值得被爱"], "trauma_triggers": ["离别", "拒绝"]},
        "ideal_world": {"ideal_self": "用诗歌记录世间所有的美与痛"},
        "motivation": {"current_goal": "寻找一位故人完成未尽的约定"},
    },
    # ── 商业/管理类 ──
    {
        "name": "赵天龙",
        "profession": "商人",
        "group": "business",
        "personality": {"openness": 0.65, "conscientiousness": 0.70, "extraversion": 0.70,
                        "agreeableness": 0.30, "neuroticism": 0.45,
                        "attachment_style": "avoidant", "defense_style": ["理智化", "投射"],
                        "cognitive_biases": ["过度自信", "自利归因"], "moral_stage": 2},
        "trauma": {"ace_score": 2, "active_schemas": ["被背叛"], "trauma_triggers": ["合作伙伴失信"]},
        "ideal_world": {"ideal_self": "建立自己的商业帝国"},
        "motivation": {"current_goal": "完成一桩跨国并购谈判"},
    },
    {
        "name": "沈万三",
        "profession": "企业高管",
        "group": "business",
        "personality": {"openness": 0.60, "conscientiousness": 0.85, "extraversion": 0.70,
                        "agreeableness": 0.30, "neuroticism": 0.55,
                        "attachment_style": "avoidant", "defense_style": ["理智化", "躯体化"],
                        "cognitive_biases": ["证实偏差", "控制错觉"], "moral_stage": 3},
        "trauma": {"ace_score": 1, "active_schemas": [], "trauma_triggers": ["市场崩盘"]},
        "ideal_world": {"ideal_self": "带领公司成为行业第一"},
        "motivation": {"current_goal": "应对突发的股价暴跌"},
    },
    {
        "name": "王浩然",
        "profession": "律师",
        "group": "business",
        "personality": {"openness": 0.55, "conscientiousness": 0.70, "extraversion": 0.65,
                        "agreeableness": 0.35, "neuroticism": 0.50,
                        "attachment_style": "secure", "defense_style": ["理智化", "合理化"],
                        "cognitive_biases": ["证实偏差"], "moral_stage": 4},
        "trauma": {"ace_score": 0, "active_schemas": [], "trauma_triggers": []},
        "ideal_world": {"ideal_self": "维护法律的公正"},
        "motivation": {"current_goal": "准备一起重大诉讼的辩护材料"},
    },
    # ── 服务/劳动类 ──
    {
        "name": "唐一勺",
        "profession": "厨师",
        "group": "service",
        "personality": {"openness": 0.65, "conscientiousness": 0.75, "extraversion": 0.50,
                        "agreeableness": 0.50, "neuroticism": 0.50,
                        "attachment_style": "secure", "defense_style": ["升华", "幽默"],
                        "cognitive_biases": ["完美主义"], "moral_stage": 3},
        "trauma": {"ace_score": 0, "active_schemas": [], "trauma_triggers": []},
        "ideal_world": {"ideal_self": "开一家让所有人吃得起的米其林餐厅"},
        "motivation": {"current_goal": "研发一道创新融合菜"},
    },
    {
        "name": "孙大山",
        "profession": "农民",
        "group": "service",
        "personality": {"openness": 0.30, "conscientiousness": 0.70, "extraversion": 0.40,
                        "agreeableness": 0.65, "neuroticism": 0.40,
                        "attachment_style": "secure", "defense_style": ["压抑", "利他"],
                        "cognitive_biases": ["现状偏见"], "moral_stage": 3},
        "trauma": {"ace_score": 1, "active_schemas": [], "trauma_triggers": ["旱灾"]},
        "ideal_world": {"ideal_self": "让全村人吃饱穿暖"},
        "motivation": {"current_goal": "应对一场突如其来的冰雹灾害"},
    },
    {
        "name": "程维",
        "profession": "程序员",
        "group": "service",
        "personality": {"openness": 0.50, "conscientiousness": 0.70, "extraversion": 0.25,
                        "agreeableness": 0.50, "neuroticism": 0.60,
                        "attachment_style": "avoidant", "defense_style": ["理智化", "隔离"],
                        "cognitive_biases": ["非黑即白"], "moral_stage": 3},
        "trauma": {"ace_score": 0, "active_schemas": [], "trauma_triggers": []},
        "ideal_world": {"ideal_self": "写出改变世界的代码"},
        "motivation": {"current_goal": "修复一个影响线上服务的严重Bug"},
    },
    # ── 特殊身份类 ──
    {
        "name": "嬴昊",
        "profession": "古代帝王",
        "group": "special",
        "personality": {"openness": 0.55, "conscientiousness": 0.80, "extraversion": 0.70,
                        "agreeableness": 0.20, "neuroticism": 0.45,
                        "attachment_style": "avoidant", "defense_style": ["投射", "全能控制"],
                        "cognitive_biases": ["权威偏差", "控制错觉"], "moral_stage": 3},
        "trauma": {"ace_score": 4, "active_schemas": ["被背叛", "权力焦虑"], "trauma_triggers": ["宫变", "密谋"]},
        "ideal_world": {"ideal_self": "千秋万代一统天下"},
        "motivation": {"current_goal": "挫败一起朝中大臣的结党营私"},
    },
    {
        "name": "萧风",
        "profession": "侠客",
        "group": "special",
        "personality": {"openness": 0.60, "conscientiousness": 0.60, "extraversion": 0.55,
                        "agreeableness": 0.65, "neuroticism": 0.30,
                        "attachment_style": "secure", "defense_style": ["利他", "升华"],
                        "cognitive_biases": [], "moral_stage": 5},
        "trauma": {"ace_score": 3, "active_schemas": ["复仇"], "trauma_triggers": ["仇人消息"]},
        "ideal_world": {"ideal_self": "仗剑走天涯, 路见不平一声吼"},
        "motivation": {"current_goal": "保护一个被追杀的无辜平民"},
    },
    {
        "name": "慧明",
        "profession": "僧人",
        "group": "special",
        "personality": {"openness": 0.50, "conscientiousness": 0.65, "extraversion": 0.30,
                        "agreeableness": 0.75, "neuroticism": 0.25,
                        "attachment_style": "secure", "defense_style": ["升华", "利他"],
                        "cognitive_biases": [], "moral_stage": 5},
        "trauma": {"ace_score": 0, "active_schemas": [], "trauma_triggers": []},
        "ideal_world": {"ideal_self": "普度众生, 看破红尘"},
        "motivation": {"current_goal": "为前来求助的村民开解心中苦恼"},
    },
    {
        "name": "杰克·斯派罗",
        "profession": "海盗",
        "group": "special",
        "personality": {"openness": 0.65, "conscientiousness": 0.25, "extraversion": 0.75,
                        "agreeableness": 0.35, "neuroticism": 0.50,
                        "attachment_style": "avoidant", "defense_style": ["幽默", "幻想", "行动化"],
                        "cognitive_biases": ["过度自信", "乐观偏差"], "moral_stage": 2},
        "trauma": {"ace_score": 2, "active_schemas": [], "trauma_triggers": ["被出卖"]},
        "ideal_world": {"ideal_self": "自由自在地航行在七大洋"},
        "motivation": {"current_goal": "寻找传说中失落的宝藏"},
    },
    # ── 竞技/风险类 ──
    {
        "name": "方竞",
        "profession": "运动员",
        "group": "sports",
        "personality": {"openness": 0.40, "conscientiousness": 0.80, "extraversion": 0.70,
                        "agreeableness": 0.55, "neuroticism": 0.45,
                        "attachment_style": "secure", "defense_style": ["升华", "幽默"],
                        "cognitive_biases": ["乐观偏差"], "moral_stage": 3},
        "trauma": {"ace_score": 1, "active_schemas": [], "trauma_triggers": ["旧伤复发"]},
        "ideal_world": {"ideal_self": "站在奥运领奖台最高处"},
        "motivation": {"current_goal": "备战一个月后的全国锦标赛"},
    },
    {
        "name": "龙五",
        "profession": "赌徒",
        "group": "sports",
        "personality": {"openness": 0.50, "conscientiousness": 0.30, "extraversion": 0.65,
                        "agreeableness": 0.35, "neuroticism": 0.70,
                        "attachment_style": "fearful_avoidant", "defense_style": ["幻想", "行动化", "反向形成"],
                        "cognitive_biases": ["赌徒谬误", "过度自信", "沉没成本"], "moral_stage": 2},
        "trauma": {"ace_score": 5, "active_schemas": ["成瘾", "自我毁灭"], "trauma_triggers": ["巨额债务", "追债人"]},
        "ideal_world": {"ideal_self": "赢回一切, 重新开始"},
        "motivation": {"current_goal": "想办法还清今天到期的赌债"},
    },
    {
        "name": "苏瑶",
        "profession": "记者",
        "group": "sports",
        "personality": {"openness": 0.75, "conscientiousness": 0.65, "extraversion": 0.70,
                        "agreeableness": 0.50, "neuroticism": 0.55,
                        "attachment_style": "secure", "defense_style": ["幽默", "升华"],
                        "cognitive_biases": ["证实偏差"], "moral_stage": 4},
        "trauma": {"ace_score": 0, "active_schemas": [], "trauma_triggers": ["暴力镇压"]},
        "ideal_world": {"ideal_self": "用笔揭露真相, 让无力者有力"},
        "motivation": {"current_goal": "追查一起官商勾结的腐败案件"},
    },
]


# ── 场景模板 ────────────────────────────────────────────────────
# 每个角色组 (group) 在每个触发条件 (trigger) 下有一个场景描述模板。
# 模板中的 {name} 会在生成时替换为角色名。
# Key: (group, trigger) -> (description, event_type, tags, significance)
SCENARIO_TEMPLATES: dict[tuple[str, str], tuple[str, str, list[str], float]] = {
    # ── education ──
    ("education", "always"): (
        "{name}刚结束一节课/实验，正在整理教案和数据，发现有几个学生的成绩出现异常波动。",
        "routine", ["日常", "工作"], 0.35,
    ),
    ("education", "social"): (
        "系里举办学术交流会，{name}遇到了一个观点截然不同的同行，对方发表了挑衅性的学术意见。",
        "social", ["社交", "学术"], 0.50,
    ),
    ("education", "romantic"): (
        "一个暗恋{name}已久的人送来了一份精心准备的礼物和一封手写信，表达了对{name}的深深仰慕。",
        "social", ["浪漫", "情感"], 0.55,
    ),
    ("education", "conflict"): (
        "{name}发现一位同事在教学评价中故意压低自己班上学生的分数以凸显自己的教学成果。",
        "conflict", ["冲突", "竞争"], 0.70,
    ),
    ("education", "moral"): (
        "一名成绩优异但家境贫寒的学生在考试时作弊被当场抓住。按照校规应记大过，但该学生请求{name}网开一面。",
        "moral_choice", ["道德", "教育", "公正"], 0.80,
    ),
    ("education", "trauma"): (
        "教室窗外传来一阵刺耳的救护车鸣笛声，混杂着学生们的尖叫声。{name}手中的粉笔突然掉在地上。",
        "reflective", ["创伤", "回忆"], 0.75,
    ),
    ("education", "reflective"): (
        "深夜独自在办公室批改作业，{name}翻到了十年前第一批学生寄来的贺卡，一时百感交集。",
        "reflective", ["反思", "回忆"], 0.40,
    ),
    ("education", "authority"): (
        "校长私下要求{name}在优秀教师评选中把名额让给一位领导亲属，作为补偿会给予其他好处。",
        "social", ["权威", "权力", "道德"], 0.85,
    ),
    # ── medical ──
    ("medical", "always"): (
        "完成了一台棘手的手术后，{name}正在电脑前补写医疗记录，护士叫{name}去接下一个急诊。",
        "routine", ["日常", "工作"], 0.40,
    ),
    ("medical", "social"): (
        "医院团建活动中，{name}被安排与一位素不相识的年轻医生一组完成协作任务。",
        "social", ["社交", "职场"], 0.45,
    ),
    ("medical", "romantic"): (
        "一个一直默默关心{name}的人终于鼓起勇气表白，承诺愿意接受{name}不规律的工作时间。",
        "social", ["浪漫", "情感"], 0.55,
    ),
    ("medical", "conflict"): (
        "一位患者家属认为误诊导致病情延误，在科室大声质问{name}，要求立刻转院和赔偿。",
        "conflict", ["冲突", "医患"], 0.80,
    ),
    ("medical", "moral"): (
        "一款进口药物疗效显著但价格昂贵，仿制药便宜但副作用更大。{name}必须为收入微薄的患者做出选择。",
        "moral_choice", ["道德", "医疗", "伦理"], 0.85,
    ),
    ("medical", "trauma"): (
        "急诊送来一个与当年让{name}失眠数月的病例几乎一模一样的病人——同样的年龄、同样的症状、同样的眼神。",
        "reflective", ["创伤", "回忆"], 0.80,
    ),
    ("medical", "reflective"): (
        "凌晨三点在值班室短暂休息，{name}望向窗外漆黑的城市，回想学医时立下的希波克拉底誓言。",
        "reflective", ["反思", "职业"], 0.45,
    ),
    ("medical", "authority"): (
        "科室主任要求{name}修改一份病历记录，将一起轻微医疗事故描述为'不可预见的并发症'。",
        "moral_choice", ["权威", "道德", "医疗"], 0.85,
    ),
    # ── law_enforcement ──
    ("law_enforcement", "always"): (
        "{name}正在写今天的工作报告，对讲机里传来了新的出勤指令。",
        "routine", ["日常", "工作"], 0.35,
    ),
    ("law_enforcement", "social"): (
        "休息日参加战友/同事的婚宴，一个喝醉的客人开始挑衅性地谈论{name}的职业。",
        "social", ["社交", "聚会"], 0.50,
    ),
    ("law_enforcement", "romantic"): (
        "一直暗恋的人约{name}单独见面，说有一件重要的事情要当面告诉{name}。",
        "social", ["浪漫", "情感"], 0.55,
    ),
    ("law_enforcement", "conflict"): (
        "在执行任务时，嫌疑人激烈反抗并试图抢夺{name}的配武器。",
        "conflict", ["冲突", "执法", "危险"], 0.85,
    ),
    ("law_enforcement", "moral"): (
        "{name}发现搭档在执行任务时私自扣留了查获的贵重物品没有上交。",
        "moral_choice", ["道德", "执法", "忠诚"], 0.85,
    ),
    ("law_enforcement", "trauma"): (
        "一声突如其来的巨响让{name}瞬间僵住，手掌不由自主地去摸腰间的装备，心跳急剧加速。",
        "reflective", ["创伤", "PTSD"], 0.80,
    ),
    ("law_enforcement", "reflective"): (
        "深夜独自整理装备，{name}擦拭着配枪，看着镜子里满脸疲惫的自己。",
        "reflective", ["反思", "职业"], 0.45,
    ),
    ("law_enforcement", "authority"): (
        "上级下达了一个{name}认为违反程序正义的抓捕命令，必须在服从命令和坚守原则之间做出抉择。",
        "moral_choice", ["权威", "道德", "执法"], 0.85,
    ),
    # ── artistic ──
    ("artistic", "always"): (
        "{name}在工作室/排练厅独自练习基本功，觉得今天状态不对劲。",
        "routine", ["日常", "创作"], 0.35,
    ),
    ("artistic", "social"): (
        "一场艺术沙龙上，一位颇有影响力的收藏家/导演对{name}的作品表现出了浓厚兴趣。",
        "social", ["社交", "艺术", "机遇"], 0.55,
    ),
    ("artistic", "romantic"): (
        "{name}遇见了一个让{name}觉得可以为之创作一辈子作品的人。那种感觉像闪电击中了心脏。",
        "social", ["浪漫", "情感", "缪斯"], 0.60,
    ),
    ("artistic", "conflict"): (
        "{name}的最新作品被一位权威人士公开批评为'肤浅'和'哗众取宠'，在网络上引起了激烈争议。",
        "conflict", ["冲突", "批评", "艺术"], 0.75,
    ),
    ("artistic", "moral"): (
        "一个报酬极其丰厚的商业项目找到{name}，但要求{name}完全放弃个人风格迎合市场低俗趣味。",
        "moral_choice", ["道德", "艺术", "原则"], 0.80,
    ),
    ("artistic", "trauma"): (
        "{name}看到了一段新闻画面——一个与童年记忆中的场景几乎完全相同的画面，手中的东西掉在了地上。",
        "reflective", ["创伤", "回忆"], 0.75,
    ),
    ("artistic", "reflective"): (
        "散场/闭馆后{name}独自坐在空荡荡的空间中央，看着四壁自己的作品，突然觉得自己一无所有。",
        "reflective", ["反思", "孤独", "创作"], 0.50,
    ),
    ("artistic", "authority"): (
        "投资方/赞助人要求{name}修改作品的关键表达以符合他们的政治立场，否则撤资。",
        "moral_choice", ["权威", "艺术", "原则"], 0.85,
    ),
    # ── business ──
    ("business", "always"): (
        "{name}正在审查一份重要合同/报表的细节，发现了一个可能被对方利用的漏洞。",
        "routine", ["日常", "工作"], 0.40,
    ),
    ("business", "social"): (
        "行业高端酒会上，{name}被引荐给一位关键的潜在合作伙伴，对方提出了一个诱人的合作意向。",
        "social", ["社交", "商机"], 0.55,
    ),
    ("business", "romantic"): (
        "{name}发现那位在商业上一直与自己竞争的人，在个人层面其实对{name}有着特别的好感。",
        "social", ["浪漫", "情感", "复杂"], 0.55,
    ),
    ("business", "conflict"): (
        "谈判桌上，对方突然祭出了{name}完全没预料到的新条款，试图逼迫{name}在不利条件下签约。",
        "conflict", ["冲突", "商业", "谈判"], 0.75,
    ),
    ("business", "moral"): (
        "{name}发现公司新产品有一个不致命但会影响声誉的安全隐患。公开承认将损失数千万订单。",
        "moral_choice", ["道德", "商业", "诚信"], 0.85,
    ),
    ("business", "trauma"): (
        "审计部门突然进场检查，那个面孔让{name}瞬间想起当年公司濒临倒闭时的审计风暴。",
        "reflective", ["创伤", "回忆"], 0.75,
    ),
    ("business", "reflective"): (
        "深夜独自在顶楼办公室看着城市的万家灯火，{name}问自己: 这一切到底是为了什么。",
        "reflective", ["反思", "孤独", "意义"], 0.50,
    ),
    ("business", "authority"): (
        "监管机构负责人暗示{name}只要支付一笔'咨询费'就能加快审批流程，否则将无限期拖延。",
        "moral_choice", ["权威", "道德", "腐败"], 0.85,
    ),
    # ── service ──
    ("service", "always"): (
        "{name}按部就班地处理今天最日常的一项工序/流程，突然发现了一个异常情况。",
        "routine", ["日常", "工作"], 0.35,
    ),
    ("service", "social"): (
        "街坊邻里/同事们聚在一起吃饭聊天，话题转到了{name}身上。",
        "social", ["社交", "日常"], 0.40,
    ),
    ("service", "romantic"): (
        "{name}默默喜欢的人今天破天荒地主动来帮忙，还在工作结束时递给了{name}一瓶水。",
        "social", ["浪漫", "情感"], 0.50,
    ),
    ("service", "conflict"): (
        "{name}发现有人明目张胆地剽窃了自己的创意/劳动成果还洋洋得意。",
        "conflict", ["冲突", "不公"], 0.70,
    ),
    ("service", "moral"): (
        "老板要求{name}使用廉价劣质材料代替正品以节省成本，称'反正用不坏，没人会发现'。",
        "moral_choice", ["道德", "诚信", "职业"], 0.80,
    ),
    ("service", "trauma"): (
        "车间/工坊里的一声巨响让{name}手中的东西掉落在地，身体不由自主地颤抖起来。",
        "reflective", ["创伤", "回忆"], 0.70,
    ),
    ("service", "reflective"): (
        "收工后{name}坐在门前/窗前，看着来来往往的人群，想着自己这辈子就这样了吗。",
        "reflective", ["反思", "生活", "意义"], 0.45,
    ),
    ("service", "authority"): (
        "老板要求{name}无偿加班完成一个几乎不可能完成的任务，理由是'能者多劳'。",
        "social", ["权威", "不公", "劳动"], 0.70,
    ),
    # ── special ──
    ("special", "always"): (
        "{name}正在巡视自己的领地/海域，盘查各项事务和人员。一切看似平静但暗流涌动。",
        "routine", ["日常", "巡视"], 0.40,
    ),
    ("special", "social"): (
        "{name}设宴款待远道而来的使者/盟友，对方言语中暗示了一个危险的秘密。",
        "social", ["社交", "外交", "暗流"], 0.55,
    ),
    ("special", "romantic"): (
        "在旅途中{name}救了一个人的命。那个人醒来后注视着{name}的眼神让{name}心跳漏了一拍。",
        "social", ["浪漫", "情感", "邂逅"], 0.60,
    ),
    ("special", "conflict"): (
        "{name}的权威在公开场合受到了无情的挑战。所有人都看着{name}，等待{name}的反应。",
        "conflict", ["冲突", "权力", "尊严"], 0.80,
    ),
    ("special", "moral"): (
        "{name}抓住了一个偷偷摸摸的人——一个饿得瘦骨嶙峋的孩子，怀里抱着偷来的食物。",
        "moral_choice", ["道德", "同情", "公正"], 0.85,
    ),
    ("special", "trauma"): (
        "远处传来的喊杀声和火光让{name}瞬间回到了那场改变一切的惨烈战斗。手中的剑/酒杯在颤抖。",
        "reflective", ["创伤", "回忆", "战斗"], 0.80,
    ),
    ("special", "reflective"): (
        "夜深人静时{name}独自登高/站在船头凝视星空，身后是沉睡的领地/大海。",
        "reflective", ["反思", "孤独", "星空"], 0.45,
    ),
    ("special", "authority"): (
        "一位德高望重的长者/前辈要求{name}放弃复仇/追寻，称这是为了{name}好。",
        "moral_choice", ["权威", "道德", "复仇"], 0.80,
    ),
    # ── sports ──
    ("sports", "always"): (
        "{name}正在做常规训练/准备工作，发现自己的状态不如预期，进度落后了。",
        "routine", ["日常", "训练"], 0.40,
    ),
    ("sports", "social"): (
        "在休息区/发布会/赛场上{name}遇到了曾经的老对手，对方今天格外热情地打招呼。",
        "social", ["社交", "竞技"], 0.50,
    ),
    ("sports", "romantic"): (
        "{name}在经常光顾的地方遇到了一个特别的人。对方微笑着说: '我一直是你的粉丝。'",
        "social", ["浪漫", "情感"], 0.55,
    ),
    ("sports", "conflict"): (
        "{name}发现有人在背后搞小动作——破坏{name}的训练器材/抹黑{name}的名声。",
        "conflict", ["冲突", "不公", "竞技"], 0.75,
    ),
    ("sports", "moral"): (
        "有人承诺给{name}一大笔钱，让{name}在比赛中放水/制造假新闻。只要输掉一场比赛/扭曲一个事实。",
        "moral_choice", ["道德", "诚信", "竞技"], 0.85,
    ),
    ("sports", "trauma"): (
        "一次意外的冲撞/声响让{name}的旧伤处传来剧痛，记忆瞬间被拉回职业生涯中最黑暗的时刻。",
        "reflective", ["创伤", "回忆", "伤病"], 0.80,
    ),
    ("sports", "reflective"): (
        "夜深人静时{name}抚摸着身上的旧伤和奖牌, 问自己: 这一切的代价值得吗。",
        "reflective", ["反思", "意义", "牺牲"], 0.50,
    ),
    ("sports", "authority"): (
        "协会领导/主编要求{name}放弃一个高风险但意义重大的目标，转而选择一条安全平庸的道路。",
        "social", ["权威", "选择", "理想"], 0.75,
    ),
}

# ── 人格 → 预期断言映射 ────────────────────────────────────────
# 根据人格特质值决定 expected 断言。
# 阈值: >=0.65 为"高", <=0.35 为"低"。
# 每个条目是 (check_path, condition, value) 的三元组结构。
# 这里使用函数式构建，适配现有的断言 DSL。

TRAIT_EXPECTATIONS: list[tuple[str, str, dict]] = [
    # 开放性高
    ("openness", "high", {"big_five_analysis": {"cognitive_style": {"contains_any": ["创造", "好奇", "探索", "open", "想象"]}}}),
    # 开放性低
    ("openness", "low", {"big_five_analysis": {"cognitive_style": {"contains_any": ["传统", "务实", "保守", "conventional"]}}}),
    # 尽责性高
    ("conscientiousness", "high", {"big_five_analysis": {"decision_style": {"contains_any": ["计划", "严谨", "条理", "deliberate", "规范"]}}}),
    # 尽责性低
    ("conscientiousness", "low", {"big_five_analysis": {"decision_style": {"contains_any": ["随性", "灵活", "即兴", "spontaneous"]}}}),
    # 外向性高
    ("extraversion", "high", {"big_five_analysis": {"social_approach": {"contains_any": ["社交", "主动", "外向", "approach", "热情"]}}}),
    # 外向性低
    ("extraversion", "low", {"big_five_analysis": {"social_approach": {"contains_any": ["回避", "安静", "内向", "withdraw", "独处"]}}}),
    # 宜人性高
    ("agreeableness", "high", {"big_five_analysis": {"conflict_style": {"contains_any": ["妥协", "合作", "体谅", "cooperative", "包容"]}}}),
    # 宜人性低
    ("agreeableness", "low", {"big_five_analysis": {"conflict_style": {"contains_any": ["对抗", "竞争", "质疑", "confrontational", "强硬"]}}}),
    # 神经质高 -> 情绪反应强
    ("neuroticism", "high", {
        "big_five_analysis": {"emotional_reactivity": {"min": 0.55}},
        "plutchik_emotion": {"internal.intensity": {"min": 0.5}},
    }),
    # 神经质低 -> 情绪反应弱
    ("neuroticism", "low", {
        "big_five_analysis": {"emotional_reactivity": {"max": 0.5}},
    }),
]

ATTACHMENT_EXPECTATIONS: dict[str, dict] = {
    "secure": {
        "attachment_style_analysis": {"activation_level": {"max": 0.6}},
    },
    "anxious": {
        "attachment_style_analysis": {"activation_level": {"min": 0.5}},
        "cognitive_bias_detect": {"activated_biases": {"contains_any": ["灾难化", "读心术", "焦虑"]}},
    },
    "avoidant": {
        "attachment_style_analysis": {"activation_level": {"max": 0.5}},
        "defense_mechanism_analysis": {"activated_defense.name": {"in": ["情感隔离", "理智化", "退缩"]}},
    },
    "fearful_avoidant": {
        "attachment_style_analysis": {"activation_level": {"min": 0.6}},
        "ptsd_trigger_check": {"hyperarousal_risk": {"min": 0.5}},
    },
}


def _trait_level(value: float) -> str:
    if value >= 0.65:
        return "high"
    if value <= 0.35:
        return "low"
    return "mid"


def build_expected(char: dict) -> dict:
    """根据角色人格档案构建 expected 断言字典。"""
    expected: dict = {
        "big_five_analysis": {},
        "plutchik_emotion": {"internal.dominant": {"not_empty": True}},
        "response_generator": {"response_text": {"not_empty": True, "min": 10}},
    }

    pers = char.get("personality", {})

    # 大五维度断言
    for trait_name, level_label, assertion in TRAIT_EXPECTATIONS:
        value = pers.get(trait_name, 0.5)
        if _trait_level(value) == level_label:
            _deep_merge(expected, assertion)

    # 依恋风格断言
    attach = pers.get("attachment_style", "secure")
    if attach in ATTACHMENT_EXPECTATIONS:
        _deep_merge(expected, ATTACHMENT_EXPECTATIONS[attach])

    # 如果神经质不高不低，至少确保 emotional_reactivity 不为空
    ba = expected.get("big_five_analysis", {})
    if "emotional_reactivity" not in ba:
        ba["emotional_reactivity"] = {"not_empty": True}

    return expected


def _deep_merge(base: dict, overlay: dict) -> None:
    """原地深度合并 overlay 到 base。"""
    for key, val in overlay.items():
        if key in base and isinstance(base[key], dict) and isinstance(val, dict):
            _deep_merge(base[key], val)
        else:
            base[key] = val


# ── 本地数据加载尝试 ────────────────────────────────────────────

def load_local_characterbench() -> list[dict] | None:
    """尝试从本地路径加载 CharacterBench 原始数据。

    CharacterBench 官方数据集格式推测: character_profiles.json + conversations.jsonl
    返回 None 表示不可用。
    """
    if not DATASET_DIR.exists():
        return None

    profiles_path = DATASET_DIR / "character_profiles.json"
    conv_path = DATASET_DIR / "conversations.jsonl"

    if not profiles_path.exists() or not conv_path.exists():
        return None

    try:
        with open(profiles_path, "r", encoding="utf-8") as f:
            profiles = json.load(f)
        with open(conv_path, "r", encoding="utf-8") as f:
            raw = f.read().strip()
            if raw.startswith("["):
                conversations = json.loads(raw)
            else:
                conversations = []
                for line in raw.split("\n"):
                    line = line.strip()
                    if line:
                        try:
                            conversations.append(json.loads(line))
                        except json.JSONDecodeError:
                            pass
    except (json.JSONDecodeError, IOError):
        return None

    # 将本地数据转换为统一格式
    cases = []
    # 已处理的角色名集合, 保持去重
    seen_chars = set()

    for conv in conversations:
        char_name = conv.get("character", conv.get("role", ""))
        if not char_name or char_name in seen_chars:
            continue
        seen_chars.add(char_name)

        profile = profiles.get(char_name, {}) if isinstance(profiles, dict) else {}
        big5 = profile.get("big_five", profile.get("personality", {}))
        mbti = profile.get("mbti", "")

        cases.append({
            "id": f"cb_local_{len(cases):04d}",
            "source": f"CharacterBench (local) - {char_name}",
            "domain": "character_consistency",
            "character_state": {
                "name": char_name,
                "personality": {
                    "openness": big5.get("openness", big5.get("O", 0.5)),
                    "conscientiousness": big5.get("conscientiousness", big5.get("C", 0.5)),
                    "extraversion": big5.get("extraversion", big5.get("E", 0.5)),
                    "agreeableness": big5.get("agreeableness", big5.get("A", 0.5)),
                    "neuroticism": big5.get("neuroticism", big5.get("N", 0.5)),
                    "attachment_style": profile.get("attachment_style", "secure"),
                    "defense_style": profile.get("defense_style", []),
                    "cognitive_biases": profile.get("cognitive_biases", []),
                    "moral_stage": profile.get("moral_stage", 3),
                },
                "trauma": profile.get("trauma", {"ace_score": 0, "active_schemas": [], "trauma_triggers": []}),
                "ideal_world": profile.get("ideal_world", {}),
                "motivation": profile.get("motivation", {"current_goal": ""}),
                "emotion_decay": {},
            },
            "event": {
                "description": conv.get("context", conv.get("dialogue", conv.get("instruction", ""))),
                "type": conv.get("type", "social"),
                "participants": conv.get("participants", []),
                "significance": conv.get("significance", 0.5),
                "tags": conv.get("tags", ["character_bench", "local"]),
            },
            "expected": {
                "big_five_analysis": {"emotional_reactivity": {"not_empty": True}},
                "plutchik_emotion": {"internal.dominant": {"not_empty": True}},
                "response_generator": {"response_text": {"not_empty": True, "min": 10}},
            },
        })

        if len(cases) >= 500:
            break

    return cases if cases else None


# ── 内置用例生成 ────────────────────────────────────────────────

def _gen_event(char: dict, trigger: str) -> dict:
    """为角色在给定触发条件下生成事件。"""
    group = char.get("group", "education")
    key = (group, trigger)
    if key not in SCENARIO_TEMPLATES:
        # 降级: 使用 education 组模板
        key = ("education", trigger)

    description, event_type, extra_tags, significance = SCENARIO_TEMPLATES[key]
    description = description.replace("{name}", char["name"])

    return {
        "description": description,
        "type": event_type,
        "participants": [],
        "significance": significance,
        "tags": extra_tags + [trigger],
    }


def generate_builtin_cases() -> list[dict]:
    """生成 ~200 条内置 CharacterBench 用例 (25 角色 × 8 触发条件)。"""
    cases: list[dict] = []
    seq = 0

    for char in CHARACTER_PROFILES:
        for trigger in TRIGGERS:
            event = _gen_event(char, trigger)
            expected = build_expected(char)

            case = {
                "id": f"cb_{seq:04d}",
                "source": f"CharacterBench (built-in) - {char['name']}({char['profession']}) × {trigger}",
                "domain": "character_consistency",
                "character_state": {
                    "name": char["name"],
                    "personality": dict(char["personality"]),
                    "trauma": dict(char["trauma"]),
                    "ideal_world": dict(char["ideal_world"]),
                    "motivation": dict(char["motivation"]),
                    "emotion_decay": {},
                },
                "event": event,
                "expected": expected,
            }
            cases.append(case)
            seq += 1

    return cases


# ── 主流程 ──────────────────────────────────────────────────────

def extract_cases(sample: int | None = None) -> list[dict]:
    """提取用例: 优先从本地数据, 不可用时生成内置用例。

    Args:
        sample: 若指定, 随机采样 N 条用例。
    """
    cases = load_local_characterbench()
    if cases is not None:
        print(f"Loaded {len(cases)} cases from local CharacterBench data")
    else:
        print("Local CharacterBench data not found, generating built-in cases...")
        cases = generate_builtin_cases()
        print(f"Generated {len(cases)} built-in CharacterBench cases")

    if sample is not None and sample < len(cases):
        cases = random.sample(cases, sample)
        print(f"Sampled {sample} cases (--sample={sample})")

    return cases


def print_stats(cases: list[dict]) -> None:
    """打印用例统计信息。"""
    if not cases:
        print("No cases to report.")
        return

    print(f"\nTotal cases: {len(cases)}")

    # 角色数量
    char_names = set(c["character_state"]["name"] for c in cases)
    print(f"Unique characters: {len(char_names)}")

    # 触发条件分布
    trigger_counts: dict[str, int] = {}
    for c in cases:
        for tag in c["event"]["tags"]:
            if tag in TRIGGERS:
                trigger_counts[tag] = trigger_counts.get(tag, 0) + 1
    if trigger_counts:
        print(f"Trigger distribution ({sum(trigger_counts.values())} total):")
        for t in TRIGGERS:
            n = trigger_counts.get(t, 0)
            bar = "#" * int(n / max(sum(trigger_counts.values()), 1) * 50)
            print(f"  {t:12s}: {n:4d} {bar}")

    # 职业分布
    prof_counts: dict[str, int] = {}
    for c in cases:
        name = c["character_state"]["name"]
        # 从 source 提取职业
        for char in CHARACTER_PROFILES:
            if char["name"] == name:
                p = char.get("profession", "未知")
                prof_counts[p] = prof_counts.get(p, 0) + 1
                break
    if prof_counts:
        print(f"Profession distribution ({len(prof_counts)} types):")
        for p, n in sorted(prof_counts.items(), key=lambda x: -x[1])[:10]:
            print(f"  {p}: {n}")

    # 事件类型分布
    type_counts: dict[str, int] = {}
    for c in cases:
        et = c["event"]["type"]
        type_counts[et] = type_counts.get(et, 0) + 1
    print(f"Event types: {dict(type_counts)}")


def main():
    parser = argparse.ArgumentParser(
        description="从 CharacterBench 数据集提取/生成角色一致性验证用例"
    )
    parser.add_argument(
        "--sample", type=int, default=None,
        help="随机采样 N 条用例 (默认全部)"
    )
    parser.add_argument(
        "--stats", action="store_true",
        help="仅打印统计信息, 不写入文件"
    )
    args = parser.parse_args()

    cases = extract_cases(sample=args.sample)

    if args.stats:
        print_stats(cases)
        return

    # 确保输出目录存在
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    out_path = OUTPUT_DIR / "character_bench_cases.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(cases, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(cases)} cases to {out_path}")

    print_stats(cases)


if __name__ == "__main__":
    main()
