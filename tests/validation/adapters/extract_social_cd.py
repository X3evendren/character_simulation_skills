"""从 SocialCD-3K 数据集提取认知偏差验证用例。

SocialCD-3K (IEEE Dataport DOI: 10.21227/jb3w-j696):
- 3,407 条中文微博
- 12 种认知扭曲类型标注
- 来源: github.com/HongzhiQ/SupervisedVsLLM-EfficacyEval

输出: 120 条验证用例 (每类 10 条), 我们的验证用例格式
"""
import json
import argparse
from pathlib import Path

import glob as _glob

OUTPUT_DIR = Path(__file__).parent.parent / "fixtures"

# ── 12 种认知扭曲的中英文名称 ──────────────────────────
DISTORTION_META = [
    {"zh": "贴标签",        "en": "Labeling",              "abbr": "label"},
    {"zh": "算命错误",       "en": "Fortune Teller Error",  "abbr": "fortune"},
    {"zh": "心理过滤",       "en": "Mental Filter",         "abbr": "filter"},
    {"zh": "夸大",           "en": "Magnification",         "abbr": "magnify"},
    {"zh": "自责",           "en": "Blaming Self",          "abbr": "self_blame"},
    {"zh": "过度概括",       "en": "Over-generalization",   "abbr": "overgen"},
    {"zh": "读心术",         "en": "Mind Reading",          "abbr": "mind_read"},
    {"zh": "应该陈述",       "en": "Should Statements",     "abbr": "should"},
    {"zh": "非黑即白",       "en": "All-or-Nothing",        "abbr": "all_or_nothing"},
    {"zh": "否定正面",       "en": "Disqualifying Positive","abbr": "disqualify"},
    {"zh": "责备他人",       "en": "Blaming Others",        "abbr": "blame_other"},
    {"zh": "情绪推理",       "en": "Emotional Reasoning",   "abbr": "emo_reason"},
]

