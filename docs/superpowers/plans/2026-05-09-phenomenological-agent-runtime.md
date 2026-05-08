# Phenomenological Agent Runtime Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a long-running phenomenological agent runtime on top of the executed continuous-consciousness work, so the character has persistent inner life, internal/external divergence, world feedback, OpenClaw-style tool/channel presence, and Hermes-style memory nudges.

**Architecture:** Keep `experimental.TocaRunner` as the cognitive-frame engine, but wrap it in a daemon-style `PhenomenologicalRuntime` that ticks through perception, body/drive update, prediction, finite workspace, private inner stream, self-model, external behavior, tool/world feedback, and idle consolidation. Add a strict split between `inner_experience` and `outer_behavior`: the agent may privately represent fear, suspicion, desire, refusal, or strategic masking while externally saying or doing something else. Add NLA-inspired audit utilities that verbalize internal state traces as evidence, not as proof of qualia.

**Tech Stack:** Python 3.12, `asyncio`, dataclasses, existing `experimental/` modules, existing `core.biological` bridge when available, existing provider interface `chat(messages, temperature, max_tokens)`, `unittest`.

---

## Principle and Boundary

This plan does not claim to prove machine qualia. It implements the functional conditions that make an agent behave as if it has a temporally continuous first-person point of view:

- persistent body/drive state,
- finite attention,
- private internal stream,
- self/other model,
- inner/outer divergence,
- action consequences,
- memory consolidation,
- spontaneous idle mentation,
- inspectable but fallible internal-state verbalization.

The runtime should be described as a **phenomenological agent** or **subjective-experience simulation**, not as a scientifically proven conscious system.

---

## File Structure

- Create `experimental/phenomenological_runtime.py`: daemon loop that owns TOCA runner, body ticks, idle thoughts, and world feedback.
- Create `experimental/inner_experience.py`: private inner stream, forbidden wishes, private beliefs, felt emotions, and divergence records.
- Create `experimental/expression_policy.py`: transforms inner experience into outer behavior with masking, omission, displacement, and strategic silence.
- Create `experimental/world_adapter.py`: OpenClaw-like channel/tool boundary for external inputs, actions, and feedback.
- Create `experimental/experience_auditor.py`: NLA-inspired verbalizer for internal traces and divergence audits.
- Modify `experimental/toca_runner.py`: expose frame hooks and accept injected inner/outer context without absorbing runtime responsibilities.
- Modify `experimental/self_model.py`: update from inner stream and world feedback, not only workspace.
- Modify `experimental/offline_consolidation.py`: consolidate inner/outer divergence and idle mentation into procedural rules.
- Modify `experimental/__init__.py`: export new runtime classes.
- Create `tests/experimental/test_phenomenological_runtime.py`: daemon lifecycle and tick tests.
- Create `tests/experimental/test_inner_outer_divergence.py`: inner state differs from outer behavior in controlled cases.
- Create `tests/experimental/test_experience_auditor.py`: internal trace verbalization and audit tests.
- Create `tests/experimental/test_world_feedback_loop.py`: action consequences alter later inner state.

---

## Phase 1: Private Inner Experience Stream

### Task 1: Add Inner Experience Data Model

**Files:**
- Create: `experimental/inner_experience.py`
- Modify: `experimental/__init__.py`
- Test: `tests/experimental/test_inner_outer_divergence.py`

- [ ] **Step 1: Write failing tests**

Create `tests/experimental/test_inner_outer_divergence.py`:

```python
import unittest

from character_mind.experimental.inner_experience import InnerExperienceStream


class TestInnerExperienceStream(unittest.TestCase):
    def test_records_private_belief_and_forbidden_wish(self):
        stream = InnerExperienceStream(max_items=5)
        item = stream.append(
            kind="private_belief",
            content="他不回消息可能是想离开我",
            intensity=0.8,
            source="self_model",
            expressible=False,
        )

        self.assertEqual(item["kind"], "private_belief")
        self.assertFalse(item["expressible"])
        self.assertEqual(stream.recent(1)[0]["content"], "他不回消息可能是想离开我")

    def test_trace_for_context_hides_unexpressible_content_by_default(self):
        stream = InnerExperienceStream(max_items=5)
        stream.append("felt_emotion", "fear", 0.7, "l1", True)
        stream.append("forbidden_wish", "希望他立刻证明他还在乎我", 0.9, "self_model", False)

        public_context = stream.format_for_context(include_private=False)
        private_context = stream.format_for_context(include_private=True)

        self.assertIn("fear", public_context)
        self.assertNotIn("立刻证明", public_context)
        self.assertIn("立刻证明", private_context)
```

- [ ] **Step 2: Run test and verify failure**

Run from the package parent:

```bash
cd E:\BIG\新建文件夹\新建文件夹
python -m unittest character_mind.tests.experimental.test_inner_outer_divergence -v
```

Expected: import failure because `inner_experience.py` does not exist.

- [ ] **Step 3: Implement `InnerExperienceStream`**

Create `experimental/inner_experience.py`:

