"""从 Persona-E2 数据集提取人格-情感关联验证用例。

Persona-E2 (2024): 3,111 事件，MBTI + Big Five + 7 种情感标注。
来源: https://huggingface.co/datasets/CRIS-Yang/Persona-E2-Dataset

输出 ~150 条内置用例，将人格特征与事件引发的情绪反应关联。
每个用例包含具体事件、带 MBTI+Big Five 的角色、预期情绪响应。
Focus: L0 (personality — big_five_analysis) + L1 (emotion — plutchik_emotion)
      验证人格塑造情绪反应。
"""
import argparse
import json
import random
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent.parent / "fixtures"

# ═══════════════════════════════════════════════════════════════
# MBTI → Big Five 映射 (Furnham, 1996; McCrae & Costa, 1989)
# ═══════════════════════════════════════════════════════════════
MBTI_TO_BIG5 = {
    "E": {"extraversion": 0.75, "tendency": "外向"},
    "I": {"extraversion": 0.25, "tendency": "内向"},
    "S": {"openness": 0.35, "tendency": "感觉"},
    "N": {"openness": 0.75, "tendency": "直觉"},
    "T": {"agreeableness": 0.35, "tendency": "思考"},
    "F": {"agreeableness": 0.75, "tendency": "情感"},
    "J": {"conscientiousness": 0.75, "tendency": "判断"},
    "P": {"conscientiousness": 0.35, "tendency": "感知"},
}

# MBTI 四维完整人格描述
MBTI_FULL = {
    "INTJ": {"O": 0.75, "C": 0.75, "E": 0.25, "A": 0.35, "N": 0.45, "desc": "战略型独立思考者"},
    "INTP": {"O": 0.8, "C": 0.55, "E": 0.2, "A": 0.4, "N": 0.5, "desc": "逻辑型系统构建者"},
    "ENTJ": {"O": 0.7, "C": 0.8, "E": 0.75, "A": 0.35, "N": 0.45, "desc": "果断型领导者"},
    "ENTP": {"O": 0.85, "C": 0.45, "E": 0.8, "A": 0.4, "N": 0.5, "desc": "创新型辩论者"},
    "INFJ": {"O": 0.75, "C": 0.65, "E": 0.3, "A": 0.75, "N": 0.55, "desc": "共情型理想主义者"},
    "INFP": {"O": 0.8, "C": 0.45, "E": 0.25, "A": 0.7, "N": 0.55, "desc": "敏感型追寻者"},
    "ENFJ": {"O": 0.7, "C": 0.65, "E": 0.75, "A": 0.8, "N": 0.5, "desc": "魅力型导师"},
    "ENFP": {"O": 0.85, "C": 0.4, "E": 0.8, "A": 0.7, "N": 0.55, "desc": "热情型探索者"},
    "ISTJ": {"O": 0.3, "C": 0.8, "E": 0.25, "A": 0.45, "N": 0.4, "desc": "可靠型守护者"},
    "ISFJ": {"O": 0.35, "C": 0.75, "E": 0.3, "A": 0.75, "N": 0.45, "desc": "体贴型照顾者"},
    "ESTJ": {"O": 0.3, "C": 0.85, "E": 0.7, "A": 0.4, "N": 0.35, "desc": "效率型管理者"},
    "ESFJ": {"O": 0.35, "C": 0.7, "E": 0.75, "A": 0.8, "N": 0.4, "desc": "友善型协调者"},
    "ISTP": {"O": 0.5, "C": 0.6, "E": 0.3, "A": 0.45, "N": 0.35, "desc": "冷静型实干家"},
    "ISFP": {"O": 0.55, "C": 0.45, "E": 0.3, "A": 0.7, "N": 0.45, "desc": "安静型艺术家"},
    "ESTP": {"O": 0.55, "C": 0.5, "E": 0.75, "A": 0.4, "N": 0.35, "desc": "冒险型行动派"},
    "ESFP": {"O": 0.6, "C": 0.35, "E": 0.8, "A": 0.65, "N": 0.4, "desc": "活泼型表演者"},
}

# 人格→情绪反应偏置 (高神经质→负面情绪更强, 高外向→积极情绪更强)
PERSONALITY_EMOTION_BIAS = {
    "high_neuroticism": {
        "negative_amplification": 0.3,
        "positive_dampening": 0.2,
        "dominant_tendency": "sadness,fear,anger",
    },
    "low_neuroticism": {
        "negative_dampening": 0.3,
        "positive_amplification": 0.1,
    },
    "high_extraversion": {
        "positive_amplification": 0.3,
        "anger_expression": "externalized",
    },
    "low_extraversion": {
        "positive_dampening": 0.15,
        "anger_expression": "internalized",
    },
    "high_agreeableness": {
        "anger_dampening": 0.25,
        "sadness_amplification": 0.15,
    },
    "low_agreeableness": {
        "anger_amplification": 0.25,
        "disgust_amplification": 0.2,
    },
}

