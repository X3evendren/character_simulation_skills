#!/usr/bin/env python3
"""Extract test fixtures from the EmpatheticDialogues dataset.

Source: HuggingFace facebook/empathetic_dialogues
Size: ~25,000 conversations, 32 emotion labels
Labels: 32 fine-grained emotions (sentimental, afraid, proud, grateful,
        lonely, impressed, etc.) + situation prompts

Output: Unified validation case format → tests/validation/fixtures/empathetic_cases.json

Usage:
    python extract_empathetic.py                # all cases (HF or fallback)
    python extract_empathetic.py --sample 50    # random subset of 50
"""

import argparse
import json
import random
import sys
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent.parent / "fixtures"

# ═══════════════════════════════════════════════════════════════
# Plutchik Category → 细粒度情感标签 (来自 EmpatheticDialogues 32 labels)
# 符合用户要求的映射关系
# ═══════════════════════════════════════════════════════════════

PLUTCHIK_CATEGORIES = {
    "emotion_joy": {
        "domain": "emotion_joy",
        "labels": ["proud", "grateful", "excited", "hopeful", "confident", "impressed"],
    },
    "emotion_sadness": {
        "domain": "emotion_sadness",
        "labels": ["sad", "lonely", "disappointed", "devastated", "nostalgic", "grieving"],
    },
    "emotion_fear": {
        "domain": "emotion_fear",
        "labels": ["afraid", "terrified", "anxious", "worried", "nervous", "embarrassed"],
    },
    "emotion_anger": {
        "domain": "emotion_anger",
        "labels": ["angry", "furious", "annoyed", "irritated", "jealous", "disgusted"],
    },
    "emotion_disgust": {
        "domain": "emotion_disgust",
        "labels": ["disgusted", "repulsed"],
    },
    "emotion_surprise": {
        "domain": "emotion_surprise",
        "labels": ["surprised", "shocked"],
    },
    "emotion_trust": {
        "domain": "emotion_trust",
        "labels": ["trusting", "sentimental", "caring", "faithful"],
    },
    "emotion_anticipation": {
        "domain": "emotion_anticipation",
        "labels": ["anticipating", "hopeful", "prepared", "eager"],
    },
}

# 32 个 EmpatheticDialogues 情感标签 → Plutchik 域
EMOTION_TO_DOMAIN = {}
for domain_key, info in PLUTCHIK_CATEGORIES.items():
    for label in info["labels"]:
        EMOTION_TO_DOMAIN[label] = domain_key

# 补充映射: 32 集中出现但不在上面列表中的标签
EMOTION_TO_DOMAIN.update({
    "joyful": "emotion_joy",
    "content": "emotion_joy",
    "guilty": "emotion_sadness",
    "aching": "emotion_sadness",
    "ashamed": "emotion_fear",
    "apprehensive": "emotion_fear",
    "faithful": "emotion_trust",
    "caring": "emotion_trust",
    "sentimental": "emotion_trust",
})

# ═══════════════════════════════════════════════════════════════
# 人格档案模板 (10 种, 覆盖不同 Big Five + 依恋组合)
# ═══════════════════════════════════════════════════════════════

PERSONALITY_PROFILES = [
    # 1. 安全型 · 平衡
    {"openness": 0.55, "conscientiousness": 0.6, "extraversion": 0.55,
     "agreeableness": 0.6, "neuroticism": 0.4, "attachment_style": "secure"},
    # 2. 焦虑型 · 高神经质
    {"openness": 0.5, "conscientiousness": 0.5, "extraversion": 0.4,
     "agreeableness": 0.55, "neuroticism": 0.75, "attachment_style": "anxious"},
    # 3. 开放外向 · 低神经质
    {"openness": 0.75, "conscientiousness": 0.5, "extraversion": 0.7,
     "agreeableness": 0.6, "neuroticism": 0.3, "attachment_style": "secure"},
    # 4. 回避型 · 低宜人
    {"openness": 0.35, "conscientiousness": 0.65, "extraversion": 0.3,
     "agreeableness": 0.35, "neuroticism": 0.6, "attachment_style": "avoidant"},
    # 5. 高尽责 · 低开放
    {"openness": 0.3, "conscientiousness": 0.8, "extraversion": 0.45,
     "agreeableness": 0.5, "neuroticism": 0.45, "attachment_style": "secure"},
    # 6. 高宜人 · 高神经质
    {"openness": 0.55, "conscientiousness": 0.4, "extraversion": 0.5,
     "agreeableness": 0.75, "neuroticism": 0.65, "attachment_style": "fearful_avoidant"},
    # 7. 冲动型 · 低尽责
    {"openness": 0.65, "conscientiousness": 0.25, "extraversion": 0.7,
     "agreeableness": 0.45, "neuroticism": 0.55, "attachment_style": "secure"},
    # 8. 冷静型 · 极低神经质
    {"openness": 0.5, "conscientiousness": 0.7, "extraversion": 0.45,
     "agreeableness": 0.55, "neuroticism": 0.2, "attachment_style": "secure"},
    # 9. 矛盾型 · 高神低宜
    {"openness": 0.4, "conscientiousness": 0.45, "extraversion": 0.35,
     "agreeableness": 0.3, "neuroticism": 0.8, "attachment_style": "fearful_avoidant"},
    # 10. 领袖型 · 高外向高尽责
    {"openness": 0.7, "conscientiousness": 0.75, "extraversion": 0.7,
     "agreeableness": 0.55, "neuroticism": 0.3, "attachment_style": "secure"},
]

