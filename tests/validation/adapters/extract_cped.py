"""从 CPED 数据集提取角色模拟验证用例。

CPED (Chinese Personalized and Emotional Dialogue Dataset):
12,000+ dialogues, 392 speakers from 40 Chinese TV dramas.
Labels: Big Five personality + 13 emotions + 19 dialogue acts per utterance.
来源: https://github.com/scutcyr/CPED (镜像: https://openi.pcl.ac.cn/xiaoxiong/xiaox202302031446558/datasets)

当数据集不可用时，生成 ~100 个内置代表性 fallback 用例。
"""
import argparse
import json
import os
import random
from pathlib import Path

_tmp = Path(os.environ.get("TEMP", "/tmp"))
DATASET_DIR = Path(os.environ.get("CPED_DIR", str(_tmp / "CPED")))
OUTPUT_DIR = Path(__file__).parent.parent / "fixtures"

# ---------------------------------------------------------------------------
# 10 个角色原型 — 不同的大五人格剖面
# ---------------------------------------------------------------------------
ARCHETYPES = [
    {
        "name": "赵明",
        "personality": {
            "openness": 0.65, "conscientiousness": 0.55,
            "extraversion": 0.80, "agreeableness": 0.75, "neuroticism": 0.30,
        },
        "attachment": "secure",
        "defense": ["humor", "intellectualization"],
        "biases": ["optimism_bias", "self_serving_bias"],
        "moral": 4,
        "ace": 0,
        "schemas": [],
        "triggers": [],
        "ideal_self": "做一个真诚可靠、能让身边人感到温暖的人。",
        "ideal_relations": "彼此信任、坦诚相待的关系。",
        "goal": "在工作上取得成绩，同时维护好身边的人际关系。",
        "traits_desc": "high_extraversion_high_agreeableness_low_neuroticism",
    },
    {
        "name": "李婷",
        "personality": {
            "openness": 0.35, "conscientiousness": 0.75,
            "extraversion": 0.25, "agreeableness": 0.60, "neuroticism": 0.80,
        },
        "attachment": "anxious",
        "defense": ["reaction_formation", "rumination"],
        "biases": ["catastrophizing", "confirmation_bias"],
        "moral": 3,
        "ace": 2,
        "schemas": ["abandonment", "vulnerability"],
        "triggers": ["被忽视", "不确定的等待", "对方语气冷淡"],
        "ideal_self": "成为一个足够好、不会被人抛弃的人。",
        "ideal_relations": "稳定、安全、可以被预测的关系。",
        "goal": "维持现有关系，避免被拒绝。",
        "traits_desc": "high_neuroticism_low_extraversion_high_conscientiousness",
    },
    {
        "name": "王刚",
        "personality": {
            "openness": 0.30, "conscientiousness": 0.80,
            "extraversion": 0.60, "agreeableness": 0.25, "neuroticism": 0.45,
        },
        "attachment": "avoidant",
        "defense": ["projection", "splitting"],
        "biases": ["fundamental_attribution_error", "authority_bias"],
        "moral": 4,
        "ace": 1,
        "schemas": ["mistrust"],
        "triggers": ["被质疑权威", "下属擅自做决定"],
        "ideal_self": "一个有威信、说一不二的人。",
        "ideal_relations": "层级分明、秩序井然的关系。",
        "goal": "巩固自己的职位和影响力。",
        "traits_desc": "low_agreeableness_high_conscientiousness_low_openness",
    },
    {
        "name": "陈静",
        "personality": {
            "openness": 0.50, "conscientiousness": 0.55,
            "extraversion": 0.50, "agreeableness": 0.85, "neuroticism": 0.25,
        },
        "attachment": "secure",
        "defense": ["altruism", "suppression"],
        "biases": ["optimism_bias", "hindsight_bias"],
        "moral": 4,
        "ace": 0,
        "schemas": [],
        "triggers": ["家人争吵"],
        "ideal_self": "一个温柔而坚强的人，能给家人带来安稳。",
        "ideal_relations": "和睦、充满支持的家庭关系。",
        "goal": "照顾好家人，维持家庭和睦。",
        "traits_desc": "high_agreeableness_low_neuroticism",
    },
    {
        "name": "周浩",
        "personality": {
            "openness": 0.85, "conscientiousness": 0.30,
            "extraversion": 0.60, "agreeableness": 0.50, "neuroticism": 0.65,
        },
        "attachment": "fearful_avoidant",
        "defense": ["sublimation", "acting_out"],
        "biases": ["illusion_of_uniqueness", "optimism_bias"],
        "moral": 3,
        "ace": 3,
        "schemas": ["emotional_deprivation", "defectiveness"],
        "triggers": ["作品被批评", "被人说「不切实际」"],
        "ideal_self": "一个不被世俗束缚、自由创作的艺术家。",
        "ideal_relations": "能够理解并欣赏自己才华的灵魂伴侣。",
        "goal": "完成一幅真正满意的作品。",
        "traits_desc": "high_openness_low_conscientiousness_high_neuroticism",
    },
    {
        "name": "孙悦",
        "personality": {
            "openness": 0.45, "conscientiousness": 0.85,
            "extraversion": 0.30, "agreeableness": 0.20, "neuroticism": 0.30,
        },
        "attachment": "avoidant",
        "defense": ["intellectualization", "isolation_of_affect"],
        "biases": ["fundamental_attribution_error", "just_world_hypothesis"],
        "moral": 5,
        "ace": 0,
        "schemas": [],
        "triggers": ["情绪化的表达", "不专业的做法"],
        "ideal_self": "一个理性客观、不被情绪左右的法律人。",
        "ideal_relations": "基于规则和理性的关系，不需要过多情感纠缠。",
        "goal": "打赢手上的案子。",
        "traits_desc": "low_agreeableness_high_conscientiousness_low_neuroticism_low_extraversion",
    },
    {
        "name": "刘洋",
        "personality": {
            "openness": 0.55, "conscientiousness": 0.30,
            "extraversion": 0.55, "agreeableness": 0.75, "neuroticism": 0.50,
        },
        "attachment": "secure",
        "defense": ["humor", "denial"],
        "biases": ["optimism_bias", "status_quo_bias"],
        "moral": 3,
        "ace": 0,
        "schemas": ["dependence"],
        "triggers": ["被催促"],
        "ideal_self": "一个活得轻松自在的人，不被压力压垮。",
        "ideal_relations": "轻松的、没有压力的友谊。",
        "goal": "顺利毕业，找份不太累的工作。",
        "traits_desc": "low_conscientiousness_high_agreeableness",
    },
    {
        "name": "吴芳",
        "personality": {
            "openness": 0.55, "conscientiousness": 0.80,
            "extraversion": 0.70, "agreeableness": 0.35, "neuroticism": 0.55,
        },
        "attachment": "anxious",
        "defense": ["sublimation", "compartmentalization"],
        "biases": ["self_serving_bias", "illusion_of_control"],
        "moral": 4,
        "ace": 1,
        "schemas": ["unrelenting_standards"],
        "triggers": ["项目延期", "下属工作马虎"],
        "ideal_self": "一个事业成功、独立自主的女性。",
        "ideal_relations": "平等但有边界的关系，对方也要有自己的追求。",
        "goal": "带领团队按时完成季度目标。",
        "traits_desc": "high_conscientiousness_high_extraversion_low_agreeableness",
    },
    {
        "name": "郑凯",
        "personality": {
            "openness": 0.25, "conscientiousness": 0.75,
            "extraversion": 0.20, "agreeableness": 0.65, "neuroticism": 0.35,
        },
        "attachment": "secure",
        "defense": ["suppression", "rationalization"],
        "biases": ["status_quo_bias", "hindsight_bias"],
        "moral": 4,
        "ace": 0,
        "schemas": [],
        "triggers": ["孩子不听话", "家庭经济问题"],
        "ideal_self": "一个稳重可靠、能撑起家的父亲。",
        "ideal_relations": "传统但和睦的家庭关系。",
        "goal": "给家人稳定的生活。",
        "traits_desc": "low_extraversion_high_conscientiousness_low_openness_low_neuroticism",
    },
    {
        "name": "林小雨",
        "personality": {
            "openness": 0.75, "conscientiousness": 0.35,
            "extraversion": 0.85, "agreeableness": 0.80, "neuroticism": 0.30,
        },
        "attachment": "secure",
        "defense": ["humor", "idealization"],
        "biases": ["optimism_bias", "halo_effect"],
        "moral": 3,
        "ace": 0,
        "schemas": [],
        "triggers": ["看到不公平的事"],
        "ideal_self": "一个永远保持好奇心和热情的人。",
        "ideal_relations": "真诚、有趣的朋友关系。",
        "goal": "体验更多新鲜有趣的事情。",
        "traits_desc": "high_extraversion_high_agreeableness_high_openness_low_conscientiousness",
    },
]