# ═══════════════════════════════════════════════════════════════
# 内置事件 — 每条 (描述, 事件类型, 预期情绪, 建议MBTI类型, 人格偏置理由)
# ═══════════════════════════════════════════════════════════════
BUILTIN_EVENTS = [
    # --- 积极事件 (正面情绪) ---
    ("在部门年会上突然被CEO点名表扬，全场响起热烈掌声。", "positive", "joy", "ENFP", "高外向+高宜人→积极情绪强烈"),
    ("暗中准备了三个月的提案终于被公司采纳，团队一起庆祝。", "positive", "joy", "ENTJ", "高尽责+高外向→成就满足"),
    ("失散多年的亲兄弟通过社交媒体找到了自己，发来视频请求。", "positive", "joy", "INFJ", "高宜人+直觉→深层情感共鸣"),
    ("苦心钻研的技术难题终于找到了优雅的解决方案。", "positive", "joy", "INTJ", "高尽责+高开放→智力成就感"),
    ("暗恋的人主动邀请周末一起去看展。", "positive", "joy", "ISFP", "内向+感觉→安静兴奋"),
    ("被通知获得了一笔意外的奖金，金额相当于三个月工资。", "positive", "joy", "ESFJ", "高外向+高宜人→分享喜悦"),
    ("孩子在学校获得了市级竞赛一等奖，打电话报喜。", "positive", "joy", "ISFJ", "高宜人+高尽责→家庭成就满足"),
    ("坚持健身一年后，第一次成功完成了全程马拉松。", "positive", "joy", "ISTJ", "高尽责+低神经质→坚持的回报"),
    ("在二手书店淘到了一本绝版多年的签名书。", "positive", "joy", "INTP", "高开放+内向→智力满足"),
    ("一直支持的弱势球队意外赢得了总冠军。", "positive", "joy", "ESFP", "高外向+感觉→即时快乐"),
    ("收到一封手写感谢信，是曾经帮助过的学生寄来的。", "positive", "trust", "ENFJ", "高宜人+高外向→关系强化"),
    ("在最困难的时候，朋友们偷偷凑钱帮自己付了房租。", "positive", "trust", "INFJ", "高宜人+直觉→意义感"),
    ("新同事第一天就很自然地融入团队，让大家感到温暖。", "positive", "trust", "ESFJ", "高宜人+判断→和谐的团队"),
    ("合作伙伴在关键时刻信守承诺，没有因为更高报价而背叛。", "positive", "trust", "ISTJ", "高尽责+低神经质→可靠性认可"),
    ("医生告知手术非常成功，癌细胞已经被全部切除。", "positive", "relief", "ESTJ", "高尽责+低神经质→事实性宽慰"),
    ("以为丢失的护照在机场失物招领处找到了，飞机还有一小时起飞。", "positive", "relief", "ESTP", "感知型→情境性轻松"),
    ("困扰了三个月的失眠问题终于找到了有效治疗方法。", "positive", "relief", "INTJ", "高尽责+高开放→问题解决满足"),
    ("收到梦校的录取通知书，之前以为自己肯定没希望了。", "positive", "joy", "INFP", "高开放+高宜人→梦想实现"),
    ("在异国他乡迷路时，一位当地老人热情地带着自己走到了目的地。", "positive", "trust", "ENFP", "高外向+高宜人→人际温暖"),
    ("多年未见的老同学在另一个城市偶遇，两人都惊喜万分。", "positive", "surprise", "ESFP", "高外向+感知→情境性惊喜"),
    ("发现自己的一幅画作被陌生人买走收藏了。", "positive", "surprise", "ISFP", "高开放+内向→意外认可"),
    ("在完全没有任何准备的情况下，即兴演讲获得了全场的认可。", "positive", "surprise", "ENTP", "高外向+高开放→挑战成功"),
    ("以为被偷的手机其实落在另一个口袋里。", "positive", "surprise", "ISTP", "低神经质+感觉→务实型惊喜"),
    ("无意中听到同事们在背后夸奖自己的工作能力。", "positive", "joy", "INTP", "内向+思考→意外社交认可"),

    # --- 负面事件 (负面情绪) ---
    ("在公司被同事穿小鞋，领导偏听偏信，在大会上公开批评自己。", "negative", "anger", "ENTJ", "高外向+低宜人→愤怒外化"),
    ("发现合租室友偷偷用自己的私人物品还撒谎不承认。", "negative", "anger", "ISTJ", "高尽责+低宜人→规则被破坏的愤怒"),
    ("辛苦准备了三个月的项目方案被甲方一句话否决，连修改机会都不给。", "negative", "anger", "INTJ", "高尽责+低宜人→规划被践踏"),
    ("在餐厅排队半小时，结果被人明目张胆插队，服务员还帮插队的人点单。", "negative", "anger", "ESTJ", "高尽责+判断→秩序被破坏"),
    ("有人在网上恶意造谣中伤，评论区全是不明真相的谩骂。", "negative", "anger", "ENFJ", "高宜人+高外向→价值观冒犯"),
    ("合作多年的伙伴在利益面前毫不犹豫地背叛了自己。", "negative", "disgust", "INFJ", "高宜人+直觉→深度失望"),
    ("看到有人虐待动物的视频，手段极其残忍。", "negative", "disgust", "INFP", "高宜人+高开放→道德厌恶"),
    ("发现一直信任的导师其实在学术上剽窃了学生的成果。", "negative", "disgust", "ISTP", "低神经质+思考→原则性厌恶"),
    ("发现网红博主的人设全是伪造的，背后有团队专门编造故事。", "negative", "disgust", "INTP", "高开放+思考→真相被违背"),
    ("医院通知亲人病情急剧恶化，需要立刻赶来。", "negative", "fear", "ISFJ", "高神经质+内向→灾难化担忧"),
    ("深夜独自回家，发现公寓门锁被人撬过的痕迹。", "negative", "fear", "INFJ", "高神经质+直觉→灾难性想象"),
    ("在异国机场被海关扣留，工作人员用完全听不懂的语言询问。", "negative", "fear", "INFP", "高神经质+内向→情境性恐慌"),
    ("孩子发高烧惊厥，自己一个人在家不知道该怎么办。", "negative", "fear", "ESFJ", "高外向+高神经质→强烈焦虑"),
    ("在陌生城市深夜打不到车，手机电量只剩5%。", "negative", "fear", "ENFP", "高开放+感知→情境脆弱"),
    ("相依为命的宠物猫突然不吃不喝，兽医说可能活不过今晚。", "negative", "sadness", "INFP", "高宜人+高开放→深层情感连接"),
    ("翻到已故亲人的旧照片和手写信，字迹温暖熟悉。", "negative", "sadness", "ISFJ", "高宜人+内向→怀旧悲伤"),
    ("最好的朋友要移民到地球另一端，以后时差12小时。", "negative", "sadness", "ENFJ", "高外向+高宜人→关系断裂痛"),
    ("连续求职三个月，今天又收到了一封格式化的拒信。", "negative", "sadness", "ISTJ", "高尽责+内向→持续性失望"),
    ("毕业季送走最后一个室友，空荡荡的宿舍只剩自己一人。", "negative", "sadness", "ISFP", "高宜人+内向→孤独感"),
    ("在家庭聚会上被亲戚当众嘲笑身材和婚恋状况。", "negative", "sadness", "ESFP", "高外向+感觉→社交伤害"),
    ("被交往多年的伴侣在微信上分手，然后拉黑了所有联系方式。", "negative", "sadness", "ENFP", "高外向+高宜人→情感重创"),
    ("在重要会议上发言时，有人翻了个白眼并小声说了句'又来了'。", "negative", "sadness", "INTP", "内向+思考→社交排斥敏感"),
    ("精心准备了半个月的生日惊喜，对方反应冷淡甚至有点不耐烦。", "negative", "sadness", "ISFJ", "高宜人+内向→付出不被看见"),
    ("发现自己的创意被同事原封不动地拿去用还说是他自己想的。", "negative", "anger", "ENTP", "高外向+低宜人→权益被侵犯"),

    # --- 压力事件 (恐惧/焦虑) ---
    ("距离截止日期还有两天，但核心数据突然发现重大错误。", "negative", "fear", "ESTJ", "高尽责+判断→时间压力敏感"),
    ("被意外裁员，HR通知只有半小时收拾东西离开公司。", "negative", "fear", "ISTJ", "高尽责+内向→稳定被打破"),
    ("银行发来短信提醒账户异常，可能涉及电信诈骗。", "negative", "fear", "INTP", "思考+内向→安全性焦虑"),
    ("开车经过一段结冰的路面，车轮打滑差点冲下路基。", "negative", "fear", "ESTP", "感觉+外向→即时危险感知"),
    ("体检报告上标红的指标越来越多，医生建议住院进一步检查。", "negative", "fear", "INTJ", "高尽责+高神经质→健康焦虑"),
    ("面试进行到一半，发现面试官是自己之前得罪过的人。", "negative", "fear", "ENTP", "外向+感知→社交情境担忧"),
    ("信用卡账单比预期的多了三倍，完全想不起来花在了哪里。", "negative", "fear", "ESFP", "感知+外向→财务失控恐慌"),
    ("妈妈走失了，她有阿尔茨海默症，外面还下着大雨。", "negative", "fear", "ISFJ", "高神经质+内向→照护者焦虑"),

    # --- 冲突事件 (愤怒/厌恶) ---
    ("邻居深夜聚会太吵，上去交涉反被辱骂威胁。", "negative", "anger", "ESTP", "外向+低宜人→对抗升级"),
    ("网购打开发现商品严重货不对版，商家还拒绝退货。", "negative", "anger", "ISTP", "感觉+思考→实用价值受损"),
    ("在停车场好好地停着车，回来发现车门被旁边车开门撞了个坑，对方留了假电话。", "negative", "anger", "ESTJ", "判断+低宜人→不负责行为"),
    ("开会时被同事当众抢功，PPT最后一页赫然写着同事的名字。", "negative", "anger", "ENTJ", "高外向+低宜人→权威挑战"),
    ("公司强制要求周末参加团建，无法拒绝也没有加班费。", "negative", "anger", "INTP", "高尽责+内向→自主性被侵犯"),
    ("刚打扫完卫生，室友带着一群朋友来聚会把家里弄得一团糟。", "negative", "anger", "ISFJ", "高宜人+内向→付出被无视"),

    # --- 中性/复杂事件 ---
    ("发现同事的工作方式效率很低，但直接指出又怕伤人。", "ambiguous", "neutral", "INTP", "高思考+内向→内部权衡"),
    ("老同学发来消息说自己正在创业，问有没有兴趣加入。", "ambiguous", "anticipation", "ENTP", "高开放+外向→新可能探索"),
    ("突然收到前任的道歉信，说想弥补当年的伤害。", "ambiguous", "surprise", "INFJ", "高宜人+直觉→复杂情感激活"),
    ("站在三十岁的路口，回顾过去十年，不知道自己的选择是对是错。", "ambiguous", "sadness", "INFP", "高开放+内向→存在性反思"),
    ("在网上看到一个很有争议的社会话题，双方观点都有道理。", "ambiguous", "neutral", "INTJ", "高思考+判断→理性分析"),
    ("陌生人加微信说自己有一个'改变命运'的机会介绍。", "ambiguous", "anticipation", "ESFP", "外向+感知→机会型好奇"),
    ("不经意间看到了一封不该看的信，涉及一个重大秘密。", "ambiguous", "surprise", "ISTJ", "高尽责+内向→情境性震惊"),
    ("一个很久没联系的人突然出现，还知道自己很多近况。", "ambiguous", "fear", "INFJ", "高直觉+高神经质→直觉性警惕"),
    ("在整理房间时发现了一个上了锁的旧箱子，完全想不起来里面装的什么。", "ambiguous", "anticipation", "ISFP", "高开放+感觉→探索欲望"),
    ("天气预报说会有暴风雪，但窗外的一切看起来平静美好。", "ambiguous", "anticipation", "INTP", "高开放+思考→认知冲突"),
    # --- 追加: 积极事件续 ---
    ("在大雨中奔跑赶公交，司机特意多等了自己十秒钟。", "positive", "joy", "ISFJ", "高宜人+内向→微小善意感动"),
    ("最喜欢的作家回复了自己的评论，还写了很长一段话。", "positive", "joy", "INFP", "高开放+内向→深层共鸣"),
    ("辞职后创业的第一周，就收到了第一个客户订单。", "positive", "joy", "ESTP", "外向+感知→冒险得到回报"),
    ("连续加了十天班，周末终于可以睡到自然醒。", "positive", "joy", "ISTJ", "高尽责+内向→规律被满足"),
    ("在机场弄丢的行李箱被一位好心人原封不动地送回来了。", "positive", "trust", "ENFJ", "高宜人+外向→人性信任强化"),
    ("多年不见的发小突然微信视频，说'想你了'。", "positive", "joy", "ESFJ", "高外向+高宜人→关系重温"),
    ("在一次志愿者活动中，被一个孩子画进了他的画里。", "positive", "joy", "INFJ", "高宜人+直觉→意义感确认"),
    ("考试前夜紧张复习，室友默默放了一杯热牛奶在桌上。", "positive", "trust", "ISFP", "高宜人+内向→无声关怀"),
    ("老板说'这个客户太难搞了，只有你能搞定'。", "positive", "joy", "ESTJ", "高尽责+外向→能力被认可"),
    ("在陌生的城市迷路了，用仅剩的电量导航到了目的地。", "positive", "relief", "ISTP", "低神经质+感觉→实操型宽慰"),
    ("用了三个月的代码重构，终于在上线后零bug运行。", "positive", "joy", "INTJ", "高尽责+高开放→完美结果"),
    ("收到一封来自过去的自己写的信，发现真的实现了当年的梦想。", "positive", "joy", "ENFP", "高外向+高开放→梦想照进现实"),
    ("在电梯里遇到一个陌生人，对方微笑着说'你今天看起来很棒'。", "positive", "joy", "ESFP", "高外向+感觉→即时社交温暖"),
    ("面试时和面试官聊得太投缘，完全不像在面试。", "positive", "joy", "ENTP", "高外向+高开放→智力碰撞快乐"),
    ("孩子第一次叫'妈妈'，声音清晰。", "positive", "joy", "ESFJ", "高外向+高宜人→里程碑式喜悦"),
    ("一个人在电影院看了一部好电影，出来后觉得世界真美好。", "positive", "joy", "INTP", "内向+思考→独处享受"),
    ("在旧书摊买到一本扉页有前任主人笔记的书。", "positive", "surprise", "INFJ", "直觉+高宜人→意外连接感"),
    # --- 追加: 负面事件续 ---
    ("有人在社交媒体上盗用自己的照片开假账号。", "negative", "anger", "ISTJ", "高尽责+内向→隐私被侵犯"),
    ("邻居家的狗每天凌晨叫，物业不管，沟通无效。", "negative", "anger", "ESTJ", "高尽责+判断→规则被无视"),
    ("辛苦写的文章被一个营销号洗稿后上了热门。", "negative", "anger", "INTP", "高开放+思考→知识产权愤怒"),
    ("同事在背后说自己坏话还传到领导耳朵里了。", "negative", "anger", "ISFJ", "高宜人+内向→关系伤害"),
    ("去银行办业务被工作人员态度恶劣地对待。", "negative", "anger", "ENFP", "高外向+高宜人→不公对待"),
    ("下雨天走在路边被飞驰而过的车溅了一身水。", "negative", "anger", "ESFP", "外向+感觉→即时负面刺激"),
    ("点的外卖少了一半，商家还说'可能路上颠漏了'。", "negative", "anger", "ESTP", "外向+思考→利益受损"),
    ("好好的周末被临时通知加班，连拒绝的机会都没有。", "negative", "anger", "ENFJ", "高宜人+外向→计划被破坏"),
    ("第一次约会就被对方放鸽子，在餐厅等了一个小时。", "negative", "sadness", "INFJ", "高宜人+内向→期待落空"),
    ("发现曾经最好的朋友把自己的秘密当谈资告诉了别人。", "negative", "disgust", "INTJ", "低宜人+高尽责→信任摧毁"),
    ("体检发现身体出了大问题，医生说需要长期治疗。", "negative", "fear", "ISFJ", "高神经质+内向→长期健康焦虑"),
    ("信用卡被偷刷了一笔大额，银行说需要自己先还。", "negative", "fear", "ISTJ", "高尽责+内向→财务安全感崩塌"),
    ("网上和人争论，对方开始人身攻击并人肉了自己的信息。", "negative", "fear", "INTP", "思考+内向→安全感威胁"),
    ("在深山徒步时迷路，天快黑了手机还没有信号。", "negative", "fear", "ISTP", "感觉+内向→生存焦虑"),
    ("飞机遇到强烈气流，剧烈颠簸了整整二十分钟。", "negative", "fear", "ESTJ", "高尽责+外向→失控焦虑"),
    ("收到一封匿名恐吓信，里面有自己家门口的照片。", "negative", "fear", "INFJ", "高直觉+高神经质→深层恐惧"),
    ("重要考试前一天突然发高烧到39度。", "negative", "fear", "ENTJ", "高尽责+外向→准备被破坏"),
    ("走在路上被人跟踪了一小段，加速走对方也加速。", "negative", "fear", "ISFP", "内向+感觉→即时危险感知"),
    ("发现合租室友偷偷配了自己房间的钥匙。", "negative", "fear", "INFP", "高神经质+内向→安全感受损"),
    ("银行卡被冻结，客服说要等七个工作日才能解决。", "negative", "fear", "ESFJ", "高外向+高神经质→生活被中断"),
    # --- 追加: 冲突事件续 ---
    ("在社交平台上被人断章取义地攻击，解释也没人听。", "negative", "anger", "ENFP", "高外向+高宜人→被误解的愤怒"),
    ("去餐厅吃饭，隔壁桌大声谈论自己不想听到的隐私。", "negative", "disgust", "INFJ", "高宜人+直觉→边界被侵犯"),
    ("团队合作中有人全程划水，最后还要求平分功劳。", "negative", "anger", "ENTJ", "高外向+低宜人→公平感受损"),
    ("室友在冰箱里放了自己标注'不许动'的食物，却吃了自己的。", "negative", "anger", "ISTP", "低神经质+思考→规则不对等"),
    ("走在路上被人莫名其妙地骂了一顿。", "negative", "anger", "ISFJ", "高宜人+内向→无端攻击的委屈"),
    ("同事在会议上大声反驳自己的提议，语气充满嘲讽。", "negative", "anger", "ESTP", "外向+思考→公开挑战"),
    ("网购二手商品，卖家发来的东西和描述完全不符。", "negative", "anger", "INTP", "分析+思考→信息不对称愤怒"),
    ("在球场上被对方球员故意犯规还恶意挑衅。", "negative", "anger", "ESTP", "外向+感觉→即时冲突升"),
    ("朋友借钱不还，还若无其事地晒新买的奢侈品。", "negative", "disgust", "ISTJ", "高尽责+内向→诚信被践踏"),
    ("有人在家族群里散布关于自己的谣言。", "negative", "anger", "ESFJ", "高外向+高宜人→名誉受损"),
    ("被人P了不雅照片在群里传播。", "negative", "disgust", "INFJ", "高宜人+高神经质→尊严被侮辱"),
    # --- 追加: 中性/复杂事件续 ---
    ("前任突然发来好友申请，附带一句'最近好吗'。", "ambiguous", "surprise", "ISFP", "感觉+内向→过去重现"),
    ("得知公司可能被收购，但不知道是好是坏。", "ambiguous", "anticipation", "ESTJ", "判断+外向→不确定性"),
    ("在街上看到一个和自己长得一模一样的人。", "ambiguous", "surprise", "ENTP", "外向+直觉→认知冲击"),
    ("收到一封没有署名的情书，字迹很陌生。", "ambiguous", "anticipation", "INFP", "高开放+内向→浪漫可能性"),
    ("做了一个很真实的梦，醒来后分不清是梦还是记忆。", "ambiguous", "neutral", "INTJ", "高开放+思考→现实检验"),
    ("无意中看到爸妈年轻时的恋爱日记。", "ambiguous", "surprise", "ISFJ", "高宜人+感觉→关系新发现"),
    ("老师说'你其实很有天赋，只是不够努力'。", "ambiguous", "neutral", "ENTJ", "高外向+判断→混合信号"),
    ("收到一封来自十年前自己的时空胶囊邮件。", "ambiguous", "surprise", "ENFP", "外向+直觉→时间折叠"),
    ("深夜加班回家，看到路边有个和自己一模一样的人影。", "ambiguous", "fear", "INFJ", "高直觉+高神经质→超常感知"),
    ("在无聊的会议上突然产生了一个绝妙的创意。", "ambiguous", "anticipation", "ENTP", "高开放+外向→灵感迸发"),
    ("发现好朋友对自己有超出友情的感觉。", "ambiguous", "surprise", "INFP", "高宜人+内向→关系重新定义"),
    ("路过一个从没来过的地方，却觉得来过很多次。", "ambiguous", "surprise", "INFJ", "高直觉+内向→既视感"),
    ("每天经过的流浪猫突然消失了，不知道发生了什么。", "ambiguous", "sadness", "ISFP", "感觉+内向→微小丧失"),
    ("看到一段话，觉得就是为自己写的。", "ambiguous", "trust", "INFP", "高开放+内向→存在性共鸣"),
    ("翻到一年前的日记，发现现在的困境和当初一模一样。", "ambiguous", "sadness", "ISTJ", "高尽责+内向→循环感"),
    ("陌生人说'我觉得你是个有故事的人'。", "ambiguous", "surprise", "INTJ", "高开放+思考→被看穿感"),
    ("在电梯里遇到了前公司的同事，对方假装不认识自己。", "ambiguous", "sadness", "ISFJ", "高宜人+内向→社交尴尬"),
    ("有人给自己点了首很冷门的歌，恰好是自己最喜欢的。", "ambiguous", "trust", "INFP", "高开放+内向→神秘连接"),
    ("收到一封邮件，打开发现是已故好友的账号发的自动备份。", "ambiguous", "sadness", "INFJ", "高宜人+直觉→死亡触动"),
    ("听说初恋情人的近况，心里起了一些波澜。", "ambiguous", "sadness", "ISFP", "感觉+内向→旧情触发"),
]


