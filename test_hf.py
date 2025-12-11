from dotenv import load_dotenv
from openai import OpenAI
import os

load_dotenv()

HF_API_KEY = os.getenv("HF_API_KEY")
print("HF_API_KEY starts with:", HF_API_KEY[:10])

client = OpenAI(
    api_key=HF_API_KEY,
    base_url="https://router.huggingface.co/v1",
)

resp = client.chat.completions.create(
    model="meta-llama/Llama-3.1-8B-Instruct",
    messages=[{"role": "user", "content": "Hi from HF router"},],
    max_tokens=50,
)

print(resp.choices[0].message.content)