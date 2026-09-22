"""Shared locations for document indexing and retrieval."""
from pathlib import Path
from threading import RLock

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "Raw Data"
CHROMA_DIR = ROOT_DIR / "chroma_db"
COLLECTION_NAME = "manual_vectors"
# Serialize indexing requests within the API process.
INDEX_LOCK = RLock()