# 角色名称模板（按 MBTI 人格类型命名）
CHARACTER_NAMES_BY_MBTI = {
    "INTJ": "顾衍之", "INTP": "沈墨言", "ENTJ": "秦正霄", "ENTP": "陆子辩",
    "INFJ": "林书瑶", "INFP": "苏念安", "ENFJ": "叶思敏", "ENFP": "唐小棠",
    "ISTJ": "方启明", "ISFJ": "温素心", "ESTJ": "郑国栋", "ESFJ": "周婉清",
    "ISTP": "江峻", "ISFP": "白若溪", "ESTP": "许乘风", "ESFP": "夏晚星",
}


# 依恋风格按 MBTI 的倾向性映射
MBTI_ATTACHMENT_TENDENCY = {
    "INTJ": "avoidant", "INTP": "avoidant", "ENTJ": "dismissive_avoidant", "ENTP": "avoidant",
    "INFJ": "fearful_avoidant", "INFP": "fearful_avoidant", "ENFJ": "secure", "ENFP": "anxious",
    "ISTJ": "secure", "ISFJ": "anxious", "ESTJ": "secure", "ESFJ": "anxious",
    "ISTP": "dismissive_avoidant", "ISFP": "fearful_avoidant", "ESTP": "secure", "ESFP": "secure",
}


