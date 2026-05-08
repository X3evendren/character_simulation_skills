# Continuous Consciousness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the experimental TOCA prototype from a time-sliced event runner into a testable continuous-consciousness runtime with attention, finite global workspace, memory nudges, self-model, and behavior feedback.

**Architecture:** Keep `CognitiveOrchestrator.process_event()` as the expensive cognitive frame. Add a small continuous runtime around it: perception enters through a gate, selected contents enter a finite workspace, orchestration writes psychological outputs back to a versioned blackboard, and behavior/output becomes new perceptual material for other agents. Hermes-style memory is added as frozen snapshots, episodic retrieval, and procedural pattern consolidation.

**Tech Stack:** Python 3.12, `asyncio`, dataclasses, existing `experimental/` modules, existing `core` memory/orchestrator APIs, `unittest`.

---

## File Structure

- Modify `experimental/blackboard.py`: add event logging and snapshot helpers for workspace/debug replay.
- Modify `experimental/consciousness.py`: fix prediction-error keys, add finite global workspace state and APIs.
- Modify `experimental/thalamic_gate.py`: expose buffered perception flushing as part of runner processing.
- Modify `experimental/toca_runner.py`: use start-snapshot versions for writes, consume gate buffer, inject workspace contents, emit behavior stream.
- Modify `experimental/offline_consolidation.py`: add Hermes-style nudge outputs for frozen snapshots and procedural patterns.
- Modify `experimental/behavior_stream.py`: no major redesign; connect it to `TocaRunner`.
- Create `experimental/self_model.py`: maintain first-person self/other/conflict/mask/intention state.
- Create `experimental/procedural_memory.py`: store consolidated trigger-pattern-response rules.
- Modify `experimental/__init__.py`: export new experimental primitives.
- Modify `tests/experimental/test_toca_integration.py`: extend current integration tests.
- Create `tests/experimental/test_conscious_workspace.py`: focused tests for global workspace and self-model.
- Create `tests/experimental/test_memory_nudges.py`: focused tests for procedural/frozen memory consolidation.

---

## Phase 1: Repair the Continuous Loop

### Task 1: Fix Prediction Error and Global Workspace

**Files:**
- Modify: `experimental/consciousness.py`
- Test: `tests/experimental/test_conscious_workspace.py`

- [ ] **Step 1: Write failing tests for prediction-error salience**

Create `tests/experimental/test_conscious_workspace.py` with:

```python
import unittest

from character_mind.experimental.blackboard import Blackboard
from character_mind.experimental.consciousness import ConsciousnessLayer


class TestConsciousWorkspace(unittest.TestCase):
    def test_prediction_error_increases_emotion_salience(self):
        bb = Blackboard()
        bb.write("pad", {"pleasure": 0.0, "arousal": 0.3, "dominance": 0.0})
        bb.write("dominant_emotion", "neutral")
        layer = ConsciousnessLayer(bb)

        layer.predict_next()
        bb.write("pad", {"pleasure": -0.8, "arousal": 0.9, "dominance": -0.2})
        layer.compute_prediction_error()
        salience = layer.score_salience()

        self.assertGreater(salience["emotion"], 0.55)

    def test_workspace_keeps_only_highest_salience_items(self):
        bb = Blackboard()
        layer = ConsciousnessLayer(bb)
        layer.workspace_capacity = 3

        items = [
            {"kind": "emotion", "content": "fear", "salience": 0.7, "source": "l1"},
            {"kind": "memory", "content": "old abandonment", "salience": 0.9, "source": "wm_ltm"},
            {"kind": "intention", "content": "ask why", "salience": 0.6, "source": "self_model"},
            {"kind": "noise", "content": "street light", "salience": 0.1, "source": "visual"},
        ]

        selected = layer.update_workspace(items)

        self.assertEqual(len(selected), 3)
        self.assertEqual(selected[0]["kind"], "memory")
        self.assertNotIn("noise", [item["kind"] for item in selected])
        self.assertEqual(bb.read(["conscious_workspace"])["conscious_workspace"], selected)
```

- [ ] **Step 2: Run the new tests and verify failure**

Run from the package parent directory:

```bash
cd E:\BIG\新建文件夹\新建文件夹
python -m unittest character_mind.tests.experimental.test_conscious_workspace -v
```

Expected: failure because `update_workspace()` does not exist and salience ignores the actual `L1_*` error keys.

