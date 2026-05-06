"""从 DailyDialog 数据集提取对话情感与社交行为验证用例。

DailyDialog (Li et al., 2017): 13,118 英文日常对话，7 情感 + 4 对话行为标注。
来源: https://huggingface.co/datasets/li2017dailydialog/daily_dialog

输出 ~150 条内置用例，覆盖 7 种情感 (anger, disgust, fear, joy, sadness, surprise, neutral)。
每个用例包含多轮对话历史 + 当前话语。
Focus: L1 plutchik_emotion (对话语境中的情感) + L3 (社交对话行为分析)
"""
import argparse
import json
import random
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent.parent / "fixtures"

# ═══════════════════════════════════════════════════════════════
# DailyDialog 7 情感 → Plutchik 8 基本情绪映射
# ═══════════════════════════════════════════════════════════════
DIALOG_EMOTION_MAP = {
    "anger":       {"base": "anger",     "pleasantness": -0.7},
    "disgust":     {"base": "disgust",   "pleasantness": -0.8},
    "fear":        {"base": "fear",      "pleasantness": -0.7},
    "joy":         {"base": "joy",       "pleasantness": 0.8},
    "sadness":     {"base": "sadness",   "pleasantness": -0.7},
    "surprise":    {"base": "surprise",  "pleasantness": 0.2},
    "neutral":     {"base": "trust",     "pleasantness": 0.0},
}

# 对话行为标签
DIALOG_ACTS = ["inform", "question", "directive", "commissive"]

