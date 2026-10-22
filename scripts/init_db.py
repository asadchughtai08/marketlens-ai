# scripts/init_db.py
# ------------------------------------------------------------------
# Chalao: python -m scripts.init_db
# Kaam: models.py ki saari tables database mein bana deta hai.
# Table pehle se ho to usay chhoota nahi (safe hai, dobara chala sakte ho).
# ------------------------------------------------------------------

# Yeh import zaroori hai, chahe models directly use na ho rahe hon.
# Import hone par hi saari table classes Base.metadata mein register hoti hain.
# Isay hata diya to create_all() ko pata hi nahi chalega ke kaun si tables banani hain.
from app.db import models  # noqa: F401
from app.db.base import Base, engine

# create_all: jo tables maujood nahi, sirf wohi banata hai
Base.metadata.create_all(engine)

# Tables ke naam print: competitors, snapshots, categories...
print("Tables ready:", ", ".join(Base.metadata.tables))