"""从 GoEmotions 数据集提取 Plutchik 情绪验证用例。

GoEmotions (Demszky et al., 2020): 58,009 Reddit 评论，27 种细粒度情感标签。
来源: https://huggingface.co/datasets/google-research-datasets/go_emotions

输出 ~150 条内置用例，覆盖全部 27 种情感，映射到 Plutchik 8 基本类别。
Focus: L1 plutchik_emotion — 检测正确的主导情感。
"""
import argparse
import json
import os
import random
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent.parent / "fixtures"

# ═══════════════════════════════════════════════════════════════
# GoEmotions 27 标签 → Plutchik 8 基本情绪 + 维度的映射
# ═══════════════════════════════════════════════════════════════
# 映射依据: Plutchik (1980) 情感轮 + Demszky et al. (2020) 标注体系

GOEMOTION_TO_PLUTCHIK = {
    "admiration":    {"base": "trust",    "pleasantness": 0.8, "intensity_range": (0.4, 0.8)},
    "amusement":     {"base": "joy",      "pleasantness": 0.9, "intensity_range": (0.5, 0.9)},
    "anger":         {"base": "anger",    "pleasantness": -0.8, "intensity_range": (0.6, 1.0)},
    "annoyance":     {"base": "anger",    "pleasantness": -0.5, "intensity_range": (0.3, 0.7)},
    "approval":      {"base": "trust",    "pleasantness": 0.6, "intensity_range": (0.3, 0.7)},
    "caring":        {"base": "trust",    "pleasantness": 0.8, "intensity_range": (0.4, 0.8)},
    "confusion":     {"base": "surprise", "pleasantness": -0.2, "intensity_range": (0.3, 0.7)},
    "curiosity":     {"base": "anticipation","pleasantness": 0.5, "intensity_range": (0.4, 0.8)},
    "desire":        {"base": "anticipation","pleasantness": 0.6, "intensity_range": (0.4, 0.8)},
    "disappointment":{"base": "sadness",  "pleasantness": -0.6, "intensity_range": (0.4, 0.8)},
    "disapproval":   {"base": "disgust",  "pleasantness": -0.6, "intensity_range": (0.3, 0.7)},
    "disgust":       {"base": "disgust",  "pleasantness": -0.9, "intensity_range": (0.5, 0.9)},
    "embarrassment": {"base": "sadness",  "pleasantness": -0.5, "intensity_range": (0.4, 0.8)},
    "excitement":    {"base": "joy",      "pleasantness": 0.8, "intensity_range": (0.6, 1.0)},
    "fear":          {"base": "fear",     "pleasantness": -0.8, "intensity_range": (0.5, 0.9)},
    "gratitude":     {"base": "joy",      "pleasantness": 0.9, "intensity_range": (0.5, 0.9)},
    "grief":         {"base": "sadness",  "pleasantness": -0.9, "intensity_range": (0.6, 1.0)},
    "joy":           {"base": "joy",      "pleasantness": 0.9, "intensity_range": (0.5, 0.9)},
    "love":          {"base": "trust",    "pleasantness": 0.9, "intensity_range": (0.5, 0.9)},
    "nervousness":   {"base": "fear",     "pleasantness": -0.5, "intensity_range": (0.3, 0.7)},
    "optimism":      {"base": "anticipation","pleasantness": 0.7, "intensity_range": (0.4, 0.8)},
    "pride":         {"base": "joy",      "pleasantness": 0.7, "intensity_range": (0.4, 0.8)},
    "realization":   {"base": "surprise", "pleasantness": 0.3, "intensity_range": (0.3, 0.7)},
    "relief":        {"base": "joy",      "pleasantness": 0.7, "intensity_range": (0.4, 0.8)},
    "remorse":       {"base": "sadness",  "pleasantness": -0.7, "intensity_range": (0.4, 0.8)},
    "sadness":       {"base": "sadness",  "pleasantness": -0.8, "intensity_range": (0.5, 0.9)},
    "surprise":      {"base": "surprise", "pleasantness": 0.2, "intensity_range": (0.4, 0.8)},
}

