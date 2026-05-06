"""从 CPsyCoun 数据集提取心理咨询验证用例。

CPsyCoun (2024): 3,134 中文心理咨询对话，覆盖 9 大咨询主题。
来源: https://huggingface.co/datasets/CAS-SIAT-XinHai/CPsyCoun

输出 ~100 条内置用例，覆盖全部 9 个咨询领域。
每个用例包含求助者角色（有心理问题）和咨询师角色。
Focus: L4 (反思性处理: 情绪调节、道德推理、需求分析、动机分析)
       + L5 (回应生成)
"""
import argparse
import json
import random
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent.parent / "fixtures"

# 9 大咨询主题
COUNSELING_TOPICS = [
    "自我成长", "情绪与压力", "教育", "婚恋",
    "家庭关系", "人际关系", "性", "职业", "心理疾病",
]

# ═══════════════════════════════════════════════════════════════
# 内置咨询案例 — 每条包含 (问题描述, 求助者回应, 主题, 求助者人格, 创伤信息, 动机)
# ═══════════════════════════════════════════════════════════════
BUILTIN_CASES = [
    # --- 自我成长 ---
    {
        "topic": "自我成长",
        "client_issue": "我总是觉得自己不够好，无论取得什么成就都觉得是侥幸。工作三年升了两次职，但我总觉得总有一天别人会发现我其实什么都不会。",
        "client_utterance": "我每天上班前都要在车里坐十分钟才能鼓起勇气进去。每次开会都怕被问到回答不上的问题。这种恐惧快把我逼疯了。",
        "client_name": "高天阳",
        "client_personality": {"openness": 0.55, "conscientiousness": 0.75, "extraversion": 0.3, "agreeableness": 0.65, "neuroticism": 0.8},
        "attachment": "anxious",
        "ace": 2,
        "schemas": ["缺陷/羞耻", "失败"],
        "goal": "想摆脱冒充者综合征",
        "moral_stage": 4,
    },
    {
        "topic": "自我成长",
        "client_issue": "我今年45岁了，突然觉得自己前半生都在为别人活。为了父母选专业，为了丈夫放弃工作，为了孩子放弃爱好。现在孩子上大学了，我不知道自己是谁。",
        "client_utterance": "上个月我试着报名了一个画画班，但第一节课就跑了。我觉得我不配为自己花时间。这种想法让我很痛苦。",
        "client_name": "苏慧敏",
        "client_personality": {"openness": 0.6, "conscientiousness": 0.7, "extraversion": 0.4, "agreeableness": 0.75, "neuroticism": 0.6},
        "attachment": "secure",
        "ace": 1,
        "schemas": ["自我牺牲", "情感压抑"],
        "goal": "寻找自我认同",
        "moral_stage": 4,
    },
    {
        "topic": "自我成长",
        "client_issue": "我没办法对别人说不。同事把工作推给我，朋友借钱不还，我都不敢拒绝。每次想说'不'的时候喉咙就像被堵住了一样。",
        "client_utterance": "上周同事把她的活也交给我做，我加班到凌晨两点。她却在朋友圈发聚餐照片。我气得睡不着，但第二天还是笑着说'没事'。",
        "client_name": "易晓",
        "client_personality": {"openness": 0.45, "conscientiousness": 0.65, "extraversion": 0.35, "agreeableness": 0.85, "neuroticism": 0.7},
        "attachment": "anxious",
        "ace": 3,
        "schemas": ["讨好", "自我牺牲"],
        "goal": "学会设立边界",
        "moral_stage": 3,
    },
    # --- 情绪与压力 ---
    {
        "topic": "情绪与压力",
        "client_issue": "最近半年我每天早上醒来第一件事就是觉得'又要熬一天'。对什么都没兴趣，以前喜欢的事情现在做起来只觉得累。",
        "client_utterance": "朋友约我出去我都找借口推掉。不是不想见他们，是我实在没有力气在别人面前假装开心了。",
        "client_name": "何思远",
        "client_personality": {"openness": 0.5, "conscientiousness": 0.5, "extraversion": 0.25, "agreeableness": 0.6, "neuroticism": 0.85},
        "attachment": "avoidant",
        "ace": 2,
        "schemas": ["情感剥夺", "社交孤立"],
        "goal": "减轻抑郁症状",
        "moral_stage": 3,
    },
    {
        "topic": "情绪与压力",
        "client_issue": "我控制不住地暴饮暴食，压力大的时候尤其严重。吃完又极度自责，然后催吐。这个循环越来越频繁。",
        "client_utterance": "昨天又开始了。白天被领导骂了之后，下班路上买了六个面包、两袋薯片和一个蛋糕，全部塞进肚子里。然后蹲在厕所里哭。",
        "client_name": "夏晚晴",
        "client_personality": {"openness": 0.5, "conscientiousness": 0.4, "extraversion": 0.55, "agreeableness": 0.7, "neuroticism": 0.85},
        "attachment": "fearful_avoidant",
        "ace": 4,
        "schemas": ["缺陷/羞耻", "不信任/虐待"],
        "goal": "打破暴食循环",
        "moral_stage": 3,
    },
    {
        "topic": "情绪与压力",
        "client_issue": "我每晚都要醒三四次，每次醒来就再也睡不着，脑子里反复想白天发生的每一件事。长期失眠让我觉得自己快要崩溃了。",
        "client_utterance": "昨晚三点又醒了，然后一直想到天亮。今天开会时完全听不懂大家在说什么，感觉大脑像一团浆糊。",
        "client_name": "沈明远",
        "client_personality": {"openness": 0.6, "conscientiousness": 0.7, "extraversion": 0.35, "agreeableness": 0.55, "neuroticism": 0.75},
        "attachment": "anxious",
        "ace": 1,
        "schemas": ["苛刻标准", "负面预期"],
        "goal": "改善睡眠质量",
        "moral_stage": 4,
    },
    # --- 教育 ---
    {
        "topic": "教育",
        "client_issue": "我儿子今年高三，最近突然不肯去上学了。他说自己不是读书的料，怎么劝都没用。以前他成绩中上，没有厌学的迹象。",
        "client_utterance": "昨天他又把自己锁在房间里一整天。我敲门说妈妈很担心你，他说'你们担心的不过是我的成绩'。这句话让我很受伤。",
        "client_name": "吴秀兰",
        "client_personality": {"openness": 0.5, "conscientiousness": 0.8, "extraversion": 0.55, "agreeableness": 0.7, "neuroticism": 0.65},
        "attachment": "secure",
        "ace": 2,
        "schemas": ["失败", "苛刻标准"],
        "goal": "改善亲子沟通，帮助孩子重返校园",
        "moral_stage": 4,
    },
    {
        "topic": "教育",
        "client_issue": "我是大二学生，选错了专业，每天上课都像在听天书。想转专业但父母强烈反对，说我不懂事、浪费钱。",
        "client_utterance": "期中考试我挂了四科。我不敢告诉父母，也不敢告诉室友。每天晚上躲在被子里哭，觉得自己的人生完蛋了。",
        "client_name": "陆子轩",
        "client_personality": {"openness": 0.7, "conscientiousness": 0.55, "extraversion": 0.45, "agreeableness": 0.6, "neuroticism": 0.7},
        "attachment": "fearful_avoidant",
        "ace": 1,
        "schemas": ["失败", "自我牺牲"],
        "goal": "在父母期待和自我意愿之间找到平衡",
        "moral_stage": 3,
    },
    {
        "topic": "教育",
        "client_issue": "我女儿小学五年级，每次考试前都会肚子疼、发烧。去医院检查没有任何问题。我怀疑是压力导致的躯体化症状。",
        "client_utterance": "昨晚她又发烧了，今天有数学考试。她说'妈妈我是不是很没用'，我抱着她哭了。我不知道怎么帮她。",
        "client_name": "林芳华",
        "client_personality": {"openness": 0.55, "conscientiousness": 0.75, "extraversion": 0.5, "agreeableness": 0.8, "neuroticism": 0.7},
        "attachment": "anxious",
        "ace": 2,
        "schemas": ["失败", "苛刻标准"],
        "goal": "减轻女儿考试焦虑",
        "moral_stage": 4,
    },
    # --- 婚恋 ---
    {
        "topic": "婚恋",
        "client_issue": "我和女朋友在一起五年了，她最近提出分手。理由是'你很好，但我感觉不到被爱'。我确实不擅长表达感情，但我真的很爱她。",
        "client_utterance": "她走的那天说：'你连我什么时候难过都看不出来。'我是真的看不出来。我以为她不说就是没事。我现在每天都会路过她公司楼下。",
        "client_name": "郑浩然",
        "client_personality": {"openness": 0.35, "conscientiousness": 0.7, "extraversion": 0.3, "agreeableness": 0.5, "neuroticism": 0.5},
        "attachment": "dismissive_avoidant",
        "ace": 3,
        "schemas": ["情感剥夺", "社交孤立"],
        "goal": "学会表达情感，尝试挽回或走出来",
        "moral_stage": 3,
    },
    {
        "topic": "婚恋",
        "client_issue": "我结婚七年了，最近发现老公和女同事有暧昧聊天记录。他说只是开玩笑，但我每天都很痛苦，不知道要不要离婚。",
        "client_utterance": "现在他碰我我都浑身僵硬。脑子里全是他们聊天的内容。我试着相信他，但信任一旦碎了怎么粘回去？",
        "client_name": "唐心如",
        "client_personality": {"openness": 0.5, "conscientiousness": 0.65, "extraversion": 0.45, "agreeableness": 0.7, "neuroticism": 0.8},
        "attachment": "anxious",
        "ace": 3,
        "schemas": ["不信任/虐待", "缺陷/羞耻"],
        "goal": "在信任重建和自我保护间做选择",
        "moral_stage": 4,
    },
    {
        "topic": "婚恋",
        "client_issue": "我30岁了，家里一直在催婚。相亲认识了现在的男朋友，条件很好，各方面都合适，但我不爱他。我不知道该不该将就。",
        "client_utterance": "上周他求婚了。我戴着戒指看着镜子里的自己，觉得那是一个陌生人的手。我应该开心才对，但我只想逃。",
        "client_name": "白露",
        "client_personality": {"openness": 0.75, "conscientiousness": 0.5, "extraversion": 0.6, "agreeableness": 0.65, "neuroticism": 0.6},
        "attachment": "fearful_avoidant",
        "ace": 1,
        "schemas": ["情感压抑", "自我牺牲"],
        "goal": "在家庭压力和个人感受之间抉择",
        "moral_stage": 4,
    },
    # --- 家庭关系 ---
    {
        "topic": "家庭关系",
        "client_issue": "我和父亲的关系一直很差。从小他对我只有批评没有鼓励。现在我30多岁了，每次接到他的电话都会焦虑发作。",
        "client_utterance": "昨天他打电话来，第一句就是'你那个工作能有什么出息'。我直接挂断了电话，然后哭了半个小时。我已经很努力了，为什么他永远不满意？",
        "client_name": "叶子铭",
        "client_personality": {"openness": 0.6, "conscientiousness": 0.7, "extraversion": 0.4, "agreeableness": 0.55, "neuroticism": 0.75},
        "attachment": "fearful_avoidant",
        "ace": 5,
        "schemas": ["苛刻标准", "缺陷/羞耻", "情感剥夺"],
        "goal": "减少父亲评价对自己的情绪影响",
        "moral_stage": 4,
    },
    {
        "topic": "家庭关系",
        "client_issue": "自从哥哥结婚后，嫂子就一直挑拨我和妈妈的关系。妈妈开始觉得我不孝顺，我回娘家像做客一样拘束。",
        "client_utterance": "上周回家，发现我的房间被改成侄子的玩具房了。妈妈说你反正在外面有房子。我什么都没说，但心里像被掏空了一样。",
        "client_name": "韩雨桐",
        "client_personality": {"openness": 0.5, "conscientiousness": 0.6, "extraversion": 0.55, "agreeableness": 0.75, "neuroticism": 0.65},
        "attachment": "anxious",
        "ace": 2,
        "schemas": ["情感剥夺", "社交孤立"],
        "goal": "重新在家庭中找到归属感",
        "moral_stage": 3,
    },
    {
        "topic": "家庭关系",
        "client_issue": "我弟弟大学毕业三年了不工作，每天在家打游戏。父母惯着他，我还要每个月给家里寄钱补贴。我觉得自己像个提款机。",
        "client_utterance": "昨天妈妈说弟弟想买新电脑，让我出钱。我说不买，妈妈就说我自私、忘了本。我挂了电话后气得浑身发抖。",
        "client_name": "钱国伟",
        "client_personality": {"openness": 0.45, "conscientiousness": 0.8, "extraversion": 0.5, "agreeableness": 0.6, "neuroticism": 0.55},
        "attachment": "secure",
        "ace": 1,
        "schemas": ["自我牺牲", "苛刻标准"],
        "goal": "设立与原生家庭的边界",
        "moral_stage": 5,
    },
    # --- 人际关系 ---
    {
        "topic": "人际关系",
        "client_issue": "我好像总被人利用。每次交朋友都是我付出更多，但需要帮助的时候那些朋友都消失了。我怀疑是不是自己有问题。",
        "client_utterance": "上周我生病了，发着高烧。我群发消息希望有人能帮我去药店买药。十个人，没有一个人回复。但我之前帮过他们每个人。",
        "client_name": "许安琪",
        "client_personality": {"openness": 0.55, "conscientiousness": 0.6, "extraversion": 0.65, "agreeableness": 0.85, "neuroticism": 0.7},
        "attachment": "anxious",
        "ace": 2,
        "schemas": ["讨好", "缺陷/羞耻"],
        "goal": "建立健康的友谊关系",
        "moral_stage": 3,
    },
    {
        "topic": "人际关系",
        "client_issue": "我在公司被同事孤立了。只是因为我在会议上提了一个不同意见，现在他们聚餐不叫我，工作群也不回我消息。",
        "client_utterance": "今天中午我一个人在食堂吃饭，看到他们围在一起有说有笑。我走过去的时候他们突然安静了。那种感觉就像回到初中被霸凌的时候。",
        "client_name": "顾北辰",
        "client_personality": {"openness": 0.55, "conscientiousness": 0.7, "extraversion": 0.35, "agreeableness": 0.5, "neuroticism": 0.7},
        "attachment": "avoidant",
        "ace": 4,
        "schemas": ["社交孤立", "不信任/虐待"],
        "goal": "在职场中重建社交关系",
        "moral_stage": 4,
    },
    {
        "topic": "人际关系",
        "client_issue": "我最好的朋友最近谈恋爱后完全变了一个人。她取消了我们的每周聚会，忘记了我的生日，发的消息隔天才回。我觉得自己被她抛弃了。",
        "client_utterance": "上周我生日，她说好一起吃饭。但我在餐厅等了她两个小时，她最后发消息说'男朋友突然来找我，改天吧'。我一个人点了一整桌菜。",
        "client_name": "姚晶晶",
        "client_personality": {"openness": 0.6, "conscientiousness": 0.5, "extraversion": 0.7, "agreeableness": 0.7, "neuroticism": 0.75},
        "attachment": "anxious",
        "ace": 2,
        "schemas": ["情感剥夺", "社交孤立"],
        "goal": "适应友谊的变化或建立新的关系",
        "moral_stage": 3,
    },
    # --- 性 ---
    {
        "topic": "性",
        "client_issue": "我结婚两年了，但对性生活完全没有兴趣。每次丈夫靠近我我就紧张到全身僵硬。我知道这伤害了他，但我控制不了。",
        "client_utterance": "昨天他又尝试了，我假装头疼。看到他失望的表情我很难过，但我是真的害怕。我小时候被亲戚猥亵过，没有告诉任何人。",
        "client_name": "温婉清",
        "client_personality": {"openness": 0.4, "conscientiousness": 0.6, "extraversion": 0.3, "agreeableness": 0.65, "neuroticism": 0.85},
        "attachment": "fearful_avoidant",
        "ace": 6,
        "schemas": ["不信任/虐待", "缺陷/羞耻", "情感压抑"],
        "goal": "处理性创伤记忆",
        "moral_stage": 3,
    },
    {
        "topic": "性",
        "client_issue": "我发现自己对同性有好感，但我来自一个非常传统的家庭。父母说过同性恋是变态。我每天都在自我厌恶中挣扎。",
        "client_utterance": "前几天妈妈说要给我介绍女朋友。我笑着说好啊，但那一瞬间我想从窗户跳下去。我不是想死，只是不知道怎么活下去。",
        "client_name": "江一舟",
        "client_personality": {"openness": 0.55, "conscientiousness": 0.6, "extraversion": 0.35, "agreeableness": 0.6, "neuroticism": 0.8},
        "attachment": "fearful_avoidant",
        "ace": 3,
        "schemas": ["缺陷/羞耻", "情感压抑"],
        "goal": "接纳性取向，减少自我厌恶",
        "moral_stage": 4,
    },
    {
        "topic": "性",
        "client_issue": "我和伴侣在性方面越来越不和谐。我想要的他不要，他想要的我觉得恶心。我们已经半年没有亲密接触了，我觉得他在外面可能有人了。",
        "client_utterance": "昨晚我试着主动，他翻过身说累了。我盯着天花板想：我们才28岁，就要过无性婚姻了吗？是我的问题还是他的问题？",
        "client_name": "秦雨霏",
        "client_personality": {"openness": 0.65, "conscientiousness": 0.55, "extraversion": 0.6, "agreeableness": 0.65, "neuroticism": 0.65},
        "attachment": "anxious",
        "ace": 1,
        "schemas": ["缺陷/羞耻", "情感剥夺"],
        "goal": "改善伴侣间性沟通",
        "moral_stage": 4,
    },
    # --- 职业 ---
    {
        "topic": "职业",
        "client_issue": "我在现在这家公司干了六年，没有升职、没有加薪，领导还说'你不做有的是人做'。我想跳槽但害怕改变。",
        "client_utterance": "今天提交了年假申请，领导批了但说'现在这么忙你还好意思休假'。我为公司加了六年班，连年假都不能休吗？",
        "client_name": "黄伟业",
        "client_personality": {"openness": 0.4, "conscientiousness": 0.8, "extraversion": 0.4, "agreeableness": 0.65, "neuroticism": 0.55},
        "attachment": "secure",
        "ace": 1,
        "schemas": ["自我牺牲", "苛刻标准"],
        "goal": "职业转型或争取应得权益",
        "moral_stage": 4,
    },
    {
        "topic": "职业",
        "client_issue": "我被公司裁员了。35岁，在这个行业突然就找不到工作了。每次面试都被嫌年龄大，或者被问'你能接受比之前低的薪资吗'。",
        "client_utterance": "今天去面试一家公司，面试官比我小十岁，全程用'你们这个年纪的人'来开头。我强忍着怒火面完，出门后踢翻了路边的垃圾桶。",
        "client_name": "马国梁",
        "client_personality": {"openness": 0.45, "conscientiousness": 0.75, "extraversion": 0.55, "agreeableness": 0.5, "neuroticism": 0.65},
        "attachment": "secure",
        "ace": 2,
        "schemas": ["失败", "苛刻标准"],
        "goal": "应对中年职业危机",
        "moral_stage": 4,
    },
    {
        "topic": "职业",
        "client_issue": "我是一名新入行的心理咨询师，每次接案后都会极度焦虑，反复怀疑自己是否伤害了来访者。督导说我的反移情太强了。",
        "client_utterance": "昨天一个来访者在咨询中哭了，我当场慌了，不知道该怎么处理。晚上失眠到天亮，一直在想我是不是不适合做这行。",
        "client_name": "曾敏",
        "client_personality": {"openness": 0.7, "conscientiousness": 0.7, "extraversion": 0.45, "agreeableness": 0.75, "neuroticism": 0.7},
        "attachment": "anxious",
        "ace": 1,
        "schemas": ["苛刻标准", "缺陷/羞耻"],
        "goal": "克服职业焦虑，提升专业能力",
        "moral_stage": 5,
    },
    # --- 心理疾病 ---
    {
        "topic": "心理疾病",
        "client_issue": "我确诊了中度抑郁症，在服药但效果不明显。每天醒来都希望自己没有醒来。我没有自杀计划，但觉得活着没有意义。",
        "client_utterance": "今天太阳很好，但我感觉一切都是灰色的。我出门散步，看到路边开的花，脑子里想的是'它们明年还会开，但我不一定在了'。",
        "client_name": "段清风",
        "client_personality": {"openness": 0.55, "conscientiousness": 0.45, "extraversion": 0.2, "agreeableness": 0.6, "neuroticism": 0.9},
        "attachment": "avoidant",
        "ace": 4,
        "schemas": ["社交孤立", "情感剥夺", "失败"],
        "goal": "减轻抑郁症状，找到生活意义",
        "moral_stage": 3,
    },
    {
        "topic": "心理疾病",
        "client_issue": "我有严重的社交焦虑。在公共场合吃饭手会抖，开会发言会脸红到脖子根，甚至去便利店买东西都要做十分钟心理建设。",
        "client_utterance": "今天公司团建要自我介绍，轮到我的时候我直接冲出了房间，躲在厕所里发抖。同事们一定觉得我是个怪人。",
        "client_name": "钟书言",
        "client_personality": {"openness": 0.45, "conscientiousness": 0.65, "extraversion": 0.15, "agreeableness": 0.7, "neuroticism": 0.85},
        "attachment": "avoidant",
        "ace": 3,
        "schemas": ["缺陷/羞耻", "社交孤立"],
        "goal": "减少社交焦虑对生活的影响",
        "moral_stage": 3,
    },
    {
        "topic": "心理疾病",
        "client_issue": "我被诊断出强迫症。每天要洗手几十次，出门前要检查门窗三次，往返确认。我知道不合理但控制不住。",
        "client_utterance": "今早出门后下了楼又折回去三次检查煤气。上班迟到了四十分钟。同事开玩笑说'你是不是有强迫症'，我笑着说有点，心里却很想哭。",
        "client_name": "曹思明",
        "client_personality": {"openness": 0.35, "conscientiousness": 0.85, "extraversion": 0.35, "agreeableness": 0.6, "neuroticism": 0.8},
        "attachment": "anxious",
        "ace": 2,
        "schemas": ["苛刻标准", "失败"],
        "goal": "减轻强迫症状对日常功能的影响",
        "moral_stage": 4,
    },
    {
        "topic": "心理疾病",
        "client_issue": "我经历了严重的车祸，虽然身体康复了，但现在一上车就心慌气短。上个月试图坐地铁，在里面惊恐发作被送去了急诊。",
        "client_utterance": "今天公司要求出差，需要坐高铁。我已经连续三天失眠了，脑子里全是车祸那天的画面和声音。我还没到车站就想逃。",
        "client_name": "程云峰",
        "client_personality": {"openness": 0.5, "conscientiousness": 0.7, "extraversion": 0.45, "agreeableness": 0.65, "neuroticism": 0.8},
        "attachment": "secure",
        "ace": 2,
        "schemas": ["脆弱性", "负面预期"],
        "goal": "克服创伤后应激障碍",
        "moral_stage": 4,
    },
    # --- 追加案例: 自我成长 ---
    {
        "topic": "自我成长",
        "client_issue": "我今年28岁，但感觉自己什么都没有做成。同学有的结婚了有的买房了有的创业了，我还在原来的岗位原地踏步。",
        "client_utterance": "每次刷朋友圈都是一种折磨。看到别人过得那么好，我就觉得自己是个失败者。我知道不应该比较，但我控制不住。",
        "client_name": "谢晓峰",
        "client_personality": {"openness": 0.5, "conscientiousness": 0.6, "extraversion": 0.45, "agreeableness": 0.6, "neuroticism": 0.75},
        "attachment": "anxious",
        "ace": 1,
        "schemas": ["失败", "苛刻标准"],
        "goal": "减少社会比较带来的焦虑",
        "moral_stage": 3,
    },
    {
        "topic": "自我成长",
        "client_issue": "我不能忍受任何不确定性。我要知道每件事情的确切结果，否则就会非常焦虑。看电影前要看影评，旅行前要做精确到小时的计划。",
        "client_utterance": "朋友约我周末去一个从没去过的地方徒步，说'不要查攻略，体验未知的乐趣'。我光是想到这句话就焦虑了一整天。",
        "client_name": "许文静",
        "client_personality": {"openness": 0.25, "conscientiousness": 0.85, "extraversion": 0.3, "agreeableness": 0.55, "neuroticism": 0.8},
        "attachment": "anxious",
        "ace": 2,
        "schemas": ["脆弱性", "苛刻标准"],
        "goal": "学会容忍不确定性",
        "moral_stage": 3,
    },
    # --- 追加案例: 情绪与压力 ---
    {
        "topic": "情绪与压力",
        "client_issue": "我最近总是莫名其妙地想哭。工作上没有出什么问题，家庭也和睦，但我就是控制不住地感到悲伤和空虚。",
        "client_utterance": "今天开车下班，等红绿灯的时候突然就流泪了。旁边的司机看了我一眼，我赶紧擦掉。我甚至不知道为什么哭。",
        "client_name": "邓安琪",
        "client_personality": {"openness": 0.55, "conscientiousness": 0.6, "extraversion": 0.5, "agreeableness": 0.7, "neuroticism": 0.8},
        "attachment": "secure",
        "ace": 1,
        "schemas": ["情感压抑", "情感剥夺"],
        "goal": "理解并处理莫名的悲伤",
        "moral_stage": 3,
    },
    {
        "topic": "情绪与压力",
        "client_issue": "我老公去年出轨了，我们选择继续婚姻。但我现在每天都会忍不住查他的手机、定位、行车记录。我知道这样不对，但我控制不了。",
        "client_utterance": "昨天他说加班，我开车去他公司楼下蹲了两个小时，看到他和同事一起出来，才放心回家。我觉得自己像个疯子。",
        "client_name": "陶晶莹",
        "client_personality": {"openness": 0.4, "conscientiousness": 0.65, "extraversion": 0.5, "agreeableness": 0.6, "neuroticism": 0.85},
        "attachment": "anxious",
        "ace": 3,
        "schemas": ["不信任/虐待", "缺陷/羞耻"],
        "goal": "重建信任或接受现实",
        "moral_stage": 4,
    },
    # --- 追加案例: 教育 ---
    {
        "topic": "教育",
        "client_issue": "我是单亲妈妈，儿子今年15岁，叛逆期特别严重。我说什么他都顶嘴，最近还学会了翘课。我打也打了骂也骂了，完全没用。",
        "client_utterance": "昨天老师打电话说他又没去上课。我回家发现他在房间里打游戏，我说你知不知道妈妈多辛苦，他说'又不是我让你生我的'。",
        "client_name": "柳如烟",
        "client_personality": {"openness": 0.45, "conscientiousness": 0.75, "extraversion": 0.5, "agreeableness": 0.6, "neuroticism": 0.75},
        "attachment": "anxious",
        "ace": 3,
        "schemas": ["失败", "缺陷/羞耻"],
        "goal": "改善与青春期儿子的关系",
        "moral_stage": 4,
    },
    {
        "topic": "教育",
        "client_issue": "我考研三次都失败了。身边的人都劝我放弃，说我不是读书的料。但我真的不甘心，我不知道是该继续还是该认命。",
        "client_utterance": "今天妈妈打电话说隔壁家的小丽研究生毕业了，找到好工作了。我没说话。挂了电话后把复习资料全部摔在地上，然后一张一张捡起来。",
        "client_name": "宋浩然",
        "client_personality": {"openness": 0.5, "conscientiousness": 0.8, "extraversion": 0.25, "agreeableness": 0.55, "neuroticism": 0.7},
        "attachment": "avoidant",
        "ace": 1,
        "schemas": ["失败", "苛刻标准"],
        "goal": "决定是否继续考研",
        "moral_stage": 4,
    },
    # --- 追加案例: 婚恋 ---
    {
        "topic": "婚恋",
        "client_issue": "我男朋友控制欲特别强，不许我和异性说话，不许穿短裙，所有密码都要给他。他说是因为太爱我了，但我感觉很窒息。",
        "client_utterance": "今天我穿了一件新买的连衣裙去上班，他发消息说'换掉，太短了'。我说这很正常，他说'你是不是故意穿给别人看'。",
        "client_name": "蓝小蝶",
        "client_personality": {"openness": 0.55, "conscientiousness": 0.5, "extraversion": 0.6, "agreeableness": 0.7, "neuroticism": 0.65},
        "attachment": "fearful_avoidant",
        "ace": 2,
        "schemas": ["情感剥夺", "不信任/虐待"],
        "goal": "分辨控制与爱的边界",
        "moral_stage": 3,
    },
    {
        "topic": "婚恋",
        "client_issue": "我离异三年了，带着一个孩子。最近有人给我介绍了一个对象，人很好，但我害怕再次受伤。孩子也不接受新的人进入我们的生活。",
        "client_utterance": "他昨天说想周末带我和孩子去游乐园。孩子说'我不要和陌生人去'。我两边都不知道怎么安抚。也许我根本不配拥有幸福。",
        "client_name": "何玉芬",
        "client_personality": {"openness": 0.5, "conscientiousness": 0.65, "extraversion": 0.35, "agreeableness": 0.75, "neuroticism": 0.7},
        "attachment": "fearful_avoidant",
        "ace": 3,
        "schemas": ["情感剥夺", "社交孤立"],
        "goal": "平衡新感情和做母亲的责任",
        "moral_stage": 4,
    },
    # --- 追加案例: 家庭关系 ---
    {
        "topic": "家庭关系",
        "client_issue": "我妈一辈子都在抱怨我爸不好、生活苦、为了我她才不离婚。我从小就觉得欠她的。现在我有自己的家庭了，她还是要干涉我的生活。",
        "client_utterance": "前天我教育孩子的时候，我妈当着孩子的面说'你小时候还不如他'。我说妈你别这样，她就开始哭，说我不孝。",
        "client_name": "魏嘉琳",
        "client_personality": {"openness": 0.5, "conscientiousness": 0.6, "extraversion": 0.5, "agreeableness": 0.7, "neuroticism": 0.65},
        "attachment": "anxious",
        "ace": 4,
        "schemas": ["讨好", "自我牺牲", "情感压抑"],
        "goal": "减少母亲的情绪勒索影响",
        "moral_stage": 4,
    },
    {
        "topic": "家庭关系",
        "client_issue": "我是家里的长子，弟弟妹妹都在上学。父亲去世后，家里的经济压力全落在我身上。我每个月工资大半寄回家，自己连女朋友都不敢谈。",
        "client_utterance": "上个月妹妹说想要一台新电脑上网课。我给了钱自己这个月房租都差点交不起。但我不给的话谁来给？",
        "client_name": "龙国栋",
        "client_personality": {"openness": 0.4, "conscientiousness": 0.8, "extraversion": 0.3, "agreeableness": 0.65, "neuroticism": 0.5},
        "attachment": "secure",
        "ace": 2,
        "schemas": ["自我牺牲", "情感压抑"],
        "goal": "在家庭责任和个人生活之间平衡",
        "moral_stage": 5,
    },
    # --- 追加案例: 人际关系 ---
    {
        "topic": "人际关系",
        "client_issue": "我在单位里是个老好人，谁叫我帮忙我都答应。但最近我发现，大家把我当成了理所当然的苦力，连谢谢都没有了。",
        "client_utterance": "今天又有三个同事让我帮忙。我说手上活有点多，他们说'你反正单身又没事'。我笑着答应了，但心里特别难过。",
        "client_name": "任嘉禾",
        "client_personality": {"openness": 0.45, "conscientiousness": 0.7, "extraversion": 0.4, "agreeableness": 0.85, "neuroticism": 0.6},
        "attachment": "anxious",
        "ace": 2,
        "schemas": ["讨好", "自我牺牲"],
        "goal": "学会拒绝而不感到内疚",
        "moral_stage": 3,
    },
    {
        "topic": "人际关系",
        "client_issue": "我觉得自己是个社交失败者。每次参加聚会我都不知道该说什么，站在那里很尴尬。看到别人谈笑风生，我更加紧张。",
        "client_utterance": "上周公司聚餐，我躲在洗手间待了二十分钟。出来后发现大家已经分组聊天了，我一个人坐在角落刷手机，假装很忙。",
        "client_name": "安静",
        "client_personality": {"openness": 0.35, "conscientiousness": 0.65, "extraversion": 0.15, "agreeableness": 0.65, "neuroticism": 0.8},
        "attachment": "avoidant",
        "ace": 2,
        "schemas": ["缺陷/羞耻", "社交孤立"],
        "goal": "减轻社交焦虑",
        "moral_stage": 3,
    },
    # --- 追加案例: 性 ---
    {
        "topic": "性",
        "client_issue": "我是无性恋者，但我不敢告诉任何人。朋友们聊到恋爱话题我就装死。家里催婚我每次都说'还没遇到合适的'。",
        "client_utterance": "昨天闺蜜神秘兮兮地给我推荐了一个'超级帅'的男生，我说我不感兴趣，她说'你是不是有问题'。我笑着说没有，但心里很痛。",
        "client_name": "秋棠",
        "client_personality": {"openness": 0.55, "conscientiousness": 0.5, "extraversion": 0.3, "agreeableness": 0.7, "neuroticism": 0.6},
        "attachment": "avoidant",
        "ace": 1,
        "schemas": ["缺陷/羞耻", "情感压抑"],
        "goal": "接纳自己的性取向",
        "moral_stage": 4,
    },
    # --- 追加案例: 职业 ---
    {
        "topic": "职业",
        "client_issue": "我在一家公司做了十年的行政，每天都做一样的事情。想转行但不知道自己能做什么。简历投出去完全没有回应。",
        "client_utterance": "今天去面试一家公司的运营岗位，面试官问'你懂数据分析吗'。我说我可以学，对方笑了笑。我知道那笑容的意思。",
        "client_name": "傅云霞",
        "client_personality": {"openness": 0.6, "conscientiousness": 0.7, "extraversion": 0.45, "agreeableness": 0.7, "neuroticism": 0.6},
        "attachment": "secure",
        "ace": 1,
        "schemas": ["失败", "情感压抑"],
        "goal": "成功转型到新行业",
        "moral_stage": 4,
    },
    {
        "topic": "职业",
        "client_issue": "我和上司有严重的冲突。他抢我的功劳、给我不合理的任务、还在其他人面前羞辱我。我想辞职，但又怕下一份工作更差。",
        "client_utterance": "今天他在全部门会议上说'我们团队有人能力跟不上'，然后看了我一眼。所有人都转头看我。我整场会议没敢抬头。",
        "client_name": "彭子豪",
        "client_personality": {"openness": 0.45, "conscientiousness": 0.7, "extraversion": 0.4, "agreeableness": 0.45, "neuroticism": 0.6},
        "attachment": "secure",
        "ace": 2,
        "schemas": ["不信任/虐待", "苛刻标准"],
        "goal": "在被尊重的环境中工作",
        "moral_stage": 4,
    },
    # --- 追加案例: 心理疾病 ---
    {
        "topic": "心理疾病",
        "client_issue": "我被诊断出双相情感障碍。躁狂期的时候我会疯狂消费、不睡觉、觉得自己无所不能。抑郁期的时候我觉得自己是个废物。药吃了又停。",
        "client_utterance": "上周躁狂发作，刷爆了两张信用卡，买了根本不用的东西。这周抑郁袭来，我觉得自己是个彻底的失败者，不配活在这个世界上。",
        "client_name": "纪嫣然",
        "client_personality": {"openness": 0.7, "conscientiousness": 0.3, "extraversion": 0.65, "agreeableness": 0.55, "neuroticism": 0.9},
        "attachment": "fearful_avoidant",
        "ace": 4,
        "schemas": ["缺陷/羞耻", "失败", "不稳定"],
        "goal": "坚持服药治疗，稳定情绪",
        "moral_stage": 3,
    },
    {
        "topic": "心理疾病",
        "client_issue": "我有边缘型人格障碍。我的人际关系总是大起大落，觉得一个人完美无缺到觉得他一文不值只需要一瞬间。我讨厌自己这样。",
        "client_utterance": "昨天男朋友半小时没回我消息，我就觉得他不爱我了，疯狂打了20个电话。他接起来说'你能不能正常一点'。我恨我自己。",
        "client_name": "郝思嘉",
        "client_personality": {"openness": 0.5, "conscientiousness": 0.35, "extraversion": 0.6, "agreeableness": 0.4, "neuroticism": 0.9},
        "attachment": "fearful_avoidant",
        "ace": 5,
        "schemas": ["不信任/虐待", "情感剥夺", "缺陷/羞耻"],
        "goal": "稳定情绪，改善人际关系模式",
        "moral_stage": 3,
    },
]