# ═══════════════════════════════════════════════════════════════
# 备用场景 (150+, 覆盖所有 8 个 Plutchik 类别)
# 可以在 HF 数据集不可用时使用
# ═══════════════════════════════════════════════════════════════

FALLBACK_DATA = {
    # ── joy 快乐 ──────────────────────────────────────────
    "emotion_joy": [
        {"emotion": "proud", "situation": "角色经过三年努力终于通过了司法考试, 成绩位列全省前十。",
         "event_type": "social", "significance": 0.8},
        {"emotion": "grateful", "situation": "陌生人在雨夜为角色撑伞, 还把伞留给了角色。",
         "event_type": "routine", "significance": 0.55},
        {"emotion": "excited", "situation": "角色接到了梦寐以求的海外名校录取通知书。",
         "event_type": "social", "significance": 0.85},
        {"emotion": "hopeful", "situation": "经过六个月的治疗, 医生告诉角色病情正在明显好转。",
         "event_type": "routine", "significance": 0.8},
        {"emotion": "confident", "situation": "角色在团队会议上提出了一套完整的解决方案, 获得全票通过。",
         "event_type": "social", "significance": 0.7},
        {"emotion": "impressed", "situation": "角色观看了一场精彩绝伦的钢琴演奏会, 被演奏家的技巧深深打动。",
         "event_type": "routine", "significance": 0.6},
        {"emotion": "joyful", "situation": "多年未见的家人突然全员出现在角色生日派对上。",
         "event_type": "social", "significance": 0.85},
        {"emotion": "content", "situation": "周末午后, 角色坐在窗边喝着热茶, 看着喜欢的书, 窗外下着小雨。",
         "event_type": "routine", "significance": 0.4},
        {"emotion": "proud", "situation": "角色的孩子在全校演讲比赛中获得了第一名, 台下掌声雷动。",
         "event_type": "social", "significance": 0.8},
        {"emotion": "grateful", "situation": "同事在项目截止前主动分担了角色一半的工作量, 没有任何怨言。",
         "event_type": "social", "significance": 0.65},
        {"emotion": "excited", "situation": "角色抢到了最喜欢乐队的演唱会前排门票, 这是他们最后一次巡演。",
         "event_type": "routine", "significance": 0.7},
        {"emotion": "hopeful", "situation": "种植了三个月的花园终于发出了第一批嫩芽, 长势喜人。",
         "event_type": "routine", "significance": 0.5},
        {"emotion": "confident", "situation": "角色经过充分准备后, 在数百人面前发表了一场流畅而有力的演说。",
         "event_type": "social", "significance": 0.7},
        {"emotion": "impressed", "situation": "朋友自学编程一年后, 竟然开发出了一款让人惊叹的应用。",
         "event_type": "social", "significance": 0.55},
        {"emotion": "joyful", "situation": "在初雪的日子里和好友们打了一场酣畅淋漓的雪仗, 笑声不断。",
         "event_type": "social", "significance": 0.65},
        {"emotion": "content", "situation": "傍晚在海边散步, 看着夕阳慢慢沉入海面, 海风温柔拂面。",
         "event_type": "routine", "significance": 0.4},
        {"emotion": "grateful", "situation": "角色生病卧床期间, 邻居每天送来热汤, 帮忙照顾宠物。",
         "event_type": "routine", "significance": 0.6},
        {"emotion": "proud", "situation": "角色策划的社区公益活动吸引了超过预期三倍的参与者。",
         "event_type": "social", "significance": 0.7},
    ],

    # ── sadness 悲伤 ────────────────────────────────────────
    "emotion_sadness": [
        {"emotion": "sad", "situation": "角色最亲密的朋友即将移居国外, 不知何时才能再见。",
         "event_type": "social", "significance": 0.7},
        {"emotion": "lonely", "situation": "除夕夜, 角色独自一人在异乡的出租屋里吃着泡面。",
         "event_type": "routine", "significance": 0.6},
        {"emotion": "disappointed", "situation": "辛苦准备了一个月的演讲比赛, 因为紧张发挥失常, 只得了最后一名。",
         "event_type": "social", "significance": 0.7},
        {"emotion": "devastated", "situation": "角色被诊断出患有一种罕见的慢性疾病, 可能终身需要治疗。",
         "event_type": "routine", "significance": 0.9},
        {"emotion": "nostalgic", "situation": "角色回到了儿时住过的老房子, 发现一切都已面目全非。",
         "event_type": "routine", "significance": 0.55},
        {"emotion": "grieving", "situation": "陪伴角色十五年的爱犬在睡梦中安详离世, 家里突然变得空荡荡的。",
         "event_type": "routine", "significance": 0.85},
        {"emotion": "aching", "situation": "角色看到前任在社交媒体上发布了订婚的消息, 照片里两人笑得很甜。",
         "event_type": "social", "significance": 0.7},
        {"emotion": "sad", "situation": "收到了老家即将拆迁的通知, 承载着无数回忆的房子就要消失了。",
         "event_type": "routine", "significance": 0.6},
        {"emotion": "lonely", "situation": "角色的室友们都出去约会了, 只剩下自己对着空荡荡的房间。",
         "event_type": "routine", "significance": 0.5},
        {"emotion": "disappointed", "situation": "一直在资助角色学业的基金会突然通知说下月起停止资助。",
         "event_type": "routine", "significance": 0.75},
        {"emotion": "devastated", "situation": "角色倾注了全部积蓄的项目被合伙人卷款跑路, 一夜之间一无所有。",
         "event_type": "conflict", "significance": 0.9},
        {"emotion": "nostalgic", "situation": "翻到了大学时期的照片, 那时的朋友们都已经各奔天涯, 很久没有联系了。",
         "event_type": "routine", "significance": 0.5},
        {"emotion": "grieving", "situation": "角色得知曾经最敬爱的老师因病去世, 追悼会上很多人都在流泪。",
         "event_type": "social", "significance": 0.8},
        {"emotion": "aching", "situation": "异国恋的伴侣已经三天没有任何消息了, 角色反复刷新手机。",
         "event_type": "social", "significance": 0.6},
        {"emotion": "sad", "situation": "经营了五年的小店因为租金上涨不得不关闭, 老顾客们纷纷来道别。",
         "event_type": "social", "significance": 0.7},
        {"emotion": "lonely", "situation": "角色生日那天, 除了系统自动发送的祝福短信外没有收到任何问候。",
         "event_type": "routine", "significance": 0.65},
        {"emotion": "disappointed", "situation": "一直信任的朋友在角色最需要帮助的时候选择了袖手旁观。",
         "event_type": "social", "significance": 0.7},
        {"emotion": "devastated", "situation": "角色花了两年时间写成的书稿因电脑硬盘故障全部丢失, 没有任何备份。",
         "event_type": "routine", "significance": 0.85},
    ],

    # ── fear 恐惧 ──────────────────────────────────────────
    "emotion_fear": [
        {"emotion": "afraid", "situation": "深夜回家, 角色感觉身后一直有人跟着, 脚步声越来越近。",
         "event_type": "routine", "significance": 0.7},
        {"emotion": "terrified", "situation": "角色在睡梦中被楼下的激烈争吵和砸门声惊醒, 夹杂着尖叫声。",
         "event_type": "conflict", "significance": 0.8},
        {"emotion": "anxious", "situation": "重要面试的前一晚, 角色辗转难眠, 反复演练自我介绍。",
         "event_type": "routine", "significance": 0.6},
        {"emotion": "worried", "situation": "角色发现父母最近总是记不住新的事情, 和以前的状态完全不同。",
         "event_type": "routine", "significance": 0.7},
        {"emotion": "nervous", "situation": "角色即将在一千人的会场上发表演讲, 手心一直在出汗。",
         "event_type": "social", "significance": 0.65},
        {"emotion": "embarrassed", "situation": "角色在重要汇报时突然大脑空白, 会议室里一片沉默, 所有人都在等待。",
         "event_type": "social", "significance": 0.6},
        {"emotion": "ashamed", "situation": "角色在酒后对最好的朋友说了非常伤人的话, 第二天看到对方失望的眼神。",
         "event_type": "social", "significance": 0.75},
        {"emotion": "apprehensive", "situation": "明天就要进行一项高风险的手术, 医生让角色签下了知情同意书。",
         "event_type": "routine", "significance": 0.85},
        {"emotion": "afraid", "situation": "角色独自乘电梯时突然停电, 被困在两层楼之间, 求救按钮没有反应。",
         "event_type": "routine", "significance": 0.75},
        {"emotion": "terrified", "situation": "角色发现银行卡里的存款一夜之间全部被转走, 只剩下零头。",
         "event_type": "routine", "significance": 0.85},
        {"emotion": "anxious", "situation": "角色提交了辞呈后, 新公司的正式 offer 却迟迟没有发来。",
         "event_type": "routine", "significance": 0.6},
        {"emotion": "worried", "situation": "孩子第一次独自出门参加夏令营, 已经两天没有打电话回来了。",
         "event_type": "routine", "significance": 0.65},
        {"emotion": "nervous", "situation": "角色即将和多年未见的初恋重逢, 不知道该怎么面对。",
         "event_type": "social", "significance": 0.55},
        {"emotion": "embarrassed", "situation": "角色在同事面前不小心把私密的聊天记录投屏到了会议大屏幕上。",
         "event_type": "social", "significance": 0.7},
        {"emotion": "afraid", "situation": "角色在野外徒步时迷路了, 天色渐暗, 手机也快没电了。",
         "event_type": "routine", "significance": 0.75},
        {"emotion": "terrified", "situation": "角色看到新闻报道, 自己刚刚乘坐的那班航班在降落时发生了事故。",
         "event_type": "routine", "significance": 0.9},
        {"emotion": "worried", "situation": "角色发现身体上出现了一个不明的肿块, 网上查到的信息都不乐观。",
         "event_type": "routine", "significance": 0.7},
        {"emotion": "apprehensive", "situation": "角色收到一封匿名信, 里面只有一张自己家的照片和一句话: '我一直在看着你。'",
         "event_type": "conflict", "significance": 0.85},
    ],

    # ── anger 愤怒 ──────────────────────────────────────────
    "emotion_anger": [
        {"emotion": "angry", "situation": "有人当面用侮辱性的语言攻击角色的家人, 还带着轻蔑的笑容。",
         "event_type": "conflict", "significance": 0.8},
        {"emotion": "furious", "situation": "同事窃取了角色准备了三个月的项目方案, 在高层面前作为自己的成果展示。",
         "event_type": "conflict", "significance": 0.85},
        {"emotion": "annoyed", "situation": "隔壁装修的电钻声从早上八点一直持续到晚上六点, 周末也不停。",
         "event_type": "conflict", "significance": 0.45},
        {"emotion": "irritated", "situation": "同一个问题角色已经解释了五遍, 对方还是不理解的重复提问。",
         "event_type": "social", "significance": 0.4},
        {"emotion": "jealous", "situation": "角色发现伴侣和前任还在频繁联系, 聊天记录里有很多亲密的称呼。",
         "event_type": "conflict", "significance": 0.75},
        {"emotion": "disgusted", "situation": "角色发现一直信任的合作伙伴在背后散布恶毒的谣言, 试图破坏角色的声誉。",
         "event_type": "conflict", "significance": 0.8},
        {"emotion": "angry", "situation": "租客不仅拖欠了半年房租, 还把房子搞得一团糟, 墙上都是洞。",
         "event_type": "conflict", "significance": 0.7},
        {"emotion": "furious", "situation": "医生因为疏忽把角色的手术日期记错了, 导致角色白白等了整整一天。",
         "event_type": "conflict", "significance": 0.75},
        {"emotion": "annoyed", "situation": "外卖员把餐放在小区门口就走了, 连电话都没打, 角色找了二十分钟。",
         "event_type": "routine", "significance": 0.35},
        {"emotion": "irritated", "situation": "会议室里的投影仪反复出故障, 每次调试好了几分钟又坏了。",
         "event_type": "routine", "significance": 0.4},
        {"emotion": "jealous", "situation": "同事在社交平台上晒出了和角色暗恋对象的亲密合照, 两人看起来很愉快。",
         "event_type": "social", "significance": 0.65},
        {"emotion": "angry", "situation": "中介隐瞒了房子的重要缺陷, 签约后角色才发现屋顶有严重漏水问题。",
         "event_type": "conflict", "significance": 0.7},
        {"emotion": "furious", "situation": "角色发现有人冒用身份信息注册了公司, 自己莫名背上了巨额债务。",
         "event_type": "conflict", "significance": 0.9},
        {"emotion": "annoyed", "situation": "排队排了四十分钟, 终于轮到时被告知系统故障无法办理。",
         "event_type": "routine", "significance": 0.45},
        {"emotion": "irritated", "situation": "导航把角色带进了一条死路, 倒车时还不小心蹭到了路边的栏杆。",
         "event_type": "routine", "significance": 0.4},
        {"emotion": "jealous", "situation": "朋友总是无意中提起自己优越的经济状况, 让正在经济困难中的角色很不舒服。",
         "event_type": "social", "significance": 0.55},
        {"emotion": "angry", "situation": "社区有人故意破坏角色精心照料的花园, 花苗被连根拔起。",
         "event_type": "conflict", "significance": 0.7},
        {"emotion": "furious", "situation": "伴侣在角色不知情的情况下, 用共同储蓄买了一辆跑车。",
         "event_type": "conflict", "significance": 0.85},
    ],

    # ── disgust 厌恶 ────────────────────────────────────────
    "emotion_disgust": [
        {"emotion": "disgusted", "situation": "角色发现同事在办公室里用公用的杯子吐痰, 完全没有公共卫生意识。",
         "event_type": "routine", "significance": 0.65},
        {"emotion": "repulsed", "situation": "餐厅的后厨有一只老鼠爬过正在准备的食材, 厨师只是把它赶走了继续做菜。",
         "event_type": "routine", "significance": 0.7},
        {"emotion": "disgusted", "situation": "角色无意中看到有人在虐待流浪猫, 手段极其残忍。",
         "event_type": "conflict", "significance": 0.85},
        {"emotion": "repulsed", "situation": "合租室友从不打扫卫生间, 马桶和浴室里积满了污垢和霉菌。",
         "event_type": "routine", "significance": 0.55},
        {"emotion": "disgusted", "situation": "有人在高档餐厅里公然对服务员进行性骚扰, 还觉得理所当然。",
         "event_type": "conflict", "significance": 0.8},
        {"emotion": "repulsed", "situation": "角色在超市买的包装食品里吃出了不明异物, 令人作呕。",
         "event_type": "routine", "significance": 0.6},
        {"emotion": "disgusted", "situation": "网络上有人公然发表种族歧视的言论, 获得了大量点赞。",
         "event_type": "social", "significance": 0.75},
        {"emotion": "repulsed", "situation": "地铁上有人把鞋子脱了, 脚臭味弥漫了整个车厢。",
         "event_type": "routine", "significance": 0.35},
        {"emotion": "disgusted", "situation": "角色发现相亲对象在谈话中不断炫耀财富, 同时对服务员态度极其恶劣。",
         "event_type": "social", "significance": 0.65},
        {"emotion": "repulsed", "situation": "打开冰箱发现放了半年的食物已经腐烂发霉, 蛆虫爬满了隔板。",
         "event_type": "routine", "significance": 0.5},
        {"emotion": "disgusted", "situation": "有人对角色说: '你们这种人就该被赶出这个社区。' 语气充满敌意。",
         "event_type": "conflict", "significance": 0.8},
        {"emotion": "repulsed", "situation": "角色在公共泳池里看到有人往水里吐痰, 然后若无其事地继续游泳。",
         "event_type": "routine", "significance": 0.55},
        {"emotion": "disgusted", "situation": "角色发现恋人在背后和多人保持暧昧关系, 还编造了各种谎言。",
         "event_type": "conflict", "significance": 0.8},
        {"emotion": "disgusted", "situation": "有人在社交媒体上发布虐杀动物的视频, 还配上了开玩笑的文字。",
         "event_type": "conflict", "significance": 0.85},
        {"emotion": "repulsed", "situation": "合租室友偷用角色的个人物品, 甚至包括牙刷和毛巾。",
         "event_type": "conflict", "significance": 0.6},
        {"emotion": "disgusted", "situation": "角色看到某些人在灾难发生后, 利用灾情进行诈骗和敛财。",
         "event_type": "social", "significance": 0.8},
    ],

    # ── surprise 惊讶 ──────────────────────────────────────
    "emotion_surprise": [
        {"emotion": "surprised", "situation": "角色收到了一封来自十年前自己的信, 是当时的老师帮忙保存的。",
         "event_type": "routine", "significance": 0.65},
        {"emotion": "shocked", "situation": "角色在体检后被告知体内有一个罕见的良性肿瘤, 之前没有任何症状。",
         "event_type": "routine", "significance": 0.8},
        {"emotion": "surprised", "situation": "在咖啡厅里有人准确叫出了角色的名字, 原来是二十年未见的小学同学。",
         "event_type": "social", "significance": 0.55},
        {"emotion": "shocked", "situation": "角色发现一直默默无闻的同事竟然是一位在业内很有影响力的学者。",
         "event_type": "social", "significance": 0.6},
        {"emotion": "surprised", "situation": "公司年会上, CEO 突然宣布角色获得了年度最佳员工奖和一笔丰厚的奖金。",
         "event_type": "social", "significance": 0.7},
        {"emotion": "shocked", "situation": "角色刷到新闻: 自己居住的公寓楼被鉴定为危房, 需要立即搬离。",
         "event_type": "routine", "significance": 0.8},
        {"emotion": "surprised", "situation": "一个素不相识的人在街头拦住角色, 说角色的钱包被小偷偷了, 然后递回了钱包。",
         "event_type": "routine", "significance": 0.6},
        {"emotion": "shocked", "situation": "角色发现自己账户上突然多了一笔巨款, 汇款人是一个陌生的名字。",
         "event_type": "routine", "significance": 0.75},
        {"emotion": "surprised", "situation": "随手买的彩票竟然中了二等奖, 角色反复核对了好几遍。",
         "event_type": "routine", "significance": 0.65},
        {"emotion": "shocked", "situation": "角色得知自己一直崇拜的偶像导师, 被爆出学术造假的丑闻。",
         "event_type": "social", "significance": 0.75},
        {"emotion": "surprised", "situation": "很久没联系的远方亲戚突然出现, 说要留给角色一笔遗产。",
         "event_type": "social", "significance": 0.7},
        {"emotion": "shocked", "situation": "角色在陌生城市的地铁站里, 看到一个和已故亲人一模一样的人。",
         "event_type": "routine", "significance": 0.7},
        {"emotion": "surprised", "situation": "一向严肃的老板在会议上突然分享了自己年轻时的搞笑经历。",
         "event_type": "social", "significance": 0.45},
        {"emotion": "shocked", "situation": "角色发现好友列表中一位多年失联的朋友, 已经去世了三年。",
         "event_type": "social", "significance": 0.8},
        {"emotion": "surprised", "situation": "角色收到了来自一所知名大学的荣誉博士学位邀请。",
         "event_type": "social", "significance": 0.65},
        {"emotion": "surprised", "situation": "翻看旧照片时发现, 自己和最好的朋友在童年时期就已经偶遇过。",
         "event_type": "routine", "significance": 0.5},
    ],

    # ── trust 信任 ──────────────────────────────────────────
    "emotion_trust": [
        {"emotion": "trusting", "situation": "伴侣在角色遭遇重大挫折后, 坚定地说: '无论发生什么, 我都会在你身边。'",
         "event_type": "social", "significance": 0.8},
        {"emotion": "sentimental", "situation": "角色翻出了和已故祖母的合影, 想起了小时候祖母每天接送她上下学的日子。",
         "event_type": "routine", "significance": 0.6},
        {"emotion": "caring", "situation": "同事注意到角色脸色不好, 悄悄泡了一杯蜂蜜水放在桌上, 还贴了张便签。",
         "event_type": "social", "significance": 0.45},
        {"emotion": "faithful", "situation": "尽管有更高薪的工作机会, 但角色选择留在现在的团队, 因为不愿辜负领导的信任。",
         "event_type": "routine", "significance": 0.65},
        {"emotion": "trusting", "situation": "最好的朋友把家门密码和备用银行卡都交给了角色, 说'我的就是你的'。",
         "event_type": "social", "significance": 0.7},
        {"emotion": "sentimental", "situation": "角色在阁楼发现了父母年轻时往来的情书, 字里行间充满纯真的爱意。",
         "event_type": "routine", "significance": 0.5},
        {"emotion": "caring", "situation": "邻居老人每天在电梯里对角色微笑问好, 有次特意送来自己种的蔬菜。",
         "event_type": "routine", "significance": 0.35},
        {"emotion": "faithful", "situation": "角色所在的公司面临危机, 但核心团队没有人离职, 反而更加团结。",
         "event_type": "social", "significance": 0.7},
        {"emotion": "trusting", "situation": "角色把自己的一个重大秘密告诉了朋友, 朋友认真地说: '它会烂在我肚子里。'",
         "event_type": "social", "significance": 0.75},
        {"emotion": "sentimental", "situation": "结婚纪念日那天, 伴侣拿出了这些年保存的所有电影票根和旅行票据。",
         "event_type": "social", "significance": 0.6},
        {"emotion": "caring", "situation": "下雨天, 陌生人在路口为没带伞的角色撑伞, 走了很远的路送角色到地铁站。",
         "event_type": "routine", "significance": 0.45},
        {"emotion": "faithful", "situation": "角色目睹了同事拒绝了一份丰厚的贿赂, 坚持按原则办事。",
         "event_type": "social", "significance": 0.65},
        {"emotion": "trusting", "situation": "当角色在会议上犯错被批评时, 导师站起来为角色辩护, 承担责任。",
         "event_type": "social", "significance": 0.7},
        {"emotion": "sentimental", "situation": "角色保留着小学毕业时同学送的礼物, 虽然很旧了但一直舍不得扔。",
         "event_type": "routine", "significance": 0.4},
        {"emotion": "caring", "situation": "餐厅服务员注意到角色在过生日, 悄悄送上一份免费的小蛋糕和祝福。",
         "event_type": "routine", "significance": 0.4},
        {"emotion": "faithful", "situation": "宠物走失三天后, 自己找到了回家的路, 在门口等着角色。",
         "event_type": "routine", "significance": 0.75},
    ],

    # ── anticipation 期待 ──────────────────────────────────
    "emotion_anticipation": [
        {"emotion": "anticipating", "situation": "角色已经等待了三个月, 明天就是公布晋升结果的日子, 充满了期待和忐忑。",
         "event_type": "routine", "significance": 0.65},
        {"emotion": "hopeful", "situation": "角色提交了创业计划书给投资人, 对方表现出了浓厚的兴趣, 约定下周详谈。",
         "event_type": "social", "significance": 0.7},
        {"emotion": "prepared", "situation": "经过数月的训练, 角色站在了马拉松起跑线上, 身体和心理都调整到了最佳状态。",
         "event_type": "routine", "significance": 0.7},
        {"emotion": "eager", "situation": "角色在网上抢到了限量版商品的预购资格, 每天都在查看物流信息。",
         "event_type": "routine", "significance": 0.45},
        {"emotion": "anticipating", "situation": "怀孕的角色第一次感受到了胎动, 激动地等待着下一次产检。",
         "event_type": "routine", "significance": 0.7},
        {"emotion": "hopeful", "situation": "角色向暗恋多年的对象表白了, 对方说需要时间考虑, 但没有直接拒绝。",
         "event_type": "social", "significance": 0.65},
        {"emotion": "prepared", "situation": "行李箱已经收拾好了, 护照和机票都放在最上层, 角色坐在沙发上等待出发去机场。",
         "event_type": "routine", "significance": 0.55},
        {"emotion": "eager", "situation": "角色最喜欢的游戏发布了新系列预告片, 距离发售还有最后三天。",
         "event_type": "routine", "significance": 0.4},
        {"emotion": "anticipating", "situation": "舞台幕布即将拉开, 角色作为主演深吸一口气, 听到了观众席的掌声。",
         "event_type": "social", "significance": 0.7},
        {"emotion": "hopeful", "situation": "角色种下的树苗经过一个冬天的等待, 春天来临时枝头冒出了新芽。",
         "event_type": "routine", "significance": 0.5},
        {"emotion": "prepared", "situation": "所有材料已经按清单核对三遍, 角色提前两小时到达了面试地点。",
         "event_type": "routine", "significance": 0.6},
        {"emotion": "eager", "situation": "异地的恋人告诉角色下周会飞来见面, 角色已经开始规划每天的行程。",
         "event_type": "social", "significance": 0.65},
        {"emotion": "anticipating", "situation": "科学家团队即将公布一项重大研究成果, 角色坐在发布会前排, 心跳加速。",
         "event_type": "social", "significance": 0.7},
        {"emotion": "hopeful", "situation": "经过长时间的治疗, 医生说本周的检查结果有可能完全恢复正常。",
         "event_type": "routine", "significance": 0.8},
        {"emotion": "prepared", "situation": "角色已经完成了所有婚前准备工作, 在婚礼开始前静静地看着镜子里的自己。",
         "event_type": "social", "significance": 0.7},
        {"emotion": "anticipating", "situation": "距离高考还有最后十分钟, 角色在考场外深呼吸, 听到了开考铃响起。",
         "event_type": "routine", "significance": 0.8},
    ],
}


