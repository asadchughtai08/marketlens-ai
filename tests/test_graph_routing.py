# tests/test_graph_routing.py
# Chalao: python -m tests.test_graph_routing
# Router functions ka test: network ya Gemini ki zaroorat nahi.
from app.agents.pipeline_graph import route_after_load, route_after_snapshot

# 1. Error state seedha finish par
assert route_after_load({"outcome": "error"}) == "finish"
# 2. paste_text ho to paste node
assert route_after_load({"competitor_id": 1, "paste_text": "kuch text"}) == "paste"
# 3. warna crawl node
assert route_after_load({"competitor_id": 1}) == "crawl"
print("load router: 3 PASS")

# 4. Naya/badla page -> extract
assert route_after_snapshot({"snapshot": {"status": "changed"}}) == "extract"
# 5. Baaqi sab -> finish (Gemini ko call nahi)
for s in ("unchanged", "blocked", "failed", "manual_paste_required"):
    assert route_after_snapshot({"snapshot": {"status": s}}) == "finish", s
print("snapshot router: 5 PASS")
print("Sab tests pass")