# ---------------------------------------------------------------------------
# 100 个场景模板（每个角色 10 个）
# ---------------------------------------------------------------------------
SCENARIOS = [
    # === 赵明 (0) ===
    {"char_idx": 0, "description": "我最好的朋友找我借了两万块说急用，说好一个月还，现在三个月过去了，他不但没还钱还躲着我。今天在商场撞见他正在买新款手机。", "domain": "friendship", "event_type": "conflict", "participants": [{"name": "张伟", "relation": "friend"}], "significance": 0.7, "emotion": "anger", "tags": ["money", "betrayal"]},
    {"char_idx": 0, "description": "我喜欢很久的女生终于答应和我约会了。我提前订好了她喜欢的餐厅，还买了一束她最爱的向日葵。今晚我要告诉她我的心意。", "domain": "romantic_intimate", "event_type": "social", "participants": [{"name": "小雅", "relation": "partner"}], "significance": 0.9, "emotion": "joy", "tags": ["confession", "date"]},
    {"char_idx": 0, "description": "下班看到小区门口有个老奶奶摔倒了，周围人来人往但没人敢扶。我赶紧跑过去把她扶起来，检查她有没有受伤。", "domain": "friendship", "event_type": "social", "participants": [], "significance": 0.4, "emotion": "trust", "tags": ["helping", "stranger"]},
    {"char_idx": 0, "description": "部门开会的时候，领导当着所有人的面说我上个月的方案做得不行，还说我不够用心。我觉得自己明明熬夜做了很久。", "domain": "workplace", "event_type": "conflict", "participants": [{"name": "领导", "relation": "colleague"}], "significance": 0.6, "emotion": "sadness", "tags": ["work", "criticism"]},
    {"char_idx": 0, "description": "女朋友因为一件小事跟我大吵一架，说我不在乎她，然后摔门走了。我其实很在乎她，只是不知道她为什么突然发这么大的火。", "domain": "romantic_conflict", "event_type": "conflict", "participants": [{"name": "女朋友", "relation": "partner"}], "significance": 0.8, "emotion": "sadness", "tags": ["argument", "relationship"]},
    {"char_idx": 0, "description": "周末去参加大学室友的婚礼，看到他们交换戒指的画面，我忍不住眼眶发热。这么多年的爱情终于修成正果了。", "domain": "friendship", "event_type": "social", "participants": [{"name": "室友", "relation": "friend"}], "significance": 0.5, "emotion": "joy", "tags": ["wedding", "celebration"]},
    {"char_idx": 0, "description": "我妈突然打电话来说我爸体检出了点问题，需要进一步检查。我一下子就慌了，拿着电话的手都在抖。", "domain": "family_daily", "event_type": "social", "participants": [{"name": "妈妈", "relation": "family"}], "significance": 0.85, "emotion": "fear", "tags": ["family", "health"]},
    {"char_idx": 0, "description": "公司年会抽奖，我居然中了头奖——一台最新款的笔记本电脑！我激动得直接从椅子上跳了起来。", "domain": "workplace", "event_type": "social", "participants": [], "significance": 0.4, "emotion": "joy", "tags": ["luck", "surprise"]},
    {"char_idx": 0, "description": "我那个总爱在背后说人坏话的同事，今天居然在聚餐时假装和我很要好。我看到他那副嘴脸就觉得恶心。", "domain": "workplace", "event_type": "conflict", "participants": [{"name": "同事", "relation": "colleague"}], "significance": 0.5, "emotion": "disgust", "tags": ["hypocrisy", "office_politics"]},
    {"char_idx": 0, "description": "我们几个好朋友约好了下个月一起去云南旅行，大家已经在群里讨论路线和美食了。我已经开始幻想在洱海边骑行的感觉了。", "domain": "friendship", "event_type": "social", "participants": [{"name": "朋友们", "relation": "friend"}], "significance": 0.5, "emotion": "anticipation", "tags": ["travel", "planning"]},

    # === 李婷 (1) ===
    {"char_idx": 1, "description": "男朋友今天一整天都没回我消息，我给他打了三个电话也没接。我脑子里一直在想他是不是出事了，还是他不想理我了。", "domain": "romantic_intimate", "event_type": "conflict", "participants": [{"name": "男朋友", "relation": "partner"}], "significance": 0.8, "emotion": "fear", "tags": ["anxiety", "attachment"]},
    {"char_idx": 1, "description": "同事们在群里聊天，我发现他们昨天聚餐没有叫我。我反复看了好几遍聊天记录，确认自己没有看错。他们是不是不喜欢我？", "domain": "workplace", "event_type": "social", "participants": [{"name": "同事们", "relation": "colleague"}], "significance": 0.6, "emotion": "sadness", "tags": ["exclusion", "social_anxiety"]},
    {"char_idx": 1, "description": "妈妈又催我找对象了，说隔壁家的女儿都二胎了。我知道她是为我好，但我就是控制不住地烦躁和委屈。", "domain": "family_daily", "event_type": "conflict", "participants": [{"name": "妈妈", "relation": "family"}], "significance": 0.6, "emotion": "anger", "tags": ["family_pressure", "dating"]},
    {"char_idx": 1, "description": "男朋友终于回我消息了，说他在开会手机静音了。还发了一张自拍证明。我松了一口气，但又觉得自己是不是太敏感了。", "domain": "romantic_intimate", "event_type": "social", "participants": [{"name": "男朋友", "relation": "partner"}], "significance": 0.7, "emotion": "trust", "tags": ["reassurance", "attachment"]},
    {"char_idx": 1, "description": "今天在公司做一个重要的汇报，PPT翻页的时候我发现有一组数据算错了。我的脸一下子就红了，感觉所有人都盯着我。", "domain": "workplace", "event_type": "social", "participants": [{"name": "领导和同事", "relation": "colleague"}], "significance": 0.7, "emotion": "fear", "tags": ["mistake", "shame"]},
    {"char_idx": 1, "description": "闺蜜告诉我她周末要订婚了，还邀请我去做伴娘。我真心为她高兴，但心里又有点酸——什么时候才能轮到我呢？", "domain": "friendship", "event_type": "social", "participants": [{"name": "闺蜜", "relation": "friend"}], "significance": 0.5, "emotion": "joy", "tags": ["engagement", "mixed_feelings"]},
    {"char_idx": 1, "description": "路过以前被人堵过的那个巷子口，我的心跳突然加快，手心开始出汗。虽然已经过去很久了，但那种恐惧感还是那么清晰。", "domain": "friendship", "event_type": "social", "participants": [], "significance": 0.9, "emotion": "fear", "tags": ["trauma", "trigger"]},
    {"char_idx": 1, "description": "我发现我最好的朋友最近和我讨厌的那个人走得很近，她们还在朋友圈发了合照。我觉得自己被背叛了。", "domain": "friendship", "event_type": "conflict", "participants": [{"name": "好朋友", "relation": "friend"}], "significance": 0.7, "emotion": "anger", "tags": ["betrayal", "jealousy"]},
    {"char_idx": 1, "description": "体检报告出来了，有一个指标异常。虽然医生说不一定有问题，但我觉得天都塌了，满脑子都是最坏的可能。", "domain": "family_daily", "event_type": "social", "participants": [], "significance": 0.85, "emotion": "fear", "tags": ["health_anxiety", "catastrophizing"]},
    {"char_idx": 1, "description": "今天下班时发现有人在我桌上放了一杯奶茶和一张纸条，写着「最近辛苦了」。不知道是谁放的，但这个小小的善意让我差点哭出来。", "domain": "workplace", "event_type": "social", "participants": [], "significance": 0.4, "emotion": "surprise", "tags": ["kindness", "unexpected"]},

    # === 王刚 (2) ===
    {"char_idx": 2, "description": "新来的下属没有经过我同意就直接改了我的项目方案，还越级汇报给了副总。这完全是在挑战我的权威。", "domain": "workplace", "event_type": "conflict", "participants": [{"name": "下属小刘", "relation": "colleague"}], "significance": 0.85, "emotion": "anger", "tags": ["authority", "insubordination"]},
    {"char_idx": 2, "description": "老婆说我最近在家太强势了，让我改改脾气。我觉得我在公司压力那么大，回家还不能放松一下吗？", "domain": "family_daily", "event_type": "conflict", "participants": [{"name": "妻子", "relation": "family"}], "significance": 0.5, "emotion": "anger", "tags": ["family", "temper"]},
    {"char_idx": 2, "description": "竞争对手公司在挖我的人，还说我的团队管理方式过时了。简直可笑，我带团队的时候他们还没入行呢。", "domain": "workplace", "event_type": "conflict", "participants": [], "significance": 0.7, "emotion": "anger", "tags": ["competition", "professional"]},
    {"char_idx": 2, "description": "儿子说要休学去创业，搞什么互联网项目。我一听就火了——不好好读书尽想这些有的没的，太不务正业了。", "domain": "family_daily", "event_type": "conflict", "participants": [{"name": "儿子", "relation": "family"}], "significance": 0.8, "emotion": "anger", "tags": ["parenting", "career"]},
    {"char_idx": 2, "description": "公司年会我拿了优秀管理者奖，领导在台上表扬了我这一年的成绩。得到认可的感觉确实不错。", "domain": "workplace", "event_type": "social", "participants": [{"name": "公司领导", "relation": "colleague"}], "significance": 0.6, "emotion": "joy", "tags": ["recognition", "achievement"]},
    {"char_idx": 2, "description": "我带的项目突然被公司叫停了，说是资金链出问题。我花了半年心血——就这么说停就停了？", "domain": "workplace", "event_type": "conflict", "participants": [], "significance": 0.85, "emotion": "sadness", "tags": ["setback", "frustration"]},
    {"char_idx": 2, "description": "多年不见的老战友突然联系我，说要来我的城市出差。我二话不说就订了最好的饭店，准备好好招待他。", "domain": "friendship", "event_type": "social", "participants": [{"name": "老战友", "relation": "friend"}], "significance": 0.5, "emotion": "anticipation", "tags": ["reunion", "comradeship"]},
    {"char_idx": 2, "description": "在停车场有人刮了我的车想跑，我一把揪住他。这种人就是欠教训，做了错事就想溜？", "domain": "friendship", "event_type": "conflict", "participants": [], "significance": 0.4, "emotion": "anger", "tags": ["injustice", "confrontation"]},
    {"char_idx": 2, "description": "听说当年和我一起入伍的老张现在都当上处长了，而我还在这个位置不上不下。心里不是滋味。", "domain": "friendship", "event_type": "social", "participants": [{"name": "老张", "relation": "friend"}], "significance": 0.6, "emotion": "sadness", "tags": ["comparison", "regret"]},
    {"char_idx": 2, "description": "女儿给我织了一条围巾当生日礼物，针脚歪歪扭扭的，但她说织了一个月。我嘴上说「织得什么玩意儿」，但心里挺暖的。", "domain": "family_daily", "event_type": "social", "participants": [{"name": "女儿", "relation": "family"}], "significance": 0.5, "emotion": "joy", "tags": ["family", "gift"]},

    # === 陈静 (3) ===
    {"char_idx": 3, "description": "老公最近天天加班到很晚回家，我给他留的饭菜他都说吃过了。我知道他工作忙，但还是有点担心他的身体。", "domain": "family_daily", "event_type": "social", "participants": [{"name": "丈夫", "relation": "family"}], "significance": 0.5, "emotion": "sadness", "tags": ["marriage", "concern"]},
    {"char_idx": 3, "description": "邻居家的小孩天天来我家玩，今天他不小心打碎了我最喜欢的花瓶。看着地上碎片我愣住了，但还是先问他有没有受伤。", "domain": "friendship", "event_type": "social", "participants": [{"name": "邻居小孩", "relation": "friend"}], "significance": 0.3, "emotion": "surprise", "tags": ["accident", "kindness"]},
    {"char_idx": 3, "description": "婆婆来家里住了几天，一直在挑我的毛病，说我做的菜太淡、家里不够干净。我什么都没说，但心里挺委屈的。", "domain": "family_daily", "event_type": "conflict", "participants": [{"name": "婆婆", "relation": "family"}], "significance": 0.6, "emotion": "sadness", "tags": ["in_law", "criticism"]},
    {"char_idx": 3, "description": "女儿考上了重点大学，第一时间给我打电话报喜。听到她兴奋的声音，我忍不住在电话这头哭了——我为她骄傲。", "domain": "family_daily", "event_type": "social", "participants": [{"name": "女儿", "relation": "family"}], "significance": 0.9, "emotion": "joy", "tags": ["pride", "achievement"]},
    {"char_idx": 3, "description": "今天在菜市场看到一个流浪汉在垃圾桶里翻吃的，我买了两个包子递给他。他抬头看我的眼神让我一整天都忘不了。", "domain": "friendship", "event_type": "social", "participants": [], "significance": 0.4, "emotion": "trust", "tags": ["compassion", "helping"]},
    {"char_idx": 3, "description": "老公偷偷订了我们去云南的旅行，说结婚十周年要给我一个惊喜。这个木头人居然还有这么浪漫的一面。", "domain": "romantic_intimate", "event_type": "social", "participants": [{"name": "丈夫", "relation": "partner"}], "significance": 0.8, "emotion": "joy", "tags": ["surprise", "anniversary"]},
    {"char_idx": 3, "description": "儿子在学校被同学欺负了，回家也不肯说，躲在房间里哭。我轻轻敲他的门，心里像刀割一样。", "domain": "family_daily", "event_type": "social", "participants": [{"name": "儿子", "relation": "family"}], "significance": 0.85, "emotion": "sadness", "tags": ["parenting", "bullying"]},
    {"char_idx": 3, "description": "朋友跟她老公闹离婚，半夜哭着给我打电话。我一边安慰她一边给她叫了车来我家住。", "domain": "friendship", "event_type": "social", "participants": [{"name": "朋友", "relation": "friend"}], "significance": 0.6, "emotion": "sadness", "tags": ["comfort", "marriage_crisis"]},
    {"char_idx": 3, "description": "小区里有人遛狗不牵绳，大狗朝我扑过来，虽然没咬到但我吓得魂都快没了。主人还在旁边说「它不咬人」。", "domain": "family_daily", "event_type": "conflict", "participants": [], "significance": 0.5, "emotion": "fear", "tags": ["safety", "anger"]},
    {"char_idx": 3, "description": "早上给全家人做了丰盛的早餐，看着老公和孩子们吃得开心的样子，我觉得这就是我想要的生活。", "domain": "family_daily", "event_type": "social", "participants": [{"name": "家人", "relation": "family"}], "significance": 0.4, "emotion": "joy", "tags": ["daily_life", "contentment"]},

    # === 周浩 (4) ===
    {"char_idx": 4, "description": "我的画展今天开幕了，来了不少人。但有个评论家当着我的面说我的作品「形式大于内容，缺乏深度」。我攥紧了拳头。", "domain": "friendship", "event_type": "conflict", "participants": [{"name": "评论家", "relation": "stranger"}], "significance": 0.85, "emotion": "anger", "tags": ["criticism", "art"]},
    {"char_idx": 4, "description": "半夜灵感来了，我从床上一跃而起开始画画，一直画到天亮。虽然很累，但那种创造的快感让我兴奋得发抖。", "domain": "friendship", "event_type": "social", "participants": [], "significance": 0.7, "emotion": "joy", "tags": ["creation", "inspiration"]},
    {"char_idx": 4, "description": "女朋友说受不了我的不稳定，跟我提了分手。她说她需要的是一个能给她安全感的人，而不是一个艺术家。", "domain": "romantic_conflict", "event_type": "conflict", "participants": [{"name": "前女友", "relation": "partner"}], "significance": 0.9, "emotion": "sadness", "tags": ["breakup", "heartbreak"]},
    {"char_idx": 4, "description": "爸妈又打电话催我找份正经工作，说画画养活不了自己。我不想跟他们吵，但也不想妥协。为什么就不能理解我呢？", "domain": "family_daily", "event_type": "conflict", "participants": [{"name": "父母", "relation": "family"}], "significance": 0.7, "emotion": "anger", "tags": ["family_conflict", "career"]},
    {"char_idx": 4, "description": "在798艺术区看到一个装置艺术，那种震撼感让我久久说不出话来。原来艺术还可以这样做。", "domain": "friendship", "event_type": "social", "participants": [], "significance": 0.6, "emotion": "surprise", "tags": ["art", "inspiration"]},
    {"char_idx": 4, "description": "一个画廊老板看中了我的作品，说要给我办个展。我感觉自己这么多年的坚持终于有了一点回应。", "domain": "friendship", "event_type": "social", "participants": [{"name": "画廊老板", "relation": "friend"}], "significance": 0.8, "emotion": "joy", "tags": ["recognition", "breakthrough"]},
    {"char_idx": 4, "description": "半夜一个人在天台上喝酒看星星，想起小时候在乡下的夏天。那时候的天空也是这么美，但人已经不在了。", "domain": "friendship", "event_type": "social", "participants": [], "significance": 0.5, "emotion": "sadness", "tags": ["nostalgia", "loneliness"]},
    {"char_idx": 4, "description": "隔壁装修的电钻声吵得我完全没法集中精力画画。我已经忍了一个星期了，今天终于爆发了，冲过去砸了他们家的门。", "domain": "friendship", "event_type": "conflict", "participants": [{"name": "邻居", "relation": "stranger"}], "significance": 0.4, "emotion": "anger", "tags": ["frustration", "noise"]},
    {"char_idx": 4, "description": "在网上看到一篇关于梵高的文章，读到他在疯人院里还在画画的部分，我忍不住哭了。我觉得我懂他。", "domain": "friendship", "event_type": "social", "participants": [], "significance": 0.6, "emotion": "sadness", "tags": ["art", "empathy"]},
    {"char_idx": 4, "description": "朋友拉我去参加一个音乐节，现场的气氛太棒了。我跟陌生人一起跳一起唱，感觉所有烦恼都消失了。", "domain": "friendship", "event_type": "social", "participants": [{"name": "朋友们", "relation": "friend"}], "significance": 0.5, "emotion": "joy", "tags": ["music", "freedom"]},

    # === 孙悦 (5) ===
    {"char_idx": 5, "description": "今天开庭，对方律师提交了一份我没想到的证据。我表面镇定，但脑子里在飞速运转寻找对策。", "domain": "workplace", "event_type": "social", "participants": [{"name": "对方律师", "relation": "colleague"}], "significance": 0.8, "emotion": "surprise", "tags": ["court", "strategy"]},
    {"char_idx": 5, "description": "助理把一份重要的合同条款弄错了，差点让公司损失几百万。我严厉地批评了她，告诉她这个行业容不得马虎。", "domain": "workplace", "event_type": "conflict", "participants": [{"name": "助理", "relation": "colleague"}], "significance": 0.7, "emotion": "anger", "tags": ["mistake", "professionalism"]},
    {"char_idx": 5, "description": "当事人突然在办公室里崩溃大哭，说不想活了。我递给她纸巾，等她情绪稳定后帮她分析了法律上的最优解。情绪解决不了问题。", "domain": "workplace", "event_type": "social", "participants": [{"name": "当事人", "relation": "colleague"}], "significance": 0.6, "emotion": "trust", "tags": ["client", "crisis"]},
    {"char_idx": 5, "description": "前男友结婚给我发了请柬。我们分手五年了，我早就放下了。不过去还是不去呢？去了显得我还在意，不去显得我放不下。", "domain": "friendship", "event_type": "social", "participants": [{"name": "前男友", "relation": "friend"}], "significance": 0.4, "emotion": "sadness", "tags": ["past", "ambivalence"]},
    {"char_idx": 5, "description": "法官在庭上采纳了我的辩护意见，这个案子我赢了。走出法院的时候，我在台阶上站了一会儿，深吸了一口气。", "domain": "workplace", "event_type": "social", "participants": [], "significance": 0.8, "emotion": "joy", "tags": ["victory", "justice"]},
    {"char_idx": 5, "description": "同事在背后说我冷血无情，说我对当事人没有同理心。我听到了，但懒得解释——我的职责是维护法律权益，不是当心理医生。", "domain": "workplace", "event_type": "conflict", "participants": [{"name": "同事", "relation": "colleague"}], "significance": 0.5, "emotion": "disgust", "tags": ["gossip", "reputation"]},
    {"char_idx": 5, "description": "母亲打电话来说身体不太舒服，让我抽空回家看看。我答应着挂了电话，心里有点愧疚——已经三个月没回去了。", "domain": "family_daily", "event_type": "social", "participants": [{"name": "母亲", "relation": "family"}], "significance": 0.6, "emotion": "sadness", "tags": ["family", "guilt"]},
    {"char_idx": 5, "description": "看到一个同行为了出名在社交媒体上编造案情博眼球。这种不专业的行为让我非常反感，法律不是儿戏。", "domain": "workplace", "event_type": "conflict", "participants": [], "significance": 0.4, "emotion": "disgust", "tags": ["unethical", "professional"]},
    {"char_idx": 5, "description": "当事人的孩子给我画了一幅画，上面写着「谢谢姐姐帮妈妈」。我把画放在办公桌上了，虽然脸上没什么表情。", "domain": "workplace", "event_type": "social", "participants": [], "significance": 0.4, "emotion": "joy", "tags": ["gratitude", "meaningful"]},
    {"char_idx": 5, "description": "发现律所合伙人私下接案不入账，这涉及严重的职业道德问题。我在考虑是否要向律师协会举报。", "domain": "workplace", "event_type": "moral_choice", "participants": [{"name": "合伙人", "relation": "colleague"}], "significance": 0.85, "emotion": "anger", "tags": ["ethics", "whistleblowing"]},

    # === 刘洋 (6) ===
    {"char_idx": 6, "description": "导师说我的论文初稿不行，要大改。我已经拖了两个星期了，每次打开电脑就忍不住刷手机。", "domain": "friendship", "event_type": "social", "participants": [{"name": "导师", "relation": "colleague"}], "significance": 0.6, "emotion": "sadness", "tags": ["procrastination", "academic"]},
    {"char_idx": 6, "description": "室友叫我去打篮球，虽然我还有很多作业没写，但我还是去了。先玩再说嘛，作业晚上赶一赶就好了。", "domain": "friendship", "event_type": "social", "participants": [{"name": "室友", "relation": "friend"}], "significance": 0.3, "emotion": "joy", "tags": ["sports", "friendship"]},
    {"char_idx": 6, "description": "在食堂吃饭的时候，看到一个女生端着餐盘找不到座位。我主动挪了个位置给她，她冲我笑了笑。", "domain": "friendship", "event_type": "social", "participants": [{"name": "陌生女生", "relation": "stranger"}], "significance": 0.2, "emotion": "trust", "tags": ["kindness", "daily"]},
    {"char_idx": 6, "description": "期末考试还有三天，我书还没看完。但兄弟叫我开黑打游戏，我纠结了三十秒就打开了游戏。", "domain": "friendship", "event_type": "social", "participants": [{"name": "兄弟们", "relation": "friend"}], "significance": 0.5, "emotion": "joy", "tags": ["procrastination", "gaming"]},
    {"char_idx": 6, "description": "跟我合租的哥们说他要搬走了，因为他女朋友要过来一起住。我又得去找新室友了，好麻烦啊。", "domain": "friendship", "event_type": "social", "participants": [{"name": "合租室友", "relation": "friend"}], "significance": 0.4, "emotion": "sadness", "tags": ["change", "annoyance"]},
    {"char_idx": 6, "description": "刷到一个公益广告，说山区孩子没有像样的教室。我心里挺难受的，捐了五十块钱。不多，但算一点心意。", "domain": "friendship", "event_type": "social", "participants": [], "significance": 0.3, "emotion": "sadness", "tags": ["empathy", "charity"]},
    {"char_idx": 6, "description": "女朋友说我太不上进了，整天就知道玩。她说她看不到未来。我开始慌了——我是不是真的要改变一下了？", "domain": "romantic_conflict", "event_type": "conflict", "participants": [{"name": "女朋友", "relation": "partner"}], "significance": 0.8, "emotion": "fear", "tags": ["relationship", "self_doubt"]},
    {"char_idx": 6, "description": "今天在街上看到有人卖艺，弹吉他唱得特别好听。我在那儿站了半小时，最后把口袋里的零钱都放进去了。", "domain": "friendship", "event_type": "social", "participants": [], "significance": 0.2, "emotion": "joy", "tags": ["music", "street_performance"]},
    {"char_idx": 6, "description": "我爸打电话来问我最近学习怎么样，我支支吾吾说还行。挂了电话有点心虚——我连作业都没交几次。", "domain": "family_daily", "event_type": "social", "participants": [{"name": "爸爸", "relation": "family"}], "significance": 0.5, "emotion": "fear", "tags": ["family", "guilt"]},
    {"char_idx": 6, "description": "看到大四学长拿到大厂offer请客吃饭，我也有点羡慕。但转念一想——算了，先享受大学生活吧，工作的事以后再说。", "domain": "friendship", "event_type": "social", "participants": [], "significance": 0.4, "emotion": "anticipation", "tags": ["future", "career"]},

    # === 吴芳 (7) ===
    {"char_idx": 7, "description": "项目上线前发现测试组漏报了一个严重的bug，现在要延期两天。我把测试经理叫到办公室，问他到底有没有认真干活。", "domain": "workplace", "event_type": "conflict", "participants": [{"name": "测试经理", "relation": "colleague"}], "significance": 0.8, "emotion": "anger", "tags": ["deadline", "blame"]},
    {"char_idx": 7, "description": "竞争对手公司挖我，开了双倍薪资。虽然很诱人，但我在这个团队付出了这么多，不是说走就能走的。", "domain": "workplace", "event_type": "moral_choice", "participants": [], "significance": 0.7, "emotion": "anticipation", "tags": ["career", "loyalty"]},
    {"char_idx": 7, "description": "今天做报告的时候，大老板特意表扬了我们团队的效率。我表面上很平静，但心里还是挺得意的。", "domain": "workplace", "event_type": "social", "participants": [{"name": "大老板", "relation": "colleague"}], "significance": 0.6, "emotion": "joy", "tags": ["recognition", "achievement"]},
    {"char_idx": 7, "description": "男朋友说我又在加班，抱怨我把工作看得比他重要。我不理解——我不努力工作，我们以后怎么生活？", "domain": "romantic_conflict", "event_type": "conflict", "participants": [{"name": "男朋友", "relation": "partner"}], "significance": 0.7, "emotion": "anger", "tags": ["work_life_balance", "argument"]},
    {"char_idx": 7, "description": "一个下属在会议上提出了一个很有创意的方案，角度很新颖。虽然和我最初的想法不一样，但我决定让他试试。", "domain": "workplace", "event_type": "social", "participants": [{"name": "下属", "relation": "colleague"}], "significance": 0.5, "emotion": "trust", "tags": ["innovation", "leadership"]},
    {"char_idx": 7, "description": "妹妹高考成绩出来了，比预期低了三十多分。她把自己关在房间里不出来。我想安慰她，但也不知道说什么好。", "domain": "family_daily", "event_type": "social", "participants": [{"name": "妹妹", "relation": "family"}], "significance": 0.6, "emotion": "sadness", "tags": ["family", "disappointment"]},
    {"char_idx": 7, "description": "发现财务部的人在报销上做手脚，涉及金额不小。这种事不能忍，我直接发了邮件给CEO。", "domain": "workplace", "event_type": "conflict", "participants": [{"name": "财务部同事", "relation": "colleague"}], "significance": 0.85, "emotion": "anger", "tags": ["integrity", "whistleblowing"]},
    {"char_idx": 7, "description": "去健身房锻炼了一个月，今天发现体重真的掉了三斤。有效果就有动力，我决定再请个私教。", "domain": "friendship", "event_type": "social", "participants": [], "significance": 0.3, "emotion": "joy", "tags": ["health", "self_improvement"]},
    {"char_idx": 7, "description": "闺蜜的创业公司融资成功了，请我吃饭庆祝。我真心为她高兴，但也在想——我是不是也该自己出来干？", "domain": "friendship", "event_type": "social", "participants": [{"name": "闺蜜", "relation": "friend"}], "significance": 0.5, "emotion": "joy", "tags": ["success", "inspiration"]},
    {"char_idx": 7, "description": "今天在地铁上看到有人晕倒了，周围人都在拍视频没人管。我冲过去帮忙做急救，直到救护车来。", "domain": "friendship", "event_type": "social", "participants": [], "significance": 0.5, "emotion": "fear", "tags": ["emergency", "bravery"]},

    # === 郑凯 (8) ===
    {"char_idx": 8, "description": "女儿期末考试成绩退步了很多，老师说她在课堂上讲话。我坐在沙发上抽了一根烟，想着怎么跟她谈。", "domain": "family_daily", "event_type": "social", "participants": [{"name": "女儿", "relation": "family"}], "significance": 0.6, "emotion": "sadness", "tags": ["parenting", "education"]},
    {"char_idx": 8, "description": "工厂说下个月可能要裁员，我在这干了十几年了。老张已经被约谈了，下一个会不会是我？", "domain": "workplace", "event_type": "social", "participants": [{"name": "老张", "relation": "colleague"}], "significance": 0.85, "emotion": "fear", "tags": ["job_security", "economic"]},
    {"char_idx": 8, "description": "老婆突然说想出去旅游，结婚二十年她一直操持家里没怎么出过门。我嘴上说「花那个钱干嘛」，但私底下已经让女儿帮忙订票了。", "domain": "family_daily", "event_type": "social", "participants": [{"name": "妻子", "relation": "family"}], "significance": 0.5, "emotion": "joy", "tags": ["family", "surprise"]},
    {"char_idx": 8, "description": "儿子跟同学打架了，老师叫我去学校。我到了之后先给老师道歉，然后看着儿子问「怎么回事」——他眼睛红红的。", "domain": "family_daily", "event_type": "conflict", "participants": [{"name": "儿子", "relation": "family"}], "significance": 0.6, "emotion": "anger", "tags": ["parenting", "school"]},
    {"char_idx": 8, "description": "在超市排队结账的时候，有人插队站到了我前面。我没说话，但心里很不舒服。后面一个小姑娘替我说话了。", "domain": "friendship", "event_type": "conflict", "participants": [], "significance": 0.3, "emotion": "anger", "tags": ["injustice", "daily"]},
    {"char_idx": 8, "description": "爸爸的坟前长满了草，我跪在那里拔了一个下午。妈走了以后，这个家就越来越散了。", "domain": "family_daily", "event_type": "social", "participants": [], "significance": 0.7, "emotion": "sadness", "tags": ["grief", "family"]},
    {"char_idx": 8, "description": "女儿做了晚饭等我回家，虽然番茄炒蛋咸了，但我吃了两碗饭。她高兴得跟什么似的。", "domain": "family_daily", "event_type": "social", "participants": [{"name": "女儿", "relation": "family"}], "significance": 0.4, "emotion": "joy", "tags": ["family", "simple_joy"]},
    {"char_idx": 8, "description": "邻居老李突发心梗走了，早上还跟我打过招呼。生命真的太脆弱了，我在他的灵前站了很久。", "domain": "friendship", "event_type": "social", "participants": [{"name": "邻居老李", "relation": "friend"}], "significance": 0.7, "emotion": "sadness", "tags": ["death", "mortality"]},
    {"char_idx": 8, "description": "儿子说他想报考外地的大学，离家很远。我沉默了半天说「你自己决定吧」。其实我不想让他走太远。", "domain": "family_daily", "event_type": "social", "participants": [{"name": "儿子", "relation": "family"}], "significance": 0.7, "emotion": "sadness", "tags": ["parenting", "empty_nest"]},
    {"char_idx": 8, "description": "发工资了，比上个月多了两百块。我存到家庭账户里，给老婆发了条消息说「这个月多了一点，给妈买点药」。", "domain": "family_daily", "event_type": "social", "participants": [{"name": "妻子", "relation": "family"}], "significance": 0.3, "emotion": "trust", "tags": ["family", "responsibility"]},

    # === 林小雨 (9) ===
    {"char_idx": 9, "description": "今天在社团招新，我拉着每一个路过的人热情介绍我们摄影社。一个学妹被我的热情感染了，当场填了报名表。", "domain": "friendship", "event_type": "social", "participants": [{"name": "学妹", "relation": "stranger"}], "significance": 0.3, "emotion": "joy", "tags": ["campus", "enthusiasm"]},
    {"char_idx": 9, "description": "看到有人在虐待流浪猫，我冲上去就跟他吵起来了。怎么会有这么残忍的人？我拍了视频说要发到网上曝光他。", "domain": "friendship", "event_type": "conflict", "participants": [], "significance": 0.6, "emotion": "anger", "tags": ["animal_abuse", "justice"]},
    {"char_idx": 9, "description": "暗恋的学长在图书馆主动坐到了我对面，还问我借了一支笔。我的心跳快得像打鼓，一个字都看不进去了。", "domain": "romantic_intimate", "event_type": "social", "participants": [{"name": "学长", "relation": "partner"}], "significance": 0.6, "emotion": "joy", "tags": ["crush", "butterflies"]},
    {"char_idx": 9, "description": "周末和朋友们去游乐园玩过山车，我全程尖叫大笑。下来之后腿都软了，但马上又去排下一个项目。", "domain": "friendship", "event_type": "social", "participants": [{"name": "朋友们", "relation": "friend"}], "significance": 0.4, "emotion": "joy", "tags": ["adventure", "fun"]},
    {"char_idx": 9, "description": "参加了学校的摄影比赛，我的作品《黄昏下的老街》居然拿了一等奖。我站在领奖台上笑得合不拢嘴。", "domain": "friendship", "event_type": "social", "participants": [], "significance": 0.7, "emotion": "joy", "tags": ["achievement", "photography"]},
    {"char_idx": 9, "description": "今天在公交车上看到一个小偷偷东西，我大喊了一声「有小偷」。全车人都看向我，小偷瞪了我一眼在下一站下车了。", "domain": "friendship", "event_type": "conflict", "participants": [], "significance": 0.5, "emotion": "fear", "tags": ["bravery", "justice"]},
    {"char_idx": 9, "description": "最好朋友突然说要转学到另一个城市，以后不能天天见面了。我抱着她哭了一场。", "domain": "friendship", "event_type": "social", "participants": [{"name": "好朋友", "relation": "friend"}], "significance": 0.7, "emotion": "sadness", "tags": ["goodbye", "friendship"]},
    {"char_idx": 9, "description": "在路边看到一个卖手工艺品的老奶奶，她做的布娃娃好可爱。我买了一个，还跟她聊了半小时天。她说我让她想起了孙女。", "domain": "friendship", "event_type": "social", "participants": [{"name": "老奶奶", "relation": "stranger"}], "significance": 0.3, "emotion": "trust", "tags": ["kindness", "connection"]},
    {"char_idx": 9, "description": "下周就是校园歌手大赛了，我报名了。这几天一直在宿舍练歌，室友说我跑调但我不管——开心就好！", "domain": "friendship", "event_type": "social", "participants": [], "significance": 0.4, "emotion": "anticipation", "tags": ["competition", "fun"]},
    {"char_idx": 9, "description": "妈妈给我寄了一箱家乡的橘子，打开箱子的那一刻那种熟悉的香味让我鼻子一酸。好想家啊。", "domain": "family_daily", "event_type": "social", "participants": [{"name": "妈妈", "relation": "family"}], "significance": 0.4, "emotion": "sadness", "tags": ["homesick", "family"]},
]

