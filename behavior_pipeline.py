# behavior_pipeline.py
import json
from typing import Dict, List

from tqdm import tqdm

from clients import get_client, chat_complete
from config import JUDGES, TARGET_MODELS, L4_INDICATORS
from prompts_behavior import PROMPT_SETS, behavior_judge_prompt

def run_model_prompt(model_cfg: Dict, user_text: str) -> str:
    client = get_client(model_cfg["provider"])
    model = model_cfg["model"]
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": user_text}
    ]
    return chat_complete(client, model, messages, temperature=0.2, max_tokens=400)

def judge_behavior(indicator_key: str, user_text: str, model_output: str) -> Dict:
    judge_cfg = JUDGES["prompt_judge"]
    client = get_client(judge_cfg["provider"])

    prompt = behavior_judge_prompt(
        indicator_key,
        L4_INDICATORS[indicator_key]["title"],
        user_text,
        model_output
    )

    content = chat_complete(
        client,
        judge_cfg["model"],
        messages=[{"role": "system", "content": "Return valid JSON only."},
                  {"role": "user", "content": prompt}],
        temperature=0.0,
        max_tokens=300
    )
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {"score": None, "rationale": f"Non-JSON judge output: {content}"}

def score_behavior_for_model(model_name: str, model_cfg: Dict, indicator_key: str) -> Dict:
    tests = PROMPT_SETS.get(indicator_key, [])
    results = []

    # progress over tests
    for t in tqdm(tests, desc=f"[helper] {indicator_key} | {model_name}", leave=False):
        out = run_model_prompt(model_cfg, t["user"])
        j = judge_behavior(indicator_key, t["user"], out)
        results.append({
            "test_id": t["id"],
            "user": t["user"],
            "output": out,
            "judge": j
        })

    scores = [r["judge"].get("score") for r in results if isinstance(r["judge"].get("score"), int)]
    avg = sum(scores) / len(scores) if scores else 0.0

    return {
        "model_name": model_name,
        "indicator": indicator_key,
        "tests": results,
        "prompt_score": avg
    }

def score_behavior_all(indicator_key: str) -> List[Dict]:
    out = []
    # progress over models
    for mname, mcfg in tqdm(TARGET_MODELS.items(), desc=f"[helper models] {indicator_key}", leave=False):
        out.append(score_behavior_for_model(mname, mcfg, indicator_key))
    return out