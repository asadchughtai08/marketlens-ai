# scripts/migrate_claims.py
# Chalao: python -m scripts.migrate_claims
# claims table mein 3 naye columns add karta hai. Dobara chalane se koi nuksan nahi.
from sqlalchemy import inspect, text

from app.db import models  # noqa: F401
from app.db.base import engine

NEW_COLS = {"verdict": "VARCHAR(20)", "reasons": "JSON", "llm_confidence": "FLOAT"}

existing = {c["name"] for c in inspect(engine).get_columns("claims")}
with engine.begin() as conn:
    for name, sqltype in NEW_COLS.items():
        if name in existing:
            print("pehle se hai:", name)
        else:
            conn.execute(text(f"ALTER TABLE claims ADD COLUMN {name} {sqltype}"))
            print("add hua:", name)
            