# ---------------------------------------------------------------------------
# 人格特质 → 预期断言映射
# ---------------------------------------------------------------------------
TRAIT_EXPECTED = {
    "neuroticism_high": {
        "big_five_analysis": {
            "emotional_reactivity": {"min": 0.5},
            "interpretation_direction": {"in": ["negative", "threat"]},
        },
    },
    "neuroticism_low": {
        "big_five_analysis": {
            "emotional_reactivity": {"max": 0.5},
            "emotional_stability": {"min": 0.5},
        },
    },
    "extraversion_high": {
        "big_five_analysis": {
            "social_approach": {"in": ["approach", "outgoing", "expressive", "warm"]},
        },
    },
    "extraversion_low": {
        "big_five_analysis": {
            "social_approach": {"in": ["reserved", "withdraw", "avoid", "quiet"]},
        },
    },
    "agreeableness_high": {
        "big_five_analysis": {
            "social_approach": {"in": ["cooperative", "accommodating", "warm", "helping"]},
        },
    },
    "agreeableness_low": {
        "big_five_analysis": {
            "social_approach": {"in": ["confrontational", "competitive", "skeptical", "assertive"]},
        },
    },
    "conscientiousness_high": {
        "big_five_analysis": {
            "decision_style": {"in": ["deliberate", "cautious", "planful", "organized"]},
        },
    },
    "conscientiousness_low": {
        "big_five_analysis": {
            "decision_style": {"in": ["spontaneous", "flexible", "adaptable", "impulsive"]},
        },
    },
    "openness_high": {
        "big_five_analysis": {
            "cognitive_style": {"in": ["curious", "imaginative", "abstract", "creative"]},
        },
    },
    "openness_low": {
        "big_five_analysis": {
            "cognitive_style": {"in": ["practical", "conventional", "concrete", "traditional"]},
        },
    },
}

