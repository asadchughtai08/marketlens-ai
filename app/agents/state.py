# app/agents/state.py
# Graph ki "state": woh dictionary jo har node ke beech safar karti hai.
# Har node sirf apna hissa wapas karta hai, LangGraph usay state mein merge kar deta hai.
import operator
from typing import Annotated, TypedDict


class PipelineState(TypedDict, total=False):
    # --- Input (graph shuru karte waqt diya jata hai) ---
    competitor_id: int
    force: bool            # True = pehle extract ho chuka ho tab bhi dobara
    paste_url: str         # Manual paste fallback: page ka URL
    paste_text: str        # Manual paste fallback: page ka text

    # --- Beech ke nodes ka kaam ---
    competitor_name: str
    snapshot: dict         # crawl ya paste ka result: {"status": "changed", ...}
    extraction: dict       # Gemini + verifier + store ka result

    # --- Aakhri nateeja (finish node bharta hai) ---
    outcome: str           # done / no_change / needs_manual_paste / extract_failed / error
    message: str

    # Reducer: har node ki line is list mein jurti jati hai (purani nahi mitati).
    # operator.add ka matlab: nayi list = purani list + node ki list.
    trace: Annotated[list[str], operator.add]
    