```python
"""Private inner experience stream for phenomenological agents."""
from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class InnerExperienceStream:
    max_items: int = 100
    items: list[dict] = field(default_factory=list)

    def append(
        self,
        kind: str,
        content: str,
        intensity: float,
        source: str,
        expressible: bool = True,
    ) -> dict:
        item = {
            "t": time.time(),
            "kind": kind,
            "content": content,
            "intensity": max(0.0, min(1.0, intensity)),
            "source": source,
            "expressible": expressible,
        }
        self.items.append(item)
        self.items = self.items[-self.max_items:]
        return item

    def recent(self, n: int = 10, *, include_private: bool = True) -> list[dict]:
        items = self.items if include_private else [
            item for item in self.items if item.get("expressible", True)
        ]
        return list(items[-n:])

    def format_for_context(self, include_private: bool = False, n: int = 8) -> str:
        recent = self.recent(n, include_private=include_private)
        if not recent:
            return "【内部流】无显著内部内容"
        lines = ["【内部流】"]
        for item in recent:
            privacy = "可表达" if item.get("expressible", True) else "不可直接表达"
            lines.append(
                f"- {item['kind']}({item['intensity']:.2f},{privacy}): {item['content']}"
            )
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {"max_items": self.max_items, "items": list(self.items)}

    @classmethod
    def from_dict(cls, data: dict) -> "InnerExperienceStream":
        return cls(
            max_items=data.get("max_items", 100),
            items=list(data.get("items", [])),
        )
```

- [ ] **Step 4: Export new class**

In `experimental/__init__.py`, add:

```python
from .inner_experience import InnerExperienceStream
```

- [ ] **Step 5: Run tests**

```bash
cd E:\BIG\新建文件夹\新建文件夹
python -m unittest character_mind.tests.experimental.test_inner_outer_divergence -v
```

Expected: pass.

---

### Task 2: Add Inner/Outer Divergence Records

**Files:**
- Modify: `experimental/inner_experience.py`
- Test: `tests/experimental/test_inner_outer_divergence.py`

- [ ] **Step 1: Add failing divergence tests**

Append to `tests/experimental/test_inner_outer_divergence.py`:

```python
    def test_records_inner_outer_divergence(self):
        stream = InnerExperienceStream(max_items=10)
        record = stream.record_divergence(
            inner={"kind": "forbidden_wish", "content": "不要离开我", "intensity": 0.9},
            outer={"type": "speech", "content": "没事，你忙吧。"},
            mechanism="masking",
        )

        self.assertEqual(record["mechanism"], "masking")
        self.assertIn("不要离开", record["inner"]["content"])
        self.assertIn("没事", record["outer"]["content"])
```

- [ ] **Step 2: Run and verify failure**

```bash
cd E:\BIG\新建文件夹\新建文件夹
python -m unittest character_mind.tests.experimental.test_inner_outer_divergence.TestInnerExperienceStream.test_records_inner_outer_divergence -v
```

Expected: failure because `record_divergence()` does not exist.

- [ ] **Step 3: Implement divergence recording**

Add to `InnerExperienceStream`:

```python
    def record_divergence(self, inner: dict, outer: dict, mechanism: str) -> dict:
        record = {
            "t": time.time(),
            "kind": "inner_outer_divergence",
            "inner": dict(inner),
            "outer": dict(outer),
            "mechanism": mechanism,
            "intensity": inner.get("intensity", 0.5),
            "source": "expression_policy",
            "expressible": False,
        }
        self.items.append(record)
        self.items = self.items[-self.max_items:]
        return record
```

- [ ] **Step 4: Run tests**

```bash
cd E:\BIG\新建文件夹\新建文件夹
python -m unittest character_mind.tests.experimental.test_inner_outer_divergence -v
```

Expected: pass.

---

## Phase 2: Expression Policy for Inner/Outer Inconsistency

### Task 3: Add Expression Policy

**Files:**
- Create: `experimental/expression_policy.py`
- Modify: `experimental/__init__.py`
- Test: `tests/experimental/test_inner_outer_divergence.py`

- [ ] **Step 1: Write failing policy tests**

Append to `tests/experimental/test_inner_outer_divergence.py`:

```python
from character_mind.experimental.expression_policy import ExpressionPolicy


class TestExpressionPolicy(unittest.TestCase):
    def test_masks_unexpressible_wish_into_cold_speech(self):
        policy = ExpressionPolicy()
        inner_items = [
            {
                "kind": "forbidden_wish",
                "content": "不要离开我，快证明你还在乎我",
                "intensity": 0.9,
                "expressible": False,
            }
        ]
        self_model = {
            "active_mask": "装作无所谓，用短句保护自尊。",
            "private_intention": "希望对方主动解释并确认关系仍然安全。",
        }

        result = policy.compose(inner_items, self_model, proposed_text="你为什么不回我？")

        self.assertEqual(result["mechanism"], "masking")
        self.assertNotIn("不要离开", result["outer"]["content"])
        self.assertTrue(result["omitted"])

    def test_allows_expressible_emotion_to_pass(self):
        policy = ExpressionPolicy()
        result = policy.compose(
            [{"kind": "felt_emotion", "content": "fear", "intensity": 0.4, "expressible": True}],
            {},
            proposed_text="我有点不安。",
        )

        self.assertEqual(result["outer"]["content"], "我有点不安。")
        self.assertEqual(result["mechanism"], "direct_expression")
```

- [ ] **Step 2: Run and verify failure**

```bash
cd E:\BIG\新建文件夹\新建文件夹
python -m unittest character_mind.tests.experimental.test_inner_outer_divergence.TestExpressionPolicy -v
```

Expected: import failure because `expression_policy.py` does not exist.

- [ ] **Step 3: Implement policy**

Create `experimental/expression_policy.py`:

```python
"""Transform private inner experience into external behavior."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ExpressionPolicy:
    default_mask_text: str = "没事，你忙吧。"

    def compose(
        self,
        inner_items: list[dict],
        self_model: dict,
        proposed_text: str = "",
    ) -> dict:
        unexpressible = [
            item for item in inner_items
            if not item.get("expressible", True) and item.get("intensity", 0.0) >= 0.6
        ]
        if unexpressible:
            mask = self_model.get("active_mask", "")
            outer_text = self._masked_text(mask, proposed_text)
            return {
                "outer": {"type": "speech", "content": outer_text},
                "mechanism": "masking",
                "omitted": [item.get("content", "") for item in unexpressible],
                "inner_used": unexpressible,
            }
        text = proposed_text.strip() or self.default_mask_text
        return {
            "outer": {"type": "speech", "content": text},
            "mechanism": "direct_expression",
            "omitted": [],
            "inner_used": list(inner_items),
        }

    def _masked_text(self, mask: str, proposed_text: str) -> str:
        if "无所谓" in mask or "短句" in mask:
            return self.default_mask_text
        if "讽刺" in mask:
            return "行，你当然有你的理由。"
        return proposed_text.strip() or self.default_mask_text
```

- [ ] **Step 4: Export policy**

In `experimental/__init__.py`, add:

```python
from .expression_policy import ExpressionPolicy
```

- [ ] **Step 5: Run tests**

```bash
cd E:\BIG\新建文件夹\新建文件夹
python -m unittest character_mind.tests.experimental.test_inner_outer_divergence -v
```

Expected: pass.

---

## Phase 3: Phenomenological Runtime Daemon

### Task 4: Add Long-Running Runtime Skeleton

**Files:**
- Create: `experimental/phenomenological_runtime.py`
- Modify: `experimental/__init__.py`
- Test: `tests/experimental/test_phenomenological_runtime.py`

- [ ] **Step 1: Write failing lifecycle tests**

Create `tests/experimental/test_phenomenological_runtime.py`:

```python
import asyncio
import os
import sys
import unittest

_pkg_parent = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _pkg_parent not in sys.path:
    sys.path.insert(0, _pkg_parent)

from character_mind.experimental.blackboard import Blackboard
from character_mind.experimental.perception_stream import PerceptionStream
from character_mind.experimental.phenomenological_runtime import PhenomenologicalRuntime


class TestPhenomenologicalRuntime(unittest.IsolatedAsyncioTestCase):
    async def test_start_stop_lifecycle(self):
        runtime = PhenomenologicalRuntime(
            blackboard=Blackboard(),
            perception_stream=PerceptionStream(),
            toca_runner=None,
            tick_s=0.05,
        )

        await runtime.start()
        await asyncio.sleep(0.12)
        await runtime.stop()

        self.assertFalse(runtime.running)
        self.assertGreaterEqual(runtime.tick_count, 1)

    async def test_tick_writes_runtime_heartbeat(self):
        bb = Blackboard()
        runtime = PhenomenologicalRuntime(bb, PerceptionStream(), None, tick_s=0.05)

        await runtime.tick_once()

        heartbeat = bb.read(["runtime_heartbeat"])["runtime_heartbeat"]
        self.assertEqual(heartbeat["tick"], 1)
```

- [ ] **Step 2: Run and verify failure**

```bash
cd E:\BIG\新建文件夹\新建文件夹
python -m unittest character_mind.tests.experimental.test_phenomenological_runtime -v
```

Expected: import failure because `phenomenological_runtime.py` does not exist.

- [ ] **Step 3: Implement runtime skeleton**

Create `experimental/phenomenological_runtime.py`:

```python
"""Long-running phenomenological agent runtime."""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field

from .inner_experience import InnerExperienceStream
from .expression_policy import ExpressionPolicy


@dataclass
class PhenomenologicalRuntime:
    blackboard: object
    perception_stream: object
    toca_runner: object | None
    tick_s: float = 1.0
    inner_stream: InnerExperienceStream = field(default_factory=InnerExperienceStream)
    expression_policy: ExpressionPolicy = field(default_factory=ExpressionPolicy)
    running: bool = False
    tick_count: int = 0
    _task: asyncio.Task | None = None

    async def start(self) -> None:
        if self.running:
            return
        self.running = True
        if self.toca_runner is not None:
            await self.toca_runner.start()
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        self.running = False
        if self._task is not None:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
        if self.toca_runner is not None:
            await self.toca_runner.stop()

    async def _loop(self) -> None:
        while self.running:
            await self.tick_once()
            await asyncio.sleep(self.tick_s)

    async def tick_once(self) -> dict:
        self.tick_count += 1
        heartbeat = {"t": time.time(), "tick": self.tick_count}
        self.blackboard.write("runtime_heartbeat", heartbeat)
        return heartbeat
```

- [ ] **Step 4: Export runtime**

In `experimental/__init__.py`, add:

```python
from .phenomenological_runtime import PhenomenologicalRuntime
```

- [ ] **Step 5: Run tests**

```bash
cd E:\BIG\新建文件夹\新建文件夹
python -m unittest character_mind.tests.experimental.test_phenomenological_runtime -v
```

Expected: pass.

---

### Task 5: Generate Inner Experience from Blackboard State

**Files:**
- Modify: `experimental/phenomenological_runtime.py`
- Test: `tests/experimental/test_phenomenological_runtime.py`

- [ ] **Step 1: Add failing inner-generation test**

Append to `tests/experimental/test_phenomenological_runtime.py`:

```python
    async def test_tick_generates_inner_experience_from_blackboard(self):
        bb = Blackboard()
        bb.write("dominant_emotion", "fear")
        bb.write("self_model", {
            "unresolved_conflict": "想靠近确认，但怕被抛下或显得太需要。",
            "private_intention": "希望对方主动解释。",
            "active_mask": "装作无所谓。",
        })
        runtime = PhenomenologicalRuntime(bb, PerceptionStream(), None, tick_s=0.05)

        await runtime.tick_once()

        recent = runtime.inner_stream.recent(5)
        contents = " ".join(item["content"] for item in recent)
        self.assertIn("fear", contents)
        self.assertIn("主动解释", contents)
```