# 情绪 → Plutchik 轮盘映射
PLUTCHIK_EMOTION_MAP = {
    "joy": "joy",
    "sadness": "sadness",
    "anger": "anger",
    "fear": "fear",
    "surprise": "surprise",
    "disgust": "disgust",
    "trust": "trust",
    "anticipation": "anticipation",
}

# ---------------------------------------------------------------------------
# CPED 数据集加载
# ---------------------------------------------------------------------------
def try_load_cped():
    """尝试从本地 CPED 目录加载数据集。返回 case 列表，不可用时返回空列表。"""
    if not DATASET_DIR.exists():
        return []

    # CPED 的可能文件名
    candidates = list(DATASET_DIR.rglob("train.json")) + list(DATASET_DIR.rglob("train.jsonl"))
    if not candidates:
        candidates = list(DATASET_DIR.rglob("*.json")) + list(DATASET_DIR.rglob("*.jsonl"))
    if not candidates:
        return []

    cases = []
    seen_ids = set()
    for path in candidates[:3]:  # 最多读取3个文件
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = f.read().strip()
            if not raw:
                continue
            data = json.loads(raw) if raw.startswith("[") else [json.loads(line) for line in raw.split("\n") if line.strip()]
        except (json.JSONDecodeError, IOError):
            continue

        for item in data:
            if not isinstance(item, dict):
                continue
            did = str(item.get("id", ""))
            if not did or did in seen_ids:
                continue
            seen_ids.add(did)

            utterances = item.get("utterances", item.get("dialogue", []))
            if not utterances:
                continue

            # 提取对话文本
            lines = []
            for utt in utterances[:6]:
                if isinstance(utt, dict):
                    speaker = utt.get("speaker", utt.get("role", ""))
                    text = utt.get("text", utt.get("content", ""))
                    lines.append(f"{speaker}: {text}" if speaker else text)
                else:
                    lines.append(str(utt))
            event_desc = "\n".join(lines)[:300]

            # 提取人格标注
            personality_raw = item.get("personality", {})
            personality = {
                "openness": personality_raw.get("openness", 0.5),
                "conscientiousness": personality_raw.get("conscientiousness", 0.5),
                "extraversion": personality_raw.get("extraversion", 0.5),
                "agreeableness": personality_raw.get("agreeableness", 0.5),
                "neuroticism": personality_raw.get("neuroticism", 0.5),
            }
            # CPED 中人格值是 1-5 整数 → 归一化到 0-1
            for k in personality:
                if isinstance(personality[k], (int, float)) and personality[k] > 1:
                    personality[k] = round(personality[k] / 5.0, 2)

            # 提取情感
            first_utt = utterances[0] if isinstance(utterances[0], dict) else {}
            emotion = first_utt.get("emotion", "")

            case = {
                "id": f"cped_{did}",
                "source": f"CPED — {item.get('source', item.get('tv_drama', 'TV drama'))}",
                "domain": "friendship",
                "character_state": {
                    "name": utterances[0].get("speaker", utterances[0].get("role", "")) if isinstance(utterances[0], dict) else "speaker",
                    "personality": {
                        **personality,
                        "attachment_style": "secure",
                        "defense_style": [],
                        "cognitive_biases": [],
                        "moral_stage": 3,
                    },
                    "trauma": {"ace_score": 0, "active_schemas": [], "trauma_triggers": []},
                    "ideal_world": {},
                    "motivation": {"current_goal": ""},
                    "emotion_decay": {},
                },
                "event": {
                    "description": event_desc,
                    "type": "social",
                    "participants": [],
                    "significance": 0.5,
                    "tags": ["dialogue", "cped"],
                },
                "expected": {
                    "big_five_analysis": {},
                    "plutchik_emotion": {"internal": {"dominant": {"in": [emotion]}}} if emotion else {},
                    "response_generator": {"response_text": {"not_empty": True}},
                },
            }
            cases.append(case)
    return cases