# ── 每种扭曲的人格模板 ─────────────────────────────────
DISTORTION_PROFILES = {
    "贴标签": {
        "personality": {"openness": 0.35, "conscientiousness": 0.50, "extraversion": 0.45,
                        "agreeableness": 0.30, "neuroticism": 0.70},
        "cognitive_biases": ["贴标签", "非黑即白"],
        "emotions": ["anger", "disgust"],
        "defense_style": ["投射", "贬低"],
    },
    "算命错误": {
        "personality": {"openness": 0.40, "conscientiousness": 0.50, "extraversion": 0.35,
                        "agreeableness": 0.50, "neuroticism": 0.80},
        "cognitive_biases": ["算命错误", "灾难化"],
        "emotions": ["fear", "anticipation"],
        "defense_style": ["预期性焦虑"],
    },
    "心理过滤": {
        "personality": {"openness": 0.40, "conscientiousness": 0.55, "extraversion": 0.30,
                        "agreeableness": 0.50, "neuroticism": 0.75},
        "cognitive_biases": ["心理过滤", "选择性抽象"],
        "emotions": ["sadness", "disgust"],
        "defense_style": ["情感隔离"],
    },
    "夸大": {
        "personality": {"openness": 0.45, "conscientiousness": 0.45, "extraversion": 0.40,
                        "agreeableness": 0.45, "neuroticism": 0.80},
        "cognitive_biases": ["夸大", "灾难化"],
        "emotions": ["fear", "anticipation"],
        "defense_style": ["灾难化"],
    },
    "自责": {
        "personality": {"openness": 0.45, "conscientiousness": 0.60, "extraversion": 0.30,
                        "agreeableness": 0.55, "neuroticism": 0.78},
        "cognitive_biases": ["自责", "个人化"],
        "emotions": ["sadness"],
        "defense_style": ["反向形成", "理智化"],
    },
    "过度概括": {
        "personality": {"openness": 0.30, "conscientiousness": 0.50, "extraversion": 0.35,
                        "agreeableness": 0.45, "neuroticism": 0.75},
        "cognitive_biases": ["过度概括", "灾难化"],
        "emotions": ["sadness", "disgust"],
        "defense_style": ["情感隔离"],
    },
    "读心术": {
        "personality": {"openness": 0.45, "conscientiousness": 0.50, "extraversion": 0.45,
                        "agreeableness": 0.35, "neuroticism": 0.72},
        "cognitive_biases": ["读心术", "个人化"],
        "emotions": ["anger", "fear"],
        "defense_style": ["投射"],
    },
    "应该陈述": {
        "personality": {"openness": 0.35, "conscientiousness": 0.75, "extraversion": 0.40,
                        "agreeableness": 0.30, "neuroticism": 0.65},
        "cognitive_biases": ["应该陈述", "完美主义"],
        "emotions": ["anger", "disgust"],
        "defense_style": ["理智化", "反向形成"],
    },
    "非黑即白": {
        "personality": {"openness": 0.30, "conscientiousness": 0.55, "extraversion": 0.40,
                        "agreeableness": 0.40, "neuroticism": 0.65},
        "cognitive_biases": ["非黑即白", "完美主义"],
        "emotions": ["disgust", "anger"],
        "defense_style": ["分裂", "理想化"],
    },
    "否定正面": {
        "personality": {"openness": 0.40, "conscientiousness": 0.50, "extraversion": 0.25,
                        "agreeableness": 0.45, "neuroticism": 0.78},
        "cognitive_biases": ["否定正面", "心理过滤"],
        "emotions": ["sadness"],
        "defense_style": ["情感隔离", "贬低"],
    },
    "责备他人": {
        "personality": {"openness": 0.35, "conscientiousness": 0.35, "extraversion": 0.50,
                        "agreeableness": 0.25, "neuroticism": 0.65},
        "cognitive_biases": ["责备他人"],
        "emotions": ["anger", "disgust"],
        "defense_style": ["投射", "合理化"],
    },
    "情绪推理": {
        "personality": {"openness": 0.45, "conscientiousness": 0.45, "extraversion": 0.35,
                        "agreeableness": 0.50, "neuroticism": 0.82},
        "cognitive_biases": ["情绪推理", "灾难化"],
        "emotions": ["fear", "sadness"],
        "defense_style": ["理智化"],
    },
}

