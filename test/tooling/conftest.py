import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from qa_support.paths import bootstrap  # noqa: E402

bootstrap()