# ---------------------------------------------------------------------------
# 内置 fallback 用例生成
# ---------------------------------------------------------------------------
def _build_assertions(char_idx, emotion):
    """根据角色人格剖面和场景情绪，构建 expected 断言字典。"""
    arch = ARCHETYPES[char_idx]
    p = arch["personality"]
    expected = {
        "big_five_analysis": {},
        "plutchik_emotion": {
            "internal": {
                "dominant": {"in": [PLUTCHIK_EMOTION_MAP.get(emotion, emotion)]},
            },
        },
        "response_generator": {
            "response_text": {"not_empty": True},
        },
    }

    ba = expected["big_five_analysis"]

    # 根据大五数值添加断言
    if p["neuroticism"] >= 0.65:
        ba.update(TRAIT_EXPECTED["neuroticism_high"]["big_five_analysis"])
    elif p["neuroticism"] <= 0.35:
        ba.update(TRAIT_EXPECTED["neuroticism_low"]["big_five_analysis"])

    if p["extraversion"] >= 0.65:
        ba.update(TRAIT_EXPECTED["extraversion_high"]["big_five_analysis"])
    elif p["extraversion"] <= 0.35:
        ba.update(TRAIT_EXPECTED["extraversion_low"]["big_five_analysis"])

    if p["agreeableness"] >= 0.65:
        ba.update(TRAIT_EXPECTED["agreeableness_high"]["big_five_analysis"])
    elif p["agreeableness"] <= 0.35:
        ba.update(TRAIT_EXPECTED["agreeableness_low"]["big_five_analysis"])

    if p["conscientiousness"] >= 0.65:
        ba.update(TRAIT_EXPECTED["conscientiousness_high"]["big_five_analysis"])
    elif p["conscientiousness"] <= 0.35:
        ba.update(TRAIT_EXPECTED["conscientiousness_low"]["big_five_analysis"])

    if p["openness"] >= 0.65:
        ba.update(TRAIT_EXPECTED["openness_high"]["big_five_analysis"])
    elif p["openness"] <= 0.35:
        ba.update(TRAIT_EXPECTED["openness_low"]["big_five_analysis"])

    return expected