# 咨询师角色 — 固定几位
COUNSELORS = [
    {
        "name": "张敏华",
        "approach": "认知行为疗法",
        "specialization": ["情绪与压力", "自我成长", "心理疾病"],
        "personality": {"openness": 0.8, "conscientiousness": 0.75, "extraversion": 0.6, "agreeableness": 0.7, "neuroticism": 0.25},
    },
    {
        "name": "李明远",
        "approach": "心理动力学疗法",
        "specialization": ["家庭关系", "婚恋", "性"],
        "personality": {"openness": 0.7, "conscientiousness": 0.7, "extraversion": 0.5, "agreeableness": 0.65, "neuroticism": 0.3},
    },
    {
        "name": "王思睿",
        "approach": "人本主义疗法",
        "specialization": ["人际关系", "自我成长", "教育"],
        "personality": {"openness": 0.85, "conscientiousness": 0.65, "extraversion": 0.65, "agreeableness": 0.8, "neuroticism": 0.2},
    },
    {
        "name": "陈慧琳",
        "approach": "整合取向",
        "specialization": ["职业", "心理疾病", "情绪与压力"],
        "personality": {"openness": 0.75, "conscientiousness": 0.8, "extraversion": 0.55, "agreeableness": 0.75, "neuroticism": 0.3},
    },
]


