import os
import re
import sys
import json
import shutil
import importlib
import subprocess
from pathlib import Path

from flask import Flask, Response, jsonify, request, send_from_directory
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent.parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(ENV_PATH)

SRC_DIR = BASE_DIR / "src"
sys.path.insert(0, str(SRC_DIR))
import config
import tools

WEB_DIR = BASE_DIR / "web"

app = Flask(__name__, static_folder=str(WEB_DIR), static_url_path="/web")

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[mKGHFJABCDnsuhl]")

def strip_ansi(text):
    return ANSI_RE.sub("", text)

# Unit Separator — marks a live-streaming event line emitted by live.py.
STREAM_SENTINEL = "\x1f"

def sse_subprocess(cmd, cwd):
    env = {**os.environ, "PYTHONUNBUFFERED": "1", "NO_COLOR": "1",
           "FORCE_COLOR": "0", "COLUMNS": "120",
           "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1",
           "TERM": "dumb", "MM_STREAM": "1"}
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, encoding="utf-8", cwd=str(cwd), env=env)
    for raw in proc.stdout:
        # Live token-stream events are sentinel-framed JSON — forward as-is.
        if raw and raw[0] == STREAM_SENTINEL:
            payload = raw.rstrip("\n")[1:]
            try:
                obj = json.loads(payload)
            except json.JSONDecodeError:
                continue
            yield f"data: {json.dumps(obj)}\n\n"
            continue
        line = strip_ansi(raw.rstrip())
        if line:
            yield f"data: {json.dumps({'type': 'log', 'text': line})}\n\n"
    proc.wait()
    yield f"data: {json.dumps({'type': 'done', 'code': proc.returncode})}\n\n"

SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}

# Human game sessions: {case_name: histories_dict}
_sessions: dict = {}

def get_session(case_name):
    if case_name not in _sessions:
        _sessions[case_name] = tools.init_session(config.CASES_DIR / case_name)
    return _sessions[case_name]


# ── General routes ────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory(str(WEB_DIR), "index.html")


@app.route("/api/config")
def get_config():
    return jsonify({
        "provider":        config.LLM_PROVIDER,
        "writer_model":    config.WRITER_MODEL,
        "detective_model": config.DETECTIVE_MODEL,
        "suspect_model":   config.SUSPECT_MODEL,
    })


# ── Settings — manage .env from the UI ────────────────────────────────

def _upsert_env(env_path, updates):
    """Update or insert env vars in .env, preserving comments and order."""
    lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
    seen  = set()
    out   = []
    pat   = re.compile(r"^([A-Z_][A-Z0-9_]*)=(.*)$")
    for line in lines:
        m = pat.match(line.lstrip())
        if m and m.group(1) in updates:
            key = m.group(1)
            seen.add(key)
            out.append(f"{key}={updates[key]}")
        else:
            out.append(line)
    for key, val in updates.items():
        if key in seen:
            continue
        out.append(f"{key}={val}")
    env_path.write_text("\n".join(out) + "\n", encoding="utf-8")


def _reload_config():
    load_dotenv(ENV_PATH, override=True)
    importlib.reload(config)


def _mask(value):
    if not value:
        return ""
    if len(value) <= 4:
        return "•" * len(value)
    return "•" * (len(value) - 4) + value[-4:]


@app.route("/api/settings", methods=["GET"])
def get_settings():
    default_model = os.getenv("DEFAULT_MODEL", "")
    return jsonify({
        "provider":            config.LLM_PROVIDER,
        "base_url":            config.LLM_BASE_URL,
        "api_key_set":         bool(config.LLM_API_KEY),
        "api_key_preview":     _mask(config.LLM_API_KEY),
        "default_model":       default_model,
        "writer_model":        os.getenv("WRITER_MODEL", ""),
        "detective_model":     os.getenv("DETECTIVE_MODEL", ""),
        "suspect_model":       os.getenv("SUSPECT_MODEL", ""),
        "writer_model_eff":    config.WRITER_MODEL,
        "detective_model_eff": config.DETECTIVE_MODEL,
        "suspect_model_eff":   config.SUSPECT_MODEL,
        "backend_url":         config.BACKEND_URL,
        "backend_key_set":     bool(config.BACKEND_KEY),
        "backend_key_preview": _mask(config.BACKEND_KEY),
        "env_path":            str(ENV_PATH),
        "env_exists":          ENV_PATH.exists(),
    })


