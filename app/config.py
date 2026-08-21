from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
BOOKS_DIR = DATA_DIR / "library" / "books"
STATIC_DIR = ROOT / "static"
ALLOWED_EXTENSIONS = {".pdf", ".epub"}
MAX_UPLOAD_BYTES = 500 * 1024 * 1024
CHUNK_TARGET_WORDS = 900
CHUNK_MAX_WORDS = 1400

for path in (DATA_DIR, BOOKS_DIR):
    path.mkdir(parents=True, exist_ok=True)