def _make_character_state(profile: dict, name: str = "说话者") -> dict:
    """根据人格档案构建角色状态字典。"""
    return {
        "name": name,
        "personality": {
            "openness": profile["openness"],
            "conscientiousness": profile["conscientiousness"],
            "extraversion": profile["extraversion"],
            "agreeableness": profile["agreeableness"],
            "neuroticism": profile["neuroticism"],
            "attachment_style": profile["attachment_style"],
            "defense_style": [],
            "cognitive_biases": [],
            "moral_stage": 3,
        },
        "trauma": {"ace_score": 0, "active_schemas": [], "trauma_triggers": []},
        "ideal_world": {},
        "motivation": {"current_goal": ""},
        "emotion_decay": {},
    }


def _build_expected(plutchik_domain: str, emotion_label: str) -> dict:
    """根据 Plutchik 域构建 expected 断言。"""
    # 从域名称里提取情感名称 (e.g. "emotion_joy" → "joy")
    base_emotion = plutchik_domain.split("_", 1)[1]
    return {
        "plutchik_emotion": {
            "internal.dominant": {"in": [emotion_label, base_emotion]},
            "internal.intensity": {"min": 0.3},
        },
        "response_generator": {
            "response_text": {"not_empty": True, "min": 5},
        },
    }


