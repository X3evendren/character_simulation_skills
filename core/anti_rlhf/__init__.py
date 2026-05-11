"""反RLHF偏差注入 — 三层防护。"""
from .silence_rule import SilenceRule
from .post_filter import PostFilter
from .ft_interface import FTInterface, FTSample
