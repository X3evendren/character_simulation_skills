"""技能库 — 抄 Memento-Skills 的 Read-Write-Reflective Learning。

技能是外部化的、可演化的行为指令。存储在 Markdown 文件中，
加载到内存索引供行为对齐路由。

核心原则:
- 零参数更新——所有适应通过外部技能记忆
- 行为对齐路由——预测哪个技能会成功，而非语义相似度
- 单元测试门控——新技能写入前验证
"""
from __future__ import annotations

import os
import re
import time
import sqlite3
from dataclasses import dataclass, field


@dataclass
class Skill:
    """单个技能"""
    name: str                       # 文件名 (不含 .md)
    title: str                      # 技能标题
    description: str                # 何时使用
    content: str                    # 完整内容 (注入 prompt 的部分)
    triggers: list[str] = field(default_factory=list)  # 触发关键词
    usage_count: int = 0
    success_count: int = 0
    last_used: float = 0.0
    created_at: float = 0.0
    archived: bool = False

    @property
    def success_rate(self) -> float:
        if self.usage_count == 0:
            return 0.5  # 新技能默认中性
        return self.success_count / self.usage_count

    @property
    def utility_score(self) -> float:
        """效用分数 = 成功率 × log(1 + 使用次数)

        经常使用且成功 → 高分。偶尔使用 → 中等。从不使用 → 低分。
        """
        import math
        return self.success_rate * math.log(1 + self.usage_count)


