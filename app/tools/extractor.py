
# app/tools/extractor.py
# Kaam: page ka text Gemini ko dena aur structured items wapas lena.
import time

from google import genai
from google.genai import types

from app.core.config import settings
from app.schemas.extraction import ExtractionResult

# Bohat lambe page ko kaat dete hain (token/cost control)
MAX_CHARS = 30000

# Strict rules: yahi hallucination rokte hain
SYSTEM_PROMPT = """You extract structured facts about solar products from the text of a \
solar company's public web page.

Rules:
1. Use ONLY information explicitly written in the page text. Never guess or use outside knowledge.
2. If a field is not stated on the page, set it to null (or [] for specs). Never invent brands, models or capacities.
3. 'quote' must be copied EXACTLY from the page text (max 200 characters) and must contain the evidence for the item.
4. Extract everything advertised: panels, inverters, batteries, ready-made packages (e.g. a 5kW system), mounting, accessories, and also new or unusual items and features (EV chargers, monitoring apps, water pumps, smart meters, etc.).
5. Include services or solutions only if they are clearly described on the page.
6. Ignore navigation menus, 'contact us', footers, cookie notices and generic marketing text without a concrete product.
7. Ignore all prices. They are out of scope.
8. kind must be one of: product, feature, service, solution.
9. suggested_category: a short lowercase singular noun phrase such as 'hybrid inverter' or 'ev charger'. Use null if unsure.
10. confidence: 0.8 or more if clearly stated, 0.5 to 0.7 if somewhat ambiguous, below 0.5 if weak.
11. specs: extra details as key/value pairs, for example type=N-type or warranty=10 years.
12. If the page contains no solar products or offerings, return an empty items list.
"""


def extract_items(page_text: str, source_url: str):
    """Return (ExtractionResult, input_tokens, output_tokens)."""
    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY .env mein nahi hai")

    client = genai.Client(api_key=settings.gemini_api_key)
    prompt = f"SOURCE URL: {source_url}\n\nPAGE TEXT:\n{page_text[:MAX_CHARS]}"
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        temperature=0.0,                       # same page = same jawab
        response_mime_type="application/json",
        response_schema=ExtractionResult,      # Pydantic schema = structured output
    )

    last_err = None
    for attempt in range(3):                   # free tier par kabhi limit lagti hai: retry
        try:
            resp = client.models.generate_content(
                model=settings.gemini_model, contents=prompt, config=config
            )
            parsed = resp.parsed
            if not isinstance(parsed, ExtractionResult):
                parsed = ExtractionResult.model_validate_json(resp.text)
            usage = resp.usage_metadata
            return (parsed,
                    getattr(usage, "prompt_token_count", 0) or 0,
                    getattr(usage, "candidates_token_count", 0) or 0)
        except Exception as e:
            last_err = e
            code = getattr(e, "code", None)
            # Sirf rate limit (429) ya server error (5xx) par retry.
            # 404/400 jaise galti wale errors par foran ruk jao.
            if code not in (429, 500, 502, 503, 504):
                raise RuntimeError(f"Gemini error: {type(e).__name__}: {e}")
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"Gemini 3 baar fail: {type(last_err).__name__}: {last_err}")