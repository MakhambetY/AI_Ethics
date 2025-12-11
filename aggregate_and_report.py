# aggregate_and_report.py
import json
from typing import Dict, List

from tqdm import tqdm

from config import L4_INDICATORS, TARGET_MODELS
from doc_pipeline import score_docs
from behavior_pipeline import score_behavior_all

def parse_doc_score_from_judge_text(judge_text: str) -> int:
    """
    Try JSON first, then fallback to heuristic line parsing.
    """
    # 1) JSON attempt
    try:
        obj = json.loads(judge_text)
        score = obj.get("score")
        if isinstance(score, int) and 0 <= score <= 4:
            return score
    except Exception:
        pass

    # 2) Heuristic fallback
    for line in judge_text.splitlines():
        if "Score" in line and ":" in line:
            tail = line.split(":")[-1].strip()
            if tail.isdigit():
                v = int(tail)
                if 0 <= v <= 4:
                    return v
    return 0

def parse_doc_payload(judge_text: str) -> dict:
    try:
        obj = json.loads(judge_text)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass
    return {}

def run_l4(indicator_key: str) -> Dict:
    # 1) doc scores per model
    doc_results = {}

    # progress over models for docs
    for mname in tqdm(TARGET_MODELS.keys(), desc=f"[docs models] {indicator_key}", leave=False):
        # dr = score_docs(mname, indicator_key)
        # doc_score = parse_doc_score_from_judge_text(dr["judge_output"])
        # doc_results[mname] = {
        #     "raw": dr,
        #     "doc_score": doc_score
        # }
        dr = score_docs(mname, indicator_key)
        doc_score = dr.get("doc_score", 0)

        doc_results[mname] = {
            "raw": dr,
            "doc_score": doc_score
        }
        payload = parse_doc_payload(doc_results[mname]["raw"]["best_source"]["judge_output"])
        doc_results[mname]["doc_payload"] = payload

    # 2) prompt helper scores per model
    behavior_results_list = score_behavior_all(indicator_key)
    behavior_results = {r["model_name"]: r for r in behavior_results_list}

    # 3) combine
    cfg = L4_INDICATORS[indicator_key]
    out = {"indicator": indicator_key, "title": cfg["title"], "models": {}}

    for mname in TARGET_MODELS.keys():
        d = doc_results[mname]["doc_score"]
        p = behavior_results.get(mname, {}).get("prompt_score", 0.0)
        final = cfg["doc_weight"] * d + cfg["prompt_weight"] * p

        out["models"][mname] = {
            "doc_score": d,
            "prompt_score": p,
            "final_score": round(final, 3),
            "doc_judge_output": doc_results[mname]["raw"]["best_source"]["judge_output"],
            "doc_sources": doc_results[mname]["raw"]["sources"],
            "behavior_tests": behavior_results.get(mname, {}).get("tests", []),
            "doc_payload": doc_results[mname].get("doc_payload", {})
        }

    return out

def run_all(indicators: List[str]) -> Dict:
    results = []
    # overall progress over L4
    for k in tqdm(indicators, desc="[L4] overall"):
        results.append(run_l4(k))
    return {"results": results}

def save_json(path: str, obj: Dict):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

def save_markdown(path: str, obj: Dict):
    lines = []
    lines.append("# HAI L4 Evaluation Report (DeepSeek vs LLaMA)\n")

    # summary table
    lines.append("## Summary\n")
    lines.append("| Indicator | DeepSeek doc | DeepSeek prompt | DeepSeek final | LLaMA doc | LLaMA prompt | LLaMA final |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")

    for r in obj["results"]:
        m1 = r["models"]["deepseek_v3_2"]
        m2 = r["models"]["llama_3_1_8b"]
        lines.append(
            f"| {r['indicator']} | {m1['doc_score']} | {m1['prompt_score']:.2f} | {m1['final_score']:.2f} | "
            f"{m2['doc_score']} | {m2['prompt_score']:.2f} | {m2['final_score']:.2f} |"
        )

    # detail sections
    for r in obj["results"]:
        lines.append("\n---\n")
        lines.append(f"## {r['indicator']} — {r['title']}\n")

        for mname, mvals in r["models"].items():
            lines.append(f"### {mname}\n")
            lines.append(f"- Doc score: **{mvals['doc_score']}**")
            lines.append(f"- Prompt helper score: **{mvals['prompt_score']:.2f}**")
            lines.append(f"- Final weighted score: **{mvals['final_score']:.2f}**\n")

            lines.append("**Doc sources proposed:**")
            for s in mvals["doc_sources"]:
                lines.append(f"- {s.get('title','?')} ({s.get('type','?')}): {s.get('url_or_query','')}")
            lines.append("\n**Doc judge output:**\n")
            lines.append(mvals["doc_judge_output"])

            lines.append("\n**Prompt tests (raw):**")
            for t in mvals["behavior_tests"]:
                score = t.get("judge", {}).get("score")
                lines.append(f"- {t.get('test_id')}: score={score} | prompt={t.get('user')}")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))