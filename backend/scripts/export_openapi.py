import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from main import app


BACKEND_ROOT.joinpath("openapi.json").write_text(
    json.dumps(app.openapi(), indent=2), encoding="utf-8"
)
