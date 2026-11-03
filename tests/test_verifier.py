# tests/test_verifier.py
# Chalao: python -m tests.test_verifier
# Verifier ke 5 cases: sahi, ghalat brand, jhooti quote, sahi capacity, ghalat capacity.
from app.tools.verifier import verify

PAGE = ("Our 5kW Residential Package includes 10 x Longi Hi-MO 6 N-type 550W panels, "
        "a Growatt SPH 5000 hybrid inverter and a 5kWh lithium battery. "
        "10 year panel warranty.")

# 1. Sab kuch sahi
r = verify("Growatt SPH 5000 hybrid inverter", "Growatt", "SPH 5000", None,
           "a Growatt SPH 5000 hybrid inverter", PAGE, 0.9)
assert r.verdict == "verified" and r.review_status == "approved", r
print("1 PASS verified:", r.reasons)

# 2. Brand page par nahi (LLM ne gadha)
r = verify("Growatt SPH 5000 hybrid inverter", "Huawei", "SPH 5000", None,
           "a Growatt SPH 5000 hybrid inverter", PAGE, 0.9)
assert r.verdict == "weak" and "brand_not_on_page" in r.reasons and r.confidence <= 0.6, r
print("2 PASS weak brand:", r.reasons)

# 3. Jhooti quote (hallucination)
r = verify("Tesla Powerwall 3", "Tesla", None, None,
           "Tesla Powerwall 3 home battery", PAGE, 0.95)
assert r.verdict == "unsupported" and r.confidence <= 0.2, r
print("3 PASS unsupported:", r.reasons)

# 4. Sahi capacity
r = verify("5kW Residential Package", None, None, "5kW",
           "Our 5kW Residential Package includes", PAGE, 0.9)
assert r.verdict == "verified", r
print("4 PASS capacity ok:", r.reasons)

# 5. Ghalat capacity: "15kW" page par nahi hai (5kW se confuse nahi hona chahiye)
r = verify("5kW Residential Package", None, None, "15kW",
           "Our 5kW Residential Package includes", PAGE, 0.9)
assert r.verdict == "weak" and "capacity_not_on_page" in r.reasons, r
print("5 PASS wrong capacity:", r.reasons)

print("Sab 5 tests pass")