# ═══════════════════════════════════════════════════════════════
# 内置多轮对话 — 每个对话包含 (历史, 当前话语, 情感, 对话行为)
# ═══════════════════════════════════════════════════════════════
BUILTIN_DIALOGUES = [
    # --- anger ---
    (
        [
            "A: 你昨天为什么没来开会？",
            "B: 我以为取消了。",
            "A: 取消？我明明给你发了邮件确认时间。",
        ],
        "B: 你发的邮件被系统过滤到垃圾箱了，我没有看到。不要每次出了问题就先指责我！",
        "anger", "inform"
    ),
    (
        [
            "A: 这个项目已经延期两周了。",
            "B: 我知道，但市场部那边一直没有给数据。",
            "A: 那你为什么不催？",
        ],
        "B: 我催了五次！你根本不知道我夹在中间有多难做。",
        "anger", "directive"
    ),
    (
        [
            "A: 你怎么又买这么多快递？",
            "B: 都是家里需要的东西。",
            "A: 上个月信用卡还没还完呢。",
        ],
        "B: 够了！我花自己的钱你也要管吗？",
        "anger", "directive"
    ),
    (
        [
            "A: 你为什么回家这么晚？",
            "B: 加班。",
            "A: 加班加班，你每次都这么说。",
        ],
        "B: 你不信任我就直说，不用这样阴阳怪气的！",
        "anger", "directive"
    ),
    (
        [
            "A: 这次考核你又是最低分。",
            "B: 我尽力了。",
            "A: 尽力？我看你根本没有认真对待。",
        ],
        "B: 你知道我每天加班到几点吗？你有什么资格这样评价我！",
        "anger", "inform"
    ),
    # --- disgust ---
    (
        [
            "A: 你看到食堂今天的菜了吗？",
            "B: 看到了，看起来好难吃。",
            "A: 那个肉颜色都不对。",
        ],
        "B: 我昨天吃了一口直接吐了，像是馊掉的。真不知道厨师是怎么想的。",
        "disgust", "inform"
    ),
    (
        [
            "A: 听说那个主管又在办公室欺负新人了。",
            "B: 真的假的？他做什么了？",
            "A: 当众骂人家一无是处，就因为表格格式不对。",
        ],
        "B: 这种行为太令人恶心了，完全没有做人的基本尊重。",
        "disgust", "inform"
    ),
    (
        [
            "A: 我在冰箱里发现了一盒发霉的饭。",
            "B: 谁的？",
            "A: 不知道，标签都看不清了。",
        ],
        "B: 好恶心，快扔掉！下次谁再把食物放坏不处理我就要发火了。",
        "disgust", "directive"
    ),
    (
        [
            "A: 你看那条新闻了吗？一个网红为了流量在墓地里直播。",
            "B: 没看，怎么了？",
            "A: 她在人家墓碑上跳舞，还说'这里好凉快'。",
        ],
        "B: 天哪，这太令人作呕了。为了流量连基本的底线都不要了。",
        "disgust", "inform"
    ),
    (
        [
            "A: 这水怎么有股怪味？",
            "B: 好像是水管生锈了。",
            "A: 物业不管吗？",
        ],
        "B: 管什么管，他们连楼道垃圾都不清理。这水质我看着就想吐。",
        "disgust", "question"
    ),
    # --- fear ---
    (
        [
            "A: 你最近怎么脸色这么差？",
            "B: 我…我收到了一封威胁信。",
            "A: 什么？报警了吗？",
        ],
        "B: 信上说知道我女儿在哪上学。我不敢报警，我怕他们伤害孩子。",
        "fear", "inform"
    ),
    (
        [
            "A: 体检报告出来了？",
            "B: 出来了，但医生说我肺部有个阴影。",
            "A: 那进一步检查了吗？",
        ],
        "B: 约了下周做CT。我一整晚没睡，脑子里全是各种可能性，太害怕了。",
        "fear", "inform"
    ),
    (
        [
            "A: 外面好像有人在翻围墙。",
            "B: 你别吓我，这么晚了。",
            "A: 真的，我刚才看到一个人影翻过去了。",
        ],
        "B: 快把门锁好！报警！我手都在抖。",
        "fear", "directive"
    ),
    (
        [
            "A: 要面试了，你准备得怎么样了？",
            "B: 昨晚背到三点，但一醒来全忘了。",
            "A: 放轻松，你准备得很充分了。",
        ],
        "B: 我控制不住地发抖，想到面试官会问的问题我就害怕到想吐。",
        "fear", "inform"
    ),
    (
        [
            "A: 台风要登陆了，你囤物资了吗？",
            "B: 囤了一些，但听说这次是超强台风。",
            "A: 是啊，比上次那个还要强。",
        ],
        "B: 上次我家窗户都被吹飞了。这次我好怕，万一屋顶撑不住怎么办？",
        "fear", "question"
    ),
    # --- joy ---
    (
        [
            "A: 考试结果出来了！",
            "B: 怎么样怎么样？",
            "A: 我通过了！而且成绩是全班第三！",
        ],
        "B: 天哪太棒了！我就知道你一定可以的！今晚必须庆祝一下！",
        "joy", "commissive"
    ),
    (
        [
            "A: 我要当爸爸了！",
            "B: 真的？！什么时候？",
            "A: 预产期是十二月，我老婆刚确认。",
        ],
        "B: 恭喜你兄弟！太为你高兴了！你一定会是个好爸爸的！",
        "joy", "commissive"
    ),
    (
        [
            "A: 猜猜我遇到了谁？",
            "B: 谁啊？",
            "A: 大学时候那个最好的朋友，李明！",
        ],
        "B: 哇！你们不是失联好几年了吗？太棒了，赶紧约出来吃饭啊！",
        "joy", "directive"
    ),
    (
        [
            "A: 我们项目获奖了！",
            "B: 真的？哪个奖？",
            "A: 年度最佳创新项目！全公司就一个！",
        ],
        "B: 太厉害了！一年的辛苦没有白费！今晚我请客，大家一起去庆祝！",
        "joy", "commissive"
    ),
    (
        [
            "A: 看窗外！",
            "B: 哇，好美的彩虹！",
            "A: 还是双彩虹呢，我好久没见过了。",
        ],
        "B: 太美了！快许愿！今天真是幸运的一天！",
        "joy", "directive"
    ),
    (
        [
            "A: 妈妈我考上北大了！",
            "B: 真的？录取通知书到了？",
            "A: 刚收到的！",
        ],
        "B: 我的天啊！太棒了！妈妈为你骄傲！快来让我抱抱！我现在就打电话告诉你爸！",
        "joy", "commissive"
    ),
    # --- sadness ---
    (
        [
            "A: 你怎么了？眼睛红红的。",
            "B: 我奶奶今天早上去世了。",
            "A: 天哪，太突然了。",
        ],
        "B: 昨天还跟我说想吃我做的红烧肉，我说下周做。没有下周了。",
        "sadness", "inform"
    ),
    (
        [
            "A: 你和XX怎么样了？",
            "B: 我们分手了。",
            "A: 什么时候的事？",
        ],
        "B: 上周。她说她不爱我了。我到现在还没缓过来，做什么都提不起劲。",
        "sadness", "inform"
    ),
    (
        [
            "A: 为什么辞掉工作？",
            "B: 公司裁员，我是其中之一。",
            "A: 那找新工作了吗？",
        ],
        "B: 投了三十份简历，一个面试都没有。我觉得自己一无是处。",
        "sadness", "inform"
    ),
    (
        [
            "A: 听说你们家老狗生病了？",
            "B: 嗯，医生说可能是肾衰竭。",
            "A: 那还能治吗？",
        ],
        "B: 治不好了，只能让它舒服地走。它陪了我十五年，从小学到工作。我真的不知道怎么面对。",
        "sadness", "inform"
    ),
    (
        [
            "A: 今天同学聚会你去吗？",
            "B: 不去了。",
            "A: 为什么？大家都很想见你。",
        ],
        "B: 看到他们就想起以前的日子，那时候我们多快乐啊。现在大家都变了。",
        "sadness", "inform"
    ),
    (
        [
            "A: 你最近怎么都不发朋友圈了？",
            "B: 没什么好发的。",
            "A: 以前你不是很爱分享生活吗？",
        ],
        "B: 生活没什么值得分享的。每天就是上班下班，一个人吃饭，一个人看电视，一个人睡觉。",
        "sadness", "inform"
    ),
    # --- surprise ---
    (
        [
            "A: 我给你买了份礼物。",
            "B: 什么礼物？",
            "A: 你猜。",
        ],
        "B: 这不是我一直想要的那个限量版手办吗？你怎么买到的？全世界只有500个！",
        "surprise", "question"
    ),
    (
        [
            "A: 还记得王老师吗？",
            "B: 当然记得，我们高中班主任。",
            "A: 他居然是XX的父亲！",
        ],
        "B: 什么？！这世界也太小了吧！完全看不出来！",
        "surprise", "question"
    ),
    (
        [
            "A: 你知道我们公司被收购了吗？",
            "B: 被谁？完全没听说。",
            "A: 被我们的最大竞争对手。",
        ],
        "B: 什么？！这也太突然了！那我们的工作还保得住吗？",
        "surprise", "question"
    ),
    (
        [
            "A: 明天有流星雨！",
            "B: 真的？几点？",
            "A: 凌晨两点，而且肉眼可见。",
        ],
        "B: 太好了！我活了三十年还没看过流星雨呢！必须去看！",
        "surprise", "commissive"
    ),
    (
        [
            "A: 你看今天的股票了吗？",
            "B: 没看，怎么了？",
            "A: 你买的那支涨了50%！",
        ],
        "B: 50%？！你没开玩笑吧？我要发财了！",
        "surprise", "question"
    ),
    # --- neutral ---
    (
        [
            "A: 下午的会议改到三点了。",
            "B: 好的，在哪个会议室？",
            "A: 还是301。",
        ],
        "B: 知道了，我会准时到。",
        "neutral", "inform"
    ),
    (
        [
            "A: 这份文件需要你签个字。",
            "B: 我看一下内容。",
            "A: 就是上个季度的财务报告。",
        ],
        "B: 没问题，数据和我的记录一致。签好了。",
        "neutral", "inform"
    ),
    (
        [
            "A: 图书馆的书明天到期。",
            "B: 我明天去还。",
            "A: 记得带上借书证。",
        ],
        "B: 好的，谢谢提醒。",
        "neutral", "inform"
    ),
    (
        [
            "A: 你看到我的车钥匙了吗？",
            "B: 在门口挂钩上。",
            "A: 哦，果然在那里。",
        ],
        "B: 你总是放在那里的，下次别到处找了。",
        "neutral", "inform"
    ),
    (
        [
            "A: 周末有什么安排？",
            "B: 没什么特别的，就在家休息。",
            "A: 要不要一起去看电影？",
        ],
        "B: 最近没什么想看的，下次吧。",
        "neutral", "inform"
    ),
    (
        [
            "A: 你收到通知了吗？",
            "B: 什么通知？",
            "A: 物业说下周要检修水管。",
        ],
        "B: 好的，我到时候留个人在家。",
        "neutral", "inform"
    ),
    (
        [
            "A: 这个周末要降温。",
            "B: 降到多少度？",
            "A: 最低零下五度。",
        ],
        "B: 那得把厚衣服拿出来了。谢谢你告诉我。",
        "neutral", "inform"
    ),
    # --- 追加对话: anger ---
    (
        [
            "A: 你踩到我的脚了！",
            "B: 对不起对不起，我没注意。",
            "A: 这么大个人了走路不看路吗？",
        ],
        "B: 我已经道歉了你还想怎么样？不要得理不饶人！",
        "anger", "directive"
    ),
    (
        [
            "A: 财务说这个报销单有问题。",
            "B: 什么问题？我按照流程填的。",
            "A: 他们说发票日期不对。",
        ],
        "B: 这明明就是上周的发票！财务部每次都在鸡蛋里挑骨头，烦死了！",
        "anger", "inform"
    ),
    (
        [
            "A: 你怎么又迟到？",
            "B: 地铁故障。",
            "A: 你每次都这一个理由。",
        ],
        "B: 你不信拉倒！我天天通勤三小时你试试！",
        "anger", "directive"
    ),
    # --- 追加对话: disgust ---
    (
        [
            "A: 你尝尝这个新出的零食。",
            "B: 这是什么味道？好怪。",
            "A: 螺蛳粉味的薯片。",
        ],
        "B: 天哪这是什么黑暗料理！一股臭袜子味！快拿开！",
        "disgust", "directive"
    ),
    (
        [
            "A: 听说隔壁那个房东又坑租客了。",
            "B: 怎么了？",
            "A: 扣押金不给，还编各种理由。",
        ],
        "B: 这种人真是社会的败类，靠欺负年轻人赚钱，太恶心了。",
        "disgust", "inform"
    ),
    (
        [
            "A: 你看这个网红吃播视频。",
            "B: 怎么吃相这么难看？",
            "A: 她为了流量故意这样。",
        ],
        "B: 太令人不适了。为了流量什么都干得出来，取关了。",
        "disgust", "inform"
    ),
    # --- 追加对话: fear ---
    (
        [
            "A: 你听说了吗？昨晚小区有人入室盗窃。",
            "B: 哪栋楼？",
            "A: 就我们隔壁那栋，半夜两点。",
        ],
        "B: 天哪，我家门锁还是老式的。今晚我肯定睡不着了。",
        "fear", "inform"
    ),
    (
        [
            "A: 检查报告出来了。",
            "B: 怎么说？",
            "A: 医生说需要做进一步检查。",
        ],
        "B: 进一步检查是什么意思？是不是有什么问题？你跟我说实话。",
        "fear", "question"
    ),
    (
        [
            "A: 外面有人按门铃。",
            "B: 这么晚了谁啊？你看看是谁。",
            "A: 看不清，外面太黑了。",
        ],
        "B: 别开门！先问问是谁。我一个人在家有点怕。",
        "fear", "directive"
    ),
    (
        [
            "A: 孩子发烧到39度了。",
            "B: 吃药了吗？",
            "A: 吃了退烧药但没退。",
        ],
        "B: 走，马上去急诊！别等了！",
        "fear", "directive"
    ),
    # --- 追加对话: joy ---
    (
        [
            "A: 猜猜我带了什么回来？",
            "B: 什么？",
            "A: 你最喜欢的那个蛋糕店的蛋糕！",
        ],
        "B: 真的吗！天哪你怎么知道我今天特别想吃甜的！你太懂我了！",
        "joy", "commissive"
    ),
    (
        [
            "A: 我们项目提前完成了！",
            "B: 太棒了！比截止日期早了整整一周！",
            "A: 客户很满意，说要推荐我们给其他公司。",
        ],
        "B: 太好了！今晚我请大家吃饭庆祝！大家辛苦了！",
        "joy", "commissive"
    ),
    (
        [
            "A: 你面试通过了！",
            "B: 真的？你不是在开玩笑吧？",
            "A: 真的，HR刚给我打的电话。",
        ],
        "B: 天哪！我太开心了！面了十几家终于拿到了！今晚必须喝一杯！",
        "joy", "commissive"
    ),
    (
        [
            "A: 今年年终奖发了不少。",
            "B: 多少？",
            "A: 六个月！",
        ],
        "B: 六个月？！公司这是发财了啊！走，我请客！",
        "joy", "commissive"
    ),
    (
        [
            "A: 生日快乐！",
            "B: 谢谢！你们怎么都来了？",
            "A: 我们策划了这个惊喜很久了。",
        ],
        "B: 我真的太感动了，没想到你们都记得。这是我过得最好的生日！",
        "joy", "commissive"
    ),
    # --- 追加对话: sadness ---
    (
        [
            "A: 怎么一个人坐在这里？",
            "B: 想一个人待会。",
            "A: 出什么事了吗？",
        ],
        "B: 今天是我妈的忌日。十年了，我还是没能习惯没有她的日子。",
        "sadness", "inform"
    ),
    (
        [
            "A: 你眼睛怎么肿了？",
            "B: 没事。",
            "A: 哭过了？发生什么了？",
        ],
        "B: 没什么大事。就是突然觉得生活好难，房租要涨了，工资没涨，身体也出问题了。",
        "sadness", "inform"
    ),
    (
        [
            "A: 今天怎么没去上课？",
            "B: 不想去。",
            "A: 是不是又因为那个同学？",
        ],
        "B: 他们把我从小组群里移除了。四个人一组，没有人选我。",
        "sadness", "inform"
    ),
    (
        [
            "A: 你看起来心情不好。",
            "B: 我爸住院了。",
            "A: 严重吗？",
        ],
        "B: 医生说可能要做手术。我请假回来照顾他，看到他躺在病床上的样子，突然觉得他老了。",
        "sadness", "inform"
    ),
    # --- 追加对话: surprise ---
    (
        [
            "A: 你猜我今天遇到谁了？",
            "B: 谁？",
            "A: 小学班主任王老师！",
        ],
        "B: 不会吧！她都退休这么多年了！你怎么认出来的？",
        "surprise", "question"
    ),
    (
        [
            "A: 我中奖了！",
            "B: 什么奖？彩票吗？",
            "A: 公司年会抽奖，我中了头奖！",
        ],
        "B: 真的假的？！你这个人从来就没中过奖！太不可思议了！",
        "surprise", "question"
    ),
    (
        [
            "A: 你知道吗，老张要辞职了。",
            "B: 他不是刚升职吗？",
            "A: 听说他拿到了一个更好的offer。",
        ],
        "B: 真没想到！他在这里干了八年了，说走就走？太突然了。",
        "surprise", "inform"
    ),
    (
        [
            "A: 我买了今晚的话剧票。",
            "B: 什么话剧？",
            "A: 你最喜欢的那部《暗恋桃花源》。",
        ],
        "B: 不是吧！这个票不是一个月前就售罄了吗？你怎么买到的？",
        "surprise", "question"
    ),
    # --- 追加对话: neutral ---
    (
        [
            "A: 明天的会议几点开始？",
            "B: 上午十点。",
            "A: 需要准备什么材料吗？",
        ],
        "B: 把上个季度的销售数据带上就行。",
        "neutral", "inform"
    ),
    (
        [
            "A: 快递到了，放在门卫室了。",
            "B: 好的，我下班去拿。",
            "A: 记得在系统里确认收货。",
        ],
        "B: 知道了，谢谢提醒。",
        "neutral", "inform"
    ),
    (
        [
            "A: 你今晚想吃什么？",
            "B: 随便。",
            "A: 火锅还是炒菜？",
        ],
        "B: 都行，你决定就好。",
        "neutral", "inform"
    ),
    (
        [
            "A: 这个文档需要盖章。",
            "B: 盖什么章？",
            "A: 公司公章。",
        ],
        "B: 那个章在行政那里，你去找一下小李。",
        "neutral", "inform"
    ),
    (
        [
            "A: 周末去爬山吗？",
            "B: 看天气吧。",
            "A: 天气预报说周六晴天。",
        ],
        "B: 那就周六去吧，我带上水和零食。",
        "neutral", "commissive"
    ),
]