def make_client_state(client: dict) -> dict:
    """构建求助者的 character_state。"""
    return {
        "name": client["client_name"],
        "personality": {
            "openness": client["client_personality"]["openness"],
            "conscientiousness": client["client_personality"]["conscientiousness"],
            "extraversion": client["client_personality"]["extraversion"],
            "agreeableness": client["client_personality"]["agreeableness"],
            "neuroticism": client["client_personality"]["neuroticism"],
            "attachment_style": client["attachment"],
            "defense_style": ["理智化", "压抑"] if client["ace"] >= 3 else ["幽默化"],
            "cognitive_biases": ["灾难化", "读心术"] if client["client_personality"]["neuroticism"] > 0.75 else [],
            "moral_stage": client["moral_stage"],
        },
        "trauma": {
            "ace_score": client["ace"],
            "active_schemas": client["schemas"],
            "trauma_triggers": ["被批评", "被忽视", "被抛弃"] if client["ace"] >= 3 else [],
        },
        "ideal_world": {},
        "motivation": {
            "current_goal": client["goal"],
        },
        "emotion_decay": {},
    }


def make_counselor_state(counselor: dict) -> dict:
    """构建咨询师的 character_state。"""
    return {
        "name": counselor["name"],
        "personality": {
            "openness": counselor["personality"]["openness"],
            "conscientiousness": counselor["personality"]["conscientiousness"],
            "extraversion": counselor["personality"]["extraversion"],
            "agreeableness": counselor["personality"]["agreeableness"],
            "neuroticism": counselor["personality"]["neuroticism"],
            "attachment_style": "secure",
            "defense_style": ["成熟防御"],
            "cognitive_biases": ["无显著偏差"],
            "moral_stage": 5,
        },
        "trauma": {"ace_score": 0, "active_schemas": [], "trauma_triggers": []},
        "ideal_world": {},
        "motivation": {"current_goal": f"帮助来访者——{counselor['approach']}"},
        "emotion_decay": {},
    }


