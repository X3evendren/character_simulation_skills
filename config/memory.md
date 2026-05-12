# 记忆系统配置

## 容量参数

working_memory_size: 50
short_term_memory_size: 200
long_term_memory_size: 500
core_graph_max_nodes: 500
core_graph_max_edges: 2000

## 衰减参数

short_term_half_life_days: 7
long_term_half_life_days: 30
graph_edge_half_life_days: 30
trust_decay_rate: 0.95

## 提升阈值

working_to_stm_significance: 0.3
working_to_stm_emotion: 0.4
stm_to_ltm_recall_count: 3
ltm_to_core_recall_count: 5
ltm_to_core_significance: 0.8
core_to_archive_confidence: 0.1

## 代谢周期

daydream_interval_ticks: 10
quick_sleep_interval_ticks: 50
full_sleep_trigger: session_end

## 检索参数

default_retrieval_count: 5
max_retrieval_count: 20
semantic_weight: 0.3
time_decay_weight: 0.3
significance_weight: 0.4

## Memory-as-Tool

auto_retrieve: false
retrieve_on_session_start: true