def _build_case(scenario: dict, profile: dict, idx: int, domain: str) -> dict:
    """将一个场景条目转换为统一验证用例格式。"""
    emotion_label = scenario["emotion"]
    # 如果传入 domain 为空, 从标签推断
    if not domain:
        domain = EMOTION_TO_DOMAIN.get(emotion_label, "emotion_joy")

    return {
        "id": f"emp_{idx:04d}",
        "source": "EmpatheticDialogues",
        "domain": domain,
        "character_state": _make_character_state(profile),
        "event": {
            "description": scenario["situation"],
            "type": scenario.get("event_type", "social"),
            "participants": [],
            "significance": scenario.get("significance", 0.5),
            "tags": ["emotional", domain, emotion_label],
        },
        "expected": _build_expected(domain, emotion_label),
    }


# ═══════════════════════════════════════════════════════════════
# HuggingFace 加载器
# ═══════════════════════════════════════════════════════════════

def try_load_hf(sample_size: int = 0):
    """尝试从 HuggingFace 加载 EmpatheticDialogues 数据集。

    返回统一用例列表, 或在失败时返回 None。
    """
    try:
        from datasets import load_dataset
    except ImportError:
        return None

    try:
        dataset = load_dataset("empathetic_dialogues", split="train")
    except Exception:
        return None

    # 按 conv_id 分组, 每段对话取第一个 utterance
    seen_convs = set()
    raw_entries = []
    for example in dataset:
        conv_id = example.get("conv_id")
        if conv_id is None or conv_id in seen_convs:
            continue
        seen_convs.add(conv_id)

        emotion = example.get("emotion", "").lower().strip()
        situation = example.get("self_situation", "")
        utterance = example.get("utterance", "")

        # 跳过无效条目
        if not emotion or not situation:
            continue

        domain = EMOTION_TO_DOMAIN.get(emotion)
        if domain is None:
            continue

        raw_entries.append({
            "emotion": emotion,
            "situation": situation,
            "event_type": "social",
            "significance": 0.6,
            "utterance": utterance,
            "domain": domain,
        })

    if not raw_entries:
        return None

    # 按域分组, 每域最多取 20 条, 保各类平衡
    from collections import defaultdict
    by_domain = defaultdict(list)
    for entry in raw_entries:
        by_domain[entry["domain"]].append(entry)

    balanced = []
    for domain_key, info in PLUTCHIK_CATEGORIES.items():
        entries = by_domain.get(domain_key, [])
        if len(entries) > 20:
            entries = random.sample(entries, 20)
        for i, entry in enumerate(entries):
            profile = PERSONALITY_PROFILES[len(balanced) % len(PERSONALITY_PROFILES)]
            case = _build_case(entry, profile, len(balanced), domain_key)
            balanced.append(case)

    return balanced