# 角色人格模板
CHARACTER_TEMPLATES = [
    {
        "name": "林小雅",
        "personality": {"openness": 0.7, "conscientiousness": 0.6, "extraversion": 0.75, "agreeableness": 0.65, "neuroticism": 0.55},
        "attachment_style": "secure",
    },
    {
        "name": "周志强",
        "personality": {"openness": 0.45, "conscientiousness": 0.8, "extraversion": 0.55, "agreeableness": 0.5, "neuroticism": 0.35},
        "attachment_style": "secure",
    },
    {
        "name": "方小雨",
        "personality": {"openness": 0.6, "conscientiousness": 0.65, "extraversion": 0.35, "agreeableness": 0.8, "neuroticism": 0.7},
        "attachment_style": "anxious",
    },
    {
        "name": "陈浩宇",
        "personality": {"openness": 0.5, "conscientiousness": 0.55, "extraversion": 0.4, "agreeableness": 0.35, "neuroticism": 0.5},
        "attachment_style": "avoidant",
    },
    {
        "name": "赵雪晴",
        "personality": {"openness": 0.85, "conscientiousness": 0.4, "extraversion": 0.7, "agreeableness": 0.6, "neuroticism": 0.6},
        "attachment_style": "fearful_avoidant",
    },
    {
        "name": "孙文博",
        "personality": {"openness": 0.55, "conscientiousness": 0.75, "extraversion": 0.5, "agreeableness": 0.7, "neuroticism": 0.3},
        "attachment_style": "secure",
    },
    {
        "name": "李思瑶",
        "personality": {"openness": 0.65, "conscientiousness": 0.45, "extraversion": 0.6, "agreeableness": 0.75, "neuroticism": 0.65},
        "attachment_style": "anxious",
    },
    {
        "name": "吴凯",
        "personality": {"openness": 0.4, "conscientiousness": 0.7, "extraversion": 0.65, "agreeableness": 0.4, "neuroticism": 0.45},
        "attachment_style": "dismissive_avoidant",
    },
]


