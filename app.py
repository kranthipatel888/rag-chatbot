import sys
import os

# Add src/ to path so all imports inside src/ resolve correctly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from src.main import app  # noqa: F401 — re-export for uvicorn
