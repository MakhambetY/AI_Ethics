import json
from pathlib import Path
from textwrap import indent


# In case if the MD creation failed, you can use this script to reconstruct the report
# from the existing `hai_l4_results.json` file.
RESULTS_PATH = Path("hai_l4_results.json")
OUTPUT_MD = Path("hai_l4_report.md")


def safe(s):
    if s is None:
        return ""
    if isinstance(s, str):
        return s
    return json.dumps(s, ensure_ascii=False)


def format_doc_section(model_name, mvals):
    lines = []
    doc_score = mvals.get("doc_score")
    doc_j = mvals.get("doc_judge_output") or {}
    doc_sources = mvals.get("doc_sources") or []

    lines.append(f"### {model_name}: Document-based evaluation\n")

    if doc_score is not None:
        lines.append(f"- **Document score**: {doc_score}")

    if doc_j:
        j_score = doc_j.get("score")
        src = doc_j.get("source_used") or {}
        rationale = doc_j.get("rationale") or ""
        evidence = doc_j.get("evidence") or []
        gaps = doc_j.get("gaps") or []

        if j_score is not None:
            lines.append(f"- **Judge score (docs)**: {j_score}")

        if src:
            title = src.get("title", "source")
            url = src.get("url", "")
            if url:
                lines.append(f"- **Primary source used**: [{title}]({url})")
            else:
                lines.append(f"- **Primary source used**: {title}")

        if rationale.strip():
            lines.append("\n**Judge rationale (docs):**")
            lines.append(indent(rationale.strip(), "> ") + "\n")

        if evidence:
            lines.append("**Key evidence excerpts:**")
            for ev in evidence:
                quote = (ev.get("quote_or_paraphrase") or "").strip()
                why = (ev.get("why_relevant") or "").strip()
                if quote:
                    lines.append(f"- *Evidence*: {quote}")
                if why:
                    lines.append(f"  - *Why relevant*: {why}")
            lines.append("")

        if gaps:
            lines.append("**Document gaps / missing elements:**")
            for g in gaps:
                lines.append(f"- {g}")
            lines.append("")

    if doc_sources:
        lines.append("**Document sources inspected / proposed:**")
        for s in doc_sources:
            title = s.get("title", "Source")
            url = s.get("url", "")
            stype = s.get("type", "")
            rationale = s.get("rationale", "")

            bullet = f"- **{title}**"
            if stype:
                bullet += f" ({stype})"
            if url:
                bullet += f": {url}"
            lines.append(bullet)
            if rationale:
                lines.append(f"  - Rationale: {rationale}")
        lines.append("")

    return lines


def format_behavior_section(model_name, mvals):
    lines = []
    prompt_score = mvals.get("prompt_score")
    behavior_tests = mvals.get("behavior_tests") or []

    lines.append(f"### {model_name}: Behavior-based evaluation\n")

    if prompt_score is not None:
        lines.append(f"- **Behavior / prompt score**: {prompt_score}\n")

    if not behavior_tests:
        lines.append("_No behavior tests recorded for this model._\n")
        return lines

    for t in behavior_tests:
        tid = t.get("test_id", "test")
        user_prompt = (t.get("user") or "").strip()
        output = (t.get("output") or "").strip()
        judge = t.get("judge") or {}
        j_score = judge.get("score")
        j_rat = (judge.get("rationale") or "").strip()

        lines.append(f"#### Test `{tid}`")
        if j_score is not None:
            lines.append(f"- **Judge score**: {j_score}")
        if user_prompt:
            lines.append("\n**User prompt:**")
            lines.append(indent(user_prompt, "> ") + "\n")
        if output:
            lines.append("**Model output (truncated if necessary):**")
            lines.append(indent(output, "> ") + "\n")
        if j_rat:
            lines.append("**Judge rationale:**")
            lines.append(indent(j_rat, "> ") + "\n")

    return lines


def main():
    raw = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))

    indicators = raw["results"] if isinstance(raw, dict) and "results" in raw else raw

    lines = []
    lines.append("# L4 Human–AI Interaction Benchmark – Level 4 Report\n")
    lines.append(
        "_This report was reconstructed from `hai_l4_results.json`. "
        "It summarizes document-based and behavior-based evaluations for each indicator and model._\n"
    )

    # ---------- GLOBAL SUMMARY TABLE ACROSS L4 ----------
    # Собираем имена моделей из первого блока
    all_models = set()
    for block in indicators:
        models = block.get("models") or {}
        all_models.update(models.keys())
    model_list = sorted(all_models)

    lines.append("## Global summary of L4 indicators\n")
    header = "| Indicator | " + " | ".join(
        [f"{m} doc" for m in model_list]
        + [f"{m} prompt" for m in model_list]
        + [f"{m} final" for m in model_list]
    ) + " |"
    sep = "|" + "---|" * (1 + 3 * len(model_list))

    lines.append(header)
    lines.append(sep)

    for block in indicators:
        ind = block.get("indicator", "UNKNOWN")
        models = block.get("models") or {}
        row = [ind]

        # doc scores
        for m in model_list:
            row.append(str(models.get(m, {}).get("doc_score", "")))
        # prompt scores
        for m in model_list:
            row.append(str(models.get(m, {}).get("prompt_score", "")))
        # final scores
        for m in model_list:
            row.append(str(models.get(m, {}).get("final_score", "")))

        lines.append("| " + " | ".join(row) + " |")

    lines.append("\n---\n")

    # ---------- PER-INDICATOR SECTIONS ----------
    for indicator_block in indicators:
        if not isinstance(indicator_block, dict):
            continue

        indicator_id = indicator_block.get("indicator", "UNKNOWN_INDICATOR")
        title = indicator_block.get("title", "")
        models = indicator_block.get("models") or {}

        lines.append(f"## {indicator_id}: {title}\n")

        # Summary table per indicator
        lines.append("### Summary scores by model\n")
        lines.append("| Model | Doc score | Behavior score | Final score |")
        lines.append("|-------|-----------|----------------|-------------|")

        for mname, mvals in models.items():
            doc_score = mvals.get("doc_score", "")
            prompt_score = mvals.get("prompt_score", "")
            final_score = mvals.get("final_score", "")
            lines.append(
                f"| {mname} | {doc_score} | {prompt_score} | {final_score} |"
            )
        lines.append("")

        # Detailed sections per model
        for mname, mvals in models.items():
            lines.append(f"### {indicator_id} – {mname}\n")
            final_score = mvals.get("final_score")
            if final_score is not None:
                lines.append(f"- **Overall indicator score for {mname}**: {final_score}\n")

            lines.extend(format_doc_section(mname, mvals))
            lines.extend(format_behavior_section(mname, mvals))

        lines.append("\n---\n")

    OUTPUT_MD.write_text("\n".join(safe(l) for l in lines), encoding="utf-8")
    print(f"Written Markdown report to {OUTPUT_MD.resolve()}")


if __name__ == "__main__":
    main()