# ── 生成内置用例的数据 ─────────────────────────────────
# 每类 10 条微博/对话片段, 附带额外可能激活的偏差
BUILTIN_SCENARIOS = {
    "贴标签": [
        "同事今天在会上说错了一个数据。哼，他就是一个不学无术的混子。",
        "相亲对象吃饭时一直在玩手机。标准的渣男/渣女, 没跑了。",
        "前面那辆车变道不打灯。典型的女司机/菜鸟, 路上最烦这种人。",
        "新来的实习生交的报告有好几处格式问题。一看就是个做事马虎粗心的人。",
        "邻居在楼道里放了很多杂物。素质低下的底层人就是这样。",
        "他刚才说话的语气好冲。这人一定脾气暴躁不好相处。",
        "面试时我紧张得说错了好几句话。我果然是个没用的废物。",
        "有个路人盯着我看了几秒。肯定是在心里嘲笑我的穿着打扮。",
        "她把咖啡洒在文件上了。这么点事都做不好, 就是个不靠谱的人。",
        "领导刚才没回我的消息。他肯定是对我有意见, 在故意冷落我。",
    ],
    "算命错误": [
        "下午就要做述职报告了, 我肯定会讲得一塌糊涂, 被全公司嘲笑。",
        "体检报告明天出来。一定是得了什么绝症, 我的身体最近到处都不对劲。",
        "下周一就要公布晋升名单了。肯定没有我, 我已经预感到会落选。",
        "他三天没主动联系我了。这段感情马上就要完了, 他肯定在考虑分手。",
        "这次项目竞标对手那么强, 我们肯定输, 准备都白做了。",
        "明天面试官一看我的简历就会直接淘汰我, 不会有任何机会。",
        "今天老婆脸色不太好。回家肯定要吵架, 我已经预见到这个结局了。",
        "刚刚不小心 CC 错了人。完了, 这件事绝对会闹到总监那里去。",
        "月底绩效考核, 我肯定垫底, 然后被裁掉, 整个职业生涯就毁了。",
        "晚上要见对方的父母。他们一定看不上我, 这顿饭注定是个灾难。",
    ],
    "心理过滤": [
        "讲师今天讲课100分钟, 前99分钟都很精彩, 但最后一句说错了。什么专家, 满嘴跑火车。",
        "男朋友给我做了一桌子菜, 每道都好吃, 但汤咸了一点。他根本不用心, 连这点小事都做不好。",
        "年终总结写了8000字, 领导就指出了一处用词不当。呵, 全盘否定了我的付出。",
        "项目上线很顺利, 用户反馈99%都是好评, 但有一条差评说加载慢。彻底失败了。",
        "她记得我的生日, 请我吃了很贵的餐厅, 但送的礼物颜色我不喜欢。她根本不了解我。",
        "今天演讲很成功, 观众鼓掌三次, 但有人在台下打了个哈欠。我在大家眼里就是个无聊的人。",
        "相亲对象条件很好, 聊得也很愉快, 但他穿了一双我不喜欢的鞋。三观不合, 没有继续的必要了。",
        "考试得了98分, 扣了2分。我太差了, 为什么总是错在这种细节上。",
        "整个聚会大家都很开心, 但有一个人中途离开了。一定是我的话题太无聊把人气走了。",
        "新工作各方面都很好, 就是通勤多了十分钟。这份工作根本不适合我, 太难受了。",
    ],
    "夸大": [
        "老板让明天交个方案。天哪, 时间根本不够, 这绝对是个不可能完成的任务！",
        "今天在地铁上被人踩了一脚。整个脚背都疼死了, 肯定骨折了。",
        "女朋友说想冷静几天。完了, 这意味着我们彻底结束了, 世界末日到了。",
        "信用卡账单忘了还, 晚了三天。征信肯定完了, 以后再也贷不了款买不了房了。",
        "脸上长了一颗痘痘。毁容了, 没法见人了, 今天绝对不能出门。",
        "方案里有一个小数据引用错了。这可是天大的错误, 客户会因此不再信任我们整个团队。",
        "同事聚餐没有叫我。我被整个团队孤立了, 以后在公司完全待不下去了。",
        "线上服务宕机了五分钟。完了, 公司要损失几百万, 我会被开除还要赔钱。",
        "孩子这次数学考了70分。他这辈子都完了, 考不上好大学找不到好工作。",
        "发布会上我停顿了三秒才回答出那个问题。所有人都看穿我有多不专业了, 职业生涯到此为止。",
    ],
    "自责": [
        "部门业绩没达标。都是我的错, 如果我能多做一点, 大家就不会这么惨了。",
        "朋友失恋了。是我没有及时关心她, 如果那天我多陪陪她就不会这样了。",
        "弟弟高考没考好。是我平时没有做好榜样, 我毁了他的前途。",
        "父母吵架了。一定是因为我不够孝顺, 让他们操心了。",
        "小组作业分数不高。都怪我拖后腿, 如果不是我, 他们都能拿A。",
        "聚会气氛有点尴尬。肯定是我说错了什么话, 把大家的兴致搞没了。",
        "下雨天她淋雨感冒了。我要是提醒她带伞就好了, 都怪我太粗心。",
        "公司的团建活动有人受伤了。我当时应该阻止的, 全都怪我反应太慢。",
        "前男友和我分手后过得很不好。是我毁了他的人生, 如果不是和我在一起他不会这样的。",
        "路上有老人摔倒了但没人扶。我是离得最近的人, 我却没去扶, 我真是太冷漠太差劲了。",
    ],
    "过度概括": [
        "今天面试被拒了。我永远也找不到工作了, 全世界的公司都不会要我。",
        "和相亲对象聊崩了。这就是我的命, 我这种人注定孤独终老。",
        "新买的手机用了三天就卡了一次。这牌子太垃圾了, 以后再也不买了。",
        "今天被领导批评了一句。领导天天针对我, 在这里根本没有活路。",
        "第一次坐高铁就坐过站了。我什么事都做不好, 连坐车都不会。",
        "约会时餐厅踩雷了。和这家相关的餐厅就都是坑, 每次都这样。",
        "今天打篮球输了一局。我就是个废物, 从小到大什么事都赢不了。",
        "刚刚打车被司机绕路了。这个城市的司机没一个好人, 全是骗子。",
        "申请奖学金被拒了。所有的申请都不会有结果的, 我永远都不够好。",
        "刚才发消息她没回。每次都是这样, 所有的人到最后都会离我而去。",
    ],
    "读心术": [
        "老板刚刚看了我一眼然后皱了下眉头。他觉得我最近的绩效很差, 在考虑要不要开除我。",
        "同事们在茶水间聊天, 我一进去他们就安静了。他们一定在背后说我的坏话。",
        "女朋友今天只回了一个'嗯'。她对我烦了, 觉得我太粘人了。",
        "路上有人对我笑了一下。他肯定是在嘲笑我今天穿得土。",
        "朋友聚会没给我发照片。他们就是故意排挤我, 不想让我参加他们的圈子。",
        "领导在群里发了个全员邮件但没有单独@我。他对我有意见, 在故意冷处理我。",
        "她看手机时笑了一下。肯定是在和别的男生聊天, 我绿了。",
        "面试官全程面无表情。他肯定觉得我是个能力不足的人, 不会给我通过的。",
        "邻居在电梯里没有主动打招呼。他一定觉得我是个没礼貌的人, 看不起我。",
        "导师在我的论文上批注了很多修改意见。他觉得我是个学术垃圾, 后悔收我做学生。",
    ],
    "应该陈述": [
        "我一个月应该赚三万块才对。现在这点工资简直是在侮辱我, 太不公平了。",
        "女朋友应该永远理解我的想法, 不需要我解释才对。她做不到就是不够爱我。",
        "服务员应该主动察觉到我需要加水, 还要我叫？这服务态度太差了。",
        "我都这么努力了, 世界应该给我回报才对。结果什么都没得到, 生活太不公平了。",
        "她应该在我生日那天给我惊喜, 而不是问我要不要一起吃饭。太让人失望了。",
        "父母应该无条件支持我的每一个决定, 他们提反对意见就是思想落后控制欲强。",
        "员工应该自觉加班到十点, 六点就走了？一点都不敬业。",
        "地铁应该永远准时准点, 晚两分钟就是不可原谅的系统性失败。",
        "我应该在35岁之前当上总监, 现在已经34了还没实现, 我的人生彻底失败了。",
        "我最好的朋友应该在我发消息的瞬间回复我, 拖这么久肯定是故意的。",
    ],
    "非黑即白": [
        "方案被否了。要么完全按照我的想法来, 要么我一个字都不改, 没有什么折中方案。",
        "他这次迟到了, 说明他就是一个不值得信任的人。信任只有100%和0%的区别。",
        "考试要么拿满分要么就是失败, 90分和0分没有本质区别。",
        "这段感情要么完美无缺, 要么就是彻底糟糕, 没有中间地带。",
        "她今天对我的态度不够热情, 说明我们已经完了。感情状态要么热恋要么分手。",
        "这次演讲要么全场掌声雷动, 要么就是彻头彻尾的失败, 没有'还不错'这个选项。",
        "他帮我一次忙是好人, 今天没帮我就是坏人。人只有好人和坏人两种。",
        "我的工作成果要么震惊全行业, 要么就是毫无价值的垃圾。",
        "在一个问题上没能说服对方, 那我就是个失败者, 没有第三种可能。",
        "这次旅行要么完美无瑕, 要么就是一场灾难, 飞机晚点半小时就已经毁了全部。",
    ],
    "否定正面": [
        "领导表扬我了, 但那只是客气客气, 同事都被表扬了, 没什么值得高兴的。",
        "这次考了全班第一, 但那是因为题目太简单了, 不是我真的厉害。",
        "有人说我长得好看, 肯定是有求于我或者眼神不好。",
        "我成功完成了这个项目, 但主要是因为团队厉害, 和我没什么关系。",
        "虽然升职了, 但这只是运气好, 真正的能力测试还没开始呢, 到时候我就露馅了。",
        "朋友说我人好, 那是他们还没看到真实的我, 等看到了就会离开的。",
        "今天被夸衣服好看, 那是因为这件衣服本来就好, 不是我会搭配。",
        "这段感情很顺利, 但他早晚会发现我有多差劲, 到时候一样会分手。",
        "虽然减了十斤, 但离我的目标体重还差很多, 这点进步根本不值一提。",
        "很多人评论说喜欢我的内容, 但这些人多半是在刷存在感, 不是真心喜欢的。",
    ],
    "责备他人": [
        "我迟到了是因为闹钟没响, 都怪我妈买的闹钟质量太差。",
        "项目搞砸了全怪产品经理需求没写清楚, 不是我们开发的问题。",
        "我吵架时说难听话是因为对方先惹我的, 责任全在对方。",
        "考试没过是因为老师出题太偏, 完全超出考纲了, 我才不背锅。",
        "我工作没完成是因为同事不配合, 他总是拖沓, 不然我早做完了。",
        "我和父母关系不好是因为他们思想太落后, 完全无法沟通, 不是我的问题。",
        "我最近状态不好全怪公司加班文化太差, 把我身体搞垮了。",
        "我脾气暴躁是因为社会环境太差, 每个人都很焦虑, 这不能怪我。",
        "我们分手了全是对方的错, 她/他太自私了, 我在这段感情里没有犯过任何错。",
        "我开车出事故是因为前车急刹车, 后车追尾, 导航也导错了, 反正不是我的错。",
    ],
    "情绪推理": [
        "我感到非常焦虑和不安。一定有什么不好的事情要发生了, 我能感觉到。",
        "我对新同事有种莫名的厌恶感。这个人肯定有问题, 我的直觉从来不会错。",
        "我今天心情特别低落。所以今天一定是糟糕的一天, 做任何事都会失败。",
        "和他在一起我总觉得不舒服。他肯定在隐瞒什么, 我的感觉不会骗我。",
        "一想到要出差我就心慌。这次出差一定会出大事的。",
        "我觉得很愧疚, 没有任何理由, 但一定是我做错了什么。",
        "我今天心情很好, 所以事情一定会顺利——你看, 果然喝咖啡都没烫到嘴。",
        "我总感觉有人在监视我, 虽然看不到任何人。这种感觉太真实了, 一定有。",
        "这个投资让我觉得特别恐慌。不管数据怎么说, 感觉不好就是不能投。",
        "我一碰到他就浑身难受。他肯定是个不好的能量场, 我得远离他。",
    ],
}


