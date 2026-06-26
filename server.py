# server.py — web server for Murder Mystery
#
# Usage:
#   python server.py
#   python server.py --port 8080
#
# Endpoints:
#   GET  /                        → UI (web/index.html)
#   GET  /api/cases               → list available cases
#   GET  /api/cases/new           → SSE: generate a new case
#   GET  /api/cases/<name>/run    → SSE: run the multi-detective pipeline
#   GET  /api/cases/<name>/result → solution (if available)

import os
import re
import sys
import json
import argparse
import subprocess
from pathlib import Path

from flask import Flask, Response, jsonify, send_from_directory
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

import config

BASE_DIR = Path(__file__).parent
WEB_DIR  = BASE_DIR / "web"

app = Flask(__name__, static_folder=str(WEB_DIR), static_url_path="/web")

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[mKGHFJABCDnsuhl]")

def strip_ansi(text):
    return ANSI_RE.sub("", text)

def sse_subprocess(cmd, cwd):
    """Starts a subprocess and yields each line as an SSE event."""
    env = {
        **os.environ,
        "PYTHONUNBUFFERED": "1",
        "NO_COLOR":         "1",
        "FORCE_COLOR":      "0",
        "COLUMNS":          "120",
    }
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        cwd=str(cwd),
        env=env,
    )
    for raw in proc.stdout:
        line = strip_ansi(raw.rstrip())
        if line:
            yield f"data: {json.dumps({'type': 'log', 'text': line})}\n\n"
    proc.wait()
    yield f"data: {json.dumps({'type': 'done', 'code': proc.returncode})}\n\n"


# ── Routes ────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory(str(WEB_DIR), "index.html")


@app.route("/api/cases")
def list_cases():
    cases = []
    for d in sorted(config.CASES_DIR.iterdir()):
        if not (d.is_dir() and d.name.startswith("caso_")):
            continue
        title = d.name
        try:
            data  = json.loads((d / "caso.json").read_text(encoding="utf-8"))
            title = data.get("titolo", d.name)
        except Exception:
            pass
        cases.append({
            "name":   d.name,
            "title":  title,
            "solved": (d / "soluzione.json").exists(),
        })
    return jsonify(cases)


@app.route("/api/cases/new")
def new_case():
    def generate():
        yield from sse_subprocess([sys.executable, "writer_agent.py"], BASE_DIR)
        cases = sorted(config.CASES_DIR.glob("caso_*"))
        if cases:
            name  = cases[-1].name
            title = name
            try:
                data  = json.loads((cases[-1] / "caso.json").read_text(encoding="utf-8"))
                title = data.get("titolo", name)
            except Exception:
                pass
            yield f"data: {json.dumps({'type': 'new_case', 'name': name, 'title': title})}\n\n"

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.route("/api/cases/<case_name>/run")
def run_case(case_name):
    case_dir = config.CASES_DIR / case_name
    if not case_dir.exists():
        return jsonify({"error": "case not found"}), 404

    def generate():
        yield from sse_subprocess(
            [sys.executable, "orchestrator_multi.py", str(case_dir)],
            BASE_DIR,
        )
        sol = case_dir / "soluzione.json"
        if sol.exists():
            data = json.loads(sol.read_text(encoding="utf-8"))
            yield f"data: {json.dumps({'type': 'verdict', 'data': data})}\n\n"

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.route("/api/cases/<case_name>/result")
def case_result(case_name):
    sol = config.CASES_DIR / case_name / "soluzione.json"
    if not sol.exists():
        return jsonify({"error": "no result available"}), 404
    return jsonify(json.loads(sol.read_text(encoding="utf-8")))


# ── Entry point ───────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=os.getenv("WEB_HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.getenv("WEB_PORT", 7860)))
    args = parser.parse_args()
    print(f"Murder Mystery UI → http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=False, threaded=True)
