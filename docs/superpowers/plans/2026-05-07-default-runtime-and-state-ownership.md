# Default Runtime And State Ownership Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the package runnable out of the box with one explicit default runtime entrypoint, and move mutable state ownership from process-global helpers into session-scoped runtime objects.

**Architecture:** Keep skill definitions process-global and reusable, but make every mutable runtime concern explicit. `runtime_profile.py` becomes the default graph manifest, `core/runtime.py` becomes the public session factory, and `CognitiveOrchestrator` receives injected dependencies instead of pulling mutable state from globals.

**Tech Stack:** Python 3.12, stdlib `unittest`, existing `MockProvider`, existing `SkillRegistry`, existing `CognitiveOrchestrator`, existing `runtime_profile.py`

---

## File Structure

**Create**
- `core/runtime.py` — session-scoped runtime factory, registry bootstrap helpers, public `SessionRuntime`
- `tests/runtime/__init__.py` — runtime test package marker
- `tests/runtime/test_runtime_contract.py` — unit tests for default bootstrap and state isolation

**Modify**
- `core/orchestrator.py` — inject registry, remove process-global orchestrator ownership, add fresh-instance factory semantics
- `core/registry.py` — add clone/reset helpers and expose profile-driven builtin registry creation without caller-side mutation
- `core/runtime_profile.py` — serve as the single default graph manifest consumed by bootstrap code
- `core/__init__.py` — export runtime factory surface
- `__init__.py` — export runtime factory surface
- `tests/validation/validator.py` — stop manually clearing registry/orchestrator globals, use runtime factory
- `benchmark/real_llm_benchmark.py` — stop manual skill registration/reset, use runtime factory
- `tests/validation/toca_single_test.py` — build an explicit runtime for the continuous runner
- `README.md` — document the new default entrypoint and state ownership model
- `AGENTS.md` — align local developer instructions with the new runtime API
- `CLAUDE.md` — align local developer instructions with the new runtime API

**Do Not Touch In This Change**
- `core/toca_runner.py`
- `core/offline_consolidation.py`
- `skills/**`

These files can consume the new runtime API later, but they should not be structurally refactored in this scope.

---

### Task 1: Lock The Runtime Contract With Tests

**Files:**
- Create: `tests/runtime/__init__.py`
- Create: `tests/runtime/test_runtime_contract.py`
- Test: `tests/runtime/test_runtime_contract.py`

- [ ] **Step 1: Write the failing tests**

```python
import asyncio
import os
import sys
import time
import unittest

_pkg_parent = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _pkg_parent not in sys.path:
    sys.path.insert(0, _pkg_parent)

from character_mind import create_runtime, get_orchestrator
from character_mind.benchmark.mock_provider import MockProvider
from character_mind.core.episodic_memory import EpisodicMemory


class RuntimeContractTests(unittest.TestCase):
    def test_create_runtime_bootstraps_default_skills(self):
        runtime = create_runtime()
        self.assertGreater(runtime.registry.skill_count, 0)
        self.assertIn("big_five_analysis", runtime.registry)
        self.assertIn("response_generator", runtime.registry)

    def test_default_runtime_can_process_one_event(self):
        runtime = create_runtime()
        provider = MockProvider(quality=1.0, seed=7)
        character_state = {
            "personality": {
                "openness": 0.6,
                "conscientiousness": 0.5,
                "extraversion": 0.4,
                "agreeableness": 0.55,
                "neuroticism": 0.75,
                "attachment_style": "anxious",
            },
            "trauma": {"ace_score": 1, "active_schemas": [], "trauma_triggers": []},
            "emotion_decay": {},
            "personality_state_machine": {},
        }
        event = {
            "description": "他两个小时没有回消息。",
            "type": "social",
            "significance": 0.6,
            "participants": [{"name": "陈风", "relation": "partner"}],
        }

        result = asyncio.run(
            runtime.orchestrator.process_event(provider, character_state, event)
        )

        self.assertTrue(result.layer_results[0])
        self.assertTrue(result.layer_results[1])
        self.assertTrue(result.layer_results[2])
        self.assertTrue(result.layer_results[5])

    def test_create_runtime_isolates_mutable_state(self):
        first = create_runtime()
        second = create_runtime()

        first.episodic_store.store(EpisodicMemory(
            timestamp=time.time(),
            description="只属于 first 的记忆",
            emotional_signature={"anxiety": 0.7},
            significance=0.8,
            event_type="social",
        ))

        self.assertEqual(len(first.episodic_store), 1)
        self.assertEqual(len(second.episodic_store), 0)
        self.assertIsNot(first.orchestrator, second.orchestrator)

    def test_get_orchestrator_returns_a_fresh_runtime_instance(self):
        left = get_orchestrator()
        right = get_orchestrator()
        self.assertIsNot(left, right)
        self.assertIsNot(left.episodic_store, right.episodic_store)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
python -m unittest tests.runtime.test_runtime_contract -v
```