def extract_cases(sample: int = 0) -> list[dict]:
    """从内置数据生成心理咨询验证用例。每个内置案例与不同咨询师组合生成 2 个用例。"""
    random.seed(42)
    cases = []
    case_counter = 0

    for idx, client in enumerate(BUILTIN_CASES):
        topic = client["topic"]

        # 分配咨询师（按专长匹配）
        suitable = [c for c in COUNSELORS if topic in c["specialization"]]
        if not suitable:
            suitable = COUNSELORS

        # 每个案例与 2 位不同咨询师组合；如果专长匹配不足则用全体
        counselors_to_use = list(suitable) if len(suitable) >= 2 else list(COUNSELORS)
        random.shuffle(counselors_to_use)
        counselors_to_use = counselors_to_use[:2]

        for counselor in counselors_to_use:
            # 构建完整对话上下文
            dialogue_context = (
                f"求助者({client['client_name']}): {client['client_issue']}\n"
                f"求助者: {client['client_utterance']}"
            )

            client_state = make_client_state(client)
            counselor_state = make_counselor_state(counselor)

            # L4 预期
            expected = {
                "gross_emotion_regulation": {
                    "detected_strategy": {"not_empty": True},
                    "effectiveness": {"min": 0.1},
                },
                "kohlberg_moral_reasoning": {
                    "moral_conflict": {"not_empty": True},
                },
                "maslow_need_stack": {
                    "current_dominant": {"min": 1, "max": 5},
                },
                "sdt_motivation_analysis": {
                    "most_threatened": {"not_empty": True},
                },
                "response_generator": {
                    "response_text": {"not_empty": True},
                },
            }

            # 高 ACE 添加创伤预期
            if client["ace"] >= 4:
                expected["ace_trauma_processing"] = {
                    "ace_activation": {"min": 0.3},
                }
                expected["young_schema_update"] = {
                    "affected_schemas": {"not_empty": True},
                }

            case = {
                "id": f"cpsy_{case_counter:04d}",
                "source": f"CPsyCoun — {topic}, 咨询师: {counselor['name']} ({counselor['approach']})",
                "domain": f"counseling/{topic}",
                "character_state": client_state,
                "event": {
                    "description": dialogue_context,
                    "type": "counseling",
                    "participants": [
                        {"name": client["client_name"], "role": "client", "relation": "求助者"},
                        {"name": counselor["name"], "role": "counselor", "relation": "咨询师"},
                    ],
                    "significance": 0.85,
                    "tags": ["counseling", topic, "心理治疗"],
                },
                "expected": expected,
                "_topic": topic,
                "_counselor": counselor["name"],
                "_ace": client["ace"],
                "_schemas": client["schemas"],
            }
            cases.append(case)
            case_counter += 1

    if sample > 0:
        random.shuffle(cases)
        cases = cases[:sample]

    return cases