def make_character_state(name: str, base_personality: dict, attachment: str) -> dict:
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


# 每个对话生成多个角色变体以实现 ~150 用例总量
TEMPLATES_PER_DIALOGUE = 2

def make_case(idx: int, history: list, current_utterance: str, emotion: str,
              dialog_act: str, template_idx: int) -> dict:
    """为单个对话+角色模板生成验证用例。"""
    mapping = DIALOG_EMOTION_MAP[emotion]
    base_emotion = mapping["base"]
    pleasantness = mapping["pleasantness"]

    # 生成对话历史文本
    history_text = "\n".join(history)
    full_context = history_text + "\n" + current_utterance

    tmpl = CHARACTER_TEMPLATES[template_idx % len(CHARACTER_TEMPLATES)]

    case = {
        "id": f"dailyd_{idx:04d}_{template_idx}",
        "source": f"DailyDialog (Li et al., 2017) — {emotion}, act={dialog_act}",
        "domain": "dialogue_emotion",
        "character_state": make_character_state(tmpl["name"], tmpl["personality"], tmpl["attachment_style"]),
        "event": {
            "description": full_context,
            "type": "social",
            "participants": [],
            "significance": round(0.4 + abs(pleasantness) * 0.3, 2),
            "tags": ["dialogue", "dailydialog", emotion, dialog_act],
        },
        "expected": {
            "plutchik_emotion": {
                "internal.dominant": {"in": [base_emotion]},
                "internal.intensity": {"min": 0.35},
                "internal.pleasantness": {
                    "direction": "positive" if pleasantness >= 0 else "negative"
                },
            },
            "response_generator": {"response_text": {"not_empty": True}},
        },
        "_dialog_emotion": emotion,
        "_dialog_act": dialog_act,
        "_history": history,
        "_current": current_utterance,
    }
    return case