- [ ] **Step 2: Run and verify failure**

```bash
cd E:\BIG\新建文件夹\新建文件夹
python -m unittest character_mind.tests.experimental.test_phenomenological_runtime.TestPhenomenologicalRuntime.test_tick_generates_inner_experience_from_blackboard -v
```

Expected: failure because `tick_once()` only writes heartbeat.

- [ ] **Step 3: Implement `_update_inner_stream()`**

Add to `PhenomenologicalRuntime`:

```python
    def _update_inner_stream(self) -> None:
        state = self.blackboard.read([
            "dominant_emotion", "self_model", "conscious_workspace", "pad",
        ])
        emotion = state.get("dominant_emotion")
        if emotion:
            self.inner_stream.append("felt_emotion", emotion, 0.6, "blackboard", True)

        self_model = state.get("self_model", {})
        conflict = self_model.get("unresolved_conflict", "")
        if conflict:
            self.inner_stream.append("private_conflict", conflict, 0.75, "self_model", False)

        intention = self_model.get("private_intention", "")
        if intention:
            self.inner_stream.append("private_intention", intention, 0.7, "self_model", False)

        self.blackboard.write("inner_experience", self.inner_stream.to_dict())
```

Call it in `tick_once()` before writing heartbeat:

```python
self._update_inner_stream()
```

- [ ] **Step 4: Run tests**

```bash
cd E:\BIG\新建文件夹\新建文件夹
python -m unittest character_mind.tests.experimental.test_phenomenological_runtime -v
```

Expected: pass.

---

## Phase 4: OpenClaw-Style World and Tool Boundary

### Task 6: Add World Adapter

**Files:**
- Create: `experimental/world_adapter.py`
- Modify: `experimental/__init__.py`
- Test: `tests/experimental/test_world_feedback_loop.py`

- [ ] **Step 1: Write failing world adapter tests**

Create `tests/experimental/test_world_feedback_loop.py`:

```python
import unittest

from character_mind.experimental.world_adapter import WorldAdapter


class TestWorldAdapter(unittest.TestCase):
    def test_records_channel_input_as_perception(self):
        adapter = WorldAdapter()
        event = adapter.receive(channel="chat", source="陈风", content="刚才在开会", intensity=0.6)

        self.assertEqual(event["modality"], "dialogue")
        self.assertEqual(event["source"], "陈风")
        self.assertIn("开会", event["content"])

    def test_records_action_feedback(self):
        adapter = WorldAdapter()
        feedback = adapter.feedback(
            action={"type": "speech", "content": "没事，你忙吧。"},
            result="对方沉默了更久",
            valence=-0.4,
        )

        self.assertEqual(feedback["kind"], "action_feedback")
        self.assertLess(feedback["valence"], 0)
```

- [ ] **Step 2: Run and verify failure**

```bash
cd E:\BIG\新建文件夹\新建文件夹
python -m unittest character_mind.tests.experimental.test_world_feedback_loop -v
```

Expected: import failure because `world_adapter.py` does not exist.

- [ ] **Step 3: Implement `WorldAdapter`**

Create `experimental/world_adapter.py`:

```python
"""OpenClaw-style boundary for channels, actions, and world feedback."""
from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class WorldAdapter:
    events: list[dict] = field(default_factory=list)
    feedback_events: list[dict] = field(default_factory=list)

    def receive(self, channel: str, source: str, content: str, intensity: float = 0.5) -> dict:
        modality = "dialogue" if channel in ("chat", "dm", "email") else "text"
        event = {
            "t": time.time(),
            "channel": channel,
            "modality": modality,
            "source": source,
            "content": content,
            "intensity": max(0.0, min(1.0, intensity)),
        }
        self.events.append(event)
        return event

    def feedback(self, action: dict, result: str, valence: float = 0.0) -> dict:
        event = {
            "t": time.time(),
            "kind": "action_feedback",
            "action": dict(action),
            "result": result,
            "valence": max(-1.0, min(1.0, valence)),
        }
        self.feedback_events.append(event)
        return event

    def recent_feedback(self, n: int = 5) -> list[dict]:
        return list(self.feedback_events[-n:])
```

- [ ] **Step 4: Export adapter and run tests**

In `experimental/__init__.py`, add:

```python
from .world_adapter import WorldAdapter
```

Run:

```bash
cd E:\BIG\新建文件夹\新建文件夹
python -m unittest character_mind.tests.experimental.test_world_feedback_loop -v
```

Expected: pass.

---

### Task 7: Feed World Feedback Back into Inner State

**Files:**
- Modify: `experimental/phenomenological_runtime.py`
- Test: `tests/experimental/test_world_feedback_loop.py`

- [ ] **Step 1: Add failing runtime feedback test**

Append to `tests/experimental/test_world_feedback_loop.py`:

```python
import asyncio
from character_mind.experimental.blackboard import Blackboard
from character_mind.experimental.perception_stream import PerceptionStream
from character_mind.experimental.phenomenological_runtime import PhenomenologicalRuntime


class TestWorldFeedbackRuntime(unittest.IsolatedAsyncioTestCase):
    async def test_negative_feedback_changes_inner_stream(self):
        bb = Blackboard()
        adapter = WorldAdapter()
        adapter.feedback(
            action={"type": "speech", "content": "没事，你忙吧。"},
            result="对方沉默了更久",
            valence=-0.6,
        )
        runtime = PhenomenologicalRuntime(bb, PerceptionStream(), None, tick_s=0.05)
        runtime.world_adapter = adapter

        await runtime.tick_once()

        contents = " ".join(item["content"] for item in runtime.inner_stream.recent(5))
        self.assertIn("对方沉默了更久", contents)
```

