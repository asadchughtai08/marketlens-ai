# app/main.py
from fastapi import FastAPI
from app.core.config import settings

# FastAPI app object; title /docs page par dikhega
app = FastAPI(title=settings.app_name)


@app.get("/health")
def health():
    """Check karta hai ke app chal rahi hai aur config sahi load hua."""
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.environment,
        # Asli key kabhi return nahi karte, sirf true/false
        "gemini_key_loaded": bool(settings.gemini_api_key),
    }