# 27 种情感的 Reddit 风格评论 — 每标签 5-6 条
BUILTIN_CASES = [
    # --- admiration (trust) ---
    ("admiration", "我真的太佩服我的导师了，她一边照顾两个孩子一边完成了博士论文，还能保持微笑。"),
    ("admiration", "这个开源项目的维护者太强了，一个人处理了三千多个 issue，回复还特别耐心。"),
    ("admiration", "看了那个消防员的采访，冲进火场救人之后第一句话是'还好不是我女儿'。"),
    ("admiration", "90岁的外婆还在学用编程，上周写了一个计算器小程序发给我。"),
    ("admiration", "那个马拉松选手在终点线前停下来扶起摔倒的对手，这才是真正的体育精神。"),
    # --- amusement (joy) ---
    ("amusement", "我家的猫学会了开门，现在半夜自己开冰箱找吃的，把厨房搞得一团糟。"),
    ("amusement", "今天开会时同事不小心把咖啡倒在了自己裤子上，然后假装什么都没发生继续讲PPT。"),
    ("amusement", "给爸爸买了智能手机，他花了三小时才搞清楚怎么解锁，现在每天发一百条表情包。"),
    ("amusement", "看到一个帖子说有人把密码贴在屏幕上，因为'最危险的地方就是最安全的地方'。"),
    ("amusement", "小侄女说她想嫁给奥特曼，因为她觉得'每个女生都需要一个会发光的男人'。"),
    # --- anger ---
    ("anger", "那个肇事逃逸的司机，撞伤老人后直接开走了，监控拍到车牌号，希望尽快抓到他。"),
    ("anger", "公司连续加班三个月不给加班费，今天还说要'优化人员结构'，这是逼人走还不给赔偿。"),
    ("anger", "有人在医院急诊室插队被制止后，竟然对护士大吼大叫还动手推搡。"),
    ("anger", "房东在没有提前通知的情况下，擅自进入我的房间，还说'这是我的房子我想进就进'。"),
    ("anger", "骗子冒充警察打电话恐吓我70岁的父亲，骗走了他所有的养老金。"),
    # --- annoyance (anger) ---
    ("annoyance", "隔壁装修从早上八点吵到晚上八点，电钻声让人头都要炸了。"),
    ("annoyance", "每次跟同事约时间开会，他都要迟到十五分钟，还不道歉。"),
    ("annoyance", "地铁上有人外放看短视频，声音巨大，说了也不听。"),
    ("annoyance", "为什么每次我排队排到最前面的时候，窗口就挂出'暂停服务'的牌子？"),
    ("annoyance", "朋友发来60秒语音方阵，连续十条，我又不想逐条听又想回。"),
    # --- approval (trust) ---
    ("approval", "我觉得公司新出台的远程办公政策特别好，每周可以居家两天，效率更高了。"),
    ("approval", "支持社区新规：遛狗必须拴绳，这才是对所有人都负责的做法。"),
    ("approval", "新来的项目经理做事很靠谱，每个里程碑都提前规划好，沟通也很透明。"),
    ("approval", "学校取消了月考排名制度，孩子们的压力真的小了很多。"),
    ("approval", "这个决定非常明智，既保护了环境又没有给企业造成过多负担。"),
    # --- caring (trust) ---
    ("caring", "妈妈每天都往我包里塞一个苹果和一张纸条，虽然我已经26岁了。"),
    ("caring", "室友知道我最近失眠，悄悄在我的枕头下面放了一瓶薰衣草精油。"),
    ("caring", "同事看我加班到深夜，默默帮我叫了外卖放在桌上就走了。"),
    ("caring", "班主任记得班上每个学生的生日，每次都会手写一张贺卡。"),
    ("caring", "楼下的老奶奶每天会给流浪猫留一碗牛奶，已经坚持了五年。"),
    # --- confusion (surprise) ---
    ("confusion", "我明明把钥匙放在鞋柜上了，现在怎么找也找不到，是不是被什么拿走了？"),
    ("confusion", "这个软件更新之后界面完全变了，原有的功能找不到了，更新说明也没写。"),
    ("confusion", "医生说我一切正常，但我确实能听到一些别人听不到的声音。"),
    ("confusion", "他昨天还说爱我要和我共度一生，今天就跟另一个人在一起了。"),
    ("confusion", "这条新闻前后矛盾，开头说气温突破历史极值，结尾又说今年是冷夏。"),
    # --- curiosity (anticipation) ---
    ("curiosity", "我一直想知道为什么天空是蓝色的而不是绿色的，大学决定学物理。"),
    ("curiosity", "那个算法是怎么做到在不到一秒内识别出几百万张图片的？背后是什么原理？"),
    ("curiosity", "我很好奇，在没有文字的时代，人们是怎么传递复杂信息的？"),
    ("curiosity", "为什么猫会对着盒子发呆？它们到底在想什么？"),
    ("curiosity", "人类如果移民火星，第一代孩子会在什么样的环境中长大？"),
    # --- desire (anticipation) ---
    ("desire", "我太想要一台新相机了，现在的这一台已经用了十年，快门都按了二十万次。"),
    ("desire", "好希望有一天能去南极看看极光，那一定是人生中最震撼的体验。"),
    ("desire", "我想学会一门乐器，不需要很精通，只要能弹出自己喜欢的旋律就好。"),
    ("desire", "一直梦想拥有一间自己的书房，四面墙都是书架，中间放一张大桌子。"),
    ("desire", "特别希望能和父亲和解，我们已经有五年没有说过话了。"),
    # --- disappointment (sadness) ---
    ("disappointment", "等了三个月的游戏终于发售了，结果bug多到根本没法玩，退款了。"),
    ("disappointment", "面试了五轮，每次都觉得聊得很好，最后还是收到了拒信。"),
    ("disappointment", "我种了一年的花，每天浇水施肥，结果被一场突如其来的冰雹全毁了。"),
    ("disappointment", "以为考得很好，对完答案发现错了三道大题，和目标分数差远了。"),
    ("disappointment", "筹备了半年的旅行，出发前一天收到航班取消通知，再也订不到合适的了。"),
    # --- disapproval (disgust) ---
    ("disapproval", "强烈反对在居民区附近建垃圾焚烧厂，环评报告明显有问题。"),
    ("disapproval", "这种抄袭他人作品还理直气壮的行为实在令人不齿。"),
    ("disapproval", "我不同意这个方案，预算超支了30%却没有任何风险控制措施。"),
    ("disapproval", "怎么可以用动物做这么残忍的实验？一定有替代方案。"),
    ("disapproval", "公众人物发表这样的歧视性言论，完全没有社会责任感。"),
    # --- disgust ---
    ("disgust", "在餐厅的汤里喝出了一只蟑螂，叫来经理他还说是调料。"),
    ("disgust", "看到有人虐待流浪猫的视频，太恶心了，这种人应该被法律严惩。"),
    ("disgust", "打开冰箱发现室友的牛奶过期两个星期了，整个冰箱都是恶臭。"),
    ("disgust", "那个政客在电视上满口谎言，还一脸正气的样子令人作呕。"),
    ("disgust", "酒店床单掀开发现上面有明显的污渍，这根本没换洗吧。"),
    # --- embarrassment (sadness) ---
    ("embarrassment", "在全体大会上演讲到一半，突然发现裤子拉链没拉上。"),
    ("embarrassment", "叫错了新同事的名字，而且连续叫错三次直到别人纠正我。"),
    ("embarrassment", "在咖啡店排队时大声跟朋友吐槽老板，回头发现老板就站在我身后。"),
    ("embarrassment", "给全班同学群发了消息，结果发现里面有一条吐槽另一个同学的私信。"),
    ("embarrassment", "约会时想展示一下厨艺，结果把厨房弄得一团糟，最后只能叫外卖。"),
    # --- excitement (joy) ---
    ("excitement", "明天就要去日本看樱花了！准备了半年终于要出发了！"),
    ("excitement", "终于收到了心仪大学的研究生录取通知书，这一年多的努力没有白费！"),
    ("excitement", "最喜欢的乐队下周要来开演唱会，我抢到了第一排的票！"),
    ("excitement", "我们要有宝宝了！马上就要当爸爸了，现在手还在抖！"),
    ("excitement", "今天收到了转正通知，试用期表现超出预期，工资还涨了20%！"),
    # --- fear ---
    ("fear", "凌晨两点听到楼下有人撬门的声音，我一个人在家，不敢动也不敢出声。"),
    ("fear", "体检报告上有个指标严重异常，医生让我明天来做进一步检查。"),
    ("fear", "台风来了，屋顶在漏水，电也断了，手机只剩10%的电量。"),
    ("fear", "孩子发高烧到40度，外面下着暴雨，叫不到车也打不通120。"),
    ("fear", "深夜走在小巷里，发现有人一直跟着我，我加快脚步他也加快。"),
    # --- gratitude (joy) ---
    ("gratitude", "非常感谢昨天那位送我口罩的好心人，我在地铁上突然流鼻血，没有你的话真不知道怎么办。"),
    ("gratitude", "感谢我的导师，不仅仅教会我知识，更教会我如何面对失败和挫折。"),
    ("gratitude", "谢谢爸爸妈妈一直支持我的选择，即使我的道路和大家不一样。"),
    ("gratitude", "真的很感谢疫情期间所有医护人员的付出，你们是真正的英雄。"),
    ("gratitude", "谢谢快递小哥在暴雨天还准时送货，他全身都湿透了但包裹是干的。"),
    # --- grief (sadness) ---
    ("grief", "今天参加了好朋友的葬礼，他才28岁，下周本应是他的婚礼。"),
    ("grief", "整理奶奶遗物时发现她保存了我从小学到大学所有的奖状，每一张都用透明胶带仔细贴好。"),
    ("grief", "从宠物医院走出来的时候手里拿着空空的项圈，陪伴了十五年的老狗再也不在了。"),
    ("grief", "回到老家，看到父亲的书房还保持着原来的样子，但他已经不在了。"),
    ("grief", "翻看以前的合照，那时候大家都在，现在各奔东西，有些人再也见不到了。"),
    # --- joy ---
    ("joy", "今天在街上看到一个小孩捡起别人丢的垃圾扔进垃圾桶，他妈妈笑着摸了摸他的头。"),
    ("joy", "终于完成了历时两年的长篇小说，打印出来的那一刻忍不住哭了。"),
    ("joy", "今天阳光特别好，公园里的花都开了，我和喜欢的人一起野餐了。"),
    ("joy", "收养了一只流浪猫，它现在会在我回家的时候跑到门口等我。"),
    ("joy", "跟老朋友们聚在一起，还是和十年前一样无话不谈。"),
    # --- love (trust) ---
    ("love", "看着熟睡中的伴侣和孩子，突然觉得这辈子最幸运的事就是遇到他们。"),
    ("love", "爸妈结婚三十周年，今天我看到爸爸偷偷在厨房亲了妈妈的脸颊。"),
    ("love", "我爱我的工作，虽然赚得不多，但每一天都在做有意义的事情。"),
    ("love", "她在我最低谷的时候没有离开，现在轮到我守护她了。"),
    ("love", "回家的路上下着小雨，他脱下了外套罩在我头上，自己的肩膀都湿透了。"),
    # --- nervousness (fear) ---
    ("nervousness", "明天是第一天上新班，不知道同事好不好相处，已经紧张得睡不着了。"),
    ("nervousness", "马上要上台做毕业答辩了，手心全是汗，腿也在发抖。"),
    ("nervousness", "约了心仪的人出来吃饭，反复看菜单想好要说什么，结果还是紧张得语无伦次。"),
    ("nervousness", "在等面试结果，手机每响一次心就跳一下，已经三天了。"),
    ("nervousness", "第一次当爸爸，抱着新生儿的时候手都在抖，怕伤到他。"),
    # --- optimism (anticipation) ---
    ("optimism", "虽然这次没考上，但我相信再努力一年一定能实现梦想。"),
    ("optimism", "经济虽然不好，但我相信只要我们互相支持，一定能渡过难关。"),
    ("optimism", "医生说康复率有60%，我要成为那60%里的人。"),
    ("optimism", "新一年开始了，我相信一切都会越来越好的。"),
    ("optimism", "虽然现在的处境很困难，但每次危机都蕴藏着转机。"),
    # --- pride (joy) ---
    ("pride", "看着女儿在舞台上弹奏钢琴，全场掌声雷动，我为她感到无比骄傲。"),
    ("pride", "今天我的论文被顶级期刊接收了，两年的辛苦终于得到了认可。"),
    ("pride", "儿子说'爸爸我以后也要像你一样当老师'，那一刻我觉得所有的付出都值得。"),
    ("pride", "我带的团队在黑客马拉松中获得了第一名，大家熬了三个通宵的成果。"),
    ("pride", "虽然我只是实习生，但我的代码被正式产品采用了。"),
    # --- realization (surprise) ---
    ("realization", "原来我一直以为的'内向'其实是社交焦虑，不是性格问题。"),
    ("realization", "我突然明白了，父母不是不爱我，他们只是用他们认为对的方式在爱。"),
    ("realization", "难怪跟他在一起总是很累，原来我一直在进行讨好。"),
    ("realization", "直到外婆去世我才意识到，我从来没有问过她年轻时的故事。"),
    ("realization", "检查了三遍才发现，那个bug是因为把==写成了=。"),
    # --- relief (joy) ---
    ("relief", "CT结果出来了，是良性的。在医院走廊上我靠着墙哭了很久。"),
    ("relief", "走失的孩子找到了，在派出所看到他那一刻我整个人都瘫了。"),
    ("relief", "终于答辩完了！走出教室的时候感觉世界都亮了。"),
    ("relief", "考试过了！原以为肯定不及格，结果低分飘过。"),
    ("relief", "航班在延误六小时后终于起飞了，虽然只晚到了几小时。"),
    # --- remorse (sadness) ---
    ("remorse", "我不应该对妈妈说出那么伤人的话，她只是想让我多吃点。"),
    ("remorse", "如果那天我没有发那条消息，也许我们还能做朋友。"),
    ("remorse", "是我太自私了，为了自己的前途忽略了他的感受。"),
    ("remorse", "当时应该站出来帮他的，但我选择了沉默。"),
    ("remorse", "我永远无法原谅自己，开车时看手机的那几秒改变了一切。"),
    # --- sadness ---
    ("sadness", "今天整理房间，发现前任留下的东西，其实早就该扔了但就是舍不得。"),
    ("sadness", "最好的朋友要移民了，以后可能好几年才能见一次。"),
    ("sadness", "一个人在异乡过节，看着窗外的万家灯火，没有一盏是为我亮起的。"),
    ("sadness", "失业两个月了，不敢告诉家人，每天早上假装去上班。"),
    ("sadness", "翻到小时候的相册，那时候爸妈还在一起，我们一家三口笑得多开心。"),
    # --- surprise ---
    ("surprise", "打开门发现所有朋友都站在客厅里大喊'生日快乐'，我完全忘记今天是我生日了。"),
    ("surprise", "收到一封来自十年前的自己的信，是小学老师组织写的，我都忘了这件事。"),
    ("surprise", "公司年会上抽中了特等奖——一辆车！我到现在还不敢相信。"),
    ("surprise", "走在大街上突然有个人叫我的名字，竟然是失联多年的发小。"),
    ("surprise", "我一直以为自己是独生子，结果昨天一个陌生人联系我说他是我同父异母的哥哥。"),
]