@app.route("/api/settings", methods=["POST"])
def save_settings():
    body = request.get_json(silent=True) or {}
    mapping = {
        "provider":        "LLM_PROVIDER",
        "base_url":        "LLM_BASE_URL",
        "api_key":         "LLM_API_KEY",
        "default_model":   "DEFAULT_MODEL",
        "writer_model":    "WRITER_MODEL",
        "detective_model": "DETECTIVE_MODEL",
        "suspect_model":   "SUSPECT_MODEL",
        "backend_url":     "BACKEND_URL",
        "backend_key":     "BACKEND_KEY",
    }
    updates = {env_key: body[k] for k, env_key in mapping.items() if k in body and body[k] is not None}
    _upsert_env(ENV_PATH, updates)
    _reload_config()
    return jsonify({"ok": True})


@app.route("/api/cases")
def list_cases():
    cases = []
    for d in sorted(config.CASES_DIR.iterdir()):
        if not (d.is_dir() and d.name.startswith("caso_")):
            continue
        title = d.name
        try:
            title = json.loads((d / "caso.json").read_text(encoding="utf-8")).get("titolo", d.name)
        except Exception:
            pass
        # "solved" means an investigation produced a verdict — NOT that the
        # answer key (soluzione.json, always present) exists.
        cases.append({"name": d.name, "title": title, "solved": (d / "verdetto.json").exists()})
    return jsonify(cases)


@app.route("/api/cases/new", methods=["POST"])
def new_case():
    brief     = request.get_json(silent=True) or {}
    brief_arg = json.dumps(brief)
    def generate():
        yield from sse_subprocess(
            [sys.executable, str(SRC_DIR / "writer_agent.py"), "--brief", brief_arg], BASE_DIR)
        cases = sorted(config.CASES_DIR.glob("caso_*"))
        if cases:
            name, title = cases[-1].name, cases[-1].name
            try:
                title = json.loads((cases[-1] / "caso.json").read_text(encoding="utf-8")).get("titolo", name)
            except Exception:
                pass
            yield f"data: {json.dumps({'type': 'new_case', 'name': name, 'title': title})}\n\n"
    return Response(generate(), mimetype="text/event-stream", headers=SSE_HEADERS)


@app.route("/api/cases/<case_name>", methods=["DELETE"])
def delete_case(case_name):
    case_dir = config.CASES_DIR / case_name
    if not case_dir.exists():
        return jsonify({"error": "case not found"}), 404
    shutil.rmtree(case_dir)
    _sessions.pop(case_name, None)
    return jsonify({"ok": True})


@app.route("/api/cases/<case_name>/run")
def run_case(case_name):
    case_dir = config.CASES_DIR / case_name
    if not case_dir.exists():
        return jsonify({"error": "case not found"}), 404
    def generate():
        yield from sse_subprocess(
            [sys.executable, str(SRC_DIR / "orchestrator_multi.py"), str(case_dir)], BASE_DIR)
        verdict = case_dir / "verdetto.json"
        if verdict.exists():
            yield f"data: {json.dumps({'type': 'verdict', 'data': json.loads(verdict.read_text(encoding='utf-8'))})}\n\n"
    return Response(generate(), mimetype="text/event-stream", headers=SSE_HEADERS)


@app.route("/api/quit", methods=["POST"])
def quit_app():
    import threading
    threading.Timer(0.3, lambda: os._exit(0)).start()
    return jsonify({"ok": True})