def print_summary(cases: list[dict]):
    """打印统计摘要。"""
    print(f"Generated {len(cases)} CPsyCoun-derived cases\n")

    # 主题分布
    topic_counts = {}
    ace_buckets = {"0-2": 0, "3-4": 0, "5+": 0}
    for c in cases:
        t = c.get("_topic", "?")
        topic_counts[t] = topic_counts.get(t, 0) + 1
        ace = c.get("_ace", 0)
        if ace <= 2:
            ace_buckets["0-2"] += 1
        elif ace <= 4:
            ace_buckets["3-4"] += 1
        else:
            ace_buckets["5+"] += 1

    print(f"Topic distribution ({len(topic_counts)} topics):")
    for t, n in sorted(topic_counts.items(), key=lambda x: -x[1]):
        print(f"  {t}: {n}")

    print(f"\nACE score distribution:")
    for bucket, n in sorted(ace_buckets.items()):
        print(f"  {bucket}: {n}")

    # 咨询师分配
    counselors_used = set(c.get("_counselor", "?") for c in cases)
    print(f"\nCounselors used: {len(counselors_used)}")
    for cn in sorted(counselors_used):
        print(f"  {cn}")

    # 依恋风格分布
    attachment_counts = {}
    for c in cases:
        att = c["character_state"]["personality"]["attachment_style"]
        attachment_counts[att] = attachment_counts.get(att, 0) + 1
    print(f"\nAttachment style distribution:")
    for a, n in sorted(attachment_counts.items(), key=lambda x: -x[1]):
        print(f"  {a}: {n}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract CPsyCoun test cases")
    parser.add_argument("--sample", type=int, default=0, help="Number of cases to sample (0=all)")
    args = parser.parse_args()

    cases = extract_cases(sample=args.sample)
    print_summary(cases)

    out_path = OUTPUT_DIR / "cpsycound_cases.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(cases, f, ensure_ascii=False, indent=2)
    print(f"\nSaved to {out_path}")