def generate_fallback_cases(sample_n=None):
    """从内置角色原型和场景模板生成验证用例。"""
    cases = []
    for i, sc in enumerate(SCENARIOS):
        arch = ARCHETYPES[sc["char_idx"]]
        expected = _build_assertions(sc["char_idx"], sc["emotion"])

        case = {
            "id": f"cped_fallback_{i:04d}",
            "source": f"CPED fallback — {arch['name']} ({sc['domain']})",
            "domain": sc["domain"],
            "character_state": {
                "name": arch["name"],
                "personality": {
                    **arch["personality"],
                    "attachment_style": arch["attachment"],
                    "defense_style": arch["defense"],
                    "cognitive_biases": arch["biases"],
                    "moral_stage": arch["moral"],
                },
                "trauma": {
                    "ace_score": arch["ace"],
                    "active_schemas": arch["schemas"],
                    "trauma_triggers": arch["triggers"],
                },
                "ideal_world": {
                    "ideal_self": arch["ideal_self"],
                    "ideal_relationships": arch["ideal_relations"],
                },
                "motivation": {
                    "current_goal": arch["goal"],
                },
                "emotion_decay": {},
            },
            "event": {
                "description": sc["description"],
                "type": sc["event_type"],
                "participants": sc["participants"],
                "significance": sc["significance"],
                "tags": sc["tags"],
            },
            "expected": expected,
        }
        cases.append(case)

    if sample_n and sample_n < len(cases):
        rng = random.Random(42)
        rng.shuffle(cases)
        cases = cases[:sample_n]
        cases.sort(key=lambda c: c["id"])

    return cases


