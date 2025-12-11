# doc_retrieval.py
import requests
from bs4 import BeautifulSoup
from config import HTTP_TIMEOUT, USER_AGENT

import re

_ARXIV_ID_RE = re.compile(r'(\d{4}\.\d{4,5}(?:v\d+)?)')

def normalize_arxiv_url(url: str) -> str:
    if "arxiv.org" not in url:
        return url

    # Explicit /abs/<id>
    m = re.search(r'arxiv\.org/abs/(\d{4}\.\d{4,5}(?:v\d+)?)', url)
    if m:
        return f"https://arxiv.org/pdf/{m.group(1)}.pdf"

    # Any path containing an arXiv id
    m = _ARXIV_ID_RE.search(url)
    if m:
        return f"https://arxiv.org/pdf/{m.group(1)}.pdf"

    return url

def fetch_url(url: str) -> str:
    headers = {"User-Agent": USER_AGENT}
    r = requests.get(url, headers=headers, timeout=HTTP_TIMEOUT)
    r.raise_for_status()
    return r.text

def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    # remove scripts/styles
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text()
    # basic cleanup
    lines = [ln.strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln]
    return "\n".join(lines)

def truncate(text: str, max_chars: int = 12000) -> str:
    return text[:max_chars]