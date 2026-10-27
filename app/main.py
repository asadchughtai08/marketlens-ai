# app/main.py
# FastAPI app ka entry point.
from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from app.api.routes import router
from app.core.config import settings

app = FastAPI(title=settings.app_name)

# Yeh line saare endpoints (competitors, crawl, paste, extract, review) jodti hai
app.include_router(router)


@app.get("/", include_in_schema=False)
def root():
    """Home page kholne par seedha /docs par bhej do."""
    return RedirectResponse(url="/docs")


@app.get("/health")
def health():
    """Check karta hai ke app chal rahi hai aur config load hua."""
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.environment,
        # Asli key kabhi return nahi karte, sirf true/false
        "gemini_key_loaded": bool(settings.gemini_api_key),
    }