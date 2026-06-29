# tools.py — detective skills: functions the agent can invoke

import json
import shutil
from pathlib import Path


# ─────────────────────────────────────────────
# PASSIVE SKILLS — observe without modifying
# ─────────────────────────────────────────────

# Files the detective must never see: the answer key and the saved verdict
# (verdetto.json contains the ground-truth culprit, so it would leak on re-runs).
HIDDEN_FILES = {"soluzione.json", "verdetto.json", "storia.txt"}


def list_files(case_dir):
    """
    Lists the files available in the case folder.
    Hides the answer key and verdict — the detective must not see them.
    Returns a human-readable string for the model.
    """
    folder = Path(case_dir)
    files  = [
        f.name for f in folder.iterdir()
        if f.is_file() and f.name not in HIDDEN_FILES
    ]
    return "Available files:\n" + "\n".join(f"- {f}" for f in sorted(files))


def read_file(case_dir, filename):
    """
    Reads and returns the content of a case file.
    Blocks access to soluzione.json.
    Hides mente and cosa_nasconde from sospettati.json.
    """
    if filename in ("soluzione.json", "verdetto.json"):
        return f"ERROR: you cannot read {filename}."

    path = Path(case_dir) / filename
    if not path.exists():
        return f"ERROR: file '{filename}' does not exist."

    text = path.read_text(encoding="utf-8")

    if filename == "sospettati.json":
        data = json.loads(text)
        for s in data:
            s.pop("mente", None)
            s.pop("cosa_nasconde", None)
            s.pop("sa_qualcosa", None)
            s.pop("alibi_verificabile", None)
        return json.dumps(data, indent=2, ensure_ascii=False)

    return text


def cross_check(case_dir, file_a, file_b):
    """
    Returns the content of two files together for comparison.
    Useful for finding contradictions between testimonies and clues.
    """
    content_a = read_file(case_dir, file_a)
    content_b = read_file(case_dir, file_b)

    return (
        f"=== {file_a} ===\n{content_a}\n\n"
        f"=== {file_b} ===\n{content_b}"
    )


# ─────────────────────────────────────────────
# ACTIVE SKILL — modifies the agent's context
# ─────────────────────────────────────────────

def take_note(case_dir, key, value, notes_file="note_detective.json"):
    """
    Writes or updates an entry in the detective's notebook.
    notes_file allows different detectives to have separate notebooks.
    Returns a confirmation string readable by the model.
    """
    path = Path(case_dir) / notes_file

    if path.exists():
        notes = json.loads(path.read_text(encoding="utf-8"))
    else:
        notes = {}

    notes[key] = value

    path.write_text(
        json.dumps(notes, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    return f"Note saved — {key}: {value}"


# ─────────────────────────────────────────────
# SESSION INITIALISATION
# ─────────────────────────────────────────────

def init_session(case_dir):
    """
    Initialises the investigation session for a case.
    Returns a dict with an empty history for each suspect.
    Used by both the human player and the detective agent.
    """
    suspects = json.loads(
        (Path(case_dir) / "sospettati.json").read_text(encoding="utf-8")
    )
    return {s["nome"]: [] for s in suspects}


# ─────────────────────────────────────────────
# INTERACTIVE SKILL (MULTI-AGENT) — calls another LLM
# ─────────────────────────────────────────────

def interrogate_suspect(case_dir, suspect_name, question, history=None):
    """
    Interrogates a suspect by calling suspect_agent.
    From the detective's perspective this is just a skill like any other:
    call a function, receive a string.
    Under the hood, another LLM impersonates the character.
    """
    import suspect_agent

    answer = suspect_agent.interrogate(case_dir, suspect_name, question, history)
    return f"RESPONSE FROM {suspect_name}: {answer}"


# ─────────────────────────────────────────────
# INFRASTRUCTURE TEST — python tools.py
# No LLM calls — local logic only.
# ─────────────────────────────────────────────

if __name__ == "__main__":

    # Create a temporary folder with dummy data
    test_dir = Path("test_tmp")
    test_dir.mkdir(exist_ok=True)

    # Minimal dummy JSON
    (test_dir / "sospettati.json").write_text(json.dumps([
        {"nome": "Mario Rossi", "ruolo": "maggiordomo", "alibi": "in cucina"}
    ], indent=2, ensure_ascii=False), encoding="utf-8")

    (test_dir / "indizi.json").write_text(json.dumps([
        {"oggetto": "coltello", "location": "biblioteca"},
        {"oggetto": "guanto",   "location": "giardino"},
    ], indent=2, ensure_ascii=False), encoding="utf-8")

    (test_dir / "testimonianze.json").write_text(json.dumps([
        {"testimone": "Gina", "dichiarazione": "ho sentito un urlo alle 22"}
    ], indent=2, ensure_ascii=False), encoding="utf-8")

    (test_dir / "soluzione.json").write_text(json.dumps(
        {"colpevole": "Mario Rossi"}, indent=2
    ), encoding="utf-8")

    print("--- list_files ---")
    print(list_files(test_dir))

    print("\n--- read_file: indizi.json ---")
    print(read_file(test_dir, "indizi.json"))

    print("\n--- read_file: soluzione.json (must be blocked) ---")
    print(read_file(test_dir, "soluzione.json"))

    print("\n--- cross_check: sospettati + testimonianze ---")
    print(cross_check(test_dir, "sospettati.json", "testimonianze.json"))

    print("\n--- take_note: two deductions ---")
    print(take_note(test_dir, "movente_principale", "eredità contesa"))
    print(take_note(test_dir, "sospettato_prioritario", "Mario Rossi"))

    print("\n--- re-read note_detective.json via read_file ---")
    print(read_file(test_dir, "note_detective.json"))

    print("\n--- interrogate_suspect (requires an existing case) ---")
    import config
    cases = list(config.CASES_DIR.glob("caso_*"))
    if not cases:
        print("No case available — run first: python writer_agent.py")
    else:
        real_case_dir = sorted(cases)[-1]
        real_suspects = json.loads(
            (real_case_dir / "sospettati.json").read_text(encoding="utf-8")
        )
        name = real_suspects[0]["nome"]
        print(interrogate_suspect(real_case_dir, name, "What do you know about the crime?"))

    # Cleanup
    shutil.rmtree(test_dir)
    print("\n--- test_tmp removed ---")
    print("PASS")