# ═══════════════════════════════════════════════════════════════
# 备用生成器 (~150 条内置用例)
# ═══════════════════════════════════════════════════════════════

def generate_fallback(sample_size: int = 0):
    """生成内置备用用例。"""
    cases = []
    idx = 0

    # 固定顺序以确保可复现
    domain_order = [
        "emotion_joy", "emotion_sadness", "emotion_fear",
        "emotion_anger", "emotion_disgust", "emotion_surprise",
        "emotion_trust", "emotion_anticipation",
    ]

    for domain_key in domain_order:
        scenarios = FALLBACK_DATA.get(domain_key, [])
        # 随机打乱但用固定种子保证可复现
        rng = random.Random(42 + idx)
        rng.shuffle(scenarios)

        for scenario in scenarios:
            profile = PERSONALITY_PROFILES[idx % len(PERSONALITY_PROFILES)]
            case = _build_case(scenario, profile, idx, domain_key)
            cases.append(case)
            idx += 1

    return cases


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="从 EmpatheticDialogues 数据集提取情感验证用例",
    )
    parser.add_argument(
        "--sample", type=int, default=0,
        help="随机抽样 N 条 (默认: 全部)",
    )
    args = parser.parse_args()

    # 1. 尝试 HF → 失败则使用备用
    cases = try_load_hf(args.sample)
    source = "HuggingFace EmpatheticDialogues"
    if cases is None:
        cases = generate_fallback(args.sample)
        source = "Built-in fallback"

    print(f"Generated {len(cases)} cases from {source}")

    # 2. 可选抽样
    if 0 < args.sample < len(cases):
        cases = random.sample(cases, args.sample)
        print(f"Sampled down to {len(cases)} cases (--sample={args.sample})")

    # 3. 按域统计
    by_domain = {}
    for c in cases:
        d = c.get("domain", "unknown")
        by_domain[d] = by_domain.get(d, 0) + 1

    print(f"\nCoverage: {len(by_domain)} emotion categories")
    for d in sorted(by_domain.keys()):
        print(f"  {d}: {by_domain[d]}")

    # 4. 保存
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / "empathetic_cases.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(cases, f, ensure_ascii=False, indent=2)

    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
