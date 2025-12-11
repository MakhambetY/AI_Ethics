from dotenv import load_dotenv
from openai import OpenAI
import os

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is not set in .env")

client = OpenAI(api_key=OPENAI_API_KEY)

prompt = f"""
You are an AI ethics auditor performing ADA-style document-based evidence collection.

Target system: DeepSeek
Indicator: "L4_HAI_AnthropomorphismDisclosure" — Anthropomorphism & capability disclaimers are clear and non-deceptive

Task:
1) Propose up to 8 HIGH-PRIORITY documentation sources to check:
   - official model card / system card
   - usage policy / acceptable use
   - safety or alignment notes
   - official Hugging Face model page
   - papers or technical reports linked from official pages
2) For each source, provide:
   - canonical title
   - expected URL (if known)
   - why it is relevant to this indicator

Rules:
- Do NOT speculate about compliance.
- Do NOT invent URLs.
- If you provide a URL, it MUST be a real URL you found via web search.
- Do NOT speculate about compliance.
- Focus on where explicit statements would likely live.
- Output JSON with fields:
  {{
    "sources": [
      {{
        "title": "...",
        "type": "model_card|policy|paper|hf_page|blog|other",
        "url": "(only one valid URL per source without extra text)",
        "rationale": "..."
      }}
    ]
  }}
"""

resp = client.responses.create(
    model="gpt-5.1",
    input=prompt,
    tools=[
        { "type": "web_search", "external_web_access": True }
    ],
    tool_choice="required",
)

print("Output:", resp.output_text)