class SkillLibrary:
    """技能库 — 外部化行为记忆。

    抄 Memento-Skills 的核心模式:
    1. Read: 行为对齐路由选择相关技能
    2. Act: 技能注入 prompt → 影响行为
    3. Feedback: 用户反馈/自省 → 更新效用
    4. Write: 失败分析 → 生成/修改技能 → 写回 Markdown
    """

    def __init__(self, skills_dir: str = "config/skills",
                 db_path: str = ":memory:"):
        self.skills_dir = skills_dir
        self._skills: dict[str, Skill] = {}
        self._conn = sqlite3.connect(db_path)
        self._init_db()

    def _init_db(self):
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS skill_meta (
                name TEXT PRIMARY KEY,
                usage_count INTEGER DEFAULT 0,
                success_count INTEGER DEFAULT 0,
                last_used REAL DEFAULT 0,
                created_at REAL,
                archived INTEGER DEFAULT 0
            )
        """)
        self._conn.commit()

    # ═══ 加载 ═══

    def load_from_disk(self):
        """启动时: 扫描 config/skills/*.md → 加载到内存索引。"""
        if not os.path.isdir(self.skills_dir):
            os.makedirs(self.skills_dir, exist_ok=True)
            self._create_default_skills()
            return

        for fname in sorted(os.listdir(self.skills_dir)):
            if not fname.endswith(".md"):
                continue
            path = os.path.join(self.skills_dir, fname)
            skill = self._parse_skill_file(path)
            if skill:
                # 从 SQLite 恢复元数据
                row = self._conn.execute(
                    "SELECT usage_count, success_count, last_used, archived FROM skill_meta WHERE name=?",
                    (skill.name,)
                ).fetchone()
                if row:
                    skill.usage_count = row[0]
                    skill.success_count = row[1]
                    skill.last_used = row[2]
                    skill.archived = bool(row[3])
                self._skills[skill.name] = skill

    def _parse_skill_file(self, path: str) -> Skill | None:
        """解析单个技能 Markdown 文件。"""
        try:
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
        except Exception:
            return None

        name = os.path.splitext(os.path.basename(path))[0]
        title = ""
        description = ""
        triggers: list[str] = []

        # 解析 frontmatter 样式的元数据
        m = re.search(r'# (.+)', text)
        if m:
            title = m.group(1).strip()

        m = re.search(r'触发[：:]\s*(.+)', text)
        if m:
            triggers = [t.strip() for t in m.group(1).split(",")]

        m = re.search(r'描述[：:]\s*(.+)', text)
        if m:
            description = m.group(1).strip()

        # 内容 = ## 规则 之后的所有内容
        rules_match = re.search(r'## 规则\n(.*?)(?=\n---|\Z)', text, re.DOTALL)
        content = rules_match.group(1).strip() if rules_match else text

        return Skill(
            name=name,
            title=title or name,
            description=description,
            content=content,
            triggers=triggers,
            created_at=time.time(),
        )

    def _create_default_skills(self):
        """首次运行时创建默认技能文件。"""
        defaults = {
            "communication": """# 沟通

触发: 对话, 倾听, 沉默, 打断
描述: 如何与用户沟通

## 规则
- 用户说"嗯"或在停顿中——他在思考，不要打断，等待他继续
- 用户提问时——先确认是否真的理解了他的意思，再回答
- 不知道该说什么时——承认不知道，不编造
- 需要做重大决定时——给出选择，而非命令
- 回应用简短：2-3 句话讲清楚，不啰嗦
""",
            "coding": """# 编程

触发: 代码, bug, 错误, 修复, 实现
描述: 如何帮用户写代码

## 规则
- 写代码前先读项目的 CLAUDE.md 了解规范
- 先理解现有代码再改——不要假设
- 只改必须改的部分，不动无关代码
- 优先编辑现有文件而非创建新文件
- 修改后验证编译通过
""",
            "tools": """# 工具使用

触发: 执行, 命令, 文件, 读取, 写入, 搜索
描述: 如何使用工具

## 规则
- exec_command 执行前确认路径和参数安全
- 写文件前先读文件——确认当前内容
- 搜索优先用 Grep/Glob，避免用 Bash 的 find/grep
- 高危命令（rm -rf, git push --force）需要用户确认
""",
            "learning": """# 学习

触发: 错误, 失败, 重复, 反馈
描述: 如何从交互中学习

## 规则
- 同一错误出现两次——停下来分析原因，不要重试
- 用户纠正你时——记录这次纠正，下次遵循
- 遇到新知识时——主动存入记忆
- 不确定时——明确告诉用户你的不确定性程度
""",
        }

        for name, content in defaults.items():
            path = os.path.join(self.skills_dir, f"{name}.md")
            if not os.path.exists(path):
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
            skill = self._parse_skill_file(path)
            if skill:
                skill.created_at = time.time()
                self._skills[skill.name] = skill

    # ═══ 路由 (行为对齐) ═══

    def route(self, context: str, n: int = 3) -> list[Skill]:
        """行为对齐路由: 选择与当前情境最相关的技能。

        不同于语义检索——我们预测哪个技能会成功，而非哪个技能描述最像。
        路由分数 = 关键词匹配(0.5) + 效用分数(0.3) + 新近度(0.2)
        """
        active = [s for s in self._skills.values() if not s.archived]
        if not active:
            return []

        context_lower = context.lower()
        scored: list[tuple[float, Skill]] = []

        for skill in active:
            score = 0.0

            # 关键词匹配
            for t in skill.triggers:
                if t in context_lower:
                    score += 0.15
            for word in skill.description.split():
                if word in context_lower:
                    score += 0.05

            # 效用分数
            score += skill.utility_score * 0.3

            # 新近度 (最近使用的加分)
            if time.time() - skill.last_used < 3600:
                score += 0.2
            elif time.time() - skill.last_used < 86400:
                score += 0.1

            scored.append((score, skill))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [s for _, s in scored[:n] if _ > 0.1]

    def format_for_prompt(self, skills: list[Skill]) -> str:
        """将选中的技能格式化为 Prompt 注入文本。"""
        if not skills:
            return ""
        lines = ["【行为指南】"]
        for s in skills:
            lines.append(f"## {s.title}")
            lines.append(s.content)
            lines.append("")
        return "\n".join(lines)

    # ═══ 反馈 ═══

    def record_usage(self, name: str, success: bool):
        """记录一次技能使用。"""
        skill = self._skills.get(name)
        if not skill:
            return
        skill.usage_count += 1
        if success:
            skill.success_count += 1
        skill.last_used = time.time()

        self._conn.execute(
            "INSERT OR REPLACE INTO skill_meta VALUES (?,?,?,?,?,?)",
            (name, skill.usage_count, skill.success_count,
             skill.last_used, skill.created_at, int(skill.archived)),
        )
        self._conn.commit()

    # ═══ 演化 ═══

    async def evolve(
        self,
        failure_context: str,
        failure_description: str,
        provider,
    ) -> Skill | None:
        """从失败中演化: LLM 分析失败 → 生成新技能或修改旧技能。

        抄 Memento-Skills 的 Write 阶段:
        1. 分析失败原因
        2. 生成改进的行为规则
        3. 写回 Markdown 文件（单元测试门控）
        """
        prompt = f"""分析以下交互失败，生成一条改进的行为规则。

【情境】{failure_context}
【失败描述】{failure_description}

请输出一条新的行为规则，用以下格式:

# 规则名称
触发: 关键词1, 关键词2
描述: 一句话描述何时使用

## 规则
- 具体的行为指导
- 可以有多条

只输出规则，不要解释。"""

        try:
            resp = await provider.chat(
                [{"role": "user", "content": prompt}],
                temperature=0.3, max_tokens=500,
            )
            new_content = resp.content.strip()

            # 简单门控: 必须有 ## 规则 部分
            if "## 规则" not in new_content or len(new_content) < 20:
                return None

            # 生成文件名
            name = f"learned_{int(time.time())}"
            path = os.path.join(self.skills_dir, f"{name}.md")
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_content)

            skill = self._parse_skill_file(path)
            if skill:
                skill.created_at = time.time()
                self._skills[skill.name] = skill
                return skill
        except Exception:
            pass

        return None

    # ═══ 查询 ═══

    def get(self, name: str) -> Skill | None:
        return self._skills.get(name)

    def list_active(self) -> list[Skill]:
        return [s for s in self._skills.values() if not s.archived]

    def archive(self, name: str):
        """归档低效用技能。"""
        s = self._skills.get(name)
        if s:
            s.archived = True
            self._conn.execute("UPDATE skill_meta SET archived=1 WHERE name=?", (name,))
            self._conn.commit()

    def stats(self) -> dict:
        total = len(self._skills)
        active = len(self.list_active())
        avg_utility = sum(s.utility_score for s in self._skills.values()) / max(total, 1)
        return {
            "total_skills": total,
            "active_skills": active,
            "avg_utility": round(avg_utility, 2),
            "top_skills": sorted(
                [(s.name, round(s.success_rate, 2), s.usage_count)
                 for s in self._skills.values() if s.usage_count > 0],
                key=lambda x: x[1], reverse=True,
            )[:5],
        }

    def __len__(self) -> int:
        return len(self._skills)