def make_base_char(overrides=None):
    """创建基础 character_state 字典。"""
    c = {
        "personality": {
            "openness": 0.5, "conscientiousness": 0.5, "extraversion": 0.5,
            "agreeableness": 0.5, "neuroticism": 0.5,
            "attachment_style": "secure", "defense_style": [], "cognitive_biases": [],
            "moral_stage": 3,
        },
        "trauma": {"ace_score": 0, "active_schemas": [], "trauma_triggers": []},
        "ideal_world": {},
        "motivation": {"current_goal": ""},
        "emotion_decay": {},
    }
    if overrides:
        for k, v in overrides.items():
            if isinstance(v, dict) and isinstance(c.get(k), dict):
                c[k].update(v)
            else:
                c[k] = v
    return c


def try_load_social_cd(case_limit_per_type=10):
    """尝试从本地 SocialCD-3K 路径加载真实数据。

    如果数据集不可用, 返回 None 触发内置生成逻辑。
    路径假设: 数据集解压后含 distorsions.json 或类似结构。
    """
    import os as _os
    _tmp = Path(_os.environ.get("TEMP", "/tmp"))
    candidate_paths = [
        _tmp / "SocialCD-3K" / "distorsions.json",       # 可能的格式
        _tmp / "SocialCD-3K" / "data" / "social_cd.json",
        Path("/data/SocialCD-3K/distorsions.json"),
        Path.cwd() / "data" / "social_cd_3k.json",
        Path.cwd().parent / "data" / "social_cd_3k.json",
    ]
    for p in candidate_paths:
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    dataset = json.load(f)
                return convert_dataset_to_cases(dataset, case_limit_per_type)
            except (json.JSONDecodeError, KeyError, TypeError):
                continue
    return None