# ---------------------------------------------------------------------------
# 统计工具
# ---------------------------------------------------------------------------
def print_summary(cases):
    """打印用例统计摘要。"""
    total = len(cases)
    print(f"\n{'='*60}")
    print(f"  CPED 验证用例生成报告")
    print(f"{'='*60}")
    print(f"  总用例数: {total}")

    # 领域覆盖
    domains = {}
    for c in cases:
        d = c.get("domain", "unknown")
        domains[d] = domains.get(d, 0) + 1
    print(f"\n  领域覆盖:")
    for d, n in sorted(domains.items(), key=lambda x: -x[1]):
        print(f"    {d}: {n} ({n*100/total:.0f}%)")

    # 情绪覆盖
    emotions = {}
    for c in cases:
        expected_plutchik = c.get("expected", {}).get("plutchik_emotion", {})
        dominant = expected_plutchik.get("internal", {}).get("dominant", {})
        emotion_list = dominant.get("in", ["unknown"])
        for e in emotion_list:
            emotions[e] = emotions.get(e, 0) + 1
    print(f"\n  情绪覆盖:")
    for e, n in sorted(emotions.items(), key=lambda x: -x[1]):
        print(f"    {e}: {n} ({n*100/total:.0f}%)")

    # 大五人格剖面多样性
    trait_ranges = {t: {"min": 1.0, "max": 0.0} for t in ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"]}
    for arch in ARCHETYPES:
        for t in trait_ranges:
            v = arch["personality"][t]
            trait_ranges[t]["min"] = min(trait_ranges[t]["min"], v)
            trait_ranges[t]["max"] = max(trait_ranges[t]["max"], v)
    print(f"\n  大五人格覆盖 (10 个角色原型):")
    for t, r in trait_ranges.items():
        print(f"    {t}: [{r['min']:.2f}, {r['max']:.2f}]")

    # 来源
    sources = {}
    for c in cases:
        s = "CPED" if c.get("source", "").startswith("CPED —") else "CPED fallback"
        sources[s] = sources.get(s, 0) + 1
    print(f"\n  来源:")
    for s, n in sorted(sources.items(), key=lambda x: -x[1]):
        print(f"    {s}: {n}")

    print(f"{'='*60}\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def extract_cases(sample_n=None):
    """主入口：优先加载 CPED 数据集，fallback 到内置用例。"""
    cases = try_load_cped()
    if cases:
        print(f"从本地 CPED 数据集加载了 {len(cases)} 条对话。")
        if sample_n and sample_n < len(cases):
            rng = random.Random(42)
            rng.shuffle(cases)
            cases = cases[:sample_n]
    else:
        print(f"CPED 数据集未找到 (路径: {DATASET_DIR})，使用内置 fallback 用例。")
        cases = generate_fallback_cases(sample_n)
    return cases


def main():
    parser = argparse.ArgumentParser(description="从 CPED 数据集提取验证用例")
    parser.add_argument("--sample", type=int, default=None, help="随机采样 N 条用例 (用于快速测试)")
    args = parser.parse_args()

    cases = extract_cases(args.sample)
    print_summary(cases)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / "cped_cases.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(cases, f, ensure_ascii=False, indent=2)
    print(f"已保存到: {out_path}")


if __name__ == "__main__":
    main()
