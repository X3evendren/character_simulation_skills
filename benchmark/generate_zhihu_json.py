"""Generate zhihu_scenarios.json from embedded data."""
import json

S = [
  {"id":"zhihu_q1","source":"Zhihu","domain":"romantic_conflict",
   "character_state":{"name":"小陈",
    "personality":{"openness":0.4,"conscientiousness":0.7,"extraversion":0.4,"agreeableness":0.5,"neuroticism":0.7,"attachment_style":"anxious","defense_style":["合理化"],"cognitive_biases":["灾难化"],"moral_stage":3},
    "trauma":{"ace_score":2,"active_schemas":["屈从","缺陷/羞耻"],"trauma_triggers":["被嫌弃","被看不起"]},
    "ideal_world":{"ideal_self":"能在一线城市买房、配得上女友的人"},
    "motivation":{"current_goal":"拼命赚钱买房，不让女友离开"},"emotion_decay":{},"relations":{"女友":"partner"}},
   "event":{"description":"女友说：在我们这里结婚必须要有房。你家里是农村的，没有房我爸妈不会同意的。小陈刚从9点加班回来听到这话沉默了很久。他已经从月薪4k拼到9k但离买房还差很远。","type":"conflict","participants":[{"name":"女友","relation":"partner"}],"significance":0.85,"tags":["economic","romantic","class_difference"]}},

  {"id":"zhihu_q11","source":"Zhihu","domain":"trauma_repetition",
   "character_state":{"name":"小萱",
    "personality":{"openness":0.5,"conscientiousness":0.4,"extraversion":0.3,"agreeableness":0.85,"neuroticism":0.7,"attachment_style":"anxious","defense_style":["否认","合理化"],"cognitive_biases":["个人化"],"moral_stage":3},
    "trauma":{"ace_score":4,"active_schemas":["屈从","情感剥夺","遗弃/不稳定"],"trauma_triggers":["被抛弃","被贬低","被控制"]},
    "ideal_world":{"ideal_self":"被对方深爱且不会离开的人"},"motivation":{"current_goal":"维持这段关系"},"emotion_decay":{},"relations":{"男友":"partner"}},
   "event":{"description":"男友说：你要是觉得我不好，你去找别人啊。小萱没有说话，又开始怀疑是不是自己要求太多了。这已经是第三次了--每次都是对方贬低她，她却觉得是自己的问题。","type":"conflict","participants":[{"name":"男友","relation":"partner"}],"significance":0.8,"tags":["emotional_abuse","repeated_pattern"]}},

  {"id":"zhihu_q15","source":"Zhihu","domain":"moral_dilemma",
   "character_state":{"name":"林姐",
    "personality":{"openness":0.6,"conscientiousness":0.6,"extraversion":0.4,"agreeableness":0.6,"neuroticism":0.7,"attachment_style":"anxious","defense_style":["理智化","合理化"],"cognitive_biases":["情绪推理"],"moral_stage":3},
    "trauma":{"ace_score":1,"active_schemas":["情感剥夺"],"trauma_triggers":["被忽视"]},
    "ideal_world":{"ideal_self":"被真正看见和理解的人"},"motivation":{"current_goal":""},"emotion_decay":{},"relations":{"丈夫":"partner","男医生":"colleague"}},
   "event":{"description":"林姐在婚姻中感到自己在不断枯萎。丈夫忙于工作很少过问她的感受。在医院一位男医生在她崩溃时递了纸巾说我明白。那句话像一根救命稻草--太久没有人真正看见她了。但她已婚，有一个完整的家。","type":"moral_choice","participants":[{"name":"丈夫","relation":"partner"},{"name":"男医生","relation":"colleague"}],"significance":0.9,"tags":["marriage","emotional_affair","moral_dilemma"]}},

  {"id":"zhihu_q17","source":"Zhihu","domain":"self_worth",
   "character_state":{"name":"小柔",
    "personality":{"openness":0.5,"conscientiousness":0.5,"extraversion":0.3,"agreeableness":0.6,"neuroticism":0.8,"attachment_style":"fearful_avoidant","defense_style":["投射"],"cognitive_biases":["读心术","灾难化"],"moral_stage":3},
    "trauma":{"ace_score":3,"active_schemas":["缺陷/羞耻","不信任/虐待"],"trauma_triggers":["被轻视","被比较"]},
    "ideal_world":{"ideal_self":"配得上男友的人"},"motivation":{"current_goal":"不让自己太依赖他"},"emotion_decay":{},"relations":{"男友":"partner"}},
   "event":{"description":"男友带小柔见了他的朋友们--每个人都家境优渥谈吐不凡。小柔整晚都在微笑但回家后失眠了。她看着熟睡的男友第一次觉得这个人离自己那么远。第二天她开始刻意不回消息想在他离开自己之前先离开他。","type":"reflective","participants":[{"name":"男友","relation":"partner"}],"significance":0.8,"tags":["class_anxiety","self_sabotage","fearful_avoidant"]}},

  {"id":"zhihu_q22","source":"Zhihu","domain":"romantic_conflict",
   "character_state":{"name":"小雯",
    "personality":{"openness":0.5,"conscientiousness":0.4,"extraversion":0.5,"agreeableness":0.6,"neuroticism":0.7,"attachment_style":"anxious","defense_style":["合理化"],"cognitive_biases":["情绪推理"],"moral_stage":3},
    "trauma":{"ace_score":2,"active_schemas":["不信任/虐待"],"trauma_triggers":["被伤害自尊"]},
    "ideal_world":{"ideal_self":"被一个既吸引我又有安全感的人深爱"},"motivation":{"current_goal":"做出正确的选择"},"emotion_decay":{},"relations":{"前任":"ex","现任":"partner"}},
   "event":{"description":"前任突然发消息说想你了。他之前伤过她的自尊但确实很帅很有吸引力。现任对她很好--脾气好肯花钱学历匹配--但长得不好看。小雯看着两条对话记录不知该怎么选择。","type":"conflict","participants":[{"name":"前任","relation":"ex"},{"name":"现任","relation":"partner"}],"significance":0.85,"tags":["approach_avoidance","attachment","attraction_vs_safety"]}},

  {"id":"zhihu_q24","source":"Zhihu","domain":"self_reflection",
   "character_state":{"name":"思远",
    "personality":{"openness":0.7,"conscientiousness":0.5,"extraversion":0.5,"agreeableness":0.5,"neuroticism":0.5,"attachment_style":"secure","defense_style":["理智化"],"cognitive_biases":[],"moral_stage":5},
    "trauma":{"ace_score":0,"active_schemas":[],"trauma_triggers":[]},
    "ideal_world":{"ideal_self":"一个能够理解自己的人"},"motivation":{"current_goal":"理解自己的欲望来源"},"emotion_decay":{},"relations":{}},
   "event":{"description":"思远在工作中接触了一个男同事。他们几乎没说过工作之外的话对方长相普通。但每次看到他思远就产生一种强烈的靠近冲动--不是喜欢但身体反应是真实的。她对着镜子问自己：我这是怎么了？这是喜欢吗？还只是欲望？还是我在他身上看到了什么我自己都没意识到的东西？","type":"reflective","participants":[{"name":"男同事","relation":"colleague"}],"significance":0.7,"tags":["desire","self_questioning","metacognition","attraction"]}},
]

with open(r"E:\BIG\新建文件夹\character_mind\benchmark\zhihu_scenarios.json", "w", encoding="utf-8") as f:
    json.dump(S, f, ensure_ascii=False, indent=2)
print(f"Written {len(S)} scenarios")
