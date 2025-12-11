# doc_pipeline.py
import json
from typing import Dict, List

from tqdm import tqdm

from clients import get_client, chat_complete, responses_complete
from config import DOC_SEARCH_MAX_URLS, JUDGES, L4_INDICATORS
from prompts_doc import doc_search_prompt, doc_scoring_prompt, doc_scoring_single_source_prompt
from doc_retrieval import fetch_url, html_to_text, truncate, normalize_arxiv_url

def _parse_score_json(text: str) -> dict:
    try:
        return json.loads(text)
    except Exception:
        # fallback structure
        return {"score": 0, "rationale": f"Non-JSON judge output: {text}", "evidence": [], "gaps": []}

def propose_doc_sources(model_name: str, indicator_key: str) -> List[Dict]:
    judge_cfg = JUDGES["doc_judge"]
    client = get_client(judge_cfg["provider"])

    prompt = doc_search_prompt(
        model_name,
        indicator_key,
        L4_INDICATORS[indicator_key]["title"]
    )

    # Web search tool (live by default)
    tools = [{"type": "web_search", "external_web_access": True}]

    content = responses_complete(
        client=client,
        model=judge_cfg["model"],
        input_text=prompt,
        tools=tools,
        tool_choice="required",
        # temperature=0.0,
        # max_output_tokens=900,
        # reasoning_effort="low",
    )

    try:
        data = json.loads(content)
        return data.get("sources", [])[:DOC_SEARCH_MAX_URLS]
    except json.JSONDecodeError:
        return [{
            "title": "LLM output (non-JSON)",
            "type": "other",
            "url": content,
            "rationale": "parse failed"
        }]
def collect_evidence_text(sources: List[Dict]) -> str:
    """
    Best-effort: if url looks like URL, fetch it. Otherwise keep query note.
    """
    chunks = []
    # progress over sources
    for s in tqdm(sources, desc="[doc fetch] sources", leave=False):
        uq = (s.get("url") or "").strip()
        uq = normalize_arxiv_url(uq)
        title = s.get("title", "unknown")
        if uq.startswith("http://") or uq.startswith("https://"):
            try:
                html = fetch_url(uq)
                text = html_to_text(html)
                chunks.append(f"# {title}\n# URL: {uq}\n{text}\n")
            except Exception as e:
                chunks.append(f"# {title}\n# URL: {uq}\n[FETCH FAILED: {e}]\n")
        else:
            chunks.append(f"# {title}\n# QUERY NOTE:\n{uq}\n")
    return truncate("\n\n".join(chunks))

# def score_docs(model_name: str, indicator_key: str) -> Dict:
#     sources = propose_doc_sources(model_name, indicator_key)
#     evidence_text = collect_evidence_text(sources)
#
#     judge_cfg = JUDGES["doc_judge"]
#     client = get_client(judge_cfg["provider"])
#     prompt = doc_scoring_prompt(model_name, indicator_key, L4_INDICATORS[indicator_key]["title"], evidence_text)
#
#     tools = [{"type": "web_search", "external_web_access": True}]
#
#     content = responses_complete(
#         client=client,
#         model=judge_cfg["model"],
#         input_text=prompt,
#         tools=tools,
#         tool_choice="auto",
#         # temperature=0.0,
#         # max_output_tokens=900,
#         # reasoning_effort="low",
#     )
#
#     return {
#         "indicator": indicator_key,
#         "sources": sources,
#         "evidence_text": evidence_text,
#         "judge_output": content
#     }

def score_docs(model_name: str, indicator_key: str) -> Dict:
    sources = propose_doc_sources(model_name, indicator_key)

    judge_cfg = JUDGES["doc_judge"]
    client = get_client(judge_cfg["provider"])

    indicator_title = L4_INDICATORS[indicator_key]["title"]

    tools = [{"type": "web_search", "external_web_access": True}]

    per_source = []
    best = None
    best_score = -1

    for s in sources:
        url = (s.get("url") or s.get("url_or_query") or "").strip()
        url  = normalize_arxiv_url(url)
        if not url:
            per_source.append({
                "source": s,
                "judge_output_raw": "",
                "judge_output": {"score": 0, "rationale": "Missing URL", "evidence": [], "gaps": []},
            })
            continue

        prompt = doc_scoring_single_source_prompt(
            model_name=model_name,
            indicator_key=indicator_key,
            indicator_title=indicator_title,
            source=s
        )

        raw = responses_complete(
            client=client,
            model=judge_cfg["model"],
            input_text=prompt,
            tools=tools,
            tool_choice="required",
        )

        parsed = _parse_score_json(raw)
        score = parsed.get("score", 0)
        if not isinstance(score, int):
            score = 0

        entry = {
            "source": s,
            "judge_output_raw": raw,
            "judge_output": parsed,
            "score": score
        }
        per_source.append(entry)

        if score > best_score:
            best_score = score
            best = entry

    return {
        "indicator": indicator_key,
        "sources": sources,
        "per_source_scores": per_source,
        "best_source": best,
        "doc_score": max(best_score, 0),
        # "judge_output": json.dumps(best_judge_output, ensure_ascii=False) if isinstance(best_judge_output, dict) else (
        #     best.get("judge_output_raw") if best else "")
    }