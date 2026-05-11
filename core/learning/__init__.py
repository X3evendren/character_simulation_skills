"""学习层 — 部署时学习 (Deployment-Time Learning)。

零参数更新，所有适应通过外部技能记忆和反馈闭环。
"""
from .skill_library import SkillLibrary, Skill
from .feedback_loop import FeedbackLoop, FeedbackEvent, FeedbackRule, FeedbackLevel
from .self_reflection import SelfReflection, ReflectionEntry
from .rl_interface import RLInterface, Trajectory, TrajectoryStep