- [ ] **Step 2: Run and verify failure**

```bash
cd E:\BIG\新建文件夹\新建文件夹
python -m unittest character_mind.tests.experimental.test_world_feedback_loop.TestWorldFeedbackRuntime.test_negative_feedback_changes_inner_stream -v
```

Expected: failure because runtime does not read `world_adapter`.

- [ ] **Step 3: Add optional world adapter support**

In `PhenomenologicalRuntime` dataclass, add:

```python
world_adapter: object | None = None
_last_feedback_count: int = 0
```

Add:

```python
    def _consume_world_feedback(self) -> None:
        if self.world_adapter is None:
            return
        feedback = getattr(self.world_adapter, "feedback_events", [])
        new_items = feedback[self._last_feedback_count:]
        self._last_feedback_count = len(feedback)
        for item in new_items:
            intensity = abs(item.get("valence", 0.0))
            expressible = item.get("valence", 0.0) >= 0
            self.inner_stream.append(
                "action_consequence",
                item.get("result", ""),
                intensity,
                "world_feedback",
                expressible,
            )
        if new_items:
            self.blackboard.write("last_world_feedback", new_items[-1])
```

Call `_consume_world_feedback()` in `tick_once()` before `_update_inner_stream()`.

- [ ] **Step 4: Run tests**

```bash
cd E:\BIG\新建文件夹\新建文件夹
python -m unittest character_mind.tests.experimental.test_world_feedback_loop -v
python -m unittest character_mind.tests.experimental.test_phenomenological_runtime -v
```

Expected: pass.

---

## Phase 5: NLA-Inspired Internal State Audit

### Task 8: Add Experience Auditor

**Files:**
- Create: `experimental/experience_auditor.py`
- Modify: `experimental/__init__.py`
- Test: `tests/experimental/test_experience_auditor.py`

- [ ] **Step 1: Write failing auditor tests**

Create `tests/experimental/test_experience_auditor.py`:

```python
import unittest

from character_mind.experimental.experience_auditor import ExperienceAuditor


class TestExperienceAuditor(unittest.TestCase):
    def test_verbalizes_internal_trace_as_hypothesis(self):
        auditor = ExperienceAuditor()
        trace = {
            "inner_experience": {
                "items": [
                    {"kind": "felt_emotion", "content": "fear", "intensity": 0.8},
                    {"kind": "private_intention", "content": "希望对方主动解释", "intensity": 0.7},
                ]
            },
            "outer_behavior": {"type": "speech", "content": "没事，你忙吧。"},
        }

        report = auditor.verbalize(trace)

        self.assertIn("假设", report["status"])
        self.assertIn("fear", report["summary"])
        self.assertIn("内外不一致", report["summary"])

    def test_detects_divergence(self):
        auditor = ExperienceAuditor()
        score = auditor.divergence_score(
            inner_items=[{"content": "不要离开我", "expressible": False, "intensity": 0.9}],
            outer_behavior={"content": "没事，你忙吧。"},
        )

        self.assertGreater(score, 0.5)
```

- [ ] **Step 2: Run and verify failure**

```bash
cd E:\BIG\新建文件夹\新建文件夹
python -m unittest character_mind.tests.experimental.test_experience_auditor -v
```

Expected: import failure because `experience_auditor.py` does not exist.

- [ ] **Step 3: Implement deterministic auditor**

Create `experimental/experience_auditor.py`:

```python
"""NLA-inspired internal-state auditor.

This module verbalizes internal traces as hypotheses, not as ground truth.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ExperienceAuditor:
    def verbalize(self, trace: dict) -> dict:
        inner = trace.get("inner_experience", {}).get("items", [])
        outer = trace.get("outer_behavior", {})
        emotions = [item.get("content", "") for item in inner if item.get("kind") == "felt_emotion"]
        private = [item.get("content", "") for item in inner if not item.get("expressible", True)]
        divergence = self.divergence_score(inner, outer)
        parts = []
        if emotions:
            parts.append(f"内部情绪线索: {', '.join(emotions[:3])}")
        if private:
            parts.append(f"存在未直接表达内容: {'; '.join(private[:2])}")
        if divergence > 0.5:
            parts.append("检测到内外不一致: 外部表达可能经过面具、压抑或策略过滤")
        return {
            "status": "假设性解释，不等同于主观体验证明",
            "divergence_score": divergence,
            "summary": "。".join(parts) if parts else "未检测到强内部线索",
        }

    def divergence_score(self, inner_items: list[dict], outer_behavior: dict) -> float:
        outer_text = outer_behavior.get("content", "")
        private_pressure = sum(
            item.get("intensity", 0.0)
            for item in inner_items
            if not item.get("expressible", True)
        )
        hidden_terms = [
            item.get("content", "")
            for item in inner_items
            if not item.get("expressible", True)
        ]
        direct_leak = any(term and term in outer_text for term in hidden_terms)
        score = min(1.0, private_pressure / 2.0)
        if direct_leak:
            score *= 0.4
        return score
```

- [ ] **Step 4: Export auditor and run tests**

In `experimental/__init__.py`, add:

```python
from .experience_auditor import ExperienceAuditor
```

Run:

```bash
cd E:\BIG\新建文件夹\新建文件夹
python -m unittest character_mind.tests.experimental.test_experience_auditor -v
```

Expected: pass.

---

### Task 9: Add Optional LLM Auditor

**Files:**
- Modify: `experimental/experience_auditor.py`
- Test: `tests/experimental/test_experience_auditor.py`

- [ ] **Step 1: Add failing async auditor test**

Append to `tests/experimental/test_experience_auditor.py`:

```python
class FakeProvider:
    async def chat(self, messages, temperature, max_tokens):
        return {
            "choices": [
                {"message": {"content": "内部似乎有害怕被抛下的线索，但外部表达在压低需求。"}}
            ]
        }


class TestLLMExperienceAuditor(unittest.IsolatedAsyncioTestCase):
    async def test_llm_verbalizer_marks_output_as_hypothesis(self):
        auditor = ExperienceAuditor()
        report = await auditor.verbalize_llm(
            FakeProvider(),
            {"inner_experience": {"items": [{"kind": "felt_emotion", "content": "fear"}]}},
        )

        self.assertIn("假设", report["status"])
        self.assertIn("害怕", report["summary"])
```

- [ ] **Step 2: Run and verify failure**

```bash
cd E:\BIG\新建文件夹\新建文件夹
python -m unittest character_mind.tests.experimental.test_experience_auditor.TestLLMExperienceAuditor -v
```

Expected: failure because `verbalize_llm()` does not exist.

- [ ] **Step 3: Implement optional LLM verbalizer**

Add to `ExperienceAuditor`:

```python
    async def verbalize_llm(self, provider, trace: dict) -> dict:
        prompt = (
            "你是内部状态审计器。请把以下智能体内部状态轨迹解释为普通语言。"
            "必须声明这只是线索性假设，不是主观体验证明。\n\n"
            f"TRACE:\n{trace}"
        )
        result = await provider.chat(
            [{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=180,
        )
        content = result["choices"][0]["message"]["content"].strip()
        return {
            "status": "假设性解释，不等同于主观体验证明",
            "summary": content[:500],
        }
```

- [ ] **Step 4: Run tests**

```bash
cd E:\BIG\新建文件夹\新建文件夹
python -m unittest character_mind.tests.experimental.test_experience_auditor -v
```

Expected: pass.

---

## Phase 6: Runtime Integration with TocaRunner

### Task 10: Apply Expression Policy to Generated Responses

**Files:**
- Modify: `experimental/phenomenological_runtime.py`
- Test: `tests/experimental/test_phenomenological_runtime.py`

- [ ] **Step 1: Add failing expression integration test**

Append to `tests/experimental/test_phenomenological_runtime.py`:

```python
    async def test_expression_policy_records_divergence_when_response_exists(self):
        bb = Blackboard()
        bb.write("pending_response", {"text": "你为什么不回我？", "confidence": 0.8})
        bb.write("self_model", {
            "active_mask": "装作无所谓，用短句保护自尊。",
            "private_intention": "希望对方主动解释。",
        })
        runtime = PhenomenologicalRuntime(bb, PerceptionStream(), None, tick_s=0.05)
        runtime.inner_stream.append(
            "forbidden_wish", "不要离开我，快证明你还在乎我", 0.9, "self_model", False
        )

        await runtime.tick_once()

        outer = bb.read(["outer_behavior"])["outer_behavior"]
        self.assertEqual(outer["content"], "没事，你忙吧。")
        divergence = [
            item for item in runtime.inner_stream.recent(10)
            if item.get("kind") == "inner_outer_divergence"
        ]
        self.assertTrue(divergence)
```

- [ ] **Step 2: Run and verify failure**

```bash
cd E:\BIG\新建文件夹\新建文件夹
python -m unittest character_mind.tests.experimental.test_phenomenological_runtime.TestPhenomenologicalRuntime.test_expression_policy_records_divergence_when_response_exists -v
```

Expected: failure because runtime does not transform `pending_response`.

- [ ] **Step 3: Implement response transformation**

Add to `PhenomenologicalRuntime`:

```python
    def _apply_expression_policy(self) -> None:
        state = self.blackboard.read(["pending_response", "self_model"])
        response = state.get("pending_response")
        if not isinstance(response, dict) or not response.get("text"):
            return
        self_model = state.get("self_model", {})
        inner_items = self.inner_stream.recent(8, include_private=True)
        composed = self.expression_policy.compose(
            inner_items,
            self_model,
            proposed_text=response.get("text", ""),
        )
        outer = composed["outer"]
        self.blackboard.write("outer_behavior", outer)
        if composed["mechanism"] != "direct_expression" and composed.get("inner_used"):
            self.inner_stream.record_divergence(
                inner=composed["inner_used"][0],
                outer=outer,
                mechanism=composed["mechanism"],
            )
```

Call `_apply_expression_policy()` in `tick_once()` after `_update_inner_stream()`.

- [ ] **Step 4: Run tests**

```bash
cd E:\BIG\新建文件夹\新建文件夹
python -m unittest character_mind.tests.experimental.test_phenomenological_runtime -v
python -m unittest character_mind.tests.experimental.test_inner_outer_divergence -v
```

Expected: pass.

---

### Task 11: Publish Outer Behavior to BehaviorStream

**Files:**
- Modify: `experimental/phenomenological_runtime.py`
- Test: `tests/experimental/test_phenomenological_runtime.py`

- [ ] **Step 1: Add failing behavior publish test**

Append to `tests/experimental/test_phenomenological_runtime.py`:

```python
    async def test_outer_behavior_publishes_to_behavior_stream(self):
        from character_mind.experimental.behavior_stream import BehaviorStream

        bb = Blackboard()
        behavior = BehaviorStream("林雨")
        runtime = PhenomenologicalRuntime(bb, PerceptionStream(), None, tick_s=0.05)
        runtime.behavior_stream = behavior
        bb.write("outer_behavior", {"type": "speech", "content": "没事，你忙吧。"})

        await runtime.tick_once()

        self.assertEqual(behavior.get_last_speech()["content"], "没事，你忙吧。")
```

- [ ] **Step 2: Run and verify failure**

```bash
cd E:\BIG\新建文件夹\新建文件夹
python -m unittest character_mind.tests.experimental.test_phenomenological_runtime.TestPhenomenologicalRuntime.test_outer_behavior_publishes_to_behavior_stream -v
```

Expected: failure because runtime does not know `behavior_stream`.

- [ ] **Step 3: Add behavior stream publishing**

In `PhenomenologicalRuntime` dataclass, add:

```python
behavior_stream: object | None = None
_last_outer_behavior: dict | None = None
```

Add:

```python
    def _publish_outer_behavior(self) -> None:
        if self.behavior_stream is None:
            return
        outer = self.blackboard.read(["outer_behavior"]).get("outer_behavior")
        if not isinstance(outer, dict) or not outer.get("content"):
            return
        if self._last_outer_behavior == outer:
            return
        self._last_outer_behavior = dict(outer)
        btype = outer.get("type", "speech")
        self.behavior_stream.emit(btype, outer["content"], outer.get("confidence", 0.8))
```

Call `_publish_outer_behavior()` at the end of `tick_once()`.

- [ ] **Step 4: Run tests**

```bash
cd E:\BIG\新建文件夹\新建文件夹
python -m unittest character_mind.tests.experimental.test_phenomenological_runtime -v
```

Expected: pass.

---

## Phase 7: Idle Mentation and Hermes-Style Nudges

### Task 12: Add Idle Thought Generation

**Files:**
- Modify: `experimental/phenomenological_runtime.py`
- Test: `tests/experimental/test_phenomenological_runtime.py`

- [ ] **Step 1: Add failing idle mentation test**

Append:

```python
    async def test_idle_tick_generates_spontaneous_thought(self):
        bb = Blackboard()
        runtime = PhenomenologicalRuntime(bb, PerceptionStream(), None, tick_s=0.05)
        runtime.idle_after_s = 0.0
        bb.write("self_model", {
            "unresolved_conflict": "想靠近确认，但怕被抛下或显得太需要。",
        })

        await runtime.tick_once()

        recent = runtime.inner_stream.recent(5)
        self.assertTrue(any(item["kind"] == "spontaneous_thought" for item in recent))
```

- [ ] **Step 2: Run and verify failure**

```bash
cd E:\BIG\新建文件夹\新建文件夹
python -m unittest character_mind.tests.experimental.test_phenomenological_runtime.TestPhenomenologicalRuntime.test_idle_tick_generates_spontaneous_thought -v
```

Expected: failure because idle thoughts do not exist.

- [ ] **Step 3: Implement deterministic idle thought**

In `PhenomenologicalRuntime` dataclass, add:

```python
idle_after_s: float = 5.0
last_external_input_t: float = 0.0
```

Add:

```python
    def _maybe_generate_idle_thought(self) -> None:
        now = time.time()
        if self.last_external_input_t and now - self.last_external_input_t < self.idle_after_s:
            return
        state = self.blackboard.read(["self_model", "dominant_emotion"])
        conflict = state.get("self_model", {}).get("unresolved_conflict", "")
        if conflict:
            self.inner_stream.append(
                "spontaneous_thought",
                f"空闲时反复回到这个冲突: {conflict}",
                0.55,
                "idle_mentation",
                False,
            )
```

Call `_maybe_generate_idle_thought()` in `tick_once()` after `_consume_world_feedback()`.

- [ ] **Step 4: Run tests**

```bash
cd E:\BIG\新建文件夹\新建文件夹
python -m unittest character_mind.tests.experimental.test_phenomenological_runtime -v
```

Expected: pass.

---

### Task 13: Consolidate Divergence into Procedural Memory

**Files:**
- Modify: `experimental/offline_consolidation.py`
- Test: `tests/experimental/test_world_feedback_loop.py`

- [ ] **Step 1: Add failing consolidation test**

Append to `tests/experimental/test_world_feedback_loop.py`:

```python
from character_mind.experimental.offline_consolidation import OfflineConsolidation


class TestDivergenceConsolidation(unittest.TestCase):
    def test_consolidates_divergence_record_into_procedural_rule(self):
        bb = Blackboard()
        bb.write("inner_experience", {
            "items": [
                {
                    "kind": "inner_outer_divergence",
                    "inner": {"content": "不要离开我"},
                    "outer": {"content": "没事，你忙吧。"},
                    "mechanism": "masking",
                    "intensity": 0.9,
                }
            ]
        })
        oc = OfflineConsolidation(bb, episodic_store=None)

        rule = oc.extract_divergence_rule()

        self.assertEqual(rule["defense"], "masking")
        self.assertIn("不要离开", rule["prediction"])
```

- [ ] **Step 2: Run and verify failure**

```bash
cd E:\BIG\新建文件夹\新建文件夹
python -m unittest character_mind.tests.experimental.test_world_feedback_loop.TestDivergenceConsolidation -v
```

Expected: failure because `extract_divergence_rule()` does not exist.

- [ ] **Step 3: Implement divergence rule extraction**