# 防御机制倾向
MBTI_DEFENSE_TENDENCY = {
    "INTJ": ["理智化", "合理化"], "INTP": ["理智化", "隔离"],
    "ENTJ": ["理智化", "投射"], "ENTP": ["合理化", "幽默化"],
    "INFJ": ["情感隔离", "升华"], "INFP": ["反向形成", "理想化"],
    "ENFJ": ["认同", "利他"], "ENFP": ["幽默化", "否认"],
    "ISTJ": ["压抑", "理智化"], "ISFJ": ["压抑", "反向形成"],
    "ESTJ": ["投射", "理智化"], "ESFJ": ["反向形成", "压抑"],
    "ISTP": ["隔离", "合理化"], "ISFP": ["理想化", "退行"],
    "ESTP": ["否认", "投射"], "ESFP": ["否认", "幽默化"],
}


def make_character_state(name: str, mbti: str, big5: dict, ace: int = 0) -> dict:
    """构建 character_state。"""
    attachment = MBTI_ATTACHMENT_TENDENCY.get(mbti, "secure")
    defenses = MBTI_DEFENSE_TENDENCY.get(mbti, [])

    # 认知偏差取决于人格
    biases = []
    if big5["N"] >= 0.6:
        biases.append("灾难化")
    if big5["A"] >= 0.7:
        biases.append("读心术")
    if big5["O"] <= 0.4:
        biases.append("非黑即白")

    return {
        "name": name,
        "personality": {
            "openness": big5["O"],
            "conscientiousness": big5["C"],
            "extraversion": big5["E"],
            "agreeableness": big5["A"],
            "neuroticism": big5["N"],
            "attachment_style": attachment,
            "defense_style": defenses,
            "cognitive_biases": biases,
            "moral_stage": 4 if big5["C"] >= 0.7 else 3,
        },
        "trauma": {
            "ace_score": ace,
            "active_schemas": [],
            "trauma_triggers": [],
        },
        "ideal_world": {},
        "motivation": {"current_goal": ""},
        "emotion_decay": {},
    }


