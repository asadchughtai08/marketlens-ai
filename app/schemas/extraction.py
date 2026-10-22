
# app/schemas/extraction.py
# Gemini se jo structured data chahiye, uska shape yahan define hai.
# Gemini isi schema ke mutabiq JSON deta hai, aur Pydantic usay validate karta hai.
# Note: fields mein default nahi rakhe (Gemini ke schema ke saath behtar chalta hai);
# "str | None" ka matlab hai ke value null ho sakti hai.
from typing import Literal

from pydantic import BaseModel


class SpecPair(BaseModel):
    """Ek khaasiyat, jaise key='type', value='N-type'."""
    key: str
    value: str


class ExtractedItem(BaseModel):
    # product / feature / service / solution
    kind: Literal["product", "feature", "service", "solution"]
    name: str                       # jaisa page par likha hai
    brand: str | None               # page par na ho to null
    model: str | None
    capacity: str | None            # "5kW", "550W" (jaisa likha hai)
    description: str | None
    specs: list[SpecPair]           # extra details (type, warranty, mode...)
    suggested_category: str | None  # agent ki raaye, jaise "hybrid inverter"
    quote: str                      # page se exact chhoti quote (saboot)
    confidence: float               # 0.0 se 1.0


class ExtractionResult(BaseModel):
    items: list[ExtractedItem]