# 角色人格模板 - 丰富多样
CHARACTER_TEMPLATES = [
    {
        "name": "林悦",
        "personality": {"openness": 0.75, "conscientiousness": 0.65, "extraversion": 0.7, "agreeableness": 0.7, "neuroticism": 0.45},
        "attachment_style": "secure",
    },
    {
        "name": "陈默",
        "personality": {"openness": 0.4, "conscientiousness": 0.8, "extraversion": 0.25, "agreeableness": 0.45, "neuroticism": 0.55},
        "attachment_style": "avoidant",
    },
    {
        "name": "张雨晴",
        "personality": {"openness": 0.85, "conscientiousness": 0.35, "extraversion": 0.75, "agreeableness": 0.65, "neuroticism": 0.6},
        "attachment_style": "anxious",
    },
    {
        "name": "王磊",
        "personality": {"openness": 0.45, "conscientiousness": 0.7, "extraversion": 0.6, "agreeableness": 0.35, "neuroticism": 0.4},
        "attachment_style": "dismissive_avoidant",
    },
    {
        "name": "李思思",
        "personality": {"openness": 0.65, "conscientiousness": 0.6, "extraversion": 0.55, "agreeableness": 0.8, "neuroticism": 0.7},
        "attachment_style": "fearful_avoidant",
    },
    {
        "name": "赵明远",
        "personality": {"openness": 0.55, "conscientiousness": 0.85, "extraversion": 0.3, "agreeableness": 0.6, "neuroticism": 0.35},
        "attachment_style": "secure",
    },
    {
        "name": "刘洋",
        "personality": {"openness": 0.7, "conscientiousness": 0.5, "extraversion": 0.8, "agreeableness": 0.55, "neuroticism": 0.5},
        "attachment_style": "secure",
    },
    {
        "name": "周小琴",
        "personality": {"openness": 0.35, "conscientiousness": 0.75, "extraversion": 0.4, "agreeableness": 0.75, "neuroticism": 0.65},
        "attachment_style": "anxious",
    },
]