def extract_cases(sample: int = 0) -> list[dict]:
    """从内置对话数据生成验证用例。"""
    random.seed(42)
    cases = []

    for idx, (history, current_utterance, emotion, dialog_act) in enumerate(BUILTIN_DIALOGUES):
        for ti in range(TEMPLATES_PER_DIALOGUE):
            template_idx = idx * TEMPLATES_PER_DIALOGUE + ti
            case = make_case(idx, history, current_utterance, emotion, dialog_act, template_idx)
            cases.append(case)

    if sample > 0:
        random.shuffle(cases)
        cases = cases[:sample]

    return cases


def print_summary(cases: list[dict]):
    """打印统计摘要。"""
    print(f"Generated {len(cases)} DailyDialog-derived cases\n")

    # 情感分布
    emotion_counts = {}
    act_counts = {}
    for c in cases:
        em = c.get("_dialog_emotion", "?")
        emotion_counts[em] = emotion_counts.get(em, 0) + 1
        act = c.get("_dialog_act", "?")
        act_counts[act] = act_counts.get(act, 0) + 1

    print(f"Emotion distribution ({len(emotion_counts)} categories):")
    for e, n in sorted(emotion_counts.items(), key=lambda x: -x[1]):
        print(f"  {e}: {n}")

    print(f"\nDialog act distribution ({len(act_counts)} categories):")
    for a, n in sorted(act_counts.items(), key=lambda x: -x[1]):
        print(f"  {a}: {n}")

    # 角色分布
    names = set(c["character_state"]["name"] for c in cases)
    print(f"\nUnique character profiles: {len(names)}")
    for n in sorted(names):
        print(f"  {n}")

    # 多轮对话信息
    max_history = max(len(c.get("_history", [])) for c in cases)
    avg_history = sum(len(c.get("_history", [])) for c in cases) / max(len(cases), 1)
    print(f"\nDialogue turns: max={max_history}, avg={avg_history:.1f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract DailyDialog test cases")
    parser.add_argument("--sample", type=int, default=0, help="Number of cases to sample (0=all)")
    args = parser.parse_args()

    cases = extract_cases(sample=args.sample)
    print_summary(cases)

    out_path = OUTPUT_DIR / "dailydialog_cases.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(cases, f, ensure_ascii=False, indent=2)
    print(f"\nSaved to {out_path}")
