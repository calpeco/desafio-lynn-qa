"""Converte a saída JSON nativa do behave (-f json) para o formato Cucumber JSON.

Por que converter em vez de usar um formatter de terceiros: o formato do behave é estável e
nativo; o Cucumber JSON é o formato que ferramentas de mercado (Jenkins, Xray, Allure,
multiple-cucumber-html-reporter, ReportPortal) entendem. Também mescla vários shards (execução
paralela) num único arquivo e anexa os screenshots de UI como embeddings.
"""
from __future__ import annotations

import base64
import json
import re
from pathlib import Path

from .naming import slug

NS = 1_000_000_000  # Cucumber JSON usa duração em nanossegundos


def _tag_list(tags, line):
    return [{"name": t if t.startswith("@") else f"@{t}", "line": line} for t in tags or []]


def _split_location(location: str) -> tuple[str, int]:
    path, _, line = (location or ":0").rpartition(":")
    return path, int(line) if line.isdigit() else 0


def _cuke_id(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _status(raw) -> str:
    status = (raw or "skipped") if isinstance(raw, str) else getattr(raw, "name", "skipped")
    return {"untested": "skipped", "error": "failed", "hook_error": "failed"}.get(status, status)


def _error_text(err) -> str | None:
    if not err:
        return None
    return "\n".join(err) if isinstance(err, list) else str(err)


def _relative(location: str) -> str:
    """Caminhos absolutos da máquina de execução viram relativos ao repositório."""
    root = str(Path.cwd()) + "/"
    return location[len(root):] if location.startswith(root) else location


def convert_step(step: dict) -> dict:
    _, line = _split_location(step.get("location", ""))
    result = step.get("result") or {}
    out = {
        "keyword": step.get("keyword", "").strip() + " ",
        "name": step.get("name", ""),
        "line": line,
        "match": {"location": _relative((step.get("match") or {}).get("location", ""))},
        "result": {"status": _status(result.get("status")),
                   "duration": int(float(result.get("duration") or 0) * NS)},
    }
    if err := _error_text(result.get("error_message")):
        out["result"]["error_message"] = err
    if table := step.get("table"):
        out["rows"] = [{"cells": list(table.get("headings", []))}] + [{"cells": list(r)} for r in table.get("rows", [])]
    if step.get("text"):
        out["doc_string"] = {"value": step["text"], "content_type": ""}
    return out


def convert_feature(feature: dict, screenshots: dict[str, Path] | None = None) -> dict:
    uri, fline = _split_location(feature.get("location", ""))
    fid = _cuke_id(feature.get("name", uri))
    elements = []
    for el in feature.get("elements", []):
        if el.get("type") == "background":
            continue  # o behave já repete os passos do Contexto dentro de cada cenário, com resultado
        _, line = _split_location(el.get("location", ""))
        steps = [convert_step(s) for s in el.get("steps", [])]
        shot = (screenshots or {}).get(slug(el.get("name", "")))
        if shot and steps:
            steps[-1].setdefault("embeddings", []).append(
                {"mime_type": "image/png", "data": base64.b64encode(shot.read_bytes()).decode()})
        elements.append({
            "id": f"{fid};{_cuke_id(el.get('name', ''))}", "keyword": el.get("keyword", "Cenário"),
            "name": el.get("name", ""), "description": "", "line": line, "type": "scenario",
            "tags": _tag_list(el.get("tags"), line - 1), "steps": steps,
        })
    desc = feature.get("description") or []
    return {"uri": uri, "id": fid, "keyword": feature.get("keyword", "Funcionalidade"),
            "name": feature.get("name", ""), "description": "\n".join(desc) if isinstance(desc, list) else desc,
            "line": fline, "tags": _tag_list(feature.get("tags"), max(fline - 1, 1)), "elements": elements}


def index_screenshots(dirs: list[Path]) -> dict[str, Path]:
    """screenshot 'ok__<slug>.png' ou 'FALHOU__<slug>.png' -> {slug: caminho}"""
    found = {}
    for d in dirs:
        for png in Path(d).rglob("*.png"):
            found[png.stem.split("__", 1)[-1]] = png
    return found


def merge_behave_json(files: list[Path], screenshot_dirs: list[Path] | None = None) -> list[dict]:
    """Mescla vários JSON do behave (um por shard) num Cucumber JSON único, agrupando por feature."""
    shots = index_screenshots(screenshot_dirs or [])
    by_uri: dict[str, dict] = {}
    for f in sorted(files):
        text = Path(f).read_text(encoding="utf-8").strip()
        if not text:
            continue
        for feature in json.loads(text):
            converted = convert_feature(feature, shots)
            if converted["uri"] in by_uri:
                by_uri[converted["uri"]]["elements"] += converted["elements"]
            else:
                by_uri[converted["uri"]] = converted
    return sorted(by_uri.values(), key=lambda f: f["uri"])


def scenario_status(element: dict) -> str:
    statuses = [s["result"]["status"] for s in element["steps"]]
    if any(s in ("failed", "undefined") for s in statuses):
        return "failed"
    if statuses and all(s == "passed" for s in statuses):
        return "passed"
    return "skipped"