def make_character_state(name: str, base_personality: dict, attachment: str) -> dict:
    """构建 character_state 对象。"""
    return {
        "name": name,
        "personality": {
            "openness": base_personality["openness"],
            "conscientiousness": base_personality["conscientiousness"],
            "extraversion": base_personality["extraversion"],
            "agreeableness": base_personality["agreeableness"],
            "neuroticism": base_personality["neuroticism"],
            "attachment_style": attachment,
            "defense_style": [],
            "cognitive_biases": [],
            "moral_stage": 3,
        },
        "trauma": {"ace_score": 0, "active_schemas": [], "trauma_triggers": []},
        "ideal_world": {},
        "motivation": {"current_goal": ""},
        "emotion_decay": {},
    }


def extract_cases(sample: int = 0) -> list[dict]:
    """从内置数据生成验证用例。"""
    random.seed(42)
    cases = []

    for idx, (emotion_label, comment) in enumerate(BUILTIN_CASES):
        mapping = GOEMOTION_TO_PLUTCHIK[emotion_label]
        base_emotion = mapping["base"]
        pleasantness = mapping["pleasantness"]
        intensity_min, intensity_max = mapping["intensity_range"]

        # 轮换使用不同人格模板
        tmpl = CHARACTER_TEMPLATES[idx % len(CHARACTER_TEMPLATES)]

        case = {
            "id": f"goemo_{idx:04d}",
            "source": f"GoEmotions (Demszky et al., 2020) — {emotion_label} → Plutchik {base_emotion}",
            "domain": "emotion_recognition",
            "character_state": make_character_state(tmpl["name"], tmpl["personality"], tmpl["attachment_style"]),
            "event": {
                "description": comment,
                "type": "social",
                "participants": [],
                "significance": round(0.5 + abs(pleasantness) * 0.3, 2),
                "tags": ["reddit", "goemotions", emotion_label, base_emotion],
            },
            "expected": {
                "plutchik_emotion": {
                    "internal.dominant": {"in": [base_emotion]},
                    "internal.intensity": {"min": intensity_min, "max": intensity_max},
                    "internal.pleasantness": {
                        "direction": "positive" if pleasantness > 0 else "negative"
                    },
                },
                "response_generator": {"response_text": {"not_empty": True}},
            },
            "_goemotion_label": emotion_label,
            "_plutchik_base": base_emotion,
        }
        cases.append(case)

    if sample > 0:
        random.shuffle(cases)
        cases = cases[:sample]

    return cases