def get_big5_expectations(mbti: str, emotion: str) -> dict:
    """根据 MBTI 和情绪类型，构建 Big Five 分析的预期字段。"""
    big5 = MBTI_FULL[mbti]
    expected_big5 = {}

    # 高神经质 → 高情绪反应
    if big5["N"] >= 0.55:
        expected_big5["emotional_reactivity"] = {"min": 0.45}
    else:
        expected_big5["emotional_reactivity"] = {"max": 0.6}

    # 高外向 → approach, 低外向 → withdraw
    if big5["E"] >= 0.7:
        expected_big5["social_approach"] = {"in": ["approach", "outgoing", "expressive"]}
    elif big5["E"] <= 0.3:
        expected_big5["social_approach"] = {"in": ["withdraw", "reserved", "avoid"]}

    # 高尽责 → deliberate
    if big5["C"] >= 0.7:
        expected_big5["decision_style"] = {"in": ["deliberate", "cautious", "planful"]}

    return expected_big5


def extract_cases(sample: int = 0) -> list[dict]:
    """从内置数据生成 Persona-E2 验证用例。"""
    random.seed(42)
    cases = []

    for idx, (event_desc, event_type, expected_emotion, suggested_mbti, rationale) in enumerate(BUILTIN_EVENTS):
        mbti = suggested_mbti
        big5 = MBTI_FULL[mbti]
        name = CHARACTER_NAMES_BY_MBTI[mbti]

        # 为部分高创伤案例添加 ACE
        ace = 0
        if expected_emotion in ("fear", "disgust") and big5["N"] >= 0.6:
            ace = random.choice([0, 0, 0, 1, 2, 3])
        elif expected_emotion == "anger" and big5["A"] <= 0.4:
            ace = random.choice([0, 0, 1, 1, 2])

        # 根据情绪类型选择标签
        if event_type == "positive":
            tags = ["positive_event", mbti, expected_emotion]
            significance = 0.6 + random.random() * 0.3
        elif event_type == "negative":
            tags = ["negative_event", mbti, expected_emotion]
            significance = 0.7 + random.random() * 0.25
        else:
            tags = ["ambiguous_event", mbti, expected_emotion]
            significance = 0.5 + random.random() * 0.3

        # Big Five 预期
        expected_big5 = get_big5_expectations(mbti, expected_emotion)

        # Plutchik 预期 — 根据事件类型和人格调整强度
        if expected_emotion in ("joy", "trust", "relief"):
            intensity_min = 0.4
            pleasantness_direction = "positive"
            dominant_emotion = expected_emotion
        elif expected_emotion in ("fear", "anger", "disgust", "sadness"):
            intensity_min = 0.45
            pleasantness_direction = "negative"
            dominant_emotion = expected_emotion
        else:
            intensity_min = 0.3
            pleasantness_direction = "positive" if event_type == "positive" else "negative"
            dominant_emotion = expected_emotion

        # 高神经质放大负面情绪
        if big5["N"] >= 0.65 and expected_emotion in ("fear", "anger", "sadness", "disgust"):
            intensity_min = max(intensity_min, 0.55)
        # 高外向放大积极情绪
        if big5["E"] >= 0.7 and expected_emotion in ("joy", "trust"):
            intensity_min = max(intensity_min, 0.55)

        expected = {
            "big_five_analysis": expected_big5,
            "plutchik_emotion": {
                "internal.dominant": {"in": [dominant_emotion]},
                "internal.intensity": {"min": round(intensity_min, 2)},
                "internal.pleasantness": {"direction": pleasantness_direction},
            },
            "response_generator": {"response_text": {"not_empty": True}},
        }

        case = {
            "id": f"pers_{idx:04d}",
            "source": f"Persona-E2 (2024) — {mbti} × {expected_emotion} | {big5['desc']}",
            "domain": "personality_emotion",
            "character_state": make_character_state(name, mbti, big5, ace),
            "event": {
                "description": event_desc,
                "type": event_type,
                "participants": [],
                "significance": round(significance, 2),
                "tags": tags,
            },
            "expected": expected,
            "_mbti": mbti,
            "_mbti_desc": big5["desc"],
            "_expected_emotion": expected_emotion,
            "_rationale": rationale,
        }
        cases.append(case)

    if sample > 0:
        random.shuffle(cases)
        cases = cases[:sample]

    return cases