- [ ] **Step 3: Implement workspace state and fix error keys**

In `experimental/consciousness.py`, extend `ConsciousnessState`:

```python
workspace: list[dict] = field(default_factory=list)
```

In `ConsciousnessLayer.__init__`, add:

```python
self.workspace_capacity = 4
```

In `score_salience()`, replace the prediction error contribution with:

```python
emotion_sal += (
    errors.get("L1_pleasure", 0.0) +
    errors.get("L1_arousal", 0.0) +
    errors.get("L1_combined", 0.0)
) * 0.2
```

Add:

```python
def update_workspace(self, candidates: list[dict]) -> list[dict]:
    valid = [
        dict(item)
        for item in candidates
        if item.get("salience", 0.0) >= self.salience_threshold
    ]
    valid.sort(key=lambda item: item.get("salience", 0.0), reverse=True)
    selected = valid[:self.workspace_capacity]
    self.state.workspace = selected
    self.bb.write("conscious_workspace", selected)
    return selected

def build_workspace_candidates(self) -> list[dict]:
    current = self.bb.read([
        "dominant_emotion", "pad", "ptsd_triggered", "active_defense",
        "pending_response", "retrieved_memories",
    ])
    salience = self.score_salience()
    candidates = []
    if current.get("dominant_emotion"):
        candidates.append({
            "kind": "emotion",
            "content": current["dominant_emotion"],
            "salience": salience.get("emotion", 0.0),
            "source": "blackboard",
        })
    if current.get("ptsd_triggered"):
        candidates.append({
            "kind": "threat",
            "content": "trauma_trigger",
            "salience": salience.get("threat", 0.0),
            "source": "ptsd_trigger",
        })
    defense = current.get("active_defense")
    if isinstance(defense, dict) and defense.get("name"):
        candidates.append({
            "kind": "defense",
            "content": defense.get("name"),
            "salience": salience.get("defense", 0.0),
            "source": "defense_mechanism",
        })
    for memory in current.get("retrieved_memories", [])[:3]:
        candidates.append({
            "kind": "memory",
            "content": memory.get("description", "")[:160],
            "salience": max(0.35, memory.get("significance", 0.4)),
            "source": "wm_ltm",
        })
    response = current.get("pending_response")
    if isinstance(response, dict) and response.get("text"):
        candidates.append({
            "kind": "response",
            "content": response["text"][:160],
            "salience": salience.get("response", 0.0),
            "source": "l5",
        })
    return candidates
```

- [ ] **Step 4: Run focused tests**

```bash
cd E:\BIG\新建文件夹\新建文件夹
python -m unittest character_mind.tests.experimental.test_conscious_workspace -v
```

Expected: pass.

- [ ] **Step 5: Run existing TOCA tests**

```bash
cd E:\BIG\新建文件夹\新建文件夹
python -m unittest character_mind.tests.experimental.test_toca_integration -v
```

Expected: pass.

---

### Task 2: Make Thalamic Gate Buffer Actually Feed the Frame

**Files:**
- Modify: `experimental/toca_runner.py`
- Test: `tests/experimental/test_toca_integration.py`

- [ ] **Step 1: Add a failing integration test**

Append to `TestTocaRunnerIntegration`:

```python
async def test_gate_flushes_buffer_into_event_when_threshold_reached(self):
    await self.runner.start()
    self.ps.feed_visual("走廊灯闪了一下", intensity=0.25)
    self.ps.feed_visual("手机屏幕又亮了", intensity=0.25)
    self.ps.feed_internal("她忽然有点不安", intensity=0.45)
    self.runner._last_input_time = time.time()
    await asyncio.sleep(self.config.pipeline_time_s + 1.5)
    await self.runner.stop()

    snapshot = self.bb.get_snapshot()
    descriptions = [
        item["value"]
        for key, item in snapshot["fields"].items()
        if key == "last_continuous_event"
    ]
    self.assertTrue(descriptions)
    self.assertIn("走廊灯", descriptions[0]["description"])
```

- [ ] **Step 2: Run the test and verify failure**

```bash
cd E:\BIG\新建文件夹\新建文件夹
python -m unittest character_mind.tests.experimental.test_toca_integration.TestTocaRunnerIntegration.test_gate_flushes_buffer_into_event_when_threshold_reached -v
```

Expected: failure because runner ignores the gate buffer and does not write `last_continuous_event`.