@app.route("/api/cases/<case_name>/result")
def case_result(case_name):
    sol = config.CASES_DIR / case_name / "soluzione.json"
    if not sol.exists():
        return jsonify({"error": "no result available"}), 404
    return jsonify(json.loads(sol.read_text(encoding="utf-8")))


# ── Human game mode routes ─────────────────────────────────────────────

@app.route("/api/cases/<case_name>/game/start")
def game_start(case_name):
    """Start/resume a game session: returns story, suspects, notes."""
    case_dir = config.CASES_DIR / case_name
    if not case_dir.exists():
        return jsonify({"error": "case not found"}), 404
    histories  = get_session(case_name)
    story      = (case_dir / "storia.txt").read_text(encoding="utf-8")
    suspects   = json.loads((case_dir / "sospettati.json").read_text(encoding="utf-8"))
    notes_path = case_dir / "note_detective.json"
    notes      = json.loads(notes_path.read_text(encoding="utf-8")) if notes_path.exists() else {}
    return jsonify({
        "storia":    story,
        "sospettati": [{"nome": s["nome"], "eta": s["eta"], "ruolo": s["ruolo"]} for s in suspects],
        "note":      notes,
        "files":     sorted(f.name for f in case_dir.iterdir()
                            if f.is_file() and f.name not in tools.HIDDEN_FILES),
    })


@app.route("/api/cases/<case_name>/game/action", methods=["POST"])
def game_action(case_name):
    """Execute a game action and return the result."""
    case_dir = config.CASES_DIR / case_name
    if not case_dir.exists():
        return jsonify({"error": "case not found"}), 404
    histories = get_session(case_name)
    data      = request.get_json(silent=True) or {}
    action    = data.get("action")

    if action == "list_files":
        result = tools.list_files(case_dir)
        return jsonify({"result": result})

    elif action == "read_file":
        result = tools.read_file(case_dir, data.get("filename", ""))
        return jsonify({"result": result})

    elif action == "cross_check":
        result = tools.cross_check(case_dir, data.get("file_a", ""), data.get("file_b", ""))
        return jsonify({"result": result})

    elif action == "take_note":
        result     = tools.take_note(case_dir, data.get("key", ""), data.get("value", ""))
        notes_path = case_dir / "note_detective.json"
        notes      = json.loads(notes_path.read_text(encoding="utf-8")) if notes_path.exists() else {}
        return jsonify({"result": result, "note": notes})

    elif action == "interrogate":
        name = data.get("suspect", "")
        key  = next((k for k in histories if k.lower() == name.lower()), None)
        if key is None:
            return jsonify({"result": f"Suspect '{name}' not found."})
        result = tools.interrogate_suspect(case_dir, key, data.get("question", ""), histories[key])
        text   = result.replace(f"RESPONSE FROM {key}: ", "")
        return jsonify({"result": text, "suspect": key})

    elif action == "accuse":
        accused    = data.get("accusato", "")
        motivation = data.get("motivazione", "")
        sol        = json.loads((case_dir / "soluzione.json").read_text(encoding="utf-8"))
        correct    = accused.strip().lower() == sol["colpevole"].strip().lower()
        # Persist the verdict so the case is marked as solved in the UI.
        (case_dir / "verdetto.json").write_text(json.dumps({
            "mode":           "human",
            "colpevole":      accused,
            "motivazione":    motivation,
            "corretto":       correct,
            "colpevole_vero": sol["colpevole"],
            "spiegazione":    sol["spiegazione"],
        }, indent=2, ensure_ascii=False), encoding="utf-8")
        return jsonify({
            "result":        "verdict",
            "accusato":      accused,
            "motivazione":   motivation,
            "colpevole_vero": sol["colpevole"],
            "spiegazione":   sol["spiegazione"],
            "corretto":      correct,
        })

    return jsonify({"error": f"unknown action '{action}'"}), 400