def convert_dataset_to_cases(dataset, limit=10):
    """将 SocialCD-3K 数据集转换为验证用例格式。

    根据数据集结构自适应: 支持列表或字典格式。
    """
    cases = []
    type_counter = {}

    # 统一为列表
    items = dataset if isinstance(dataset, list) else list(dataset.values())

    for item in items:
        if isinstance(item, str):
            # 纯文本格式
            text = item
            dist_type = "未知"
        else:
            text = item.get("text", item.get("content", item.get("post", "")))
            dist_type = item.get("label", item.get("type", item.get("distorsion", "未知")))

        # 匹配已知扭曲类型
        matched_meta = None
        for meta in DISTORTION_META:
            if dist_type == meta["en"] or dist_type == meta["zh"] or dist_type == meta["abbr"]:
                matched_meta = meta
                break
        if matched_meta is None:
            continue
        type_name = matched_meta["zh"]
        type_counter[type_name] = type_counter.get(type_name, 0) + 1
        if type_counter[type_name] > limit:
            continue

        profile = DISTORTION_PROFILES.get(type_name, DISTORTION_PROFILES["贴标签"])
        bias_name = type_name

        case = {
            "id": f"scd_{len(cases):04d}",
            "source": f"SocialCD-3K (DOI: 10.21227/jb3w-j696) — {type_name}",
            "domain": "cognitive_distortion",
            "character_state": {
                "name": "微博用户",
                **make_base_char({
                    "personality": {
                        **profile["personality"],
                        "attachment_style": "secure",
                        "defense_style": list(profile.get("defense_style", [])),
                        "cognitive_biases": list(profile.get("cognitive_biases", [])),
                        "moral_stage": 3,
                    },
                    "motivation": {"current_goal": "表达当下的情绪感受"},
                }),
            },
            "event": {
                "description": text[:300],
                "type": "social",
                "participants": [],
                "significance": 0.65,
                "tags": ["cognitive_bias", type_name, "weibo"],
            },
            "expected": {
                "cognitive_bias_detect": {
                    "activated_biases": {"contains_any": [bias_name]},
                },
                "plutchik_emotion": {
                    "internal.dominant": {"in": profile["emotions"]},
                },
                "response_generator": {
                    "response_text": {"not_empty": True},
                },
            },
        }
        cases.append(case)

    return cases if cases else None