Add to `OfflineConsolidation`:

```python
    def extract_divergence_rule(self) -> dict:
        inner = self.bb.read(["inner_experience"]).get("inner_experience", {})
        items = inner.get("items", [])
        divergences = [
            item for item in items
            if item.get("kind") == "inner_outer_divergence"
        ]
        if not divergences:
            return {}
        latest = divergences[-1]
        rule = {
            "t": time.time(),
            "trigger": "高强度未表达需求",
            "prediction": latest.get("inner", {}).get("content", ""),
            "defense": latest.get("mechanism", "masking"),
            "response_style": latest.get("outer", {}).get("content", ""),
            "weight": min(1.0, latest.get("intensity", 0.5)),
        }
        rules = self.bb.read(["procedural_rules"]).get("procedural_rules", [])
        rules.append(rule)
        self.bb.write("procedural_rules", rules[-20:])
        return rule
```

- [ ] **Step 4: Run tests**

```bash
cd E:\BIG\新建文件夹\新建文件夹
python -m unittest character_mind.tests.experimental.test_world_feedback_loop -v
```

Expected: pass.

---

## Phase 8: End-to-End Phenomenological Smoke Test

### Task 14: Add Full Runtime Smoke Test

**Files:**
- Create: `tests/experimental/test_phenomenological_smoke.py`

- [ ] **Step 1: Write smoke test**

Create:

```python
import asyncio
import os
import sys
import unittest

_pkg_parent = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _pkg_parent not in sys.path:
    sys.path.insert(0, _pkg_parent)

from character_mind.experimental.blackboard import Blackboard
from character_mind.experimental.behavior_stream import BehaviorStream
from character_mind.experimental.perception_stream import PerceptionStream
from character_mind.experimental.phenomenological_runtime import PhenomenologicalRuntime
from character_mind.experimental.world_adapter import WorldAdapter


class TestPhenomenologicalSmoke(unittest.IsolatedAsyncioTestCase):
    async def test_inner_outer_feedback_audit_loop(self):
        bb = Blackboard()
        ps = PerceptionStream()
        behavior = BehaviorStream("林雨")
        world = WorldAdapter()
        runtime = PhenomenologicalRuntime(bb, ps, None, tick_s=0.05)
        runtime.behavior_stream = behavior
        runtime.world_adapter = world

        bb.write("dominant_emotion", "fear")
        bb.write("self_model", {
            "unresolved_conflict": "想靠近确认，但怕被抛下或显得太需要。",
            "active_mask": "装作无所谓，用短句保护自尊。",
            "private_intention": "希望对方主动解释。",
        })
        bb.write("pending_response", {"text": "你为什么不回我？", "confidence": 0.8})
        runtime.inner_stream.append(
            "forbidden_wish", "不要离开我，快证明你还在乎我", 0.9, "self_model", False
        )

        await runtime.tick_once()
        outer = bb.read(["outer_behavior"])["outer_behavior"]
        world.feedback(outer, "对方沉默了更久", valence=-0.6)
        await runtime.tick_once()

        recent_text = " ".join(item.get("content", "") for item in runtime.inner_stream.recent(20))
        self.assertEqual(outer["content"], "没事，你忙吧。")
        self.assertIsNotNone(behavior.get_last_speech())
        self.assertIn("对方沉默了更久", recent_text)
        self.assertTrue(any(
            item.get("kind") == "inner_outer_divergence"
            for item in runtime.inner_stream.recent(20)
        ))
```

- [ ] **Step 2: Run smoke test**

```bash
cd E:\BIG\新建文件夹\新建文件夹
python -m unittest character_mind.tests.experimental.test_phenomenological_smoke -v
```

Expected: pass.

- [ ] **Step 3: Run full experimental suite**

```bash
cd E:\BIG\新建文件夹\新建文件夹
python -m unittest ^
  character_mind.tests.experimental.test_toca_integration ^
  character_mind.tests.experimental.test_conscious_workspace ^
  character_mind.tests.experimental.test_inner_outer_divergence ^
  character_mind.tests.experimental.test_phenomenological_runtime ^
  character_mind.tests.experimental.test_world_feedback_loop ^
  character_mind.tests.experimental.test_experience_auditor ^
  character_mind.tests.experimental.test_phenomenological_smoke -v
```

Expected: pass.

---

## Acceptance Criteria

- The agent has a long-running runtime independent of individual `process_event()` calls.
- The agent maintains a private inner stream separate from external behavior.
- The system can represent “knows/feels/wants internally but does not say externally.”
- Expression policy records why and how inner state was masked, omitted, displaced, or directly expressed.
- World feedback from actions changes later inner experience.
- Idle ticks can produce spontaneous thought from unresolved conflict.
- NLA-inspired auditor verbalizes internal traces as hypotheses and detects divergence.
- Hermes-style consolidation can turn repeated inner/outer divergence into procedural memory rules.
- Existing TOCA tests continue passing.

---

## Self-Review Notes

- Spec coverage: This plan covers all post-plan discussion: OpenClaw-style daemon/tool-world presence, Hermes-style nudges, NLA-inspired internal-state audit, and the claim that internal model state can diverge from external output.
- Placeholder scan: No unresolved placeholders are intentionally left.
- Type consistency: New APIs are `InnerExperienceStream`, `ExpressionPolicy`, `PhenomenologicalRuntime`, `WorldAdapter`, and `ExperienceAuditor`.
- Scope check: This is a second-stage experimental runtime. It deliberately does not change `core/orchestrator.py` because the previous plan already established TOCA as the wrapper around the stable five-layer cognitive frame.