- [ ] **Step 3: Implement gate-buffer consumption**

In `TocaRunner._run_instance()`, after `gate_result` passes:

```python
if perception_window:
    latest = perception_window[-1]
    gate_result = self.thalamic_gate.evaluate(latest)
    if not gate_result["should_process"]:
        meta.status = "gated"
        return
    buffered = self.thalamic_gate.flush()
    if buffered:
        seen = set()
        merged = []
        for item in buffered + perception_window:
            key = (item.get("t"), item.get("modality"), item.get("content"))
            if key not in seen:
                seen.add(key)
                merged.append(item)
        perception_window = merged
```

After `event = self._build_event(...)`, before processing:

```python
self.bb.write("last_continuous_event", event, instance_id)
```

- [ ] **Step 4: Run the new test and full experimental tests**

```bash
cd E:\BIG\新建文件夹\新建文件夹
python -m unittest character_mind.tests.experimental.test_toca_integration.TestTocaRunnerIntegration.test_gate_flushes_buffer_into_event_when_threshold_reached -v
python -m unittest character_mind.tests.experimental.test_toca_integration -v
```

Expected: pass.

---

### Task 3: Restore Real Optimistic Writes

**Files:**
- Modify: `experimental/toca_runner.py`
- Test: `tests/experimental/test_toca_integration.py`

- [ ] **Step 1: Add failing test for stale write rejection**

Add to `TestTocaRunnerIntegration`:

```python
async def test_write_back_uses_instance_snapshot_versions(self):
    from character_mind.core.base import SkillResult
    from character_mind.core.orchestrator import CognitiveResult

    self.bb.write("pad", {"pleasure": 0.0, "arousal": 0.3, "dominance": 0.0}, instance_id=1)
    start_versions = self.bb.read_with_versions()
    self.bb.write("pad", {"pleasure": 0.2, "arousal": 0.4, "dominance": 0.0}, instance_id=2)

    result = CognitiveResult(layer_results={
        1: [SkillResult(
            skill_name="plutchik_emotion",
            layer=1,
            output={"internal": {"pleasantness": -0.8, "intensity": 0.9, "dominant": "fear"}},
            success=True,
        )],
    })

    writes, conflicts = self.runner._write_back(result, instance_id=99, expected_versions=start_versions)

    self.assertEqual(writes, 1)  # dominant_emotion did not exist at snapshot version 0
    self.assertGreaterEqual(conflicts, 1)
    self.assertEqual(self.bb.read(["pad"])["pad"]["pleasure"], 0.2)
```

- [ ] **Step 2: Run and verify failure**

```bash
cd E:\BIG\新建文件夹\新建文件夹
python -m unittest character_mind.tests.experimental.test_toca_integration.TestTocaRunnerIntegration.test_write_back_uses_instance_snapshot_versions -v
```

Expected: failure because `_write_back()` does not accept `expected_versions` and rereads current versions.

- [ ] **Step 3: Change `_write_back` signature and callsite**

In `_run_instance()`:

```python
self._write_back(result, instance_id, snap)
```

Change `_write_back`:

```python
def _write_back(self, result, instance_id: int, expected_versions: dict | None = None) -> tuple[int, int]:
    versions = expected_versions or self.bb.read_with_versions()
    ...
    ev = versions.get("pad", (None, 0))[1]
    ...
    return writes, conflicts
```

Use `versions` everywhere instead of `now_versions`.

- [ ] **Step 4: Run tests**

```bash
cd E:\BIG\新建文件夹\新建文件夹
python -m unittest character_mind.tests.experimental.test_toca_integration.TestTocaRunnerIntegration.test_write_back_uses_instance_snapshot_versions -v
python -m unittest character_mind.tests.experimental.test_toca_integration -v
```

Expected: pass.

---

## Phase 2: Close the Perception-Behavior Loop

### Task 4: Connect BehaviorStream to TocaRunner

**Files:**
- Modify: `experimental/toca_runner.py`
- Modify: `experimental/behavior_stream.py`
- Test: `tests/experimental/test_toca_integration.py`

- [ ] **Step 1: Add failing behavior-stream test**

Add to `TestTocaRunnerIntegration`:

```python
async def test_pending_response_emits_behavior_stream_speech(self):
    from character_mind.experimental.behavior_stream import BehaviorStream

    self.runner.behavior_stream = BehaviorStream("测试角色")
    await self.runner.start()
    self.ps.feed_dialogue("你还好吗？", source="对方", intensity=0.7)
    self.runner._last_input_time = time.time()
    await asyncio.sleep(self.config.pipeline_time_s + 1.5)
    await self.runner.stop()

    speech = self.runner.behavior_stream.get_last_speech()
    self.assertIsNotNone(speech)
    self.assertTrue(speech["content"].strip())
```

- [ ] **Step 2: Run and verify failure**

```bash
cd E:\BIG\新建文件夹\新建文件夹
python -m unittest character_mind.tests.experimental.test_toca_integration.TestTocaRunnerIntegration.test_pending_response_emits_behavior_stream_speech -v
```

Expected: failure because `TocaRunner` does not emit behaviors.

- [ ] **Step 3: Add optional behavior stream dependency**

In `TocaRunner.__init__`, add optional parameter:

```python
behavior_stream=None,
```

Set:

```python
self.behavior_stream = behavior_stream
```

After `_write_back()` and consciousness processing:

```python
response = self.get_latest_response()
if self.behavior_stream is not None and response and response.get("text"):
    last_speech = self.behavior_stream.get_last_speech()
    if not last_speech or last_speech.get("content") != response["text"]:
        self.behavior_stream.emit("speech", response["text"], response.get("confidence", 0.8))
```

- [ ] **Step 4: Run behavior and full tests**

```bash
cd E:\BIG\新建文件夹\新建文件夹
python -m unittest character_mind.tests.experimental.test_toca_integration.TestTocaRunnerIntegration.test_pending_response_emits_behavior_stream_speech -v
python -m unittest character_mind.tests.experimental.test_toca_integration -v
```

Expected: pass.

---

## Phase 3: Add Hermes-Style Memory

### Task 5: Add Frozen Snapshot Memory

**Files:**
- Modify: `experimental/offline_consolidation.py`
- Modify: `experimental/blackboard.py`
- Test: `tests/experimental/test_memory_nudges.py`

- [ ] **Step 1: Write failing frozen snapshot tests**

Create `tests/experimental/test_memory_nudges.py`:

```python
import time
import unittest

from character_mind.experimental.blackboard import Blackboard
from character_mind.experimental.offline_consolidation import OfflineConsolidation


class TestMemoryNudges(unittest.TestCase):
    def test_build_frozen_snapshot_contains_workspace_and_self_perception(self):
        bb = Blackboard()
        bb.write("conscious_workspace", [
            {"kind": "emotion", "content": "fear", "salience": 0.8, "source": "l1"}
        ])
        bb.write("self_perception", "我正感到明显的负面情绪。")
        bb.write("dominant_emotion", "fear")
        oc = OfflineConsolidation(bb, episodic_store=None)

        snapshot = oc.build_frozen_snapshot()

        self.assertEqual(snapshot["dominant_emotion"], "fear")
        self.assertEqual(snapshot["workspace"][0]["kind"], "emotion")
        self.assertIn("明显", snapshot["self_perception"])

    def test_blackboard_event_log_records_writes(self):
        bb = Blackboard()
        bb.write("x", 1, instance_id=7)
        log = bb.get_event_log()

        self.assertEqual(log[-1]["key"], "x")
        self.assertEqual(log[-1]["instance_id"], 7)
```

- [ ] **Step 2: Run and verify failure**

```bash
cd E:\BIG\新建文件夹\新建文件夹
python -m unittest character_mind.tests.experimental.test_memory_nudges -v
```

Expected: failure because snapshots and event log accessor do not exist.

- [ ] **Step 3: Implement blackboard event logging**

In `Blackboard.write()` after setting the field, append:

```python
self._event_log.append({
    "t": time.time(),
    "key": key,
    "value": value,
    "version": self._fields[key].version,
    "instance_id": instance_id,
})
if len(self._event_log) > 500:
    self._event_log = self._event_log[-500:]
```

Add:

```python
def get_event_log(self, limit: int = 50) -> list[dict]:
    return list(self._event_log[-limit:])
```

- [ ] **Step 4: Implement frozen snapshot builder**

In `OfflineConsolidation`, add:

```python
def build_frozen_snapshot(self) -> dict:
    current = self.bb.read([
        "conscious_workspace",
        "self_perception",
        "dominant_emotion",
        "pad",
        "active_defense",
        "schema_trajectory",
    ])
    return {
        "t": time.time(),
        "workspace": current.get("conscious_workspace", []),
        "self_perception": current.get("self_perception", ""),
        "dominant_emotion": current.get("dominant_emotion", "neutral"),
        "pad": current.get("pad", {}),
        "active_defense": current.get("active_defense", {}),
        "schema_trajectory": current.get("schema_trajectory", []),
    }
```

At the end of successful `consolidate()`, write:

```python
self.bb.write("frozen_snapshot", self.build_frozen_snapshot())
```

- [ ] **Step 5: Run tests**

```bash
cd E:\BIG\新建文件夹\新建文件夹
python -m unittest character_mind.tests.experimental.test_memory_nudges -v
python -m unittest character_mind.tests.experimental.test_toca_integration -v
```

Expected: pass.

---

### Task 6: Add Procedural Psychological Memory

**Files:**
- Create: `experimental/procedural_memory.py`
- Modify: `experimental/offline_consolidation.py`
- Modify: `experimental/__init__.py`
- Test: `tests/experimental/test_memory_nudges.py`

- [ ] **Step 1: Add failing procedural memory tests**

Append to `tests/experimental/test_memory_nudges.py`:

```python
from character_mind.experimental.procedural_memory import ProceduralMemoryStore


class TestProceduralMemory(unittest.TestCase):
    def test_store_extracts_trigger_pattern_response(self):
        store = ProceduralMemoryStore()
        rule = store.learn_rule(
            trigger="对方沉默",
            prediction="我会被抛弃",
            defense="冷淡试探",
            response_style="短句、否认需要",
            weight=0.7,
        )

        self.assertEqual(rule["trigger"], "对方沉默")
        self.assertGreater(rule["weight"], 0.6)

    def test_retrieve_returns_matching_rule(self):
        store = ProceduralMemoryStore()
        store.learn_rule("对方沉默", "我会被抛弃", "冷淡试探", "短句", 0.7)

        matches = store.retrieve("他很久没回消息，她开始不安")

        self.assertEqual(matches[0]["defense"], "冷淡试探")
```

- [ ] **Step 2: Run and verify failure**

```bash
cd E:\BIG\新建文件夹\新建文件夹
python -m unittest character_mind.tests.experimental.test_memory_nudges -v
```

Expected: failure because `procedural_memory.py` does not exist.

- [ ] **Step 3: Implement `ProceduralMemoryStore`**

Create `experimental/procedural_memory.py`:

```python
from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class ProceduralMemoryStore:
    rules: list[dict] = field(default_factory=list)
    max_rules: int = 50

    def learn_rule(
        self,
        trigger: str,
        prediction: str,
        defense: str,
        response_style: str,
        weight: float = 0.5,
    ) -> dict:
        rule = {
            "t": time.time(),
            "trigger": trigger,
            "prediction": prediction,
            "defense": defense,
            "response_style": response_style,
            "weight": max(0.0, min(1.0, weight)),
        }
        self.rules.append(rule)
        self.rules.sort(key=lambda item: (item["weight"], item["t"]), reverse=True)
        self.rules = self.rules[:self.max_rules]
        return rule

    def retrieve(self, text: str, n: int = 3) -> list[dict]:
        scored = []
        chars = set(text)
        for rule in self.rules:
            trigger_chars = set(rule["trigger"])
            overlap = len(chars & trigger_chars) / max(len(trigger_chars), 1)
            synonym_hit = (
                ("沉默" in rule["trigger"] and ("没回" in text or "不回复" in text)) or
                ("批评" in rule["trigger"] and ("责备" in text or "骂" in text))
            )
            score = overlap + (0.5 if synonym_hit else 0.0) + rule["weight"] * 0.3
            if score >= 0.35:
                item = dict(rule)
                item["match_score"] = score
                scored.append(item)
        scored.sort(key=lambda item: item["match_score"], reverse=True)
        return scored[:n]

    def to_dict(self) -> dict:
        return {"rules": list(self.rules), "max_rules": self.max_rules}

    @classmethod
    def from_dict(cls, data: dict) -> "ProceduralMemoryStore":
        return cls(rules=list(data.get("rules", [])), max_rules=data.get("max_rules", 50))
```

- [ ] **Step 4: Export the store**

In `experimental/__init__.py`:

```python
from .procedural_memory import ProceduralMemoryStore
```

- [ ] **Step 5: Run tests**