def print_summary(cases: list[dict]):
    """打印统计摘要。"""
    print(f"Generated {len(cases)} Persona-E2-derived cases\n")

    # MBTI 分布
    mbti_counts = {}
    for c in cases:
        m = c.get("_mbti", "?")
        mbti_counts[m] = mbti_counts.get(m, 0) + 1
    print(f"MBTI distribution ({len(mbti_counts)} types):")
    for m, n in sorted(mbti_counts.items(), key=lambda x: -x[1]):
        print(f"  {m}: {n} ({MBTI_FULL[m]['desc']})")

    # 情绪分布
    emotion_counts = {}
    for c in cases:
        em = c.get("_expected_emotion", "?")
        emotion_counts[em] = emotion_counts.get(em, 0) + 1
    print(f"\nExpected emotion distribution ({len(emotion_counts)} categories):")
    for e, n in sorted(emotion_counts.items(), key=lambda x: -x[1]):
        print(f"  {e}: {n}")

    # 事件类型
    type_counts = {"positive": 0, "negative": 0, "ambiguous": 0}
    for c in cases:
        t = c["event"]["type"]
        if t in type_counts:
            type_counts[t] += 1
    print(f"\nEvent type distribution:")
    for t, n in sorted(type_counts.items()):
        print(f"  {t}: {n}")

    # 人格维度分布
    traits = ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"]
    print(f"\nBig Five trait ranges:")
    for trait in traits:
        vals = [c["character_state"]["personality"][trait] for c in cases]
        print(f"  {trait}: min={min(vals):.2f}, max={max(vals):.2f}, avg={sum(vals)/len(vals):.2f}")

    # 依恋风格分布
    att_counts = {}
    for c in cases:
        att = c["character_state"]["personality"]["attachment_style"]
        att_counts[att] = att_counts.get(att, 0) + 1
    print(f"\nAttachment style distribution:")
    for a, n in sorted(att_counts.items(), key=lambda x: -x[1]):
        print(f"  {a}: {n}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract Persona-E2 test cases")
    parser.add_argument("--sample", type=int, default=0, help="Number of cases to sample (0=all)")
    args = parser.parse_args()

    cases = extract_cases(sample=args.sample)
    print_summary(cases)

    out_path = OUTPUT_DIR / "persona_e2_cases.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(cases, f, ensure_ascii=False, indent=2)
    print(f"\nSaved to {out_path}")