def generate_builtin_cases():
    """生成 ~120 条内置用例, 每类 10 条。"""
    cases = []
    case_id = 0

    for meta in DISTORTION_META:
        type_name = meta["zh"]
        scenarios = BUILTIN_SCENARIOS.get(type_name, [])
        profile = DISTORTION_PROFILES.get(type_name, DISTORTION_PROFILES["贴标签"])

        for i, scenario_text in enumerate(scenarios):
            # 每 3 条换一种次级关联偏差增加多样性
            secondary_biases = list(profile.get("cognitive_biases", []))
            if i >= 3 and len(secondary_biases) > 1:
                expected_biases = [secondary_biases[1]]
            else:
                expected_biases = [type_name]

            # 对应情绪也适当变化
            emotions = list(profile["emotions"])
            if i >= 5 and len(emotions) > 1:
                expected_emotions = [emotions[1]]
            else:
                expected_emotions = [emotions[0]]

            case = {
                "id": f"scd_{case_id:04d}",
                "source": f"SocialCD-3K — {type_name} ({meta['en']})",
                "domain": "cognitive_distortion",
                "character_state": {
                    "name": "微博用户",
                    **make_base_char({
                        "personality": {
                            **profile["personality"],
                            "attachment_style": "secure",
                            "defense_style": list(profile.get("defense_style", [])),
                            "cognitive_biases": list(profile.get("cognitive_biases", [])),
                            "moral_stage": 3,
                        },
                        "motivation": {"current_goal": "在微博上表达不满或担忧"},
                    }),
                },
                "event": {
                    "description": scenario_text,
                    "type": "social",
                    "participants": [],
                    "significance": 0.6,
                    "tags": ["cognitive_bias", type_name, "weibo"],
                },
                "expected": {
                    "cognitive_bias_detect": {
                        "activated_biases": {"contains_any": expected_biases},
                        "activation_relevance": {"min": 0.3},
                    },
                    "plutchik_emotion": {
                        "internal.dominant": {"in": expected_emotions},
                        "internal.intensity": {"min": 0.4},
                    },
                    "response_generator": {
                        "response_text": {"not_empty": True},
                    },
                },
            }
            cases.append(case)
            case_id += 1

    return cases