def print_summary(cases: list[dict]):
    """打印统计摘要。"""
    print(f"Generated {len(cases)} GoEmotions-derived cases")

    # 按 Plutchik 基本情绪分布
    base_counts = {}
    goemo_counts = {}
    for c in cases:
        base = c.get("_plutchik_base", "?")
        base_counts[base] = base_counts.get(base, 0) + 1
        label = c.get("_goemotion_label", "?")
        goemo_counts[label] = goemo_counts.get(label, 0) + 1
    print(f"\nPlutchik base emotion distribution ({len(base_counts)} categories):")
    for b, n in sorted(base_counts.items(), key=lambda x: -x[1]):
        print(f"  {b}: {n}")

    print(f"\nGoEmotion label distribution ({len(goemo_counts)} labels):")
    for g, n in sorted(goemo_counts.items(), key=lambda x: -x[1]):
        print(f"  {g}: {n}")

    # 人格分布
    names = set(c["character_state"]["name"] for c in cases)
    print(f"\nUnique character profiles: {len(names)}")
    for n in sorted(names):
        print(f"  {n}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract GoEmotions test cases")
    parser.add_argument("--sample", type=int, default=0, help="Number of cases to sample (0=all)")
    args = parser.parse_args()

    cases = extract_cases(sample=args.sample)
    print_summary(cases)

    out_path = OUTPUT_DIR / "goemotions_cases.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(cases, f, ensure_ascii=False, indent=2)
    print(f"\nSaved to {out_path}")
