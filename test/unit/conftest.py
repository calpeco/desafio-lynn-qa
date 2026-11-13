"""Unit tests: sem servidor, sem rede.

Rastreabilidade: @pytest.mark.trace("CONV-RN04", "R09") liga o teste a regras de negócio (specs/)
e riscos (docs/ESTRATEGIA_E_RISCOS.md). Os resultados (com as tags) vão para
reports/raw/unit-results.json, consumido por report.html e cobertura.html.
"""
import json
import os
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from qa_support.paths import RAW, bootstrap  # noqa: E402

bootstrap()
_RESULTS: list[dict] = []


def pytest_configure(config):
    config.addinivalue_line("markers", "trace(*tags): regras (ex.: CONV-RN04) e riscos (ex.: R09) cobertos")


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    if rep.when == "call" or (rep.when == "setup" and rep.outcome != "passed"):
        tags = sorted({t for m in item.iter_markers("trace") for t in m.args})
        _RESULTS.append({
            "id": item.nodeid, "file": item.location[0], "name": item.name,
            "status": "passed" if rep.passed else ("skipped" if rep.skipped else "failed"),
            "duration_s": round(rep.duration, 4), "tags": tags,
            "error": str(rep.longrepr)[:2000] if rep.failed else None,
        })


def pytest_sessionfinish(session, exitstatus):
    out = Path(os.getenv("LYNN_UNIT_RESULTS", RAW / "unit-results.json"))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"layer": "unit", "finished_at": time.time(), "tests": _RESULTS},
                              ensure_ascii=False, indent=1), encoding="utf-8")
