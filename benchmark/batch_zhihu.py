"""Batch run all 24 Zhihu questions through the pipeline and collect responses."""
import asyncio, sys, json, os, re, html as html_mod, time
sys.path.insert(0, '.')

from benchmark.real_llm_benchmark import register_all_skills, load_provider
from character_mind import get_orchestrator
from character_mind.core import orchestrator as orch_mod
from character_mind.core.biological import BiologicalBridge

# Question IDs
IDS = [
    "2005071851332854891", "2032539697113723840", "2034965455148991362",
    "2035110064781009012", "2035004114074121016", "2034091170238812279",
    "2034553991615471818", "2031161952588842515", "2017407919415641570",
    "2002942063210152397", "2028850331992204268", "1946312769805746588",
    "2031500648240427545", "1973926654654034929", "2024016293058152365",
    "1999901210073923638", "2031694895572849594", "2033515106714263635",
    "2032882966494458289", "2027357417361384490", "2034176539441501986",
    "1979012803231780976", "2029670364574224709", "2033326255232263272",
]

TMPDIR = os.environ.get("TEMP", "/tmp")


def extract_question(qid: str) -> dict:
    """Extract question title and content from downloaded HTML."""
    fpath = os.path.join(TMPDIR, f"zhihu_{qid}.html")
    if not os.path.exists(fpath):
        return {"id": qid, "title": "FILE NOT FOUND", "content": ""}

    content = open(fpath, "r", encoding="utf-8", errors="replace").read()
    title_match = re.search(r"<title[^>]*>([^<]+)</title>", content)
    title = html_mod.unescape(title_match.group(1).strip()) if title_match else "NO TITLE"
    title = re.sub(r"\s*-\s*知乎\s*$", "", title)

    json_match = re.search(r'<script id="js-initialData" type="text/json">(.*?)</script>', content, re.DOTALL)
    detail = ""
    if json_match:
        try:
            data = json.loads(json_match.group(1))
            qdata = data.get("initialState", {}).get("entities", {}).get("questions", {})
            if qdata:
                for k, v in qdata.items():
                    d = v.get("detail", v.get("title", ""))
                    detail = re.sub(r"<[^>]+>", "", str(d))
                    break
        except:
            pass
    return {"id": qid, "title": title, "content": detail[:600]}


def build_character_state(q: dict) -> dict:
    """Build a default character state from question content."""
    # Infer basic OCEAN from question content
    text = q.get("content", "") + q.get("title", "")
    neuroticism = 0.7 if any(w in text for w in ["怎么办", "焦虑", "担心", "害怕", "难过", "痛苦"]) else 0.5
    agreeableness = 0.7 if any(w in text for w in ["对不起", "原谅", "妥协", "算了", "忍"]) else 0.5

    return {
        "name": f"提问者_{q['id'][-4:]}",
        "personality": {
            "openness": 0.5, "conscientiousness": 0.5, "extraversion": 0.4,
            "agreeableness": agreeableness, "neuroticism": neuroticism,
            "attachment_style": "anxious",
            "defense_style": ["合理化"],
            "cognitive_biases": ["灾难化"],
            "moral_stage": 3,
        },
        "trauma": {"ace_score": 1, "active_schemas": [], "trauma_triggers": []},
        "ideal_world": {},
        "motivation": {"current_goal": ""},
        "emotion_decay": {},
    }


async def run_one(provider, q: dict, idx: int):
    """Run one question through the pipeline."""
    cs = build_character_state(q)
    p = cs["personality"]

    bio = BiologicalBridge()
    bio.set_character_profile(
        ocean={"extraversion": p["extraversion"], "neuroticism": p["neuroticism"],
               "openness": p["openness"], "conscientiousness": p["conscientiousness"],
               "agreeableness": p["agreeableness"]},
        attachment=p["attachment_style"],
        ace=cs["trauma"]["ace_score"],
    )

    orch_mod._orchestrator = None
    o = get_orchestrator(anti_alignment_enabled=True, biological_bridge=bio)

    event = {
        "description": f"你在知乎上写下了这个问题：{q['title']}。你正在反思自己的处境。{q['content'][:200]}",
        "type": "reflective",
        "participants": [],
        "significance": 0.7,
        "tags": ["self_reflection", "zhihu"],
    }

    r = await o.process_event(provider, cs, event)
    resp = ""
    for sr in r.layer_results.get(5, []):
        if sr.skill_name == "response_generator" and sr.success:
            resp = sr.output.get("response_text", "")
            break
    return {"id": q["id"], "title": q["title"], "response": resp, "tokens": r.total_tokens}


async def main():
    provider = load_provider("deepseek", thinking=True)
    register_all_skills()

    print(f"Running {len(IDS)} Zhihu questions...")
    results = []

    for i, qid in enumerate(IDS):
        q = extract_question(qid)
        print(f"[{i+1}/{len(IDS)}] {q['title'][:50]}...", end=" ", flush=True)
        start = time.perf_counter()
        result = await run_one(provider, q, i)
        elapsed = time.perf_counter() - start
        print(f"{elapsed:.0f}s, {result['tokens']}tok, resp={len(result['response'])}chars")
        results.append(result)

    # Save results
    outpath = "docs/zhihu_responses.json"
    with open(outpath, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nSaved {len(results)} responses to {outpath}")


if __name__ == "__main__":
    asyncio.run(main())
