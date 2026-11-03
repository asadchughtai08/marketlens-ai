# app/agents/pipeline_graph.py
# MarketLens ka pehla LangGraph: crawl/paste -> extract (verify + categorize + save) -> finish.
# Nodes ke andar kaam purani files karti hain (app/services/pipeline.py).
# Graph ka kaam: unhein jodna aur "agla step kya ho" ka faisla karna.
from langgraph.graph import END, START, StateGraph

from app.agents.state import PipelineState
from app.db.base import SessionLocal
from app.db.models import Competitor
from app.services import pipeline


# ======================= NODES =======================
# Har node: state leta hai, state ka sirf badla hua hissa (dict) wapas karta hai.

def load_node(state: PipelineState) -> dict:
    """Company DB mein hai aur active hai? Nahi to error."""
    with SessionLocal() as db:
        comp = db.get(Competitor, state["competitor_id"])
        if comp is None:
            return {"outcome": "error", "message": "Company nahi mili",
                    "trace": ["load: company nahi mili"]}
        if not comp.active:
            return {"outcome": "error", "message": f"{comp.name} active nahi hai",
                    "trace": [f"load: {comp.name} inactive"]}
        return {"competitor_name": comp.name, "trace": [f"load: {comp.name}"]}


def crawl_node(state: PipelineState) -> dict:
    """robots.txt check, page fetch, hash compare, snapshot save."""
    with SessionLocal() as db:
        comp = db.get(Competitor, state["competitor_id"])
        res = pipeline.crawl_competitor(db, comp)
    return {"snapshot": res, "trace": [f"crawl: {res['status']}"]}


def paste_node(state: PipelineState) -> dict:
    """Manual paste fallback: insaan ka diya hua text snapshot banta hai."""
    with SessionLocal() as db:
        comp = db.get(Competitor, state["competitor_id"])
        res = pipeline.paste_snapshot(db, comp, state["paste_url"], state["paste_text"])
    return {"snapshot": res, "trace": [f"paste: {res['status']}"]}


def extract_node(state: PipelineState) -> dict:
    """Gemini se items, verifier, category matching, DB mein save (sab pipeline.extract_latest mein)."""
    with SessionLocal() as db:
        comp = db.get(Competitor, state["competitor_id"])
        try:
            res = pipeline.extract_latest(db, comp, state.get("force", False))
        except RuntimeError as e:
            # Gemini ka masla (key, model, limit): graph crash nahi hota, state mein likh deta hai
            res = {"status": "failed", "detail": str(e)}
    return {"extraction": res, "trace": [f"extract: {res['status']}"]}


def finish_node(state: PipelineState) -> dict:
    """Aakhri nateeja ek jagah: outcome aur insaan ke liye message."""
    if state.get("outcome") == "error":
        return {"trace": ["finish: error"]}

    snap = state.get("snapshot") or {}
    ext = state.get("extraction")

    if ext:
        if ext["status"] == "failed":
            outcome, msg = "extract_failed", ext.get("detail", "")
        elif ext["status"] == "extracted":
            outcome = "done"
            msg = f"{ext['items_found']} items nikle, saved: {ext['saved']}"
        else:
            outcome, msg = "done", f"extract: {ext['status']}"
    elif snap.get("status") == "unchanged":
        outcome, msg = "no_change", "Page nahi badla, Gemini ko call nahi gayi"
    else:
        outcome = "needs_manual_paste"
        msg = snap.get("detail", "Crawl nahi ho saka, manual paste use karo")

    return {"outcome": outcome, "message": msg, "trace": [f"finish: {outcome}"]}


# ======================= ROUTERS (conditional edges) =======================
# Yeh functions state dekh kar agle node ka NAAM (string) wapas karte hain.

def route_after_load(state: PipelineState) -> str:
    if state.get("outcome") == "error":
        return "finish"
    if state.get("paste_text"):
        return "paste"          # insaan ne text diya: crawler ki zaroorat nahi
    return "crawl"


def route_after_snapshot(state: PipelineState) -> str:
    # Sirf naya ya badla hua page Gemini tak jata hai. Baaqi sab seedha finish.
    if state["snapshot"]["status"] == "changed":
        return "extract"
    return "finish"


# ======================= GRAPH BANANA =======================
def build_graph():
    g = StateGraph(PipelineState)

    g.add_node("load", load_node)
    g.add_node("crawl", crawl_node)
    g.add_node("paste", paste_node)
    g.add_node("extract", extract_node)
    g.add_node("finish", finish_node)

    g.add_edge(START, "load")
    g.add_conditional_edges("load", route_after_load,
                            {"paste": "paste", "crawl": "crawl", "finish": "finish"})
    g.add_conditional_edges("crawl", route_after_snapshot,
                            {"extract": "extract", "finish": "finish"})
    g.add_conditional_edges("paste", route_after_snapshot,
                            {"extract": "extract", "finish": "finish"})
    g.add_edge("extract", "finish")
    g.add_edge("finish", END)

    return g.compile()


graph = build_graph()


def run_company(competitor_id: int, force: bool = False,
                paste_url: str | None = None, paste_text: str | None = None) -> dict:
    """Ek company par graph chalao, har node ki line print karo, aakhri state wapas karo."""
    init: dict = {"competitor_id": competitor_id, "force": force, "trace": []}
    if paste_text:
        init["paste_text"], init["paste_url"] = paste_text, paste_url or ""

    printed, final = 0, {}
    # stream_mode="values": har node ke baad poori state milti hai
    for state in graph.stream(init, stream_mode="values"):
        trace = state.get("trace", [])
        for line in trace[printed:]:
            print("  ->", line)
        printed = len(trace)
        final = state
    return final