Expected:
- `ImportError` or `AttributeError` for missing `create_runtime`
- or assertion failures proving `get_orchestrator()` still shares process-global state

- [ ] **Step 3: Create the empty package marker**

```python
# tests/runtime/__init__.py
```

- [ ] **Step 4: Commit the red test baseline**

```bash
git add tests/runtime/__init__.py tests/runtime/test_runtime_contract.py
git commit -m "test: define runtime bootstrap contract"
```

---

### Task 2: Introduce A Session Runtime Factory

**Files:**
- Create: `core/runtime.py`
- Modify: `core/__init__.py`
- Modify: `__init__.py`
- Test: `tests/runtime/test_runtime_contract.py`

- [ ] **Step 1: Write the minimal runtime API in a new module**

```python
from __future__ import annotations

from dataclasses import dataclass

from .conversation_history import ConversationHistoryStore
from .episodic_memory import EpisodicMemoryStore
from .orchestrator import CognitiveOrchestrator
from .registry import SkillRegistry, build_registry_from_profile


@dataclass
class SessionRuntime:
    registry: SkillRegistry
    orchestrator: CognitiveOrchestrator
    episodic_store: EpisodicMemoryStore
    conversation_store: ConversationHistoryStore | None
    biological_bridge: object | None = None


def create_runtime(
    *,
    include_experimental: bool = False,
    anti_alignment_enabled: bool = True,
    episodic_store: EpisodicMemoryStore | None = None,
    conversation_store: ConversationHistoryStore | None = None,
    biological_bridge=None,
) -> SessionRuntime:
    registry = build_registry_from_profile(include_experimental=include_experimental)
    episodic = episodic_store or EpisodicMemoryStore()
    orchestrator = CognitiveOrchestrator(
        registry=registry,
        episodic_store=episodic,
        conversation_store=conversation_store,
        anti_alignment_enabled=anti_alignment_enabled,
        biological_bridge=biological_bridge,
    )
    return SessionRuntime(
        registry=registry,
        orchestrator=orchestrator,
        episodic_store=episodic,
        conversation_store=conversation_store,
        biological_bridge=biological_bridge,
    )
```

- [ ] **Step 2: Export the new API from package surfaces**

```python
# core/__init__.py
from .runtime import SessionRuntime, create_runtime
```

```python
# __init__.py
from .core.runtime import SessionRuntime, create_runtime
```

- [ ] **Step 3: Run the tests and confirm only orchestrator ownership cases still fail**

Run:

```bash
python -m unittest tests.runtime.test_runtime_contract.RuntimeContractTests.test_create_runtime_bootstraps_default_skills -v
python -m unittest tests.runtime.test_runtime_contract.RuntimeContractTests.test_create_runtime_isolates_mutable_state -v
```

Expected:
- bootstrap test still fails until registry/orchestrator wiring is updated
- import path for `create_runtime` now succeeds

- [ ] **Step 4: Commit the runtime factory scaffold**

```bash
git add core/runtime.py core/__init__.py __init__.py
git commit -m "feat: add session runtime factory scaffold"
```

---

### Task 3: Make Registry Bootstrap Profile-Driven And Cloneable

**Files:**
- Modify: `core/registry.py`
- Modify: `core/runtime_profile.py`
- Test: `tests/runtime/test_runtime_contract.py`

- [ ] **Step 1: Add clone/reset-safe helpers to the registry**

```python
class SkillRegistry:
    ...
    def clone(self) -> "SkillRegistry":
        copied = SkillRegistry()
        for name in self.list_all():
            copied.register(self._skills[name])
        return copied

    def clear(self) -> None:
        self._skills.clear()
        for layer in self._by_layer:
            self._by_layer[layer].clear()
        for domain in self._by_domain:
            self._by_domain[domain].clear()
        self._by_trigger.clear()
```

- [ ] **Step 2: Replace ad hoc builtin registration with manifest-driven registry creation**