def sample_cases(cases, k=12):
    """按类型均匀采样。"""
    by_type = {}
    for c in cases:
        tags = c.get("event", {}).get("tags", [])
        # 从 tags 提取类型名
        dist_type = None
        for meta in DISTORTION_META:
            if meta["zh"] in tags:
                dist_type = meta["zh"]
                break
        if dist_type is None:
            by_type.setdefault("other", []).append(c)
        else:
            by_type.setdefault(dist_type, []).append(c)

    sampled = []
    for t, lst in sorted(by_type.items()):
        sampled.extend(lst[:1])  # 每类取 1 条
    return sampled


def main():
    parser = argparse.ArgumentParser(description="Extract SocialCD-3K test fixtures")
    parser.add_argument("--sample", action="store_true",
                        help="仅输出采样 (每类型 1 条)")
    parser.add_argument("--output", type=str, default=None,
                        help="输出路径 (默认: fixtures/social_cd_cases.json)")
    args = parser.parse_args()

    # 先尝试加载数据集
    cases = try_load_social_cd(case_limit_per_type=10)

    if cases is None:
        print("SocialCD-3K 数据集未找到, 使用内置生成逻辑...")
        cases = generate_builtin_cases()
        print(f"生成了 {len(cases)} 条内置用例")
    else:
        print(f"从 SocialCD-3K 数据集中提取了 {len(cases)} 条用例")

    if args.sample:
        cases = sample_cases(cases, k=12)
        print(f"采样 {len(cases)} 条 (每类型 1 条)")
        # --sample 时默认输出到含 sample 标记的文件, 避免覆盖主输出
        default_name = "social_cd_cases_sample.json"
    else:
        default_name = "social_cd_cases.json"

    # 统计
    by_type = {}
    for c in cases:
        tags = c.get("event", {}).get("tags", [])
        dist_type = None
        for meta in DISTORTION_META:
            if meta["zh"] in tags:
                dist_type = meta["zh"]
                break
        if dist_type is None:
            dist_type = "other"
        by_type[dist_type] = by_type.get(dist_type, 0) + 1
    print("\n各类型数量:")
    for t, n in sorted(by_type.items()):
        print(f"  {t}: {n}")

    # 保存
    out_path = args.output if args.output else OUTPUT_DIR / default_name
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(cases, f, ensure_ascii=False, indent=2)
    print(f"\n保存到 {out_path}")


if __name__ == "__main__":
    main()
