# app/tools/robots.py
# Responsible scraping engine: Kisi bhi target page ko fetch karne se pehle robots.txt rules verify karna zaroori hai.
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx

from app.core.config import settings


def is_allowed(url: str) -> tuple[bool, str]:
    """
    Verifies if the configured User-Agent is allowed to crawl the given URL based on the domain's robots.txt.
    
    Return:
        tuple[bool, str]: (allowed_status, reason_or_error_message).
        Shak ya network issue ho to safety ke liye hamesha False return hoga (Conservative Execution Pattern).
    """
    # URL parsing se root domain aur scheme extract ki ja rahi hai taake robots.txt ka direct path ban sake
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

    try:
        # App configuration se standard production User-Agent header pass kiya ja raha hai
        resp = httpx.get(
            robots_url,
            headers={"User-Agent": settings.user_agent},
            timeout=10,
            follow_redirects=True, # Redirects (HTTP to HTTPS) handle karna zaroori hai root domain verification ke liye
        )
    except httpx.HTTPError as e:
        # Agar connection timeout, DNS failure ya koi bhi network exception aaye toh pipeline ko block karo
        return False, f"robots.txt fetch failed: {type(e).__name__}"

    # CRITICAL STATUS CHECK GATES:
    
    # 404 Status: Matlab target server par robots.txt rule-book exist nahi karti. standard protocol ke mutabiq full access allowed hai.
    if resp.status_code == 404:
        return True, "no robots.txt (allowed)"
        
    # 401/403 Status: Server ne authentication ya authorization deny ki hai. Isko strictly block assume kiya jayega.
    if resp.status_code in (401, 403):
        return False, f"robots.txt returned {resp.status_code}"
        
    # 5xx Server Errors ya koi bhi custom status code: Ehtiyat ke taur par crawling execute nahi ki jayega.
    if resp.status_code != 200:
        return False, f"robots.txt status {resp.status_code}"

    # PARSING ENGINE LOGIC:
    # Standard Python library ka parser use ho raha hai text formatting rules read karne ke liye
    parser = RobotFileParser()
    parser.parse(resp.text.splitlines())
    
    # Hamare system ke unique User-Agent identifier ke mutabiq target sub-path checker logic
    ok = parser.can_fetch(settings.user_agent, url)
    return ok, "allowed by robots.txt" if ok else "disallowed by robots.txt"
