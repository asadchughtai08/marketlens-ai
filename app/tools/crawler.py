
# app/tools/crawler.py
# Kaam: Crawl4AI se ek public page fetch karke markdown text deta hai.
# robots.txt check yahan nahi, caller (scripts/crawl.py) pehle karta hai.
import asyncio

from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig

from app.core.config import settings


async def _fetch(url: str) -> tuple[str | None, str]:
    # headless = browser ki window nahi khulti (RAM bhi kam lagti hai)
    # user_agent = website ko bot ki pehchan (naam + email) dikhata hai
    browser_cfg = BrowserConfig(
        headless=True,
        user_agent=settings.user_agent,
        verbose=False,
    )
    # BYPASS = purani cached copy nahi, har baar taaza page
    # page_timeout milliseconds mein (30 second)
    run_cfg = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, page_timeout=30000)

    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        result = await crawler.arun(url=url, config=run_cfg)

    if not result.success:
        return None, result.error_message or "unknown error"
    # markdown = page ka saaf text (menu/script hata kar)
    return str(result.markdown), ""


def fetch_page(url: str) -> tuple[str | None, str]:
    """Return (text, error). Kamyab ho to error khali, fail ho to text None."""
    try:
        return asyncio.run(_fetch(url))
    except Exception as e:  # network, timeout, browser ka koi masla
        return None, f"{type(e).__name__}: {e}"