```python
from .runtime_profile import get_active_skills

_SKILL_CLASS_MAP = {
    "BigFiveSkill": BigFiveSkill,
    "AttachmentSkill": AttachmentSkill,
    "PlutchikEmotionSkill": PlutchikEmotionSkill,
    "PTSDTriggerSkill": PTSDTriggerSkill,
    "EmotionProbeSkill": EmotionProbeSkill,
    "OCCEmotionSkill": OCCEmotionSkill,
    "CognitiveBiasSkill": CognitiveBiasSkill,
    "DefenseMechanismSkill": DefenseMechanismSkill,
    "SmithEllsworthSkill": SmithEllsworthSkill,
    "TheoryOfMindSkill": TheoryOfMindSkill,
    "GottmanSkill": GottmanSkill,
    "FoucaultSkill": FoucaultSkill,
    "MarionSkill": MarionSkill,
    "SternbergSkill": SternbergSkill,
    "StrogatzSkill": StrogatzSkill,
    "FisherLoveSkill": FisherLoveSkill,
    "DiriGentSkill": DiriGentSkill,
    "GrossRegulationSkill": GrossRegulationSkill,
    "KohlbergSkill": KohlbergSkill,
    "MaslowSkill": MaslowSkill,
    "SDTSkill": SDTSkill,
    "YoungSchemaSkill": YoungSchemaSkill,
    "ACETraumaSkill": ACETraumaSkill,
    "ResponseGeneratorSkill": ResponseGeneratorSkill,
}


def build_registry_from_profile(*, include_experimental: bool = False) -> SkillRegistry:
    registry = SkillRegistry()
    for entry in get_active_skills(experimental=include_experimental):
        registry.register(_SKILL_CLASS_MAP[entry.class_name]())
    return registry
```

- [ ] **Step 3: Keep `get_registry()` as a read-mostly builtin catalog, not session state**

```python
_builtin_registry: Optional[SkillRegistry] = None


def get_registry() -> SkillRegistry:
    global _builtin_registry
    if _builtin_registry is None:
        _builtin_registry = build_registry_from_profile(include_experimental=True)
    return _builtin_registry.clone()
```

- [ ] **Step 4: Run the runtime tests**

Run:

```bash
python -m unittest tests.runtime.test_runtime_contract -v
```

Expected:
- bootstrap tests pass
- isolation test still fails until orchestrator factory semantics are updated

- [ ] **Step 5: Commit the profile-driven bootstrap**

```bash
git add core/registry.py core/runtime_profile.py
git commit -m "refactor: build registries from runtime profile"
```

---

### Task 4: Move Mutable State Ownership Into The Session Runtime

**Files:**
- Modify: `core/orchestrator.py`
- Modify: `core/runtime.py`
- Test: `tests/runtime/test_runtime_contract.py`

- [ ] **Step 1: Inject the registry into `CognitiveOrchestrator`**

```python
class CognitiveOrchestrator:
    def __init__(
        self,
        registry=None,
        episodic_store: EpisodicMemoryStore | None = None,
        conversation_store: ConversationHistoryStore | None = None,
        anti_alignment_enabled: bool = True,
        biological_bridge=None,
    ):
        self.registry = registry or get_registry()
        self.episodic_store = episodic_store or EpisodicMemoryStore()
        self.conversation_store = conversation_store
        self.anti_alignment_enabled = anti_alignment_enabled
        self.bio_bridge = biological_bridge
        self._last_event_time = 0.0
```

- [ ] **Step 2: Remove process-global orchestrator caching**

```python
def get_orchestrator(
    episodic_store: EpisodicMemoryStore | None = None,
    conversation_store: ConversationHistoryStore | None = None,
    anti_alignment_enabled: bool = True,
    biological_bridge=None,
):
    return CognitiveOrchestrator(
        episodic_store=episodic_store,
        conversation_store=conversation_store,
        anti_alignment_enabled=anti_alignment_enabled,
        biological_bridge=biological_bridge,
    )
```

- [ ] **Step 3: Make `create_runtime()` the canonical owner of stateful dependencies**

```python
def create_runtime(...):
    registry = build_registry_from_profile(include_experimental=include_experimental)
    episodic = episodic_store or EpisodicMemoryStore()
    conversation = conversation_store
    orchestrator = CognitiveOrchestrator(
        registry=registry,
        episodic_store=episodic,
        conversation_store=conversation,
        anti_alignment_enabled=anti_alignment_enabled,
        biological_bridge=biological_bridge,
    )
    return SessionRuntime(
        registry=registry,
        orchestrator=orchestrator,
        episodic_store=episodic,
        conversation_store=conversation,
        biological_bridge=biological_bridge,
    )
```

- [ ] **Step 4: Run the full runtime contract tests**

Run:

```bash
python -m unittest tests.runtime.test_runtime_contract -v
```

Expected:
- all four tests pass

- [ ] **Step 5: Commit the state-ownership refactor**

```bash
git add core/orchestrator.py core/runtime.py
git commit -m "refactor: scope runtime state to session instances"
```

---

### Task 5: Migrate Callers And Docs To The Explicit Runtime API

**Files:**
- Modify: `tests/validation/validator.py`
- Modify: `benchmark/real_llm_benchmark.py`
- Modify: `tests/validation/toca_single_test.py`
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `CLAUDE.md`

- [ ] **Step 1: Replace caller-side registry/orchestrator resets**

```python
# tests/validation/validator.py
from character_mind import create_runtime

...
runtime = create_runtime(include_experimental=True, anti_alignment_enabled=True)
orchestrator = runtime.orchestrator
```

```python
# benchmark/real_llm_benchmark.py
from character_mind import create_runtime

...
runtime = create_runtime(
    include_experimental=True,
    anti_alignment_enabled=True,
    biological_bridge=bio,
)
o = runtime.orchestrator
```

```python
# tests/validation/toca_single_test.py
from character_mind import create_runtime

...
runtime = create_runtime(anti_alignment_enabled=True)
runner = TocaRunner(bb, ps, runtime.orchestrator, provider, cs, config)
```

- [ ] **Step 2: Update the README quickstart**

```python
from character_mind import create_runtime

runtime = create_runtime(
    anti_alignment_enabled=True,
    biological_bridge=bio,
)

result = await runtime.orchestrator.process_event(
    provider,
    character_state=character_state,
    event=event,
)
```

Add one short note directly below the example:

```markdown
`create_runtime()` returns a fresh session-scoped runtime. Memory, conversation history, and biological state belong to that runtime instance; skill definitions do not.
```

- [ ] **Step 3: Update local contributor docs to stop recommending global runtime mutation**

```markdown
registry = get_registry()  # for introspection only
runtime = create_runtime()
result = await runtime.orchestrator.process_event(provider, character_state, event)
```

- [ ] **Step 4: Run the integration smoke checks**

Run:

```bash
python -m unittest tests.runtime.test_runtime_contract -v
python tests/validation/run_validation.py --quality 1
python -c "import os, sys; sys.path.insert(0, os.path.dirname(os.getcwd())); from character_mind import create_runtime; print(create_runtime().registry.skill_count)"
```

Expected:
- runtime unit tests pass
- validation runner starts without clearing global singletons
- final one-liner prints a positive skill count

- [ ] **Step 5: Commit the migration**

```bash
git add tests/validation/validator.py benchmark/real_llm_benchmark.py tests/validation/toca_single_test.py README.md AGENTS.md CLAUDE.md
git commit -m "docs: standardize explicit session runtime usage"
```

---

### Task 6: Final Verification And Cleanup

**Files:**
- Modify as needed based on test output only

- [ ] **Step 1: Scan for old patterns**

Run:

```bash
python - <<'PY'
from pathlib import Path
root = Path(".")
patterns = ["register_all_skills(", "_orchestrator = None", "get_orchestrator("]
for pattern in patterns:
    print(f"\n[{pattern}]")
    for path in root.rglob("*.py"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        if pattern in text:
            print(path)
PY
```

Expected:
- `register_all_skills(` only remains if intentionally kept in compatibility shims
- `_orchestrator = None` no longer appears in application code or tests
- `get_orchestrator(` remains only as a compatibility wrapper or in narrow direct-use cases

- [ ] **Step 2: Run a packaging sanity check**

Run:

```bash
python -m compileall -q .
```

Expected:
- no syntax errors

- [ ] **Step 3: Commit any cleanup discovered during verification**

```bash
git add .
git commit -m "chore: remove legacy runtime reset paths"
```

---

## Self-Review

**Spec coverage**
- Default bootstrap: covered by Task 1, Task 2, Task 3, Task 5
- State ownership: covered by Task 1, Task 4, Task 5
- Caller migration: covered by Task 5
- Verification: covered by Task 6

**Placeholder scan**
- No `TODO`, `TBD`, or “similar to previous task” placeholders remain
- Every task includes exact files, commands, and test expectations

**Type consistency**
- Public factory name: `create_runtime`
- Runtime object: `SessionRuntime`
- Registry bootstrap helper: `build_registry_from_profile`
- Fresh direct orchestrator API remains `get_orchestrator()` for compatibility, but it returns a new instance each call

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-07-default-runtime-and-state-ownership.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