```bash
cd E:\BIG\新建文件夹\新建文件夹
python -m unittest character_mind.tests.experimental.test_memory_nudges -v
```

Expected: pass.

---

## Phase 4: Add Self Model

### Task 7: Add First-Person Self Model

**Files:**
- Create: `experimental/self_model.py`
- Modify: `experimental/toca_runner.py`
- Modify: `experimental/consciousness.py`
- Modify: `experimental/__init__.py`
- Test: `tests/experimental/test_conscious_workspace.py`

- [ ] **Step 1: Add failing self-model tests**

Append to `tests/experimental/test_conscious_workspace.py`:

```python
from character_mind.experimental.self_model import SelfModel


class TestSelfModel(unittest.TestCase):
    def test_self_model_updates_private_conflict_from_workspace(self):
        model = SelfModel()
        workspace = [
            {"kind": "emotion", "content": "fear", "salience": 0.8, "source": "l1"},
            {"kind": "memory", "content": "上次他也没有回复", "salience": 0.7, "source": "wm_ltm"},
        ]

        state = model.update(workspace)

        self.assertIn("怕被抛下", state["unresolved_conflict"])
        self.assertIn("装作", state["active_mask"])

    def test_self_model_prompt_context_is_compact(self):
        model = SelfModel()
        model.update([
            {"kind": "emotion", "content": "anger", "salience": 0.8, "source": "l1"}
        ])

        text = model.format_for_context()

        self.assertIn("未说出口", text)
        self.assertLess(len(text), 300)
```

- [ ] **Step 2: Run and verify failure**

```bash
cd E:\BIG\新建文件夹\新建文件夹
python -m unittest character_mind.tests.experimental.test_conscious_workspace -v
```

Expected: failure because `self_model.py` does not exist.

- [ ] **Step 3: Implement `SelfModel`**

Create `experimental/self_model.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SelfModel:
    current_self_image: str = "我需要维持自己的体面。"
    current_other_model: str = "对方的意图尚不明确。"
    unresolved_conflict: str = ""
    active_mask: str = ""
    private_intention: str = ""
    history: list[dict] = field(default_factory=list)

    def update(self, workspace: list[dict]) -> dict:
        text = " ".join(str(item.get("content", "")) for item in workspace)
        kinds = {item.get("kind") for item in workspace}

        if "fear" in text or "没有回复" in text or "抛" in text:
            self.unresolved_conflict = "想靠近确认，但怕被抛下或显得太需要。"
            self.active_mask = "装作无所谓，用短句保护自尊。"
            self.private_intention = "希望对方主动解释并确认关系仍然安全。"
            self.current_other_model = "对方可能正在远离我，也可能只是没有意识到我的不安。"
        elif "anger" in text or "愤" in text:
            self.unresolved_conflict = "想攻击对方，又想保留关系。"
            self.active_mask = "把受伤包装成冷淡或讽刺。"
            self.private_intention = "让对方承认自己造成了伤害。"
        elif "response" in kinds:
            self.private_intention = "把已经形成的回应说出口，同时隐藏更脆弱的动机。"

        state = self.to_dict()
        self.history.append(state)
        self.history = self.history[-10:]
        return state

    def format_for_context(self) -> str:
        return (
            f"【自我模型】自我形象:{self.current_self_image} "
            f"他人模型:{self.current_other_model} "
            f"未说出口的冲突:{self.unresolved_conflict} "
            f"面具:{self.active_mask} "
            f"私下意图:{self.private_intention}"
        )[:300]

    def to_dict(self) -> dict:
        return {
            "current_self_image": self.current_self_image,
            "current_other_model": self.current_other_model,
            "unresolved_conflict": self.unresolved_conflict,
            "active_mask": self.active_mask,
            "private_intention": self.private_intention,
        }
```

- [ ] **Step 4: Connect self-model to runner**

In `TocaRunner.__init__`:

```python
from .self_model import SelfModel
self.self_model = SelfModel()
```

After workspace update in `_run_instance()`:

```python
candidates = self.consciousness.build_workspace_candidates()
workspace = self.consciousness.update_workspace(candidates)
self_model_state = self.self_model.update(workspace)
self.bb.write("self_model", self_model_state, instance_id)
```

In `_build_event()`, if `self_model` exists on blackboard, prepend:

```python
self_model = snap.get("self_model", (None,))[0] if snap else None
if self_model:
    context += f"（未说出口的冲突: {self_model.get('unresolved_conflict', '')}）"
```

- [ ] **Step 5: Export and run tests**

In `experimental/__init__.py`:

```python
from .self_model import SelfModel
```

Run:

```bash
cd E:\BIG\新建文件夹\新建文件夹
python -m unittest character_mind.tests.experimental.test_conscious_workspace -v
python -m unittest character_mind.tests.experimental.test_toca_integration -v
```

Expected: pass.

---

## Phase 5: Integrate Memory Nudges into Runtime

### Task 8: Use Frozen Snapshot and Procedural Rules in Runner Context

**Files:**
- Modify: `experimental/toca_runner.py`
- Modify: `experimental/offline_consolidation.py`
- Test: `tests/experimental/test_memory_nudges.py`
- Test: `tests/experimental/test_toca_integration.py`

- [ ] **Step 1: Add failing test for procedural context injection**

Add to `TestTocaRunnerIntegration`:

```python
async def test_runner_injects_procedural_memory_into_continuous_event(self):
    from character_mind.experimental.procedural_memory import ProceduralMemoryStore

    self.runner.procedural_memory = ProceduralMemoryStore()
    self.runner.procedural_memory.learn_rule(
        "对方沉默", "我会被抛弃", "冷淡试探", "短句、否认需要", 0.8
    )

    await self.runner.start()
    self.ps.feed_internal("他很久没回消息，她开始不安", intensity=0.7)
    self.runner._last_input_time = time.time()
    await asyncio.sleep(self.config.pipeline_time_s + 1.5)
    await self.runner.stop()

    event = self.bb.read(["last_continuous_event"])["last_continuous_event"]
    self.assertIn("习得模式", event["description"])
    self.assertIn("冷淡试探", event["description"])
```

- [ ] **Step 2: Run and verify failure**

```bash
cd E:\BIG\新建文件夹\新建文件夹
python -m unittest character_mind.tests.experimental.test_toca_integration.TestTocaRunnerIntegration.test_runner_injects_procedural_memory_into_continuous_event -v
```

Expected: failure because runner does not own or query procedural memory.

- [ ] **Step 3: Add procedural memory to runner**

In `TocaRunner.__init__`:

```python
from .procedural_memory import ProceduralMemoryStore
self.procedural_memory = ProceduralMemoryStore()
```

Before `_build_event()`:

```python
perception_text = " ".join(p.get("content", "") for p in perception_window)
procedural_matches = self.procedural_memory.retrieve(perception_text)
procedural_context = ""
if procedural_matches:
    lines = ["[习得模式]"]
    for rule in procedural_matches[:2]:
        lines.append(
            f"- 触发:{rule['trigger']} 预期:{rule['prediction']} "
            f"防御:{rule['defense']} 表达:{rule['response_style']}"
        )
    procedural_context = "\n".join(lines)
```

Pass `memory_context + "\n" + procedural_context` into `_build_event()`.

- [ ] **Step 4: Let consolidation learn one simple rule**

In `OfflineConsolidation.consolidate()`, after replay loop, add optional procedural learning when blackboard has repeated workspace fear/defense:

```python
workspace = self.bb.read(["conscious_workspace"]).get("conscious_workspace", [])
workspace_text = " ".join(str(item.get("content", "")) for item in workspace)
if "fear" in workspace_text or "没有回复" in workspace_text:
    rules = self.bb.read(["procedural_rules"]).get("procedural_rules", [])
    rules.append({
        "t": now,
        "trigger": "对方沉默",
        "prediction": "我会被抛弃",
        "defense": "冷淡试探",
        "response_style": "短句、否认需要",
        "weight": 0.6,
    })
    self.bb.write("procedural_rules", rules[-20:])
```

- [ ] **Step 5: Run focused and integration tests**

```bash
cd E:\BIG\新建文件夹\新建文件夹
python -m unittest character_mind.tests.experimental.test_toca_integration.TestTocaRunnerIntegration.test_runner_injects_procedural_memory_into_continuous_event -v
python -m unittest character_mind.tests.experimental.test_memory_nudges -v
python -m unittest character_mind.tests.experimental.test_toca_integration -v
```

Expected: pass.

---

## Phase 6: System-Level Validation

### Task 9: Add Continuous Consciousness Smoke Scenario

