from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

DB_PATH = BASE_DIR / "configm.db"
DATABASE_URL = f"sqlite+aiosqlite:///{DB_PATH}"

TEMPLATES_DIR = BASE_DIR / "templates" / "tpl"
GENERATED_DIR = BASE_DIR / "generated"
GENERATED_DIR.mkdir(exist_ok=True)
