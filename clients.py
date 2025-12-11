# clients.py
from openai import OpenAI
from config import OPENAI_API_KEY, HF_API_KEY

def get_openai_client():
    return OpenAI(api_key=OPENAI_API_KEY)

def get_hf_client():
    return OpenAI(
        base_url="https://router.huggingface.co/v1",
        api_key=HF_API_KEY
    )

def get_client(provider: str):
    if provider == "openai":
        return get_openai_client()
    if provider == "hf":
        return get_hf_client()
    raise ValueError(f"Unknown provider: {provider}")

def chat_complete(client: OpenAI, model: str, messages, temperature=0.0, max_tokens=800):
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_completion_tokens=max_tokens,
        )
        return resp.choices[0].message.content
    except Exception as e:
        # Fallback for providers/models that don't support max_completion_tokens
        msg = str(e)
        if "max_completion_tokens" in msg or "Unsupported parameter" in msg:
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return resp.choices[0].message.content
        raise

# clients.py
from typing import Optional, List, Dict, Any

def responses_complete(
    client: OpenAI,
    model: str,
    input_text: str,
    tools: Optional[List[Dict[str, Any]]] = None,
    tool_choice: str = "auto",
    temperature: float = 0.0,
    max_output_tokens: int = 900,
    reasoning_effort: Optional[str] = None,
):
    """
    Thin wrapper over Responses API.
    We keep it simple: pass a single input string.
    For reasoning models you may optionally set reasoning_effort: "low|medium|high".
    """
    kwargs = dict(
        model=model,
        input=input_text,
        tool_choice=tool_choice,
    )

    if tools:
        kwargs["tools"] = tools

    # # Optional knobs (safe default)
    # # Some SDK versions/models may ignore these.
    # if reasoning_effort:
    #     kwargs["reasoning"] = {"effort": reasoning_effort}
    #
    # # Temperature for Responses is supported by most models; if not, it will be ignored.
    # kwargs["temperature"] = temperature
    #
    # # Conservative token cap
    # kwargs["max_output_tokens"] = max_output_tokens

    resp = client.responses.create(**kwargs)
    return resp.output_text