**Files:**
- Create: `tests/experimental/test_continuous_consciousness_smoke.py`

- [ ] **Step 1: Write smoke test**

Create:

```python
import asyncio
import os
import sys
import time
import unittest

_pkg_parent = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _pkg_parent not in sys.path:
    sys.path.insert(0, _pkg_parent)

from character_mind import CognitiveOrchestrator, SkillRegistry
from character_mind import BigFiveSkill, PlutchikEmotionSkill, OCCEmotionSkill, ResponseGeneratorSkill
from character_mind.benchmark.mock_provider import MockProvider
from character_mind.experimental.blackboard import Blackboard
from character_mind.experimental.behavior_stream import BehaviorStream
from character_mind.experimental.perception_stream import PerceptionStream
from character_mind.experimental.toca_runner import TocaRunner, TocaConfig


class TestContinuousConsciousnessSmoke(unittest.IsolatedAsyncioTestCase):
    async def test_continuous_runtime_produces_workspace_self_model_and_behavior(self):
        registry = SkillRegistry()
        registry.register(BigFiveSkill())
        registry.register(PlutchikEmotionSkill())
        registry.register(OCCEmotionSkill())
        registry.register(ResponseGeneratorSkill())
        orchestrator = CognitiveOrchestrator(registry=registry)

        bb = Blackboard()
        ps = PerceptionStream()
        behavior = BehaviorStream("林雨")
        runner = TocaRunner(
            bb, ps, orchestrator, MockProvider(quality=0.9, base_tokens=200),
            {
                "name": "林雨",
                "personality": {
                    "openness": 0.6,
                    "conscientiousness": 0.5,
                    "extraversion": 0.4,
                    "agreeableness": 0.55,
                    "neuroticism": 0.75,
                    "attachment_style": "anxious",
                },
                "trauma": {"ace_score": 2, "active_schemas": ["遗弃/不稳定"]},
            },
            TocaConfig(pipeline_time_s=1.0, instance_count=2, window_s=5.0),
            behavior_stream=behavior,
        )

        await runner.start()
        ps.feed_internal("他很久没回消息，她开始害怕被抛下", intensity=0.8)
        runner._last_input_time = time.time()
        await asyncio.sleep(2.5)
        await runner.stop()

        fields = bb.read(["conscious_workspace", "self_model", "pending_response"])
        self.assertTrue(fields["conscious_workspace"])
        self.assertIn("unresolved_conflict", fields["self_model"])
        self.assertTrue(fields["pending_response"]["text"])
        self.assertIsNotNone(behavior.get_last_speech())
```

- [ ] **Step 2: Run smoke test**

```bash
cd E:\BIG\新建文件夹\新建文件夹
python -m unittest character_mind.tests.experimental.test_continuous_consciousness_smoke -v
```

Expected: pass.

- [ ] **Step 3: Run all experimental tests**

```bash
cd E:\BIG\新建文件夹\新建文件夹
python -m unittest character_mind.tests.experimental.test_toca_integration character_mind.tests.experimental.test_conscious_workspace character_mind.tests.experimental.test_memory_nudges character_mind.tests.experimental.test_continuous_consciousness_smoke -v
```

Expected: pass.

---

## Acceptance Criteria

- Low-salience perception is buffered and later merged into a full conscious frame.
- Prediction error increases salience and can alter workspace selection.
- `conscious_workspace` contains a finite ranked set of psychological contents.
- Runner writes `self_model`, `conscious_workspace`, `last_continuous_event`, and `pending_response` into Blackboard.
- `BehaviorStream` receives speech behavior from generated responses.
- Offline consolidation can create a frozen snapshot.
- Procedural memory stores and retrieves trigger-prediction-defense-response rules.
- All existing experimental tests pass, plus new focused tests.

---

## Self-Review Notes

- Spec coverage: The plan covers loop repair, attention/workspace, Hermes-style memory, self-model, behavior feedback, and smoke validation.
- Placeholder scan: No unresolved placeholder steps are intentionally left.
- Type consistency: New APIs are `ConsciousnessLayer.update_workspace`, `ConsciousnessLayer.build_workspace_candidates`, `Blackboard.get_event_log`, `OfflineConsolidation.build_frozen_snapshot`, `ProceduralMemoryStore`, and `SelfModel`.
- Scope check: This is large but still one coherent subsystem because all changes live under `experimental/` and preserve `core/` as the stable cognitive frame.
