# app/core/config.py
# Saari settings ek hi jagah se padhi jati hain (.env file se).
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
"""
1. Sabse pehle: Ye code kyun chahiye?
Maan lo tumhara MarketLens AI ek AI agent hai jo market ki websites se information collect karta hai, usko analyze karta hai aur market research report banata hai.

Is project ko kuch settings chahiye hongi:
- Gemini API key, taake AI model use ho sake.
- Database location, taake collected information save ho.
- AI model ka naam.
- Website scraping ke darmiyan delay.
- Bot ki identification.
Agar tum ye settings har Python file mein alag-alag likhoge, to code manage karna mushkil ho jayega.

Isliye hum config.py bana rahe hain, jahan application ki settings ek hi jagah define hongi.
"""
# Project ka root folder: resolve() absolute path banata hai.
# __file__ = yeh file; parents[0]=core, parents[1]=app, parents[2]=project root.
BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    # Jo value .env mein na mile, yeh default use hogi.
    # Field ka naam .env ke variable se match hota hai (case-insensitive):
    # gemini_api_key  <-  GEMINI_API_KEY
    app_name: str = "MarketLens AI"
    environment: str = "dev"

    # SQLite database ek file hai: data/marketlens.db
    database_url: str = f"sqlite:///{BASE_DIR / 'data' / 'marketlens.db'}"

    # Gemini LLM
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash-lite"

    # Responsible scraping: har request ke beech delay aur bot ki pehchan
    crawl_delay_seconds: float = 3.0
    user_agent: str = "MarketLensBot/0.1"

    # .env file ka path batao; extra="ignore" = .env mein extra variable ho to error nahi
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore")

        # Optional discovery. Khali ho to discovery band rahegi.
    brave_api_key: str = ""

    # Competitors ki list ka path
    competitors_csv: str = str(BASE_DIR / "data" / "competitors.csv")


# Ek hi object poori app mein import hoga:
# from app.core.config import settings
settings = Settings()
