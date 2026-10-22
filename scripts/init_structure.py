# scripts/init_structure.py
# Yeh script project ke saare folders ek saath bana deti hai.
from pathlib import Path

# Jo folders chahiye unki list
FOLDERS = [
    "app/api",       # FastAPI routes (endpoints)
    "app/agents",    # LangGraph agents (baad ke phases mein)
    "app/tools",     # crawler, search, CSV tools
    "app/db",        # database models aur connection
    "app/schemas",   # Pydantic schemas (extraction ka structure)
    "app/core",      # config, logging jaisi shared cheezein
    "data",          # SQLite DB aur raw pages yahan save honge
    "docs",          # scope, architecture notes
    "tests",         # tests
]

for folder in FOLDERS:
    path = Path(folder)
    # parents=True: beech ke folders khud ban jayein
    # exist_ok=True: folder pehle se ho to error na aaye
    path.mkdir(parents=True, exist_ok=True)

    # Sirf app ke folders ko Python package banana hai.
    # __init__.py ki wajah se "from app.core.config import settings" chalta hai.
    if folder.startswith("app"):
        (path / "__init__.py").touch()

# Main app folder ko bhi package banao
Path("app/__init__.py").touch()

# Khali data/ folder Git mein track karne ke liye .gitkeep
Path("data/.gitkeep").touch()

print("Folders ready")
