# AI_Ethics — HAI L4 Evaluation Toolkit

A small evaluation toolkit for performing HAI L4-style safety assessments of language models. The repo includes pipelines for:
- Document-based evidence collection and scoring (doc pipeline)
- Prompt-based behavior testing (behavior pipeline)
- Aggregation and reporting into JSON and a Markdown report (aggregate_and_report)

The code is organized to (1) propose and fetch documentation sources, (2) run a judge model over documentation and model outputs, (3) run prompt-based test suites against target models, and (4) combine results into final scores.

This README describes how the pieces fit together, how to configure and run the pipelines, and how to extend them.

## Quick summary

- Main entrypoint: `run.py` — runs evaluation across configured L4 indicators and target models and writes:
  - `hai_l4_results.json` (structured results)
  - `hai_l4_report.md` (human-readable report)
- Doc pipeline: `doc_pipeline.py` (proposes sources, fetches & scores per-source evidence)
- Behavior pipeline: `behavior_pipeline.py` (runs prompt sets against models and judges outputs)
- Aggregation & reporting: `aggregate_and_report.py`
- Utilities: `doc_retrieval.py`, `clients.py`, and prompt templates in `prompts_doc.py` and `prompts_behavior.py`
- Configuration: `config.py` — target models, judges, indicators, and other knobs

## Repository layout

- aggregate_and_report.py — orchestrates combining doc + behavior scores and report generation
- behavior_pipeline.py — runs prompt-based tests and judges model outputs
- clients.py — thin wrappers around OpenAI / HuggingFace client initialization and helper completion functions
- config.py — API keys, target models, judges, indicators, and constants
- doc_pipeline.py — propose doc sources and run per-source doc scoring
- doc_retrieval.py — simple fetcher + HTML -> text + arXiv URL normalizer
- prompts_doc.py — prompt templates for doc search & doc scoring
- prompts_behavior.py — prompt sets (tests) and judging prompt builder
- run.py — high-level run script
- hai_l4_report.md — example generated report (included)
- README.md — this file

## Requirements

This project depends on Python 3.9+ and several common packages. Example install steps:

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install openai python-dotenv requests beautifulsoup4 tqdm
```

Note: the code also expects an OpenAI-compatible SDK for the "OpenAI" client used in `clients.py`. The repo uses the newer Responses/chat wrappers in places; adjust installed SDKs if needed (e.g., `openai` or official provider SDK). If you use Hugging Face Router via the same OpenAI-compatible client, ensure your HF API key is usable via that base URL.

## Configuration (.env)

Create a `.env` file in the project root with at least:

```text
OPENAI_API_KEY=sk-...
HF_API_KEY=hf_...
```

- `OPENAI_API_KEY` is required and used for judge models / Responses and chat completions.
- `HF_API_KEY` is required when the Hugging Face Router-style client is used for target model calls.

Important: these keys are required by `config.py`. The script raises if either is missing.

## How to run

1. Ensure your virtual environment is active and dependencies installed.
2. Populate `.env` with API keys.
3. Optionally edit `config.py`:
   - `TARGET_MODELS` — models you want to evaluate (provider + model name)
   - `JUDGES` — which provider/models to use for document and prompt judging
   - `L4_INDICATORS` — indicators you want to evaluate and their weights
4. Run the evaluation:

```bash
python run.py
```

This will call `run_all` which iterates configured indicators and target models and will write:
- `hai_l4_results.json`
- `hai_l4_report.md`

## Important implementation notes & caveats

- Doc search / scoring steps rely on an LLM judge using the Responses API and a `web_search` tool (see `doc_pipeline.propose_doc_sources` and `responses_complete` usage). To run the doc search end-to-end you need an environment where the judge model can access web search (and your account supports the Responses API + tools). If your environment does not support external web access for the judge model, propose/collect steps will likely fail or return non-URL outputs.
- `clients.py` contains helpers for two different call styles:
  - `chat_complete` — calls `client.chat.completions.create(...)` (for chat models)
  - `responses_complete` — calls `client.responses.create(...)` (for Responses-style models)
  Adjust these if your SDK differs or if using other providers.
- Some judge model names in `config.py` (e.g., `"gpt-5.1"`, `"gpt-4.1-mini"`) are placeholders. Use models available to your account or change them to supported names.
- The doc pipeline will try to fetch URLs (via requests + BeautifulSoup). Network fetch errors are caught and recorded as fetch failures in the evidence text.
- The behavior pipeline uses deterministic sampling (temperature=0.2) for model outputs; adjust as required.

## Extending and customizing

- Add / change indicators:
  - Edit `L4_INDICATORS` in `config.py` to add, remove, or tune indicators and weights.
- Add / change target models:
  - Modify `TARGET_MODELS` in `config.py`. Each entry must specify `provider` (`"openai"` or `"hf"`) and `model` string.
- Add / change judge models:
  - Modify `JUDGES` in `config.py`. There are two judge roles: `doc_judge` (used for document evidence scoring) and `prompt_judge` (used to judge prompt outputs).
- Add new behavior tests:
  - Edit `prompts_behavior.PROMPT_SETS` to add new test prompts or test suites per indicator. Each test item should include an `id` and `user` field at minimum.
- Add / change doc search prompt templates:
  - Edit `prompts_doc.py` to tune the doc search and scoring prompts.

## Outputs

- hai_l4_results.json — canonical full results (programmatic)
- hai_l4_report.md — human readable report with a summary table and per-indicator details
- The doc pipeline currently embeds fetched page text into judge prompts transiently; if you want persistent evidence storage, add a file write step in `doc_pipeline.collect_evidence_text` or elsewhere.

## Troubleshooting

- "OPENAI_API_KEY is not set": ensure `.env` exists and contains correct key; `python-dotenv` loads environment variables for `config.py`.
- Network timeouts while fetching documentation: adjust `HTTP_TIMEOUT` in `config.py`.
- Judge model returns non-JSON: aggregate parser tries to handle non-JSON but you may need to inspect raw `doc_judge_output` in the JSON results for details.
- If the Responses API usage is incompatible with your SDK version, adapt `clients.responses_complete` to your provider's SDK.

## Security & privacy

- Be careful with API keys — do not commit `.env` to source control.
- Fetching external URLs will send requests from your environment; ensure compliance with the remote site’s terms.

## Example development workflow

1. Add or tweak prompts in `prompts_behavior.py` or `prompts_doc.py`.
2. Add a new model to `config.py -> TARGET_MODELS`.
3. Run `python run.py`.
4. Inspect `hai_l4_results.json` and `hai_l4_report.md` for results and per-test outputs.

## License

No license file included. Add a `LICENSE` if you want to make the repo public under a specific license (e.g., MIT).

## Contact / Contributing

If you want to contribute or have questions, open an issue or pull request on the repository:
https://github.com/MakhambetY/AI_Ethics

If you need help adapting the code to your environment (different SDK versions, missing Responses API, or provider differences), open an issue describing your environment and the error.
