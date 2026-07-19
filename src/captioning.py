import base64
import os
from pathlib import Path

from openai import OpenAI

_client = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


def caption_image(image_path: str) -> str:
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    ext = Path(image_path).suffix.lstrip(".").lower()
    mime = "image/png" if ext == "png" else "image/jpeg"
    response = _get_client().chat.completions.create(
        model="gpt-4o-mini",
        messages=[{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                {"type": "text", "text": "Describe this image concisely for search purposes. Focus on what is shown, any visible text, UI elements, or scene details."}
            ]
        }],
        max_tokens=200
    )
    return response.choices[0].message.content.strip()
