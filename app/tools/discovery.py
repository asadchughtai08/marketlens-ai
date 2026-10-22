        
"""
[ START: Trigger Discovery ]
                                     │
                                     ▼
                        /─────────────────────────\
                       /   Is BRAVE_API_KEY set    \
                      <     in settings layer?      >
                       \   (discovery_enabled())   /
                        \─────────────────────────/
                                     │
                        ┌────────────┴────────────┐
                     NO │                         │ YES
                        ▼                         ▼
             +──────────────────────+  +─────────────────────────+
             │  RAISE RUNTIMEERROR  │  │ httpx.get(Brave Search) │ ──► (Fetches top 'count'
             │  (Execution Blocked) │  +─────────────────────────+      live web results)
             +──────────────────────+            │
                                                 ▼
                                       +─────────────────────────+
                                       │   Load Existing Repo    │ ──► (Extracts 'known' domains
                                       │    (registry.load())    │      via registry.domain_of)
                                       +─────────────────────────+
                                                 │
                                                 ▼
                                     [ LOOP: Iterate Results ]
                                                 │
                                                 ▼
                                       +─────────────────────────+
                                       │  urlparse().netloc ...  │ ──► (Cleans and strips 'www.'
                                       │   Extract pure domain   │      from candidate URL)
                                       +─────────────────────────+
                                                 │
                                                 ▼
                                   /───────────────────────────\
                                  /  Is domain already known OR \
                                 <   does it match any entry in  >
                                  \       SKIP_DOMAINS?         /
                                   \───────────────────────────/
                                                 │
                                    ┌────────────┴────────────┐
                                 YES│                         │ NO
                                    ▼                         ▼
                             [ IGNORE TARGET ]       +───────────────────+
                                                     │ Clean Homepage Map│ ──► (Forces root domain format:
                                                     +───────────────────+      'https://{domain}')
                                                               │
                                                               ▼
                                                     +───────────────────+
                                                     │ Unique HashSet Map│ ──► (Removes intra-loop duplicate
                                                     │  Dictionary Sift  │      domains dynamically)
                                                     +───────────────────+
                                                               │
                                                               ▼
                                                   [ OUTPUT: Clean Candidate List ]

"""

# app/tools/discovery.py
# ==============================================================================
# Automated Market Discovery & Reconnaissance Engine
# ==============================================================================
# Yeh module internet se autonomously solar installations platforms aur EPC 
# providers ke web targets scout karta hai. Yeh engine direct core database mein
# changes nahi karta, balki ingestion pipeline ko optimal target pipelines deta hai.
# ==============================================================================

from urllib.parse import urlparse

import httpx

from app.core.config import settings
from app.tools import registry

# Enterprise Isolation Domain Blocklist:
# Yeh web layouts and directories single brand service companies nahi hain.
# System performance optimization aur noise mapping ko reduce karne ke liye in domains ko pass-through filter drop karega.
SKIP_DOMAINS = {
    "facebook.com",    # Social footprint nodes - Manual review streams ke liye isolated hain
    "instagram.com",   # Media social content arrays
    "youtube.com",     # Video broadcasting directories
    "olx.com.pk",      # Classified generic peer-to-peer marketplaces
    "daraz.pk",        # Generic consumer retail e-commerce networks
    "linkedin.com",    # Professional staffing networks
    "twitter.com",     # Microblogging social handles
    "x.com",           # Legacy microblogging network redirects
    "wikipedia.org",   # Informational open wiki knowledge bases
    "pakwheels.com"    # Auto-automotive inventory marketplace listings
}


def discovery_enabled() -> bool:
    """
    System Hardware and Token Access Gatekeeper:
    Checks if the external search intelligence token is successfully bound to system context.
    """
    return bool(settings.brave_api_key)


def discover(query: str = "solar company Islamabad", count: int = 15) -> list[dict]:
    """
    Scouts live ecosystem networks via search brokers and aggregates fresh candidate arrays.
    
    Arguments:
        query (str): Search parameter mapping matrix sent to target search grids.
        count (int): Volume parameter capping upper search tier data limit. Defaults to 15.
        
    Returns:
        list[dict]: Deduplicated and stripped target structural records array: [{'title', 'website', 'description'}]
    """
    # Guardrail Check 1: Token existence sequence confirmation window
    if not discovery_enabled():
        raise RuntimeError("Operational Crash: BRAVE_API_KEY environment structure me loaded nahi hai.")

    # Secure downstream execution block dispatching transaction layer
    resp = httpx.get(
        "https://api.search.brave.com/res/v1/web/search",
        params={"q": query, "count": count},
        headers={
            "X-Subscription-Token": settings.brave_api_key, # Explicit secure identification sequence
            "Accept": "application/json"                    # Direct structured payload configuration mapping request
        },
        timeout=15, # Network bottleneck protection parameter threshold
    )
    # Integrity Verification Check: Throws exception mapping logs if status code isn't 200 OK
    resp.raise_for_status()
    
    # Text data transformation parsing dictionary layer arrays
    results = resp.json().get("web", {}).get("results", [])

    # Memory Cache Load Strategy: Current registry database systems links compile mapping arrays.
    # Set comprehension use ho rhi hai fast internal domain verification matrix mapping processing lookup structures ke liye.
    known = {registry.domain_of(r["website"]) for r in registry.load()}
    
    candidates = [] # Temporary tracking bucket array for filtered provider candidates

    # Filtering Pipeline Architecture Routing Loop
    for item in results:
        # Step 1: Raw network URL paths normalization parsing operations layer
        domain = urlparse(item["url"]).netloc.lower().removeprefix("www.")
        
        # Step 2: Strict Exclusion Gatekeepers. 
        # Collision Check A: Kya company domain base repository arrays 'known' sets me pehle se localized hai?
        # Collision Check B: Kya candidate sub-path text validation mappings keyword blocklist filters se match hoti hain?
        if domain in known or any(domain.endswith(s) for s in SKIP_DOMAINS):
            continue
            
        # Step 3: Absolute Pathway Trimming Pattern.
        # Deep paths indices data points (jaise articles, profiles, contact-us forms) drop hote hain
        # taake validation check engine clean root target index mapping build kray.
        candidates.append({
            "title": item.get("title", "").strip(),
            "website": f"https://{domain}",                     # Root entry schema structure validation standard enforced
            "description": item.get("description", "").strip(),  # Strategic text anchor points mapping tracking block
        })
        
    # Step 4: Intra-Loop Deduplication Safe Layer.
    # Agar incoming bulk search streams me ek hi company multiple URLs index forms paths display kare,
    # toh Dictionary comprehension structure matching keys mapping ke through unique entries filter dynamic process complete hoga.
    unique = {c["website"]: c for c in candidates}
    
    # Structured transaction emission return block
    return list(unique.values())
